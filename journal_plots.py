'''Script to create the plots for the journal paper

'''

import logging
import complexity
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import stats
import rateless
import plot
import deadline
import simulation

from functools import partial
from plot import get_parameters_size, load_delay_plot
from plot import get_parameters_partitioning, get_parameters_partitioning_2
from plot import get_parameters_N
from simulation import Simulator
from evaluation import analytic
from evaluation.binsearch import SampleEvaluator
from solvers.randomsolver import RandomSolver
from solvers.heuristicsolver import HeuristicSolver
from solvers.assignmentloader import AssignmentLoader
from assignments.cached import CachedAssignment

def deadline_plots():
    '''deadline plots'''

    # Setup the evaluators
    sample_100 = SampleEvaluator(num_samples=100)
    sample_1000 = SampleEvaluator(num_samples=1000)

    # Get parameters
    partition_parameters = get_parameters_partitioning_2()
    size_parameters = plot.get_parameters_size_2()[0:-4] # -2

    # Setup the simulators
    heuristic_sim = Simulator(
        solver=HeuristicSolver(),
        assignment_eval=sample_1000,
        directory='./results/Heuristic/',
    )

    random_sim = Simulator(
        solver=RandomSolver(),
        assignments=100,
        assignment_eval=sample_100,
        directory='./results/Random_100/',
    )

    hybrid_sim = Simulator(
        solver=AssignmentLoader(directory='./results/Hybrid/assignments/'),
        assignments=1,
        assignment_eval=sample_1000,
        assignment_type=CachedAssignment,
        directory='./results/Hybrid/'
    )

    uncoded_sim = Simulator(
        solver=None,
        assignments=1,
        parameter_eval=analytic.uncoded_performance,
        directory='./results/Uncoded/',
    )

    cmapred_sim = Simulator(
        solver=None,
        assignments=1,
        parameter_eval=analytic.cmapred_performance,
        directory='./results/Cmapred/',
    )

    stragglerc_sim = Simulator(
        solver=None,
        assignments=1,
        parameter_eval=analytic.stragglerc_performance,
        directory='./results/Stragglerc/',
    )

    rs_sim = Simulator(
        solver=None,
        assignments=1,
        parameter_eval=analytic.mds_performance,
        directory='./results/RS/',
    )

    # lt code simulations are handled using the rateless module. the simulation
    # framework differs from that for the BDC and analytic.
    # lt_partitions = [rateless.evaluate(
    #     partition_parameters[0],
    #     target_overhead=1.3,
    #     target_failure_probability=1e-1,
    # )] * len(partition_parameters)
    # lt_partitions = pd.DataFrame(lt_partitions)
    # lt_partitions['partitions'] = [parameters.num_partitions
    #                                for parameters in partition_parameters]

    # lt_size = rateless.evaluate_parameter_list(
    #     size_parameters,
    #     target_overhead=1.3,
    #     target_failure_probability=1e-1,
    # )
    # lt_size['servers'] = [parameters.num_servers
    #                       for parameters in size_parameters]

    # Simulate partition parameters
    heuristic_partitions = heuristic_sim.simulate_parameter_list(partition_parameters)
    hybrid_partitions = hybrid_sim.simulate_parameter_list(partition_parameters)
    random_partitions = random_sim.simulate_parameter_list(partition_parameters)
    rs_partitions = rs_sim.simulate_parameter_list(partition_parameters)
    uncoded_partitions = uncoded_sim.simulate_parameter_list(partition_parameters)
    cmapred_partitions = cmapred_sim.simulate_parameter_list(partition_parameters)
    stragglerc_partitions = stragglerc_sim.simulate_parameter_list(partition_parameters)

    # include encoding delay
    heuristic_partitions.set_encode_delay(function=complexity.partitioned_encode_delay)
    hybrid_partitions.set_encode_delay(function=complexity.partitioned_encode_delay)
    random_partitions.set_encode_delay(function=complexity.partitioned_encode_delay)
    rs_partitions.set_encode_delay(
        function=partial(complexity.partitioned_encode_delay, partitions=1)
    )
    stragglerc_partitions.set_encode_delay(function=complexity.stragglerc_encode_delay)

    # Include the reduce delay
    heuristic_partitions.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    hybrid_partitions.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    random_partitions.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    rs_partitions.set_reduce_delay(
        function=partial(complexity.partitioned_reduce_delay, partitions=1)
    )
    uncoded_partitions.set_uncoded(enable=True)
    cmapred_partitions.set_cmapred(enable=True)
    stragglerc_partitions.set_reduce_delay(function=complexity.stragglerc_reduce_delay)
    stragglerc_partitions.set_stragglerc(enable=True)

    # Simulate size parameters
    heuristic_size = heuristic_sim.simulate_parameter_list(size_parameters)
    random_size = random_sim.simulate_parameter_list(size_parameters)
    rs_size = rs_sim.simulate_parameter_list(size_parameters)
    uncoded_size = uncoded_sim.simulate_parameter_list(size_parameters)
    cmapred_size = cmapred_sim.simulate_parameter_list(size_parameters)
    stragglerc_size = stragglerc_sim.simulate_parameter_list(size_parameters)

    # include encoding delay
    heuristic_size.set_encode_delay(function=complexity.partitioned_encode_delay)
    random_size.set_encode_delay(function=complexity.partitioned_encode_delay)
    rs_size.set_encode_delay(
        function=partial(complexity.partitioned_encode_delay, partitions=1)
    )
    stragglerc_size.set_encode_delay(function=complexity.stragglerc_encode_delay)

    # Include the reduce delay
    heuristic_size.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    random_size.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    rs_size.set_reduce_delay(
        function=partial(complexity.partitioned_reduce_delay, partitions=1)
    )
    uncoded_size.set_uncoded(enable=True)
    cmapred_size.set_cmapred(enable=True)
    stragglerc_size.set_reduce_delay(function=complexity.stragglerc_reduce_delay)
    stragglerc_size.set_stragglerc(enable=True)

    i = 0
    parameters = heuristic_size.parameter_list[i]
    df = heuristic_size.dataframes[i]
    df['encode'] = heuristic_size['encode'][i]
    df['reduce'] = heuristic_size['reduce'][i]
    deadline.delay_cdf_from_df(parameters, df)
    return

