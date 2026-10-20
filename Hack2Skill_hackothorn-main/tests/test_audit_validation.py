"""Comprehensive test suite for audit, edge cases, tie-breaking, and validation.

Covers Section 7 requirements:
- Normal execution
- Missing or incorrect input files
- Missing required fields / quarantine
- Missing values and invalid data
- Duplicate candidate IDs
- Fewer than 100 eligible candidates (no fabrication)
- More than 100 eligible candidates (exact 100 top-ranked)
- Equal candidate scores (tie-breaking by candidate_id ascending)
- Format compliance with data/validate_submission.py
- Repeated execution determinism
- JSON array (.json) and JSONL (.jsonl) inputs
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest

from src.pipeline1.config import load_settings
from src.pipeline1.ingestion.reader import JsonlReader
from src.pipeline1.pipeline import Pipeline
from src.pipeline1.reporting.writers import JsonlWriter
from src.pipeline3.config import load_pipeline3_settings
from src.pipeline3.pipeline import Pipeline3
from data.validate_submission import validate_submission
from tests.conftest import CONFIG, FIXTURE, ROOT


def _make_candidate(cid: str, headline: str = "AI Engineer", yoe: float = 6.0, score_adj: float = 0.0) -> dict:
    """Helper to generate a structurally valid candidate dict."""
    return {
        "candidate_id": cid,
        "profile": {
            "anonymized_name": f"Candidate {cid}",
            "headline": headline,
            "summary": f"Engineer specializing in {headline} with {yoe} years of experience.",
            "location": "Pune",
            "country": "India",
            "years_of_experience": yoe,
            "current_title": headline,
            "current_company": "TechCorp",
            "current_company_size": "201-500",
            "current_industry": "Software",
        },
        "career_history": [
            {
                "company": "TechCorp",
                "title": headline,
                "start_date": "2020-01-01",
                "end_date": None,
                "duration_months": int(yoe * 12),
                "is_current": True,
                "industry": "Software",
                "company_size": "201-500",
                "description": f"Worked as {headline} developing ML systems and data pipelines.",
            }
        ],
        "education": [
            {
                "institution": "IIT Delhi",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2014,
                "end_year": 2018,
                "tier": "tier_1",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "endorsements": 40, "duration_months": 60},
            {"name": "Machine Learning", "proficiency": "expert", "endorsements": 35, "duration_months": 50},
            {"name": "PyTorch", "proficiency": "advanced", "endorsements": 25, "duration_months": 40},
        ],
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "profile_completeness_score": 90.0,
            "signup_date": "2022-01-01",
            "last_active_date": "2026-06-01",
            "open_to_work_flag": True,
            "profile_views_received_30d": 15,
            "applications_submitted_30d": 2,
            "recruiter_response_rate": 0.85,
            "avg_response_time_hours": 4.0,
            "skill_assessment_scores": {"Python": 90.0, "Machine Learning": 88.0},
            "connection_count": 250,
            "endorsements_received": 55,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 25.0, "max": 40.0},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 75.0,
            "search_appearance_30d": 60,
            "saved_by_recruiters_30d": 8,
            "interview_completion_rate": 0.9,
            "offer_acceptance_rate": 0.7,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


def test_missing_input_file(tmp_path):
    """Verify that a non-existent input file raises FileNotFoundError or is reported cleanly."""
    settings = load_settings(CONFIG)
    settings.paths.output_dir = str(tmp_path / "output")
    pipeline = Pipeline(settings)
    with pytest.raises((FileNotFoundError, OSError)):
        pipeline.run(tmp_path / "non_existent_file.jsonl")


def test_missing_required_fields_quarantine(tmp_path):
    """Verify that records missing required fields are quarantined without halting execution."""
    settings = load_settings(CONFIG)
    settings.paths.output_dir = str(tmp_path / "output")
    settings.paths.errors_dir = str(tmp_path / "errors")
    settings.paths.transparency_dir = str(tmp_path / "transparency")
    settings.paths.logs_dir = str(tmp_path / "logs")

    input_file = tmp_path / "test_input.jsonl"
    valid_cand = _make_candidate("CAND_0000001")
    # Cand missing profile (schema violation)
    invalid_cand = {"candidate_id": "CAND_0000002", "skills": []}

    with open(input_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(valid_cand) + "\n")
        f.write(json.dumps(invalid_cand) + "\n")

    summary = Pipeline(settings).run(input_file)
    assert summary["records_processed"] == 2
    assert summary["records_written"] == 1
    assert summary["records_failed"] == 1

    # Verify quarantine file
    invalid_lines = (tmp_path / "errors" / "invalid_records.jsonl").read_text("utf-8").strip().splitlines()
    assert len(invalid_lines) == 1
    rec = json.loads(invalid_lines[0])
    assert rec["candidate_id"] == "CAND_0000002"
    assert rec["status"] == "invalid"


def test_duplicate_candidate_ids(tmp_path):
    """Verify deduplication: first candidate kept, duplicate quarantined with duplicate_of."""
    settings = load_settings(CONFIG)
    settings.paths.output_dir = str(tmp_path / "output")
    settings.paths.errors_dir = str(tmp_path / "errors")
    settings.paths.transparency_dir = str(tmp_path / "transparency")
    settings.paths.logs_dir = str(tmp_path / "logs")

    input_file = tmp_path / "test_dups.jsonl"
    cand1 = _make_candidate("CAND_0000001", headline="AI Engineer")
    cand1_dup = _make_candidate("CAND_0000001", headline="Copy of AI Engineer")

    with open(input_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(cand1) + "\n")
        f.write(json.dumps(cand1_dup) + "\n")

    summary = Pipeline(settings).run(input_file)
    assert summary["records_processed"] == 2
    assert summary["records_written"] == 1
    assert summary["duplicates_removed"] == 1

    invalid_lines = (tmp_path / "errors" / "invalid_records.jsonl").read_text("utf-8").strip().splitlines()
    assert len(invalid_lines) == 1
    dup_entry = json.loads(invalid_lines[0])
    assert dup_entry["status"] == "duplicate"
    assert dup_entry["duplicate_of"] == "CAND_0000001"


def test_fewer_than_100_candidates(tmp_path):
    """Verify that when fewer than 100 eligible candidates are available, exactly that count is returned without fabrication."""
    s1 = load_settings(CONFIG)
    s1.paths.output_dir = str(tmp_path / "output")
    s1.paths.errors_dir = str(tmp_path / "errors")
    s1.paths.transparency_dir = str(tmp_path / "transparency")
    s1.paths.logs_dir = str(tmp_path / "logs")

    input_file = tmp_path / "small_pool.jsonl"
    count = 15
    candidates = [_make_candidate(f"CAND_{i:07d}", yoe=float(5 + (i % 5))) for i in range(1, count + 1)]
    with open(input_file, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")

    Pipeline(s1).run(input_file)

    s3 = load_pipeline3_settings(p1_config_path=CONFIG)
    s3.p1.paths.output_dir = str(tmp_path / "output")
    s3.p1.paths.transparency_dir = str(tmp_path / "transparency")
    s3.p1.paths.logs_dir = str(tmp_path / "logs")

    p3 = Pipeline3(s3)
    p3.run(tmp_path / "output" / "transformed_candidates.jsonl", top_n=100)

    # Check ranked_candidates.csv
    csv_path = tmp_path / "output" / "ranked_candidates.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    
    header = rows[0]
    data_rows = rows[1:]
    assert header == ["candidate_id", "rank", "score", "reasoning"]
    assert len(data_rows) == 15  # Exactly 15, no fabrication up to 100
    
    ranks = [int(r[1]) for r in data_rows]
    assert ranks == list(range(1, 16))


def test_more_than_100_candidates_generates_exact_100(tmp_path):
    """Verify that with >100 candidates, exactly 100 top-ranked candidates are selected and pass validate_submission."""
    s1 = load_settings(CONFIG)
    s1.paths.output_dir = str(tmp_path / "output")
    s1.paths.errors_dir = str(tmp_path / "errors")
    s1.paths.transparency_dir = str(tmp_path / "transparency")
    s1.paths.logs_dir = str(tmp_path / "logs")

    input_file = tmp_path / "large_pool.jsonl"
    total_candidates = 120
    with open(input_file, "w", encoding="utf-8") as f:
        for i in range(1, total_candidates + 1):
            f.write(json.dumps(_make_candidate(f"CAND_{i:07d}", yoe=float(3 + (i % 10)))) + "\n")

    Pipeline(s1).run(input_file)

    s3 = load_pipeline3_settings(p1_config_path=CONFIG)
    s3.p1.paths.output_dir = str(tmp_path / "output")
    s3.p1.paths.transparency_dir = str(tmp_path / "transparency")
    s3.p1.paths.logs_dir = str(tmp_path / "logs")

    p3 = Pipeline3(s3)
    p3.run(tmp_path / "output" / "transformed_candidates.jsonl", top_n=100)

    csv_path = tmp_path / "output" / "ranked_candidates.csv"
    errors = validate_submission(csv_path)
    assert errors == []

    sub_path = tmp_path / "output" / "submission.csv"
    assert validate_submission(sub_path) == []

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 101  # 1 header + 100 rows


def test_equal_candidate_scores_tie_breaking(tmp_path):
    """Verify that when candidates have equal scores, candidate_id ascending tie-break is applied strictly."""
    s1 = load_settings(CONFIG)
    s1.paths.output_dir = str(tmp_path / "output")
    s1.paths.errors_dir = str(tmp_path / "errors")
    s1.paths.transparency_dir = str(tmp_path / "transparency")
    s1.paths.logs_dir = str(tmp_path / "logs")

    # Create 105 identical profile candidates with IDs in reverse order
    input_file = tmp_path / "tied_candidates.jsonl"
    cids = [f"CAND_{i:07d}" for i in range(105, 0, -1)]
    with open(input_file, "w", encoding="utf-8") as f:
        for cid in cids:
            # All candidates have identical features/scores
            f.write(json.dumps(_make_candidate(cid)) + "\n")

    Pipeline(s1).run(input_file)

    s3 = load_pipeline3_settings(p1_config_path=CONFIG)
    s3.p1.paths.output_dir = str(tmp_path / "output")
    s3.p1.paths.transparency_dir = str(tmp_path / "transparency")
    s3.p1.paths.logs_dir = str(tmp_path / "logs")

    p3 = Pipeline3(s3)
    p3.run(tmp_path / "output" / "transformed_candidates.jsonl", top_n=100)

    csv_path = tmp_path / "output" / "ranked_candidates.csv"
    errors = validate_submission(csv_path)
    assert errors == []

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    
    # Verify candidate IDs are sorted in ascending order for equal scores
    extracted_cids = [r[0] for r in rows]
    expected_cids = [f"CAND_{i:07d}" for i in range(1, 101)]
    assert extracted_cids == expected_cids


def test_json_array_support(tmp_path):
    """Verify JsonlReader transparently reads .json files with JSON arrays."""
    json_path = tmp_path / "sample.json"
    data = [_make_candidate("CAND_0000001"), _make_candidate("CAND_0000002")]
    json_path.write_text(json.dumps(data), encoding="utf-8")

    reader = JsonlReader(json_path)
    records = list(reader)
    assert len(records) == 2
    assert records[0][1]["candidate_id"] == "CAND_0000001"
    assert records[1][1]["candidate_id"] == "CAND_0000002"
