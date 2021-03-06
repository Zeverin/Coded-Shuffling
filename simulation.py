############################################################################
# Copyright 2016 Albin Severinson                                          #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License");          #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#     http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
############################################################################

'''This module is used to simulate the performance of coded distributed
computing schemes. It connects the solver and evaluation packages and the
complexity module.

'''

import os
import math
import logging
import datetime
import numpy as np
import pandas as pd
import scipy.stats
import complexity
import model
import stats

from functools import partial
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import Pool
from solvers import Solver
from model import SystemParameters
from assignments.sparse import SparseAssignment
from evaluation import AssignmentEvaluator

# create a process and thread pool executor for this module. these are used to
# increase computing and I/O throughput, respectively.
# there is a bug when using more than 1 worker:
# https://bitbucket.org/pypy/pypy/issues/2530/segfault-with-threadpool-pandas-when
process_pool = Pool(processes=12)
thread_executor = ThreadPoolExecutor(max_workers=1)

def completion_cdf(x, distributions=None, probabilities=None):
    '''CDF of the computational delay.

    Args:

    distributions: dict with mapping the number of servers needed to
    decode to the corresponding probability distribution.

    probabilities: dict mapping the number of servers needed to decode
    to the probability of needing the number of servers.

    '''
    assert isinstance(distributions, dict)
    assert isinstance(probabilities, dict)
    assert len(distributions) == len(probabilities)
    result = 0
    for servers in distributions:
        server_probability = probabilities[servers]
        a, loc, scale = distributions[servers]
        t = scipy.stats.gamma.cdf(x, a, loc, scale)
        if np.isnan(t):
            return 1
        result += server_probability*t
    return result

def infer_completion_cdf(parameters=None,
                         order_values=None,
                         order_probabilities=None,
                         num_samples=1000,
                         map_complexity_fun=None,
                         encode_complexity_fun=None,
                         reduce_complexity_fun=None):
    '''Return a CDF of the computational delay inferred from simulations.

    '''


    distributions = dict()
    probabilities = dict()
    samples = np.zeros(num_samples)
    if encode_complexity_fun:
        encoding_distribution = stats.ShiftexpOrder(
            parameter=encode_complexity_fun(parameters) / parameters.num_servers,
            total=parameters.num_servers,
            order=parameters.num_servers,
        )

    if reduce_complexity_fun:
        reduce_distribution = stats.ShiftexpOrder(
            parameter=reduce_complexity_fun(parameters) / parameters.q,
            total=parameters.q,
            order=parameters.q,
        )

    # for each unique number of servers, fit a gamma distribution
    minv, maxv = 0, 0
    for order, probability in zip(order_values, order_probabilities):
        samples[:] = 0
        if encode_complexity_fun:
            samples += encoding_distribution.sample(n=num_samples)

        if reduce_complexity_fun:
            samples += reduce_distribution.sample(n=num_samples)

        map_distribution = stats.ShiftexpOrder(
            parameter=map_complexity_fun(parameters),
            total=parameters.num_servers,
            order=order,
        )
        samples += map_distribution.sample(n=num_samples)

        # normalize
        samples /= parameters.num_source_rows * parameters.num_outputs

        # store the minimum and maximum values
        minv = min(minv, samples.min())
        maxv = max(maxv, samples.max())

        # fit a distribution and store the order probability
        distributions[order] = scipy.stats.gamma.fit(samples, loc=samples.min())
        probabilities[order] = probability

    return partial(
        completion_cdf,
        distributions=distributions,
        probabilities=probabilities,
    ), minv, maxv

def cdf_from_samples(samples, loc=None, n=1):
    '''infer the cdf from samples. assumes the samples are gamma distributed.

    The sum of exponentially distributed random variables is gamma
    distributed. fit a CDF accordingly.

    returns: lambda expression cdf(t) that gives the probability of the
    computation completing before time t.

    '''
    a, loc, scale = 0, 0, 0
    for _ in range(n):
        np.random.shuffle(samples)
        # a0, loc0, scale0 = scipy.stats.gamma.fit(samples)
        a0, loc0, scale0 = scipy.stats.gamma.fit(samples, loc=samples.min())
        a += a0
        loc += loc0
        scale += scale0

    a /= n
    loc /= n
    scale /= n
    logging.info("found Gamma distribution parameters a={}, loc={}, scale={}".format(a, loc, scale))
    return lambda t: scipy.stats.gamma.cdf(t, a, loc=loc, scale=scale)