def encode_decode_plots():
    '''load/delay plots as function of partitions and size'''

    # Setup the evaluators
    sample_100 = SampleEvaluator(num_samples=100)
    sample_1000 = SampleEvaluator(num_samples=1000)

    # Get parameters
    partition_parameters = get_parameters_partitioning_2()
    parameter_list = plot.get_parameters_size_2()[0:-4] # -2

    # Setup the simulators
    heuristic_sim = Simulator(
        solver=HeuristicSolver(),
        assignment_eval=sample_1000,
        directory='./results/Heuristic/',
    )

    # lt code simulations are handled using the rateless module. the simulation
    # framework differs from that for the BDC and analytic.
    # lt_partitions = [rateless.evaluate(
    #     partition_parameters[0],
    #     target_overhead=1.3,
    #     target_failure_probability=1e-1,
    # )] * len(partition_parameters)
    # lt_partitions = pd.DataFrame(lt_partitions)
    # lt_partitions['partitions'] = [parameters.num_partitions
    #                                for parameters in partition_parameters]

    # lt_size = rateless.evaluate_parameter_list(
    #     size_parameters,
    #     target_overhead=1.3,
    #     target_failure_probability=1e-1,
    # )
    # lt_size['servers'] = [parameters.num_servers
    #                       for parameters in size_parameters]

    lt_2_1 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.2,
        target_failure_probability=1e-1,
    )
    lt_2_1['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_2_1 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.2,
        target_failure_probability=1e-1,
    )
    lt_2_1['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_2_3 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.2,
        target_failure_probability=1e-3,
    )
    lt_2_3['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_3_1 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.3,
        target_failure_probability=1e-1,
    )
    lt_3_1['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_3_3 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.3,
        target_failure_probability=1e-3,
    )
    lt_3_3['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    # Simulate BDC heuristic
    heuristic = heuristic_sim.simulate_parameter_list(parameter_list)

    # include encoding delay
    heuristic.set_encode_delay(function=complexity.partitioned_encode_delay)

    # Include the reduce delay
    heuristic.set_reduce_delay(function=complexity.partitioned_reduce_delay)

    # plot settings
    settings_2_1 = {
        'label': r'LT $(0.2, 10^{-1})$',
        'color': 'g',
        'marker': 'x-',
        'linewidth': 2,
        'size': 7}
    settings_2_3 = {
        'label': r'LT $(0.2, 10^{-3})$',
        'color': 'b',
        'marker': 'd-',
        'linewidth': 2,
        'size': 7}
    settings_3_1 = {
        'label': r'LT $(0.3, 10^{-1})$',
        'color': 'k',
        'marker': 'x--',
        'linewidth': 2,
        'size': 7}
    settings_3_2 = {
        'label': r'LT $(0.3, 10^{-3})$',
        'color': 'c',
        'marker': 'd--',
        'linewidth': 2,
        'size': 8}
    settings_heuristic = {
        'label': 'BDC, Heuristic',
        'color': 'r',
        'marker': 'H-',
        'linewidth': 3,
        'size': 8
    }

    encode_decode_plot(
        [lt_2_1,
         lt_2_3,
         lt_3_1,
         lt_3_3],
        [settings_2_1,
         settings_2_3,
         settings_3_1,
         settings_3_2],
        xlabel=r'$K$',
        normalize=heuristic,
        show=False,
    )
    plt.show()
    return

    # encoding/decoding complexity as function of num_partitions
    # plot.encode_decode_plot(
    #     [lt_partitions],
    #     [lt_plot_settings],
    #     'partitions',
    #     xlabel=r'$T$',
    #     normalize=heuristic_partitions,
    #     show=False,
    # )
    # plt.savefig('./plots/journal/complexity_partitions.pdf')

    # encoding/decoding complexity as function of system size
    plot.encode_decode_plot(
        [],
        [lt_plot_settings],
        'servers',
        xlabel=r'$K$',
        normalize=heuristic_size,
        legend='encode',
        show=False,
    )
    # plt.savefig('./plots/journal/complexity_size.pdf')
    plt.show()
    return

def lt_plots():

    # get system parameters
    # parameter_list = plot.get_parameters_size_2()[:-4]
    parameter_list = plot.get_parameters_N()

    lt_2_1 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.2,
        target_failure_probability=1e-1,
    )
    lt_2_1['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_2_3 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.2,
        target_failure_probability=1e-3,
    )
    lt_2_3['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_3_1 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.3,
        target_failure_probability=1e-1,
    )
    lt_3_1['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    lt_3_3 = rateless.evaluate_parameter_list(
        parameter_list,
        target_overhead=1.3,
        target_failure_probability=1e-3,
    )
    lt_3_3['servers'] = [
        parameters.num_servers for parameters in parameter_list
    ]

    # Setup the evaluators
    sample_1000 = SampleEvaluator(num_samples=1000)

    # Setup the simulators
    heuristic_sim = Simulator(
        solver=HeuristicSolver(),
        assignment_eval=sample_1000,
        directory='./results/Heuristic/',
    )
    uncoded_sim = Simulator(
        solver=None,
        assignments=1,
        parameter_eval=analytic.uncoded_performance,
        directory='./results/Uncoded/',
    )

    # run simulations
    heuristic = heuristic_sim.simulate_parameter_list(parameter_list)
    uncoded = uncoded_sim.simulate_parameter_list(parameter_list)

    # include encoding/decoding delay
    heuristic.set_encode_delay(function=complexity.partitioned_encode_delay)
    heuristic.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    uncoded.set_uncoded(enable=True)

    settings_2_1 = {
        'label': r'LT $(0.2, 10^{-1})$',
        'color': 'g',
        'marker': 'x-',
        'linewidth': 2,
        'size': 7}
    settings_2_3 = {
        'label': r'LT $(0.2, 10^{-3})$',
        'color': 'b',
        'marker': 'd-',
        'linewidth': 2,
        'size': 7}
    settings_3_1 = {
        'label': r'LT $(0.3, 10^{-1})$',
        'color': 'k',
        'marker': 'x--',
        'linewidth': 2,
        'size': 7}
    settings_3_2 = {
        'label': r'LT $(0.3, 10^{-3})$',
        'color': 'c',
        'marker': 'd--',
        'linewidth': 2,
        'size': 8}
    settings_heuristic = {
        'label': 'BDC, Heuristic',
        'color': 'r',
        'marker': 'H-',
        'linewidth': 3,
        'size': 8
    }

    load_delay_plot(
        [heuristic,
         lt_2_1,
         lt_2_3,
         lt_3_1,
         lt_3_3],
        [settings_heuristic,
         settings_2_1,
         settings_2_3,
         settings_3_1,
         settings_3_2],
        'num_columns',
        xlabel=r'$n$',
        normalize=uncoded,
        ncol=2,
        loc=(0.025, 0.125),
        show=False,
    )
    plt.savefig('./plots/journal/lt.pdf')
    plt.show()
    return

