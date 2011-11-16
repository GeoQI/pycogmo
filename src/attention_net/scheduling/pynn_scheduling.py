#!/usr/bin/env python2
""" Utilities and algorithms to integrate PyNN and SimPy
"""

import pyNN.nest as pynnn
import SimPy.Simulation as sim
from common.pynn_utils import InputSample
from common.utils import LOGGER, optimal_rounding

SIMPY_END_T = -1

PYNN_TIME_STEP = pynnn.get_time_step()
PYNN_TIME_ROUNDING = optimal_rounding(PYNN_TIME_STEP)

class DummyProcess(sim.Process):
    def ACTIONS(self):
        yield sim.hold,self,0

def configure_scheduling():
    sim.initialize()
    pynnn.setup()

def run_simulation(end_time = None):
    """Runs the simulation while keeping SimPy and PyNN synchronized at
    event times. Runs until no event is scheduled unless end_time is
    provided. if end_time is given, runs until end_time."""
    def run_pynn(end_t):
        pynn_now = pynnn.get_current_time()
        pynn_now_round = round(pynn_now, PYNN_TIME_ROUNDING)
        delta_t = round(end_t - pynn_now_round, PYNN_TIME_ROUNDING)
        if pynn_now <= pynn_now_round and delta_t > PYNN_TIME_STEP:
            delta_t = round(delta_t - PYNN_TIME_STEP, PYNN_TIME_ROUNDING)
        if delta_t > 0: # necessary because run(0) may run PyNN by timestep
            pynnn.run(delta_t) # neuralensemble.org/trac/PyNN/ticket/200
    is_not_end = None
    if end_time == None:
        # Would testing len(sim.Globals.allEventTimes()) be faster?
        is_not_end = lambda t: not isinstance(t, sim.Infinity)
    else:
        DummyProcess().start(at=end_time)
        is_not_end = lambda t: t <= end_time
    t_event_start = sim.peek()
    while is_not_end(t_event_start):
        LOGGER.debug("Progressing to SimPy event at time %s",
                     t_event_start)
        run_pynn(t_event_start) # run until event start
        sim.step() # process the event
        run_pynn(sim.now()) # run PyNN until event end
        t_event_start = sim.peek()
        

class InputPresentation(sim.Process):
    def __init__(self, population, input_sample):
        Process.__init__(self)
        self.name = "Presentation of " + str(input_sample) + \
            " to " + population.label
        self.population = population
        self.input_sample = input_sample # class InputSample
    
    def ACTIONS(self):
        LOGGER.debug("%s starting", self.name)
        TODO
        yield sim.hold, self, 0


def schedule_input_presentation(population, 
                                input_sample, 
                                duration,
                                start_t = None):
    """Schedule the constant application of the input sample to the
    population, for duration ms, by default from start_t = current end
    of simulation, extending the simulation's scheduled end
    SIMPY_END_T by duration milliseconds."""
    global SIMPY_END_T
    if start_t == None:
        start_t = SIMPY_END_T
    if start_t + duration > SIMPY_END_T:
        SIMPY_END_T = start_t + duration
    
