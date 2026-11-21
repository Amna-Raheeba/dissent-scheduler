import os

from dissent_sched.cli import build_parser, main

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def test_parser_commands():
    parser = build_parser()
    args = parser.parse_args(["demo"])
    assert args.command == "demo"
    args = parser.parse_args(["evaluate", "--outdir", "out"])
    assert args.command == "evaluate"
    assert args.outdir == "out"


def test_cli_demo_runs(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "Failure-pathway audit" in out
    assert "Chosen schedule:" in out
    assert "Policy comparison" in out


def test_cli_audit_runs(capsys):
    path = os.path.join(EXAMPLES, "demo_scenario.json")
    assert main(["audit", "--scenario", path]) == 0
    out = capsys.readouterr().out
    assert "Failure-pathway audit" in out


def test_cli_schedule_runs(capsys):
    path = os.path.join(EXAMPLES, "demo_scenario.json")
    assert main(["schedule", "--scenario", path]) == 0
    out = capsys.readouterr().out
    assert "Dissent schedule search" in out


def test_cli_no_command_returns_2():
    assert main([]) == 2