def load_delay_plots():
    '''load/delay plots as function of partitions and size'''

    # Setup the evaluators
    sample_100 = SampleEvaluator(num_samples=100)
    sample_1000 = SampleEvaluator(num_samples=1000)

    # Get parameters
    partition_parameters = get_parameters_partitioning_2()
    size_parameters = plot.get_parameters_size_2()[0:-4] # -2

    # setup the partial functions that handles running the simulations
    heuristic_fun = partial(
        simulation.simulate,
        directory='./results/Heuristic/',
        samples=1,
        solver=HeuristicSolver(),
        assignment_eval=sample_1000,
    )

    random_fun = partial(
        simulation.simulate,
        directory='./results/Random_100/',
        samples=100,
        solver=RandomSolver(),
        assignment_eval=sample_100,
    )

    hybrid_fun = partial(
        simulation.simulate,
        directory='./results/Hybrid/',
        samples=1,
        solver=AssignmentLoader(directory='./results/Hybrid/assignments/'),
        assignment_type=CachedAssignment,
        assignment_eval=sample_1000,
    )

    uncoded_fun = partial(
        simulation.simulate,
        directory='./results/Uncoded/',
        samples=1,
        parameter_eval=analytic.uncoded_performance,
    )

    cmapred_fun = partial(
        simulation.simulate,
        directory='./results/Cmapred/',
        samples=1,
        parameter_eval=analytic.cmapred_performance,
    )

    stragglerc_fun = partial(
        simulation.simulate,
        directory='./results/Stragglerc/',
        samples=1,
        parameter_eval=analytic.stragglerc_performance,
    )

    rs_fun = partial(
        simulation.simulate,
        directory='./results/RS/',
        samples=1,
        parameter_eval=analytic.mds_performance,
    )

    # lt code simulations are handled using the rateless module. the simulation
    # framework differs from that for the BDC and analytic.
    # lt_partitions = [rateless.evaluate(
    #     partition_parameters[0],
    #     target_overhead=1.3,
    #     target_failure_probability=1e-1,
    # )] * len(partition_parameters)
    # lt_partitions = pd.DataFrame(lt_partitions)
    # lt_partitions['partitions'] = [parameters.num_partitions
    #                                for parameters in partition_parameters]

    # lt_size = rateless.evaluate_parameter_list(
    #     size_parameters,
    #     target_overhead=1.3,
    #     target_failure_probability=1e-1,
    # )
    # lt_size['servers'] = [parameters.num_servers
    #                      for parameters in size_parameters]

    # Simulate partition parameters
    heuristic_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=heuristic_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=complexity.partitioned_encode_delay,
        reduce_delay_fun=complexity.partitioned_reduce_delay,
    )
    hybrid_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=hybrid_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=complexity.partitioned_encode_delay,
        reduce_delay_fun=complexity.partitioned_reduce_delay,
    )
    random_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=random_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=complexity.partitioned_encode_delay,
        reduce_delay_fun=complexity.partitioned_reduce_delay,
    )
    rs_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=rs_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=partial(
            complexity.partitioned_encode_delay,
            partitions=1
        ),
        reduce_delay_fun=partial(
            complexity.partitioned_reduce_delay,
            partitions=1,
        ),
    )
    uncoded_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=uncoded_fun,
        map_complexity_fun=complexity.map_complexity_uncoded,
        encode_delay_fun=lambda x: 0,
        reduce_delay_fun=lambda x: 0,
    )
    cmapred_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=cmapred_fun,
        map_complexity_fun=complexity.map_complexity_cmapred,
        encode_delay_fun=lambda x: 0,
        reduce_delay_fun=lambda x: 0,
    )
    stragglerc_partitions = simulation.simulate_parameter_list(
        parameter_list=partition_parameters,
        simulate_fun=stragglerc_fun,
        map_complexity_fun=complexity.map_complexity_stragglerc,
        encode_delay_fun=complexity.stragglerc_encode_delay,
        reduce_delay_fun=complexity.stragglerc_reduce_delay,
    )

    # # include encoding delay
    # heuristic_partitions.set_encode_delay(function=complexity.partitioned_encode_delay)
    # hybrid_partitions.set_encode_delay(function=complexity.partitioned_encode_delay)
    # random_partitions.set_encode_delay(function=complexity.partitioned_encode_delay)
    # rs_partitions.set_encode_delay(
    #     function=partial(complexity.partitioned_encode_delay, partitions=1)
    # )
    # stragglerc_partitions.set_encode_delay(function=complexity.stragglerc_encode_delay)

    # # Include the reduce delay
    # heuristic_partitions.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    # hybrid_partitions.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    # random_partitions.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    # rs_partitions.set_reduce_delay(
    #     function=partial(complexity.partitioned_reduce_delay, partitions=1)
    # )
    # uncoded_partitions.set_uncoded(enable=True)
    # cmapred_partitions.set_cmapred(enable=True)
    # stragglerc_partitions.set_reduce_delay(function=complexity.stragglerc_reduce_delay)
    # stragglerc_partitions.set_stragglerc(enable=True)

    # Simulate size parameters
    heuristic_size = simulation.simulate_parameter_list(
        parameter_list=size_parameters,
        simulate_fun=heuristic_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=complexity.partitioned_encode_delay,
        reduce_delay_fun=complexity.partitioned_reduce_delay,
    )
    random_size = simulation.simulate_parameter_list(
        parameter_list=size_parameters,
        simulate_fun=random_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=complexity.partitioned_encode_delay,
        reduce_delay_fun=complexity.partitioned_reduce_delay,
    )
    rs_size = simulation.simulate_parameter_list(
        parameter_list=size_parameters,
        simulate_fun=rs_fun,
        map_complexity_fun=complexity.map_complexity_unified,
        encode_delay_fun=partial(
            complexity.partitioned_encode_delay,
            partitions=1
        ),
        reduce_delay_fun=partial(
            complexity.partitioned_reduce_delay,
            partitions=1,
        ),
    )
    uncoded_size = simulation.simulate_parameter_list(
        parameter_list=size_parameters,
        simulate_fun=uncoded_fun,
        map_complexity_fun=complexity.map_complexity_uncoded,
        encode_delay_fun=lambda x: 0,
        reduce_delay_fun=lambda x: 0,
    )
    cmapred_size = simulation.simulate_parameter_list(
        parameter_list=size_parameters,
        simulate_fun=cmapred_fun,
        map_complexity_fun=complexity.map_complexity_cmapred,
        encode_delay_fun=lambda x: 0,
        reduce_delay_fun=lambda x: 0,
    )
    stragglerc_size = simulation.simulate_parameter_list(
        parameter_list=size_parameters,
        simulate_fun=stragglerc_fun,
        map_complexity_fun=complexity.map_complexity_stragglerc,
        encode_delay_fun=complexity.stragglerc_encode_delay,
        reduce_delay_fun=complexity.stragglerc_reduce_delay,
    )

    print(heuristic_size)


    # # include encoding delay
    # heuristic_size.set_encode_delay(function=complexity.partitioned_encode_delay)
    # random_size.set_encode_delay(function=complexity.partitioned_encode_delay)
    # rs_size.set_encode_delay(
    #     function=partial(complexity.partitioned_encode_delay, partitions=1)
    # )
    # stragglerc_size.set_encode_delay(function=complexity.stragglerc_encode_delay)

    # # Include the reduce delay
    # heuristic_size.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    # random_size.set_reduce_delay(function=complexity.partitioned_reduce_delay)
    # rs_size.set_reduce_delay(
    #     function=partial(complexity.partitioned_reduce_delay, partitions=1)
    # )
    # uncoded_size.set_uncoded(enable=True)
    # cmapred_size.set_cmapred(enable=True)
    # stragglerc_size.set_reduce_delay(function=complexity.stragglerc_reduce_delay)
    # stragglerc_size.set_stragglerc(enable=True)

    # plot settings
    heuristic_plot_settings = {
        'label': r'BDC, Heuristic',
        'color': 'r',
        'marker': 'H-',
        'linewidth': 2,
        'size': 7}
    random_plot_settings = {
        'label': r'BDC, Random',
        'color': 'b',
        'marker': '^-',
        'linewidth': 2,
        'size': 8}
    hybrid_plot_settings = {
        'label': r'BDC, Hybrid',
        'color': 'c-',
        'marker': 'd',
        'linewidth': 2,
        'size': 6}
    lt_plot_settings = {
        'label': r'LT',
        'color': 'c',
        'marker': 'v',
        'linewidth': 3,
        'size': 8
    }
    cmapred_plot_settings = {
        'label': r'CMR',
        'color': 'g',
        'marker': 's--',
        'linewidth': 2,
        'size': 7}
    stragglerc_plot_settings = {
        'label': r'SC',
        'color': 'k',
        'marker': 'H',
        'linewidth': 2,
        'size': 7}
    rs_plot_settings = {
        'label': r'Unified',
        'color': 'k',
        'marker': 'd--',
        'linewidth': 2,
        'size': 7}

    # # encoding/decoding complexity as function of num_partitions
    # plot.encode_decode_plot(
    #     [lt_partitions],
    #     [lt_plot_settings],
    #     'partitions',
    #     xlabel=r'$T$',
    #     normalize=heuristic_partitions,
    #     show=False,
    # )
    # # plt.savefig('./plots/journal/complexity_partitions.pdf')

    # # encoding/decoding complexity as function of system size
    # plot.encode_decode_plot(
    #     [lt_size],
    #     [lt_plot_settings],
    #     'servers',
    #     xlabel=r'$K$',
    #     normalize=heuristic_size,
    #     legend='load',
    #     show=False,
    # )
    # # plt.savefig('./plots/journal/complexity_size.pdf')

    # load/delay as function of num_partitions
    plot.load_delay_plot(
        [heuristic_partitions,
         # lt_partitions,
         cmapred_partitions,
         stragglerc_partitions,
         rs_partitions],
        [heuristic_plot_settings,
         # lt_plot_settings,
         cmapred_plot_settings,
         stragglerc_plot_settings,
         rs_plot_settings],
        'num_partitions',
        xlabel=r'$T$',
        normalize=uncoded_partitions,
        loc=(0.025, 0.125),
        show=False,
    )
    # plt.savefig('./plots/journal/partitions.pdf')

    # load/delay as function of system size
    plot.load_delay_plot(
        [heuristic_size,
         # lt_size,
         cmapred_size,
         stragglerc_size,
         rs_size],
        [heuristic_plot_settings,
         # lt_plot_settings,
         cmapred_plot_settings,
         stragglerc_plot_settings,
         rs_plot_settings],
        'num_servers',
        xlabel=r'$K$',
        normalize=uncoded_size,
        legend='load',
        ncol=2,
        show=False,
    )
    # plt.savefig('./plots/journal/size.pdf')

    # load/delay for different solvers as function of num_partitions
    plot.load_delay_plot(
        [heuristic_partitions,
         hybrid_partitions,
         random_partitions],
        [heuristic_plot_settings,
         hybrid_plot_settings,
         random_plot_settings],
        'num_partitions',
        xlabel=r'$T$',
        normalize=uncoded_partitions,
        show=False,
    )
    # plt.savefig('./plots/journal/solvers_partitions.pdf')

    # load/delay as function of system size
    plot.load_delay_plot(
        [heuristic_size,
         random_size],
        [heuristic_plot_settings,
         random_plot_settings],
        'num_servers',
        xlabel=r'$K$',
        normalize=uncoded_size,
        legend='load',
        show=False,
    )
    # plt.savefig('./plots/journal/solvers_size.pdf')

    plt.show()
    return

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # deadline_plots()
    # encode_decode_plots()
    # lt_plots()
    load_delay_plots()
