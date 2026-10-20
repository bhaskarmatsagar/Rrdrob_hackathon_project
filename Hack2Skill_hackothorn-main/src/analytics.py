"""Talent Analytics Engine for REDROB Recruit Intelligence.

Computes descriptive statistics, distributions, cohort comparisons, and
component breakdowns over the verified top candidate pool.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def compute_summary_statistics(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute verified descriptive statistics for the loaded candidate cohort."""
    if not candidates:
        return {}

    scores = [c["score"] for c in candidates if "score" in c and c["score"] is not None]
    if not scores:
        return {}

    scores_arr = np.array(scores)
    stats = {
        "count": len(candidates),
        "mean_score": float(np.mean(scores_arr)),
        "median_score": float(np.median(scores_arr)),
        "std_score": float(np.std(scores_arr)),
        "min_score": float(np.min(scores_arr)),
        "max_score": float(np.max(scores_arr)),
        "p25_score": float(np.percentile(scores_arr, 25)),
        "p75_score": float(np.percentile(scores_arr, 75)),
        "iqr_score": float(np.percentile(scores_arr, 75) - np.percentile(scores_arr, 25)),
    }

    # Experience stats if available
    exp_years = [c.get("years_of_experience", 0.0) for c in candidates if c.get("years_of_experience") is not None]
    if exp_years and any(e > 0 for e in exp_years):
        exp_arr = np.array(exp_years)
        stats["mean_exp"] = float(np.mean(exp_arr))
        stats["median_exp"] = float(np.median(exp_arr))
        stats["min_exp"] = float(np.min(exp_arr))
        stats["max_exp"] = float(np.max(exp_arr))

    return stats


def compute_cohort_comparison(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare Top 10 cohort vs Ranks 11–100 cohort."""
    if len(candidates) < 20:
        return {}

    sorted_cands = sorted(candidates, key=lambda x: x["rank"])
    top_10 = sorted_cands[:10]
    rest = sorted_cands[10:]

    def get_avg_metric(cohort: List[Dict[str, Any]], key: str) -> float:
        vals = [c.get(key, 0.0) for c in cohort if c.get(key) is not None]
        return float(np.mean(vals)) if vals else 0.0

    metrics = [
        ("Score", "score"),
        ("Title Alignment", "title_score"),
        ("Semantic Career", "semantic_score"),
        ("Company Tier", "company_score"),
        ("Experience Duration", "experience_score"),
        ("Skill Match", "skill_score"),
        ("Behavioral Stability", "behavioral_score"),
        ("Total Experience (Yrs)", "years_of_experience"),
    ]

    comparison_rows = []
    for label, key in metrics:
        avg_top = get_avg_metric(top_10, key)
        avg_rest = get_avg_metric(rest, key)
        diff = avg_top - avg_rest
        comparison_rows.append({
            "metric": label,
            "top_10_mean": round(avg_top, 4),
            "ranks_11_100_mean": round(avg_rest, 4),
            "delta": round(diff, 4),
            "pct_delta": round((diff / avg_rest * 100) if avg_rest != 0 else 0.0, 1),
        })

    return {
        "top_10_count": len(top_10),
        "rest_count": len(rest),
        "comparison_table": pd.DataFrame(comparison_rows),
    }


def compute_domain_distribution(candidates: List[Dict[str, Any]]) -> pd.DataFrame:
    """Calculate candidate counts and percentages per inferred domain."""
    domains = [c.get("candidate_domain", "Unknown") for c in candidates]
    df = pd.Series(domains).value_counts().reset_index()
    df.columns = ["Domain", "Candidate Count"]
    df["Percentage"] = (df["Candidate Count"] / len(candidates) * 100).round(1)
    return df


def compute_component_averages(candidates: List[Dict[str, Any]]) -> pd.DataFrame:
    """Calculate mean score components across the entire top 100."""
    components = [
        ("Title Alignment", "title_score", 0.25),
        ("Semantic Career", "semantic_score", 0.20),
        ("Experience Duration", "experience_score", 0.15),
        ("Skill Match", "skill_score", 0.15),
        ("Behavioral Stability", "behavioral_score", 0.15),
        ("Company Tier", "company_score", 0.10),
    ]

    rows = []
    for label, key, weight in components:
        vals = [c.get(key, 0.0) for c in candidates if c.get(key) is not None]
        mean_val = float(np.mean(vals)) if vals else 0.0
        rows.append({
            "Component": label,
            "Average Score": round(mean_val, 4),
            "Assigned Weight": f"{int(weight*100)}%",
            "Weighted Contribution": round(mean_val * weight, 4),
        })

    return pd.DataFrame(rows)


def analyze_score_ties_and_gaps(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect score ties, score plateaus, and largest gaps between adjacent ranks."""
    sorted_cands = sorted(candidates, key=lambda x: x["rank"])
    gaps = []
    ties = []

    for i in range(len(sorted_cands) - 1):
        c1 = sorted_cands[i]
        c2 = sorted_cands[i + 1]
        gap = round(c1["score"] - c2["score"], 5)
        if gap == 0.0:
            ties.append((c1["rank"], c2["rank"], c1["candidate_id"], c2["candidate_id"], c1["score"]))
        else:
            gaps.append({
                "rank_pair": f"{c1['rank']} → {c2['rank']}",
                "gap": gap,
                "c1_id": c1["candidate_id"],
                "c2_id": c2["candidate_id"],
                "c1_score": c1["score"],
                "c2_score": c2["score"],
            })

    # Sort largest gaps
    gaps.sort(key=lambda x: x["gap"], reverse=True)
    largest_gaps = gaps[:5]

    return {
        "total_ties": len(ties),
        "ties_list": ties,
        "largest_gaps": largest_gaps,
        "min_score": sorted_cands[-1]["score"],
        "max_score": sorted_cands[0]["score"],
        "total_score_spread": round(sorted_cands[0]["score"] - sorted_cands[-1]["score"], 4),
    }
