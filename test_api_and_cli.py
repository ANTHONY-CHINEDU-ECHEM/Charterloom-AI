"""REST API and command line interface."""

from fastapi.testclient import TestClient

from charterloom.api import create_app
from charterloom.cli import _parse, main
from charterloom.knowledge.templates import build_template


def test_cli_option_parsing():
    positional, options = _parse(["charter.md", "out=result.json", "port=9000"])
    assert positional == ["charter.md"]
    assert options == {"out": "result.json", "port": "9000"}


def test_cli_help_and_unknown_command(capsys):
    assert main(["help"]) == 0
    assert main(["unknown"]) == 2
    assert "Charterloom AI" in capsys.readouterr().out


def test_api_end_to_end(settings, pipeline, example_charters):
    client = TestClient(create_app(settings, pipeline=pipeline))
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/templates").json()) == 8
    assert client.get("/templates/not_real").status_code == 404

    response = client.post("/recommend", json={"charter_text": example_charters["claims_fraud_research"],
                                               "project_name": "Kestrel Signal"})
    assert response.status_code == 200
    body = response.json()
    assert body["project_name"] == "Kestrel Signal"
    assert body["configuration"]["validation"]["valid"]

    hits = client.post("/retrieve", json={"query": "change freeze rollback", "top_k": 3}).json()["hits"]
    assert len(hits) == 3

    verdict = client.post("/validate", json={"configuration": build_template("stage_gate_waterfall")}).json()
    assert verdict["valid"]
    assert client.post("/validate", json={"configuration": {"states": []}}).status_code == 422


def test_api_rejects_short_charter(settings, pipeline):
    client = TestClient(create_app(settings, pipeline=pipeline))
    assert client.post("/recommend", json={"charter_text": "too short"}).status_code == 422
