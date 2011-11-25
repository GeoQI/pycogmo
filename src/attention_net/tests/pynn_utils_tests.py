#!/usr/bin/env python2

from copy import deepcopy
import itertools
import logging
from logging import NullHandler 
from mock import Mock, patch
from nose import with_setup
from nose.tools import eq_, raises, timed, nottest
import pyNN.nest as pynnn
from common.pynn_utils import *
from common.utils import splice

NAN = float("NaN")

BASE_DATA_TESTPATH = "test_data/"
VALID_SAMPLE_INPUT_FILEPATHS = {
    "png" : [BASE_DATA_TESTPATH + "bnw_checker_8x8_24bit.png",
             BASE_DATA_TESTPATH + "bnw_checker_8x8_2bit.png",
             BASE_DATA_TESTPATH + "color_checker_8x8_24bit.png",],
    "csv" : [BASE_DATA_TESTPATH + "csv_checker.txt"]}
ALL_SAMPLE_INPUT_FILES = splice(VALID_SAMPLE_INPUT_FILEPATHS.values())

def list_units(ril):
    """Returns the list of PyNN units linked by the given rectilinear
    input layer."""
    return [b for a, b in
         list(splice(ril.electrodes))]

class Tns(object):
    pass

def setup_weights():
    Tns.w1_array = [[j/63. for j in range(i*8,8+i*8)] 
                    for i in range(8)]
    Tns.w1 = Weights(Tns.w1_array)
    Tns.w2_array = [[j/63. for j in 
                     list(itertools.chain(*zip(itertools.repeat(NAN), 
                                               range(i*8,4+i*8))))]
                    for i in range(8)]
    Tns.w2 = Weights(Tns.w2_array)

def setup_pynn_populations():
    pynnn.setup()
    Tns.p1 = pynnn.Population(64, pynnn.IF_curr_alpha,
                          structure=pynnn.space.Grid2D())
    Tns.p2 = pynnn.Population(64, pynnn.IF_curr_alpha,
                          structure=pynnn.space.Grid2D())


def setup_rectinilearinputlayers():
    setup_pynn_populations()
    Tns.ril1_max_namp = 1
    Tns.ril2_max_namp = 2
    Tns.ril1 = RectilinearInputLayer(Tns.p1, 8, 8, Tns.ril1_max_namp)
    Tns.ril2 = RectilinearInputLayer(Tns.p2, 8, 8, Tns.ril2_max_namp)

# def setup_mock_dcsource():
#     Tns.dcsource_patch = patch.object(pynnn., "__int__")
#     Tns.dcsource_patch.start()

# def teardown_mock_dcsource():
#     Tns.dcsource_patch.stop()
#     Tns.dcsource_patch = None

@with_setup(setup_weights)
def test_weights_eq():
    assert Tns.w1_array == Tns.w1.weights, "initial data == property"
    assert Tns.w1 == Weights(Tns.w1_array), "only the instance changes"
    assert Tns.w2_array != Tns.w2.weights, "NaNs should not be equal" # Because of NaNs
    assert Tns.w2 == Weights(Tns.w2_array), "NaNs should be ignored"
    assert Tns.w1 != Tns.w2, "completetly different objects"

@with_setup(setup_weights)
def test_weights_accessors():
    assert Tns.w1[1][2] == Tns.w1_array[1][2]
    Tns.w1[1][2] = 1
    assert Tns.w1[1][2] == 1
    Tns.w1.weights = Tns.w2_array
    assert Tns.w1 == Tns.w2
    Tns.w1.weights = Tns.w1_array
    assert Tns.w1 == Tns.w1
    Tns.w1.weights = Tns.w2
    assert Tns.w1 == Tns.w2
    assert Tns.w2 == Weights(Tns.w2_array)

@raises(IndexError)
@with_setup(setup_weights)
def test_weights_get_item_exception_1():
    return Tns.w1[1000][2]

@raises(IndexError)
@with_setup(setup_weights)
def test_weights_get_item_exception_2():
    return Tns.w1[1][2000]

@raises(IndexError)
@with_setup(setup_weights)
def test_weights_set_item_exception_1():
    Tns.w1[1000][2] = 1

@raises(IndexError)
@with_setup(setup_weights)
def test_weights_set_item_exception_2():
    Tns.w1[1][2000] = 1

@with_setup(setup_weights)
def test_weights_adjusted():
    error = deepcopy(Tns.w1_array)
    assert Tns.w2 == Tns.w2.adjusted(error, learning=0)

    r1 = Tns.w1.adjusted(error, learning=1)
    for i, j in itertools.product(xrange(8), repeat=2):
        error[i][j] = 0
    assert r1 == error
    
    assert Tns.w2.adjusted(error) == Tns.w2

    for i, j in itertools.product(xrange(8), repeat=2):
        error[i][j] = 1
        Tns.w2_array[i][j] = Tns.w2_array[i][j] - Tns.w2._default_l_rate

    assert Tns.w2.adjusted(error) == Weights(Tns.w2_array)

@with_setup(setup_rectinilearinputlayers)
def test_rectilinearinputlayer_init():
    assert len(Tns.ril1.electrodes) == 8
    assert set(Tns.p1) == set(list_units(Tns.ril1))
    assert set(Tns.p2) == set(list_units(Tns.ril2))

@with_setup(setup_rectinilearinputlayers)
def test_rectilinearinputlayer_access():
    a, b = Tns.ril1[1][2] # __getitem__
    assert a == None
    assert b in set(Tns.p1)
    assert Tns.ril1.shape == (8, 8)

@with_setup(setup_rectinilearinputlayers)
def test_rectilinearinputlayer_apply_input():
    mock_dcsource = Mock(spec = pynnn.DCSource)
    some_sample = [[5]*8]*8
    Tns.ril1.apply_input(sample = some_sample, 
                         start_time = 12, duration = 51,
                         max_namp = None, dcsource_class = mock_dcsource)
    assert mock_dcsource.call_count == 64
    for args_i in itertools.product(xrange(8), repeat=2):
        args = mock_dcsource.call_args_list[args_i[0]*8+args_i[1]]
        assert args[0] == ()
        assert args[1] == {'amplitude' : Tns.ril1_max_namp * \
                               some_sample[args_i[0]][args_i[1]] , 
                           'start' : 12, 'stop' : 12 + 51}



# def setup_