def delay_samples(dataframe, num_samples=100000, parameters=None, map_complexity_fun=None,
                  encode_complexity_fun=None, reduce_complexity_fun=None,
                  order_values=None, order_probabilities=None):
    '''find the delay distribution via Monte Carlo simulations

    args:

    dataframe: dataframe of performance samples. used to infer the PDF over the
    number of servers needed to decode.

    num_sample: number of samples to take.

    parameters: system parameters.

    map_complexity_fun: function that takes parameters as its single argument
    and returns the complexity of the map phase.

    encode_complexity_fun: function that takes parameters as its single
    argument and returns the complexity of the encode phase. set to False if
    not applicable.

    reduce_complexity_fun: function that takes parameters as its single
    argument and returns the complexity of the reduce phase. set to False if
    not applicable.

    order_values: array-like with the possible number of servers needed to
    decode. inferred from the dataframe if None.

    order_probabilities: array-like with probabilities of needing the
    corresponding number of servers in order_values. inferred from the
    dataframe if None.

    returns: array or samples drawn from the overall delay distribution.

    '''
    assert num_samples > 0 and num_samples % 1 == 0
    assert isinstance(parameters, SystemParameters)
    assert callable(map_complexity_fun)
    assert callable(encode_complexity_fun) or encode_complexity_fun is False
    assert callable(reduce_complexity_fun) or reduce_complexity_fun is False
    if order_values is None:
        assert order_probabilities is None
    else:
        assert order_probabilities is not None
        assert len(order_values) == len(order_probabilities)
    if order_probabilities is None:
        assert order_values is None
    else:
        assert order_values is not None
        assert len(order_values) == len(order_probabilities)

    samples = np.zeros(num_samples)

    # first, sample the encoding and reduce delay
    if encode_complexity_fun:
        encoding_distribution = stats.ShiftexpOrder(
            parameter=encode_complexity_fun(parameters) / parameters.num_servers,
            total=parameters.num_servers,
            order=parameters.num_servers,
        )
        samples += encoding_distribution.sample(n=num_samples)
    if reduce_complexity_fun:
        reduce_distribution = stats.ShiftexpOrder(
            parameter=reduce_complexity_fun(parameters) / parameters.q,
            total=parameters.q,
            order=parameters.q,
        )
        samples += reduce_distribution.sample(n=num_samples)

    # next, get the empiric PDF of the number of servers we need to wait for in
    # the map phase (if it wasn't provided)
    if order_values is None:
        order_counts = dataframe['servers'].value_counts(normalize=True)
        order_values = order_counts.index
        order_probabilities = order_counts.values

    # sample the distribution for each order. the number of samples is given by
    # the probability of needing to wait for that number of servers in the map
    # phase.
    i = 0
    a = 0
    for order, probability in zip(order_values, order_probabilities):
        map_distribution = stats.ShiftexpOrder(
            parameter=map_complexity_fun(parameters),
            total=parameters.num_servers,
            order=order,
        )
        a += num_samples*probability
        num_order_samples = min(
            num_samples-i,
            int(round(a)),
        )
        if num_order_samples <= 0:
            continue
        samples[i:i+num_order_samples] += map_distribution.sample(n=num_order_samples)
        i += num_order_samples
        a -= num_order_samples

    # normalize the values
    samples /= parameters.num_source_rows * parameters.num_outputs

    return samples

def set_load(dataframe, strategy='best'):
    '''compute the communication load for simulated results.

    args:

    strategy: data shuffling strategy. L1, L2, or best. see the paper for
    details.

    '''

    # the load may have already been computed by other means
    if 'load' in dataframe:
        return dataframe

    # otherwise, compute the load depending on what shuffling strategy is used.
    load_1 = dataframe['unicast_load_1'] + dataframe['multicast_load_1']
    load_2 = dataframe['unicast_load_2'] + dataframe['multicast_load_2']
    load_best = pd.concat([load_1, load_2], axis=1).min(axis=1)
    if 'strategy' == 'L1':
        dataframe['load'] = load_1
    elif strategy == 'L2':
        dataframe['load'] = load_2
    elif strategy == 'best':
        dataframe['load'] = load_best
    return dataframe

