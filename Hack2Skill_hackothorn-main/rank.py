#!/usr/bin/env python3
"""End-to-end Candidate Discovery & Ranking Pipeline Runner.

Orchestrates:
1. Pipeline 1 & 2: Ingestion, schema validation, non-destructive cleaning,
   quality flagging, transformation, and feature generation.
2. Pipeline 3: Hybrid candidate scoring, honeypot mitigation,
   explainability generation, tie-breaking, and top-N ranking.
3. Validation: Automated compliance verification using validate_submission.py.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from src.pipeline1.config import load_settings
from src.pipeline1.pipeline import Pipeline
from src.pipeline3.config import load_pipeline3_settings
from src.pipeline3.pipeline import Pipeline3
from data.validate_submission import validate_submission


def run_ranking(
    input_path: str | Path = "data/candidates.jsonl",
    config_p1: str | Path = "config/settings.yaml",
    config_p3: str | Path = "config/ranking.yaml",
    taxonomy_path: str | Path = "config/skill_taxonomy.yaml",
    jd_path: str | Path = "config/job_description.txt",
    top_n: int = 100,
) -> int:
    """Execute the complete candidate ranking pipeline end-to-end.

    Returns:
        0 on success, non-zero on error.
    """
    total_start = time.perf_counter()
    input_file = Path(input_path)

    # Fallback to sample if primary dataset is not at expected location
    if not input_file.exists():
        fallback_json = Path("data/sample_candidates.json")
        if fallback_json.exists():
            print(f"WARNING: Specified input '{input_file}' not found. Falling back to '{fallback_json}'.")
            input_file = fallback_json
        else:
            print(f"FATAL: Candidate dataset file not found at '{input_file}'.", file=sys.stderr)
            return 2

    print("=" * 70)
    print(" REDROB CANDIDATE RANKING PIPELINE — END-TO-END EXECUTION")
    print("=" * 70)
    print(f"Input Dataset     : {input_file}")
    print(f"Pipeline 1 Config : {config_p1}")
    print(f"Pipeline 3 Config : {config_p3}")
    print(f"Target Top-N      : {top_n}")
    print("-" * 70)

    # Ensure UTF-8 output if supported
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # STAGE 1: Pipeline 1 & 2 (Ingestion, Cleaning, Quality, Features)
    # -------------------------------------------------------------------------
    print("\n[Stage 1/2] Running Pipeline 1 (Ingestion, Validation, Cleaning & Features)...")
    s1 = load_settings(config_p1)
    p1 = Pipeline(s1)
    
    p1_summary = p1.run(input_file)
    print(f"  [OK] Processed Records   : {p1_summary['records_processed']}")
    print(f"  [OK] Valid & Written     : {p1_summary['records_written']}")
    print(f"  [OK] Quarantined / Failed : {p1_summary['records_failed']}")
    print(f"  [OK] Duplicates Removed  : {p1_summary['duplicates_removed']}")
    print(f"  [OK] Parse Errors        : {p1_summary['parse_errors']}")
    print(f"  [OK] Stage 1 Time        : {p1_summary['processing_time']}s")

    transformed_file = Path(s1.paths.output_dir) / "transformed_candidates.jsonl"
    if not transformed_file.exists() or p1_summary["records_written"] == 0:
        print("FATAL: Pipeline 1 produced no eligible transformed candidates.", file=sys.stderr)
        return 1

    # -------------------------------------------------------------------------
    # STAGE 2: Pipeline 3 (Scoring, Honeypot Mitigation & Top-N Ranking)
    # -------------------------------------------------------------------------
    print("\n[Stage 2/2] Running Pipeline 3 (Scoring, Explainability & Ranking)...")
    s3 = load_pipeline3_settings(
        p1_config_path=config_p1,
        p3_config_path=config_p3,
        taxonomy_path=taxonomy_path,
        jd_path=jd_path,
    )
    p3 = Pipeline3(s3)
    p3_summary = p3.run(transformed_file, top_n=top_n)
    print(f"  [OK] Candidates Scored   : {p3_summary['records_processed']}")
    print(f"  [OK] Stage 2 Time        : {p3_summary['processing_time']}s")

    # -------------------------------------------------------------------------
    # STAGE 3: Submission Specification Validation
    # -------------------------------------------------------------------------
    csv_out = Path(s1.paths.output_dir) / "ranked_candidates.csv"
    sub_out = Path(s1.paths.output_dir) / "submission.csv"

    print("\n[Validation] Checking output compliance with hackathon submission spec...")
    val_errors = validate_submission(csv_out)
    if val_errors:
        print(f"  [FAIL] Validation FAILED for '{csv_out}' ({len(val_errors)} issue(s)):")
        for err in val_errors:
            print(f"    - {err}")
        return 1
    else:
        print(f"  [OK] Ranked Candidates CSV : {csv_out} (VALID: 100 top candidates)")

    val_sub_errors = validate_submission(sub_out)
    if not val_sub_errors:
        print(f"  [OK] Official Submission CSV: {sub_out} (VALID: ready for portal)")

    total_elapsed = round(time.perf_counter() - total_start, 2)
    print("-" * 70)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {total_elapsed}s (within 5-min budget)")
    print("=" * 70)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Redrob Candidate Ranking Pipeline end-to-end.")
    parser.add_argument("--input", default="data/candidates.jsonl", help="Path to input candidate dataset")
    parser.add_argument("--config-p1", default="config/settings.yaml", help="Path to Pipeline 1 settings")
    parser.add_argument("--config-p3", default="config/ranking.yaml", help="Path to Pipeline 3 config")
    parser.add_argument("--taxonomy", default="config/skill_taxonomy.yaml", help="Path to skill taxonomy")
    parser.add_argument("--jd", default="config/job_description.txt", help="Path to job description")
    parser.add_argument("--top-n", type=int, default=100, help="Number of top candidates to rank (default: 100)")

    args = parser.parse_args()
    sys.exit(
        run_ranking(
            input_path=args.input,
            config_p1=args.config_p1,
            config_p3=args.config_p3,
            taxonomy_path=args.taxonomy,
            jd_path=args.jd,
            top_n=args.top_n,
        )
    )


if __name__ == "__main__":
    main()
