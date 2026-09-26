"""P-23 to P-26: HTTP API contract (I-17)."""

import json

import pytest
from fastapi.testclient import TestClient

from gemetro.api import create_app
from gemetro.guided import PERIODS, run_guided
from gemetro.scenario import Scenario, run_scenario, scenario_config

FORBIDDEN_KEYS = ("prob", "confidence", "confianza", "accuracy", "precision", "precisión")


@pytest.fixture(scope="module")
def client(fixture_model_dir):
    with TestClient(create_app(fixture_model_dir)) as test_client:
        yield test_client


def _all_keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _all_keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _all_keys(inner)


def test_health_reports_loaded_model(client):
    assert client.get("/health").json() == {"status": "ok", "model_loaded": True}


def test_config_exposes_sliders(client):
    config = client.get("/config").json()
    assert config["defaults"]["tau_r"] == 60
    assert config["sliders"]["phi_peak"] == {"min": 0.5, "max": 1.0, "step": 0.05,
                                              "default": 0.75}


def test_config_keeps_existing_fields_and_adds_guided_fields(client):
    config = client.get("/config").json()
    assert set(scenario_config()) <= set(config)
    assert {k: config[k] for k in scenario_config()} == json.loads(json.dumps(scenario_config()))
    assert config["domain"]["rh"] == {"min": 52.05, "max": 89.47}
    assert config["domain"]["postures"] == ["seated", "standing"]
    assert config["pmv_ranges"]["ta"] == {"min": 10.0, "max": 30.0}
    assert config["pmv_ranges"]["pmv"] == {"min": -2.0, "max": 2.0}
    assert set(config["pmv_ranges"]) == {"ta", "tr", "vel", "met", "clo", "pa", "pmv"}
    assert config["guided"]["periods"] == {
        "morning": list(range(4, 11)), "midday": [11, 12, 13, 14],
        "afternoon": [15, 16, 17, 18], "night": [19, 20, 21, 22],
    }
    # Default posture is "seated" for both modes (direction 2026-09-26).
    assert config["guided"]["fixed"] == {"phi_peak": 0.75, "vel": 0.3, "clo": 0.5,
                                         "posture": "seated"}


def test_guided_endpoint_matches_direct_service_call(client, fixture_model):
    response = client.get("/guided", params={"line": "A", "period": "afternoon"})
    assert response.status_code == 200
    assert response.json() == json.loads(json.dumps(run_guided("A", "afternoon", fixture_model)))


def test_guided_midday_is_a_labelled_fallback(client):
    guided = client.get("/guided", params={"line": "B", "period": "midday"}).json()
    assert [e["selection"] for e in guided["entries"]] == ["no_in_domain_fallback"] * 4


def test_every_guided_period_is_served(client):
    for period in PERIODS:
        assert client.get("/guided", params={"line": "A", "period": period}).status_code == 200


def test_guided_has_no_confidence_or_probability_fields(client):
    guided = client.get("/guided", params={"line": "A", "period": "morning"}).json()
    for key in _all_keys(guided):
        assert not any(word in key.lower() for word in FORBIDDEN_KEYS), key


@pytest.mark.parametrize(
    "params",
    [{"line": "C", "period": "morning"}, {"line": "A", "period": "evening"},
     {"line": "A"}, {"period": "night"}, {}],
)
def test_invalid_guided_requests_are_rejected(client, params):
    assert client.get("/guided", params=params).status_code == 422


def test_default_scenario_record(client):
    response = client.post("/scenario", json={})
    assert response.status_code == 200
    record = response.json()
    assert len(record["sensitivity"]) == 8
    assert record["ml"]["domain_status"]
    assert record["pmv"]["status"]


def test_no_confidence_or_probability_fields(client):
    # P-24
    record = client.post("/scenario", json={"hour": 8, "tau_r": 20}).json()
    for key in _all_keys(record):
        assert not any(word in key.lower() for word in FORBIDDEN_KEYS), key


def test_same_request_same_response(client):
    # P-23
    body = {"line": "B", "hour": 7, "phi_peak": 0.9, "tau_r": 45, "vel": 0.8, "clo": 0.35,
            "posture": "seated"}
    assert client.post("/scenario", json=body).json() == client.post("/scenario", json=body).json()


def test_api_matches_direct_service_call(client, fixture_model):
    # P-26
    body = {"line": "A", "hour": 12, "phi_peak": 0.55, "tau_r": 120, "vel": 1.2, "clo": 0.8,
            "posture": "standing", "delta_t": 3.5}
    direct = run_scenario(Scenario(**body), fixture_model)
    assert client.post("/scenario", json=body).json() == json.loads(json.dumps(direct))


@pytest.mark.parametrize(
    "body",
    [
        {"line": "C"}, {"hour": 23}, {"phi_peak": 0.3}, {"tau_r": 50}, {"vel": 2.0},
        {"clo": 0.21}, {"posture": "lying"}, {"delta_t": 20}, {"unknown": 1},
    ],
)
def test_invalid_scenarios_are_rejected(client, body):
    # P-25
    assert client.post("/scenario", json=body).status_code == 422


def test_missing_model_artifact_gives_503(tmp_path):
    with TestClient(create_app(tmp_path)) as test_client:
        assert test_client.get("/health").json()["model_loaded"] is False
        response = test_client.post("/scenario", json={})
        assert response.status_code == 503
        assert "I-15" in response.json()["detail"]
        guided = test_client.get("/guided", params={"line": "A", "period": "morning"})
        assert guided.status_code == 503
        assert "I-15" in guided.json()["detail"]
        config = test_client.get("/config")
        assert config.status_code == 200
        assert config.json()["domain"] is None


def test_cors_allows_local_frontend_origin(client):
    response = client.get("/config", headers={"Origin": "http://localhost:5500"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"