def flatten_dataframes(dataframe_iter):
    '''flatten an iterable of dataframes by creating a new dataframe where the i-th
    row is the average of all columns from the i-th dataframe in the list.

    '''
    return pd.DataFrame([
        {column:dataframe[column].mean() for column in dataframe}
        for dataframe in dataframe_iter
    ])

def recompute_map_delay(dataframe, parameters, scale, map_complexity_fun):
    '''Recompute the delay of the map phase for a given ratio between the
    shift and tail scale of the shifted exponential (see
    stats.order_mean_shiftexp())

    '''
    parameter = map_complexity_fun(parameters)
    dataframe['delay'] = np.fromiter(
        (parameters.computational_delay(
            q=q,
            parameter=parameter,
            scale=scale)
         for q in dataframe['servers']),
        dtype=float,
    )
    return dataframe

def simulate_parameter_list(parameter_list=None,
                            tail_scale=None,
                            simulate_fun=None,
                            map_complexity_fun=None,
                            encode_delay_fun=None,
                            reduce_delay_fun=None):
    '''Run simulations for a list of parameters.

    args

    parameter_list: list of SystemParameters for which to run simulations.

    shift_tail_ratio: the ratio between the shift and tail scale of
    the shifted exponential (see stats.order_mean_shiftexp()). if
    None, the delay of the map phase in the dataframe loaded from disk
    is used. otherwise the delay of the map phase is recomputed using
    the given ratio.

    simulation_fun: function to apply to each SystemParameters object. use
    functools.partial to set the arguments to the simulate() function below and
    provide it as this argument.

    map_complexity_fun: function that takes parameters as its single argument
    and returns the complexity of the map phase.

    encode_delay_fun: function that takes parameters as its single argument and
    returns the delay of the encode phase. set to False if not applicable.

    reduce_delay_fun: function that takes parameters as its single argument and
    returns the delay of the reduce phase. set to False if not applicable.

    '''
    assert parameter_list is not None
    assert callable(simulate_fun), simulate_fun
    assert callable(map_complexity_fun), map_complexity_fun
    assert callable(encode_delay_fun) or encode_delay_fun is False, encode_delay_fun
    assert callable(reduce_delay_fun) or reduce_delay_fun is False, reduce_delay_fun
    logging.info('Running simulations for %d parameters.', len(parameter_list))

    # run simulations for all parameters. we use a thread pool as most of the
    # time is spent waiting for I/O when loading cached results from disk.
    dataframe_iter = thread_executor.map(simulate_fun, parameter_list)

    # recompute the delay of the map phase if a ratio is given
    if tail_scale is not None:
        dataframe_iter = (
            recompute_map_delay(
                dataframe,
                parameters,
                tail_scale,
                map_complexity_fun,
            )
            for (dataframe, parameters) in zip(dataframe_iter, parameter_list)
        )

    # flatten the iterable of dataframes into a single dataframe
    dataframe = flatten_dataframes(dataframe_iter)

    # set the communication load
    dataframe = set_load(dataframe)

    # scale the map phase delay by its complexity
    if tail_scale is None:
        map_complexity = np.fromiter(
            (map_complexity_fun(parameters) for parameters in parameter_list),
            dtype=float,
        )
        dataframe['delay'] *= map_complexity

    #  compute the encoding and reduce (decoding) delay
    if encode_delay_fun:
        dataframe['encode'] = np.fromiter(
            (encode_delay_fun(parameters) for parameters in parameter_list),
            dtype=float,
        )
    elif 'encode' not in dataframe:
        raise ValueError('dataframe must contain encoding delay if encode_delay_fun is False')
    if reduce_delay_fun:
        dataframe['reduce'] = np.fromiter(
            (reduce_delay_fun(parameters) for parameters in parameter_list),
            dtype=float,
        )
    elif 'reduce' not in dataframe:
        raise ValueError('dataframe must contain reduce delay if reduce_delay_fun is False')

    # finally, compute the overall delay
    dataframe['overall_delay'] = dataframe['delay'] + dataframe['encode'] + dataframe['reduce']

    return dataframe

