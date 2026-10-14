"""Template library, validator and editor."""

import copy

import pytest

from charterloom.catalog import ARCHETYPE_KEYS
from charterloom.knowledge.templates import build_template
from charterloom.state_machine import StateMachineEditor, validate


@pytest.mark.parametrize("archetype", ARCHETYPE_KEYS)
def test_every_template_is_valid(archetype):
    report = validate(build_template(archetype))
    assert report.valid, report.errors


def test_validator_detects_trap_state():
    config = build_template("scrum_product_delivery")
    config["transitions"] = [t for t in config["transitions"] if t["key"] != "unblock"]
    report = validate(config)
    assert any("blocked cannot reach" in e for e in report.errors)


def test_validator_detects_unknown_state_reference():
    config = build_template("kanban_continuous_flow")
    config["transitions"].append({"key": "ghost", "name": "Ghost", "from": "intake", "to": "nowhere",
                                  "guards": [], "actions": []})
    assert not validate(config).valid


def test_validator_requires_segregation_for_strict_regimes():
    config = build_template("scrumban_hybrid")
    config["compliance"] = {"regimes": ["sox"]}
    assert any("segregation of duties" in e for e in validate(config).errors)


def test_gate_insertion_chains_and_stays_valid():
    config = build_template("scrum_product_delivery")
    editor = StateMachineEditor(config)
    assert editor.insert_gate("security_review", "Security Review", "security_engineer", "security_assessment", "test")
    assert editor.insert_gate("user_acceptance_testing", "UAT", "client", "uat_signoff", "test")
    order = [s["key"] for s in config["states"]]
    assert order.index("security_review") < order.index("user_acceptance_testing") < order.index("done")
    assert config["anchors"]["release_transition"] == "user_acceptance_testing_passed"
    assert validate(config).valid
    assert len(editor.changelog) == 2


def test_duplicate_gate_is_ignored():
    config = build_template("kanban_continuous_flow")
    editor = StateMachineEditor(config)
    editor.insert_gate("security_review", "Security Review", "security_engineer", "x", "r")
    snapshot = copy.deepcopy(config)
    assert not editor.insert_gate("security_review", "Security Review", "security_engineer", "x", "r")
    assert config == snapshot
