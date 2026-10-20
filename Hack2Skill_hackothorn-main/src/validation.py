"""Data Quality and Validation Suite for REDROB Recruit Intelligence.

Provides rigorous, read-only audit checks according to the challenge submission
specification and the UI/UX implementation plan.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")
REQUIRED_COLUMNS = ["candidate_id", "rank", "score", "reasoning"]
EXPECTED_ROWS = 100


class ValidationResult:
    def __init__(self) -> None:
        self.checks: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True
        self.stats: Dict[str, Any] = {}

    def add_check(self, name: str, status: str, detail: str) -> None:
        self.checks.append({
            "name": name,
            "status": status,  # "PASS", "WARN", "FAIL"
            "detail": detail,
        })
        if status == "FAIL":
            self.is_valid = False
            self.errors.append(f"[{name}] {detail}")
        elif status == "WARN":
            self.warnings.append(f"[{name}] {detail}")


def run_full_data_audit(csv_path: Path) -> ValidationResult:
    """Execute complete validation checks on the target ranked candidates CSV."""
    result = ValidationResult()

    # Check 1: File Existence & Accessibility
    if not csv_path.exists():
        result.add_check(
            "File Existence",
            "FAIL",
            f"Target file does not exist at '{csv_path}'",
        )
        return result
    
    file_size_kb = round(csv_path.stat().st_size / 1024, 2)
    result.stats["file_size_kb"] = file_size_kb
    result.stats["file_name"] = csv_path.name
    result.stats["file_path"] = str(csv_path)

    result.add_check(
        "File Accessibility",
        "PASS",
        f"File found ({file_size_kb} KB, UTF-8 readable)",
    )

    # Check 2: UTF-8 Encoding and Parsing
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                result.add_check("CSV Structure", "FAIL", "File is empty.")
                return result

            # Normalize header
            norm_header = [c.strip().lower() for c in header]
            
            # Check 3: Required Columns
            if norm_header == REQUIRED_COLUMNS:
                result.add_check(
                    "Column Header Integrity",
                    "PASS",
                    f"Exact expected columns in order: {', '.join(REQUIRED_COLUMNS)}",
                )
            else:
                missing = [col for col in REQUIRED_COLUMNS if col not in norm_header]
                if missing:
                    result.add_check(
                        "Column Header Integrity",
                        "FAIL",
                        f"Missing required columns: {missing}. Found: {norm_header}",
                    )
                    return result
                else:
                    result.add_check(
                        "Column Header Integrity",
                        "WARN",
                        f"Columns present but different order/casing. Found: {header}",
                    )

            data_rows = []
            for line_no, row in enumerate(reader, start=2):
                if any(cell.strip() for cell in row):
                    data_rows.append((line_no, row))

    except UnicodeDecodeError:
        result.add_check("Encoding", "FAIL", "File cannot be parsed as UTF-8.")
        return result
    except Exception as e:
        result.add_check("File Read", "FAIL", f"Unexpected error reading CSV: {e}")
        return result

    # Check 4: Row Count
    n_rows = len(data_rows)
    result.stats["row_count"] = n_rows

    if n_rows == EXPECTED_ROWS:
        result.add_check(
            "Row Count Verification",
            "PASS",
            f"Contains exactly {EXPECTED_ROWS} ranked candidate rows (rows 2 to 101).",
        )
    elif n_rows < EXPECTED_ROWS:
        result.add_check(
            "Row Count Verification",
            "WARN",
            f"Contains {n_rows} candidate rows (fewer than expected {EXPECTED_ROWS}).",
        )
    else:
        result.add_check(
            "Row Count Verification",
            "FAIL",
            f"Contains {n_rows} rows (expected exactly {EXPECTED_ROWS}).",
        )

    # Validate individual rows
    seen_ids = set()
    duplicate_ids = []
    seen_ranks = set()
    invalid_ids = []
    invalid_ranks = []
    invalid_scores = []
    empty_reasonings = []
    by_rank: List[Tuple[int, float, str, int]] = []

    for line_no, cells in data_rows:
        if len(cells) < len(REQUIRED_COLUMNS):
            result.add_check(
                "Row Format",
                "FAIL",
                f"Row {line_no} has {len(cells)} columns, expected {len(REQUIRED_COLUMNS)}.",
            )
            continue

        cid = cells[0].strip()
        rank_str = cells[1].strip()
        score_str = cells[2].strip()
        reasoning = cells[3].strip() if len(cells) > 3 else ""

        # Candidate ID check
        if not cid or not CANDIDATE_ID_PATTERN.match(cid):
            invalid_ids.append((line_no, cid))
        elif cid in seen_ids:
            duplicate_ids.append((line_no, cid))
        else:
            seen_ids.add(cid)

        # Rank check
        rank_val: Optional[int] = None
        try:
            rank_val = int(rank_str)
            if str(rank_val) != rank_str or not (1 <= rank_val <= 100):
                invalid_ranks.append((line_no, rank_str))
            else:
                seen_ranks.add(rank_val)
        except ValueError:
            invalid_ranks.append((line_no, rank_str))

        # Score check
        score_val: Optional[float] = None
        try:
            score_val = float(score_str)
            if score_val < 0.0:
                invalid_scores.append((line_no, score_str))
        except ValueError:
            invalid_scores.append((line_no, score_str))

        # Reasoning check
        if not reasoning:
            empty_reasonings.append(line_no)

        if rank_val is not None and score_val is not None and cid:
            by_rank.append((rank_val, score_val, cid, line_no))

    result.stats["unique_candidate_ids"] = len(seen_ids)
    result.stats["unique_ranks"] = len(seen_ranks)

    # Check 5: Candidate ID Validation
    if not invalid_ids and not duplicate_ids:
        result.add_check(
            "Candidate ID Compliance",
            "PASS",
            f"All {len(seen_ids)} IDs are strictly unique and match CAND_XXXXXXX format.",
        )
    else:
        if invalid_ids:
            result.add_check(
                "Candidate ID Compliance",
                "FAIL",
                f"Invalid candidate IDs detected at rows: {[x[0] for x in invalid_ids[:5]]}",
            )
        if duplicate_ids:
            result.add_check(
                "Candidate ID Uniqueness",
                "FAIL",
                f"Duplicate candidate IDs detected: {[x[1] for x in duplicate_ids[:5]]}",
            )

    # Check 6: Consecutive Rank Sequence
    missing_ranks = set(range(1, EXPECTED_ROWS + 1)) - seen_ranks
    if not invalid_ranks and not missing_ranks:
        result.add_check(
            "Rank Sequence Integrity",
            "PASS",
            f"Ranks 1 through {EXPECTED_ROWS} appear exactly once consecutively without gaps.",
        )
    else:
        detail = []
        if invalid_ranks:
            detail.append(f"Invalid rank values at rows {[x[0] for x in invalid_ranks[:5]]}")
        if missing_ranks:
            detail.append(f"Missing ranks: {sorted(list(missing_ranks))[:5]}")
        result.add_check("Rank Sequence Integrity", "FAIL", "; ".join(detail))

    # Check 7: Score Monotonicity (Non-increasing by rank)
    by_rank.sort(key=lambda x: x[0])
    monotonicity_violations = []
    tie_break_violations = []

    for i in range(len(by_rank) - 1):
        r1, s1, c1, _ = by_rank[i]
        r2, s2, c2, _ = by_rank[i + 1]

        if s1 < s2:
            monotonicity_violations.append((r1, s1, r2, s2))

        if s1 == s2 and c1 > c2:
            tie_break_violations.append((r1, r2, c1, c2))

    if not monotonicity_violations:
        result.add_check(
            "Score Monotonicity",
            "PASS",
            "Model scores decrease or stay equal monotonically with increasing rank.",
        )
    else:
        result.add_check(
            "Score Monotonicity",
            "FAIL",
            f"Inverted score ordering detected at {len(monotonicity_violations)} rank transitions.",
        )

    # Check 8: Tie-Breaking Policy
    if not tie_break_violations:
        result.add_check(
            "Deterministic Tie-Breaking",
            "PASS",
            "Equal scores are tie-broken by ascending candidate ID.",
        )
    else:
        result.add_check(
            "Deterministic Tie-Breaking",
            "FAIL",
            f"Tie-breaking rule violation at ranks: {[x[:2] for x in tie_break_violations[:5]]}",
        )

    # Check 9: Model Reasoning Text
    if not empty_reasonings:
        result.add_check(
            "Explainability Reasoning",
            "PASS",
            "100% of candidate rows have detailed explainability reasoning text.",
        )
    else:
        result.add_check(
            "Explainability Reasoning",
            "WARN",
            f"{len(empty_reasonings)} candidates have empty reasoning strings.",
        )

    return result
