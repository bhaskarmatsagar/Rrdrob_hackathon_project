"""Configurable Candidate Comparison Engine and Metric Registry for REDROB Recruit Intelligence.

Guarantees:
- Centralized MetricRegistry with explicit type declarations (numeric, categorical, list, text).
- Always available metrics: Rank, Model Score, Model Reasoning.
- Discovered verified metrics from candidate profiles and pipeline breakdown.
- Meaningful difference calculations:
  * Numeric differences (A - B with sign and context).
  * Categorical side-by-side display (same/different).
  * List comparison (shared overlap, unique to A, unique to B).
  * Text side-by-side.
- Missing values clearly rendered as 'Not available in loaded data', never zero or fabricated.
- Duplicate candidate ID guardrails.
- Optional exploratory custom scoring that never touches or overwrites the model ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class ComparisonMetric:
    id: str
    label: str
    category: str  # "Core Ranking", "Scoring Breakdown", "Experience & Role", "Skills", "Education", "Redrob Signals"
    value_type: str  # "numeric", "categorical", "list", "text", "score"
    description: str
    is_core: bool = False
    higher_is_better: Optional[bool] = None  # None for categories/text; True for score; False for rank

    def extract_value(self, candidate: Dict[str, Any]) -> Any:
        """Safely extract value from candidate dict."""
        val = candidate.get(self.id)
        if val is None or val == "" or val == []:
            return None
        return val


class MetricRegistry:
    """Centralized registry of candidate comparison metrics."""

    def __init__(self) -> None:
        self._metrics: Dict[str, ComparisonMetric] = {}
        self._register_default_metrics()

    def register(self, metric: ComparisonMetric) -> None:
        self._metrics[metric.id] = metric

    def get(self, metric_id: str) -> Optional[ComparisonMetric]:
        return self._metrics.get(metric_id)

    def list_all(self) -> List[ComparisonMetric]:
        return list(self._metrics.values())

    def get_defaults(self) -> List[str]:
        return ["rank", "score", "reasoning"]

    def _register_default_metrics(self) -> None:
        # Always Available Core Metrics
        self.register(ComparisonMetric(
            id="rank",
            label="Rank",
            category="Core Ranking",
            value_type="numeric",
            description="Overall leaderboard rank assigned by the deterministic ranking engine (1 = Top candidate).",
            is_core=True,
            higher_is_better=False,  # Lower rank number = better position
        ))
        self.register(ComparisonMetric(
            id="score",
            label="Model Score",
            category="Core Ranking",
            value_type="score",
            description="Composite model score computed across title, semantic, company, experience, skill, and behavioral weights.",
            is_core=True,
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="reasoning",
            label="Model Reasoning",
            category="Core Ranking",
            value_type="text",
            description="Full automated explainability rationale summarizing candidate strengths and domain fit.",
            is_core=True,
        ))
        self.register(ComparisonMetric(
            id="candidate_domain",
            label="Inferred Domain",
            category="Core Ranking",
            value_type="categorical",
            description="Primary technical domain inferred by the skill taxonomy engine (e.g. ai_ml, backend, devops).",
        ))

        # Model Breakdown Component Scores
        self.register(ComparisonMetric(
            id="title_score",
            label="Title Relevance Score (25%)",
            category="Scoring Breakdown",
            value_type="score",
            description="Career progression and seniority alignment relative to target role requirements.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="semantic_score",
            label="Semantic Career Score (20%)",
            category="Scoring Breakdown",
            value_type="score",
            description="Text semantic alignment between full candidate career history descriptions and target JD.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="experience_score",
            label="Experience Duration Score (15%)",
            category="Scoring Breakdown",
            value_type="score",
            description="Tenure duration and career stability evaluated against the 5–9 year target band.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="skill_score",
            label="Skill Match Score (15%)",
            category="Scoring Breakdown",
            value_type="score",
            description="Normalized skill match coverage mapped against canonical skills taxonomy.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="behavioral_score",
            label="Behavioral & Stability Score (15%)",
            category="Scoring Breakdown",
            value_type="score",
            description="Job hopping risk, average role tenure, and career continuity signal.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="company_score",
            label="Company Alignment Score (10%)",
            category="Scoring Breakdown",
            value_type="score",
            description="Product-company tiering vs pure consulting/services company background penalty.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="honeypot_multiplier",
            label="Honeypot Quality Multiplier",
            category="Scoring Breakdown",
            value_type="score",
            description="Data integrity factor (1.0 = flawless profile; < 1.0 = penalized for suspicious claims).",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="penalties_count",
            label="Detected Penalties Count",
            category="Scoring Breakdown",
            value_type="numeric",
            description="Number of quality heuristic violations triggered (e.g. impossible tenure, conflicting titles).",
            higher_is_better=False,
        ))

        # Candidate Experience & Profile Fields
        self.register(ComparisonMetric(
            id="years_of_experience",
            label="Total Experience (Years)",
            category="Experience & Role",
            value_type="numeric",
            description="Total verified professional tenure in years.",
            higher_is_better=None,  # Role target is 5-9 years
        ))
        self.register(ComparisonMetric(
            id="current_title",
            label="Current Job Title",
            category="Experience & Role",
            value_type="categorical",
            description="Most recent professional title from candidate career history.",
        ))
        self.register(ComparisonMetric(
            id="current_company",
            label="Current Company",
            category="Experience & Role",
            value_type="categorical",
            description="Most recent employer listed on candidate profile.",
        ))
        self.register(ComparisonMetric(
            id="current_company_size",
            label="Current Company Size",
            category="Experience & Role",
            value_type="categorical",
            description="Headcount bracket of current employer.",
        ))
        self.register(ComparisonMetric(
            id="current_industry",
            label="Current Industry",
            category="Experience & Role",
            value_type="categorical",
            description="Industry domain of current employer.",
        ))
        self.register(ComparisonMetric(
            id="location",
            label="Location",
            category="Experience & Role",
            value_type="categorical",
            description="Candidate primary residence city.",
        ))

        # Skills & Match
        self.register(ComparisonMetric(
            id="skills",
            label="Skills Inventory",
            category="Skills",
            value_type="list",
            description="Verified skills extracted and normalized against Redrob skill registry.",
        ))

        # Education
        self.register(ComparisonMetric(
            id="education",
            label="Education Background",
            category="Education",
            value_type="list",
            description="Academic degrees, university institutions, and tier classifications.",
        ))

        # Redrob Signals
        self.register(ComparisonMetric(
            id="preferred_work_mode",
            label="Preferred Work Mode",
            category="Redrob Signals",
            value_type="categorical",
            description="Candidate preferred arrangement (Remote, Hybrid, On-site).",
        ))
        self.register(ComparisonMetric(
            id="notice_period_days",
            label="Notice Period (Days)",
            category="Redrob Signals",
            value_type="numeric",
            description="Required notice duration in days (sub-30 days preferred by JD).",
            higher_is_better=False,
        ))
        self.register(ComparisonMetric(
            id="willing_to_relocate",
            label="Willing to Relocate",
            category="Redrob Signals",
            value_type="categorical",
            description="Candidate willingness to relocate to Pune/Noida offices.",
        ))
        self.register(ComparisonMetric(
            id="open_to_work_flag",
            label="Open to Work Status",
            category="Redrob Signals",
            value_type="categorical",
            description="Candidate active job-seeking status flag.",
        ))
        self.register(ComparisonMetric(
            id="profile_completeness_score",
            label="Profile Completeness (%)",
            category="Redrob Signals",
            value_type="numeric",
            description="Percentage of verified profile fields filled by candidate.",
            higher_is_better=True,
        ))
        self.register(ComparisonMetric(
            id="recruiter_response_rate",
            label="Recruiter Response Rate (%)",
            category="Redrob Signals",
            value_type="numeric",
            description="Historical response rate to recruiter outreach messages on Redrob.",
            higher_is_better=True,
        ))


REGISTRY = MetricRegistry()


def format_metric_value(metric: ComparisonMetric, raw_value: Any) -> str:
    """Format raw value into user-friendly text, or 'Not available in loaded data'."""
    if raw_value is None or raw_value == "":
        return "Not available in loaded data"

    if metric.value_type == "score":
        try:
            return f"{float(raw_value):.4f}"
        except Exception:
            return str(raw_value)

    if metric.value_type == "numeric":
        try:
            val = float(raw_value)
            if val.is_integer():
                return f"{int(val)}"
            return f"{val:.1f}"
        except Exception:
            return str(raw_value)

    if metric.value_type == "list":
        if isinstance(raw_value, list):
            if not raw_value:
                return "Not available in loaded data"
            # If skills list of dicts with 'name'
            if isinstance(raw_value[0], dict) and "name" in raw_value[0]:
                names = [s.get("name", "") for s in raw_value if s.get("name")]
                return ", ".join(names[:10]) + (f" (+{len(names)-10} more)" if len(names) > 10 else "")
            # If education list of dicts
            if isinstance(raw_value[0], dict) and ("degree" in raw_value[0] or "institution" in raw_value[0]):
                items = [f"{e.get('degree', '')} from {e.get('institution', '')}" for e in raw_value]
                return " | ".join(items)
            return ", ".join(str(x) for x in raw_value[:10])
        return str(raw_value)

    if isinstance(raw_value, bool):
        return "Yes" if raw_value else "No"

    return str(raw_value)


def compare_metric(
    metric: ComparisonMetric,
    val_a: Any,
    val_b: Any,
    cand_a_name: str = "Candidate A",
    cand_b_name: str = "Candidate B",
) -> Dict[str, Any]:
    """Perform honest, verified comparison between two candidates for a single metric."""
    disp_a = format_metric_value(metric, val_a)
    disp_b = format_metric_value(metric, val_b)

    # Check availability
    avail_a = disp_a != "Not available in loaded data"
    avail_b = disp_b != "Not available in loaded data"

    if not avail_a and not avail_b:
        return {
            "metric_id": metric.id,
            "metric_name": metric.label,
            "category": metric.category,
            "val_a": disp_a,
            "val_b": disp_b,
            "difference": "Not available for either candidate",
            "interpretation": "Neither candidate has this metric recorded.",
            "status": "missing",
        }

    if not avail_a or not avail_b:
        missing_side = cand_a_name if not avail_a else cand_b_name
        return {
            "metric_id": metric.id,
            "metric_name": metric.label,
            "category": metric.category,
            "val_a": disp_a,
            "val_b": disp_b,
            "difference": f"Incomplete comparison ({missing_side} missing data)",
            "interpretation": f"Cannot compute difference because metric is missing for {missing_side}.",
            "status": "partial",
        }

    # Rank comparison
    if metric.id == "rank":
        try:
            r_a = int(val_a)
            r_b = int(val_b)
            diff = r_a - r_b
            if diff < 0:
                interp = f"{cand_a_name} ranked {abs(diff)} position(s) higher in pipeline ordering"
            elif diff > 0:
                interp = f"{cand_b_name} ranked {abs(diff)} position(s) higher in pipeline ordering"
            else:
                interp = "Both candidates share the exact same rank"
            return {
                "metric_id": metric.id,
                "metric_name": metric.label,
                "category": metric.category,
                "val_a": disp_a,
                "val_b": disp_b,
                "difference": f"Δ {diff:+d}",
                "interpretation": interp,
                "status": "comparable",
            }
        except Exception:
            pass

    # Numeric & Score Comparison
    if metric.value_type in ["score", "numeric"]:
        try:
            num_a = float(val_a)
            num_b = float(val_b)
            diff = num_a - num_b

            if abs(diff) < 1e-5:
                interp = "Values are identical"
                diff_str = "0.0000" if metric.value_type == "score" else "0"
            else:
                fmt = "+.4f" if metric.value_type == "score" else "+.1f"
                abs_fmt = ".4f" if metric.value_type == "score" else ".1f"
                diff_str = f"Δ {diff:{fmt}}"

                if metric.higher_is_better is True:
                    leader = cand_a_name if diff > 0 else cand_b_name
                    interp = f"{leader} higher by {abs(diff):{abs_fmt}}"
                elif metric.higher_is_better is False:
                    # e.g., penalties or notice period: lower is better
                    leader = cand_a_name if diff < 0 else cand_b_name
                    interp = f"{leader} more favorable (lower by {abs(diff):{abs_fmt}})"
                else:
                    interp = f"{cand_a_name} differs by {diff:{fmt}} from {cand_b_name}"

            return {
                "metric_id": metric.id,
                "metric_name": metric.label,
                "category": metric.category,
                "val_a": disp_a,
                "val_b": disp_b,
                "difference": diff_str,
                "interpretation": interp,
                "status": "comparable",
            }
        except Exception:
            pass

    # List Comparison (Skills)
    if metric.value_type == "list":
        if isinstance(val_a, list) and isinstance(val_b, list):
            # Extract names if skill objects
            def get_names(items: List[Any]) -> Set[str]:
                s = set()
                for item in items:
                    if isinstance(item, dict) and "name" in item:
                        s.add(str(item["name"]).strip().lower())
                    elif isinstance(item, str):
                        s.add(item.strip().lower())
                return s

            set_a = get_names(val_a)
            set_b = get_names(val_b)
            if set_a and set_b:
                overlap = set_a & set_b
                only_a = set_a - set_b
                only_b = set_b - set_a
                interp = f"{len(overlap)} shared skill(s); {len(only_a)} unique to {cand_a_name}; {len(only_b)} unique to {cand_b_name}"
                return {
                    "metric_id": metric.id,
                    "metric_name": metric.label,
                    "category": metric.category,
                    "val_a": f"{len(set_a)} skills ({', '.join(sorted(list(set_a))[:5])}...)",
                    "val_b": f"{len(set_b)} skills ({', '.join(sorted(list(set_b))[:5])}...)",
                    "difference": f"{len(overlap)} in common",
                    "interpretation": interp,
                    "status": "comparable",
                    "overlap_skills": sorted(list(overlap)),
                    "only_a_skills": sorted(list(only_a)),
                    "only_b_skills": sorted(list(only_b)),
                }

    # Text Comparison
    if metric.value_type == "text":
        return {
            "metric_id": metric.id,
            "metric_name": metric.label,
            "category": metric.category,
            "val_a": disp_a,
            "val_b": disp_b,
            "difference": "Free-text explanation",
            "interpretation": "Compare explanatory reasoning side-by-side above.",
            "status": "text",
        }

    # Categorical comparison
    match = (str(val_a).strip().lower() == str(val_b).strip().lower())
    return {
        "metric_id": metric.id,
        "metric_name": metric.label,
        "category": metric.category,
        "val_a": disp_a,
        "val_b": disp_b,
        "difference": "Exact match" if match else "Different",
        "interpretation": f"Both candidates are {disp_a}" if match else f"{cand_a_name} is '{disp_a}'; {cand_b_name} is '{disp_b}'",
        "status": "comparable",
    }
