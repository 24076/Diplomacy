import json
from pathlib import Path

from engine.game import Game
from tools.run_full_test_and_report import (
    generate_sample_battle_report,
    play_multi_year_full_flow,
    play_rulebook_normal_flow,
)


def test_generate_sample_battle_report_writes_expected_artifacts():
    output_dir = Path("tests_artifacts")
    summary = generate_sample_battle_report(output_dir=output_dir, stem="script_run")

    markdown_path = output_dir / "script_run.md"
    json_path = output_dir / "script_run.json"
    summary_path = output_dir / "script_run_summary.json"

    assert summary["report_paths"]["markdown"].endswith("script_run.md")
    assert summary["report_paths"]["json"].endswith("script_run.json")
    assert summary["summary_path"].endswith("script_run_summary.json")
    assert summary["final_phase"] == "SPRING 1903 ORDERS"
    assert summary["winner"] is None
    assert summary["total_phases"] == 7

    markdown_text = markdown_path.read_text(encoding="utf-8")
    report_data = json.loads(json_path.read_text(encoding="utf-8"))
    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))

    assert "# Diplomacy Test Run" in markdown_text
    assert "## Phase 7: WINTER 1902 ADJUSTMENTS -> SPRING 1903 ORDERS" in markdown_text
    assert report_data["total_phases"] == 7
    assert report_data["winner"] is None
    assert summary_data["final_phase"] == "SPRING 1903 ORDERS"


def test_play_multi_year_full_flow_reaches_rulebook_victory_condition():
    game = play_multi_year_full_flow(Game())

    assert game.get_current_phase() == "FALL 1903 COMPLETED"
    assert game.state.winner == "ENGLAND"
    assert game.get_supply_center_counts()["ENGLAND"] == 18
    assert game.get_battle_report_data()["total_phases"] == 10


def test_play_rulebook_normal_flow_matches_expected_adjustment_state():
    game = play_rulebook_normal_flow(Game())

    assert game.get_current_phase() == "SPRING 1903 ORDERS"
    assert game.state.winner is None
    assert game.get_supply_center_counts()["ENGLAND"] == 6
    assert game.get_supply_center_counts()["GERMANY"] == 2
    assert game.get_battle_report_data()["total_phases"] == 7
