"""P-21: the evaluation and the API use the same simulator, PMV and model code (no copies)."""

import gemetro.experiments.e01_nanjing_final_set as e01
import gemetro.experiments.e03_final_model as e03
from gemetro import api, comfort_model, pmv, scenario, simulator
from gemetro.evaluation import cv


def test_pmv_is_one_function_everywhere():
    assert e01.pmv_baseline is pmv.pmv_baseline
    assert scenario.pmv_baseline is pmv.pmv_baseline


def test_simulator_is_one_implementation():
    assert scenario.simulate is simulator.simulate
    assert scenario.simulate_advanced is simulator.simulate_advanced


def test_model_artifact_contract_is_shared():
    assert e03.save_artifact is comfort_model.save_artifact
    assert e03.Domain is comfort_model.Domain
    assert api.ComfortModel is comfort_model.ComfortModel
    assert e03.FEATURES == cv.FEATURES == comfort_model.FEATURES
