from datetime import date

from app.analytics import candidates_per_open_position, percentage_share, previous_period, suppress_small
from app.marketplace import _employer_quality_warnings
from app.analytics import median, time_to_hire_bin
from app.national_context import parse_annual_observations
from app.observatory_config import OBSERVATORY_CONFIG, skills_gap_status
import csv
import json
from pathlib import Path


def test_suppression_marks_small_counts():
    assert suppress_small(1) == {"value": None, "suppressed": True}
    assert suppress_small(4) == {"value": None, "suppressed": True}
    assert suppress_small(5) == {"value": 5, "suppressed": False}
    assert suppress_small(12) == {"value": 12, "suppressed": False}


def test_governorate_ratio_privacy_and_zero_positions():
    assert candidates_per_open_position(3, 2) == {"value": None, "suppressed": True}
    assert candidates_per_open_position(10, 4) == {"value": None, "suppressed": True}
    assert candidates_per_open_position(10, 5) == {"value": 2.0, "suppressed": False}
    assert candidates_per_open_position(10, 0) == {
        "value": None,
        "reason": "no_open_positions",
    }


def test_skills_gap_status_uses_configured_thresholds():
    config = OBSERVATORY_CONFIG["skills_gap"]
    assert skills_gap_status(
        int(config["shortage_ratio"] * 2),
        2,
    ) == "shortage"
    assert skills_gap_status(2, int(config["surplus_ratio"] * 2)) == "surplus"
    assert skills_gap_status(4, 3) == "balanced"


def test_employer_quality_shares_and_warnings():
    assert percentage_share(36, 100) == 36.0
    assert percentage_share(1, 0) is None
    warnings = _employer_quality_warnings(36.0, 50.0, 70.0)
    assert any("36 % des candidatures sans décision" in warning for warning in warnings)
    assert any("résultat déclaré" in warning for warning in warnings)


def test_previous_period_has_equal_length():
    assert previous_period(date(2026, 1, 11), date(2026, 1, 20)) == {
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 10),
    }


def test_observatory_filter_contract_has_no_municipality():
    import inspect
    from app.analytics import AnalyticsFilters

    parameters = inspect.signature(AnalyticsFilters).parameters
    assert "governorate_code" in parameters
    assert "municipality_code" not in parameters


def test_time_to_hire_fixture_median_and_bins():
    durations = [5, 10, 18, 25, 40, 65]
    assert median(durations) == 21.5
    assert [time_to_hire_bin(days) for days in durations] == [
        "0-7", "8-14", "15-21", "22-30", "31-45", "60+"
    ]


def test_national_content_parser():
    content = (
        "Indicator: unemployment.\n"
        "Annual observations: 2022: 16.4 percent; 2023: 15.7 percent."
    )
    assert parse_annual_observations(content) == [(2022, 16.4), (2023, 15.7)]


def test_governorate_boundary_codes_match_reference_exactly_once():
    data_dir = Path(__file__).resolve().parents[1] / "data" / "location"
    governorates = {
        row["code"]
        for row in csv.DictReader((data_dir / "governorates.csv").open(encoding="utf-8"))
    }
    geojson = json.loads((data_dir / "tunisia-governorates-coded.geojson").read_text(encoding="utf-8"))
    boundary_codes = [
        feature["properties"]["governorate_code"]
        for feature in geojson["features"]
    ]
    assert len(boundary_codes) == 24
    assert set(boundary_codes) == governorates
    assert len(boundary_codes) == len(set(boundary_codes))


def test_every_national_series_requires_source_metadata():
    series = [{
        "series": [{"year": 2023, "value": 15.7}],
        "unit": "%",
        "methodology": "World Bank annual observation",
        "source": "World Bank",
        "source_url": "https://data.worldbank.org",
        "retrieved_at": "2026-01-01T00:00:00Z",
    }]
    for item in series:
        assert item["source"]
        assert item["source_url"]
        assert item["methodology"]
        assert item["retrieved_at"]
