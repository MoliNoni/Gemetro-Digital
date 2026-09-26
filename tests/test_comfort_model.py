"""P-16: training-domain check and inference contract (I-11)."""

import pandas as pd
import pytest

from gemetro.comfort_model import (
    CLASSES,
    STATUS_EXTRAPOLATION,
    STATUS_IN_DOMAIN,
    ComfortModel,
    Domain,
)

INSIDE = {"ta": 25.0, "rh_percent": 70.0, "vel": 0.3, "clo": 0.5, "posture": "standing"}


def test_inside_domain(fixture_model):
    prediction = fixture_model.predict(**INSIDE)
    assert prediction.comfort_class in CLASSES
    assert prediction.domain_status == STATUS_IN_DOMAIN
    assert prediction.out_of_domain == ()


@pytest.mark.parametrize(
    ("change", "name"),
    [({"ta": 31.64}, "ta"), ({"rh_percent": 45.0}, "rh"), ({"vel": 1.8}, "vel"),
     ({"clo": 0.1}, "clo")],
)
def test_outside_domain_still_predicts_with_extrapolation_status(fixture_model, change, name):
    prediction = fixture_model.predict(**{**INSIDE, **change})
    assert prediction.comfort_class in CLASSES
    assert prediction.domain_status == STATUS_EXTRAPOLATION
    assert name in prediction.out_of_domain


def test_every_offending_input_is_reported(fixture_model):
    prediction = fixture_model.predict(35.0, 40.0, 0.3, 0.5, "seated")
    assert prediction.out_of_domain == ("ta", "rh")


@pytest.mark.parametrize("value", [21.07, 31.63])
def test_limits_are_inclusive(fixture_model, value):
    assert fixture_model.predict(**{**INSIDE, "ta": value}).domain_status == STATUS_IN_DOMAIN


@pytest.mark.parametrize("posture", ["seated", "standing"])
def test_posture_is_always_inside(fixture_model, posture):
    assert fixture_model.predict(**{**INSIDE, "posture": posture}).out_of_domain == ()


def test_limits_come_from_the_artifact(fixture_model_dir):
    domain = ComfortModel.load(fixture_model_dir).domain
    assert domain.ranges["ta"] == (21.07, 31.63)


def test_domain_from_rows_is_min_max():
    rows = pd.DataFrame(
        {"ta": [22.0, 30.0], "rh": [55.0, 80.0], "vel": [0.1, 1.2], "clo": [0.3, 0.9],
         "posture": ["seated", "standing"]}
    )
    domain = Domain.from_rows(rows)
    assert domain.ranges == {"ta": (22.0, 30.0), "rh": (55.0, 80.0), "vel": (0.1, 1.2),
                             "clo": (0.3, 0.9)}
    assert domain.postures == ("seated", "standing")


def test_no_probabilities_in_prediction(fixture_model):
    fields = set(fixture_model.predict(**INSIDE).__dataclass_fields__)
    assert fields == {"comfort_class", "domain_status", "out_of_domain"}


def test_missing_artifact_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="I-15"):
        ComfortModel.load(tmp_path)
