"""Tests for data_loader module."""

from pathlib import Path
import pytest
import pandas as pd

from src.data_loader import (
    get_default_paths,
    load_all_candidates_data,
    load_job_description,
    load_ranked_csv,
    load_transparency_reports,
)


def test_load_ranked_csv_types_and_count():
    """Verify that ranked candidates CSV loads with correct types and exactly 100 rows."""
    df, source_path = load_ranked_csv()
    assert len(df) == 100, f"Expected 100 rows, found {len(df)}"
    assert "candidate_id" in df.columns
    assert "rank" in df.columns
    assert "score" in df.columns
    assert "reasoning" in df.columns

    # Candidate IDs must strictly be strings
    for cid in df["candidate_id"]:
        assert isinstance(cid, str)
        assert cid.startswith("CAND_")

    # Ranks must be integers 1 to 100
    ranks = list(df["rank"])
    assert sorted(ranks) == list(range(1, 101))

    # Scores must be floats and monotonic
    scores = list(df["score"])
    for s in scores:
        assert isinstance(s, float)
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Score at {i} ({scores[i]}) < {i+1} ({scores[i+1]})"


def test_load_all_candidates_data():
    """Verify loading unified top-100 rich candidate packages."""
    candidates, manifest = load_all_candidates_data()
    assert len(candidates) == 100
    assert manifest.get("status") == "PASSED"
    assert manifest.get("candidate_count") == 100

    cand_0 = candidates[0]
    assert cand_0["rank"] == 1
    assert "candidate_id" in cand_0
    assert "score" in cand_0
    assert "reasoning" in cand_0
    assert "title_score" in cand_0
    assert "skills" in cand_0


def test_load_transparency_reports():
    """Verify loading transparency report files."""
    reports = load_transparency_reports()
    assert isinstance(reports, dict)
    assert "ranking_report" in reports
    assert "quality_report" in reports


def test_load_job_description():
    """Verify reading job description text."""
    jd = load_job_description()
    assert isinstance(jd, str)
    assert len(jd) > 100
    assert "Redrob" in jd or "Senior AI Engineer" in jd


def test_missing_csv_error():
    """Verify clear FileNotFoundError on bad path."""
    with pytest.raises(FileNotFoundError):
        load_ranked_csv("non_existent_directory/fake_candidates.csv")
