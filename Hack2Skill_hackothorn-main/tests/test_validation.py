"""Tests for data validation and audit module."""

from pathlib import Path
import tempfile
import pytest

from src.data_loader import get_default_paths
from src.validation import run_full_data_audit, EXPECTED_ROWS


def test_audit_real_ranked_csv():
    """Verify that the actual pipeline output passes all submission checks."""
    paths = get_default_paths()
    res = run_full_data_audit(paths["ranked_csv"])
    assert res.is_valid is True, f"Validation failed with errors: {res.errors}"
    assert res.stats["row_count"] == EXPECTED_ROWS
    assert res.stats["unique_candidate_ids"] == EXPECTED_ROWS
    assert res.stats["unique_ranks"] == EXPECTED_ROWS

    # Check every check passed
    for c in res.checks:
        assert c["status"] in ["PASS", "WARN"], f"Check failed: {c}"


def test_audit_detects_missing_column(tmp_path):
    """Verify that missing required columns fail validation."""
    bad_csv = tmp_path / "bad_columns.csv"
    bad_csv.write_text("candidate_id,rank,score\nCAND_0000001,1,0.95\n", encoding="utf-8")
    res = run_full_data_audit(bad_csv)
    assert res.is_valid is False
    assert any("Missing required columns" in err for err in res.errors)


def test_audit_detects_duplicate_id(tmp_path):
    """Verify that duplicate candidate IDs fail validation."""
    lines = ["candidate_id,rank,score,reasoning"]
    for i in range(1, 101):
        # Force duplicate ID at rank 2
        cid = "CAND_0000001" if i == 2 else f"CAND_{i:07d}"
        lines.append(f"{cid},{i},{1.0 - i*0.005:.4f},Reasoning text here")

    bad_csv = tmp_path / "dup_id.csv"
    bad_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = run_full_data_audit(bad_csv)
    assert res.is_valid is False
    assert any("Duplicate candidate IDs detected" in err for err in res.errors)


def test_audit_detects_inverted_score_monotonicity(tmp_path):
    """Verify that inverted score ordering fails validation."""
    lines = ["candidate_id,rank,score,reasoning"]
    for i in range(1, 101):
        score = 0.50 if i == 1 else 0.90  # Inversion: rank 1 lower than rank 2
        lines.append(f"CAND_{i:07d},{i},{score:.4f},Reasoning")

    bad_csv = tmp_path / "inverted_score.csv"
    bad_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = run_full_data_audit(bad_csv)
    assert res.is_valid is False
    assert any("Inverted score ordering detected" in err for err in res.errors)


def test_audit_detects_missing_file():
    """Verify clean failure on non-existent file."""
    res = run_full_data_audit(Path("does_not_exist.csv"))
    assert res.is_valid is False
    assert any("File Existence" in err for err in res.errors)
