"""Unit tests for resilient GrammarValidator modes, SVG shortcut, and diagnostic classification."""

import subprocess
from unittest.mock import patch, MagicMock
from agents.uml_generator.validators import GrammarValidator, GrammarValidationMode


def test_grammar_validator_disabled_mode():
    """Test DISABLED mode skips syntax checking and returns passed: True immediately."""
    validator = GrammarValidator(mode="DISABLED")
    res = validator.validate("component", "@startuml\ncomponent A\n@enduml")
    assert res["passed"] is True
    assert res["status"] == "passed"
    assert res["score"] == 100
    assert len(res["errors"]) == 0


@patch("subprocess.run")
def test_grammar_validator_best_effort_timeout_svg_shortcut(mock_run):
    """Test BEST_EFFORT mode when -syntax times out but -tsvg render shortcut succeeds."""
    # First call (-syntax) times out, second call (-tsvg) succeeds with returncode 0
    mock_run.side_effect = [
        subprocess.TimeoutExpired(cmd="plantuml -syntax", timeout=5),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    validator = GrammarValidator(mode="BEST_EFFORT", timeout=5)
    res = validator.validate("component", "@startuml\ncomponent A\n@enduml")

    assert res["passed"] is True
    assert res["status"] == "passed"
    assert "SVG render shortcut" in res["warnings"][0]


@patch("subprocess.run")
def test_grammar_validator_best_effort_timeout_fallback(mock_run):
    """Test BEST_EFFORT mode when both -syntax and -tsvg time out -> returns status timed_out and passed True."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="plantuml", timeout=5)

    validator = GrammarValidator(mode="BEST_EFFORT", timeout=5)
    res = validator.validate("component", "@startuml\ncomponent A\n@enduml")

    assert res["passed"] is True
    assert res["status"] == "timed_out"
    assert "Grammar Validation Unavailable" in res["warnings"][0]


@patch("subprocess.run")
def test_grammar_validator_strict_mode_timeout(mock_run):
    """Test STRICT mode fails on timeout with TOOL_TIMEOUT diagnostic code."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="plantuml -syntax", timeout=5)

    validator = GrammarValidator(mode="STRICT", timeout=5)
    res = validator.validate("component", "@startuml\ncomponent A\n@enduml")

    assert res["passed"] is False
    assert res["status"] == "failed"
    assert len(res["errors"]) == 1
    assert res["diagnostics"][0]["code"] == "TOOL_TIMEOUT"


@patch("subprocess.run")
def test_grammar_validator_syntax_error_classification(mock_run):
    """Test syntax error classification into SYNTAX_ERROR diagnostic code."""
    mock_run.returncode = 1
    mock_run.returncode = 1
    mock_run.side_effect = None
    mock_run.return_value = MagicMock(returncode=1, stdout="Syntax Error at line 3", stderr="")

    validator = GrammarValidator(mode="STRICT", timeout=5)
    res = validator.validate("component", "@startuml\ncomponent A\n@enduml")

    assert res["passed"] is False
    assert res["status"] == "failed"
    assert res["diagnostics"][0]["code"] == "SYNTAX_ERROR"


@patch("subprocess.run")
def test_grammar_validator_missing_executable_strict(mock_run):
    """Test STRICT mode missing executable raises MISSING_EXECUTABLE diagnostic code."""
    mock_run.side_effect = FileNotFoundError("plantuml")

    validator = GrammarValidator(mode="STRICT", timeout=5)
    res = validator.validate("component", "@startuml\ncomponent A\n@enduml")

    assert res["passed"] is False
    assert res["status"] == "failed"
    assert res["diagnostics"][0]["code"] == "MISSING_EXECUTABLE"