def parameter_sample(i, parameters=None, parameter_eval=None):
    assert i >= 0 and i % 1 == 0
    assert parameters is not None
    assert parameter_eval is not None
    result = parameter_eval(parameters)
    if isinstance(result, dict):
        result = pd.DataFrame([result])
    result['assignment'] = i * np.ones(len(result))
    return result

def assignment_sample(i, parameters=None, solver=None,
                      assignment_eval=None, assignment_type=None):
    assert i >= 0 and i % 1 == 0
    assert parameters is not None
    assert solver is not None
    assert assignment_eval is not None
    assert assignment_type is not None

    # use the solver to find an assignment
    assignment = solver.solve(
        parameters,
        assignment_type=assignment_type
    )

    # make sure the assignment is valid
    if not assignment.is_valid():
        logging.error('Assignment invalid for parameters: %s.', str(parameters))
        return pd.DataFrame()

    # evaluate the performance of the assignment
    result = assignment_eval.evaluate(parameters, assignment)

    if isinstance(result, dict):
        result = pd.DataFrame([result])
    result['assignment'] = i * np.ones(len(result))
    return result

def simulate(parameters, directory='./results/', rerun=False, samples=None,
             solver=None, assignment_eval=None, parameter_eval=None,
             assignment_type=None):
    '''simulate a set of system parameters. results are cached on disk.

    the simulator allows for running two kinds of simulations:
        - assigments: create assignments using a solver and evaluate them.
        - parameters: evaluate the performance of a parameters object
          without creating an assignment. useful for analytic performance measures.

    which method is used depends on which on solver, assignment_eval and
    parameter_eval is provided.

    args:

    parameters: SystemParameters to simulate.

    directory: directory to store results in.

    rerun: rerun simulations even if there are results on disk.

    samples: number of samples to simulate.

    solver: assignment solver, i.e., a method that returns a good assignment
    matrix. must be None if a parameter_eval method is provided.

    assignment_eval: method that evaluates the performance of an assignment
    returned by the solver. should be an AssignmentEvaluator object. must be
    provided if a solver is given.

    parameter_eval: method that takes a SystemParameters object and returns a
    DataFrame with its performance. must be None if a solver or assignment_eval
    is provided.

    assignment_type: there are several options for how the assignment matrix is
    stored. this argument sets that type. defaults to SparseAssignment.

    returns: DataFrame with performance samples for all assignments.

    '''
    logging.info('Running simulations for %s: %s',
                  directory, parameters.identifier())
    assert isinstance(parameters, SystemParameters)
    assert isinstance(directory, str)
    assert samples > 0
    if solver is None:
        assert assignment_eval is None
        assert parameter_eval is not None
    else:
        assert assignment_eval is not None
    if assignment_eval is None:
        assert solver is None
        assert parameter_eval is not None
    else:
        assert solver is not None
    if parameter_eval is None:
        assert solver is not None
        assert assignment_eval is not None
    else:
        assert solver is None
        assert assignment_eval is None

    # there are several options for how the assignment matrix is stored.
    # default to a sparse assignment type
    if assignment_type is None:
        assignment_type = SparseAssignment

    if not os.path.exists(directory):
        os.makedirs(directory)

    # first, attempt to return a cached result
    filename = os.path.join(directory, parameters.identifier() + '.csv')
    if not rerun:
        try:
            dataframe = pd.read_csv(filename)

            # add the system parameters to the dataframe
            for key, value in parameters.asdict().items():
                dataframe[key] = value

            return dataframe
        except FileNotFoundError:
            pass

    best_assignment = None
    best_avg_load = math.inf
    best_avg_delay = math.inf

    # select the simulation type
    if solver is None:
        f = partial(
            parameter_sample,
            parameters=parameters,
            parameter_eval=parameter_eval,
        )
    else:
        f = partial(
            assignment_sample,
            parameters=parameters,
            solver=solver,
            assignment_eval=assignment_eval,
            assignment_type=assignment_type,
        )

    # run simulations in parallel using a process pool
    # with Pool(processes=8) as pool:
    results = map(f, range(samples))

    # concatenate the DataFrames and write the result to disk
    dataframe = pd.concat(results)
    dataframe.to_csv(filename)

    # add the system parameters to the dataframe
    for key, value in parameters.asdict().items():
        dataframe[key] = value

    return dataframe
