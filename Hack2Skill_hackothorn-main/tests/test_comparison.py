"""Tests for candidate comparison and metric registry."""

import pytest
from src.comparison import (
    REGISTRY,
    ComparisonMetric,
    compare_metric,
    format_metric_value,
)


def test_registry_contains_defaults():
    """Verify registry has the required default core metrics."""
    defaults = REGISTRY.get_defaults()
    assert defaults == ["rank", "score", "reasoning"]

    for d in defaults:
        metric = REGISTRY.get(d)
        assert metric is not None
        assert metric.is_core is True
        assert metric.description != ""


def test_numeric_comparison_and_delta():
    """Verify numeric metric comparison computes exact difference and contextual text."""
    score_metric = REGISTRY.get("score")
    res = compare_metric(score_metric, 0.8500, 0.8000, cand_a_name="Alice", cand_b_name="Bob")

    assert res["status"] == "comparable"
    assert "Δ +0.0500" in res["difference"]
    assert "Alice higher by 0.0500" in res["interpretation"]


def test_rank_comparison():
    """Verify rank comparison correctly interprets lower numbers as better standing."""
    rank_metric = REGISTRY.get("rank")
    res = compare_metric(rank_metric, 1, 5, cand_a_name="Cand A", cand_b_name="Cand B")

    assert res["status"] == "comparable"
    assert "Cand A ranked 4 position(s) higher in pipeline ordering" in res["interpretation"]


def test_list_skills_comparison():
    """Verify skills comparison computes overlap, unique to A, and unique to B."""
    skills_metric = REGISTRY.get("skills")
    skills_a = [{"name": "Python"}, {"name": "PyTorch"}, {"name": "Docker"}]
    skills_b = [{"name": "Python"}, {"name": "Kubernetes"}, {"name": "AWS"}]

    res = compare_metric(skills_metric, skills_a, skills_b, cand_a_name="A", cand_b_name="B")
    assert res["status"] == "comparable"
    assert res["overlap_skills"] == ["python"]
    assert "pytorch" in res["only_a_skills"]
    assert "kubernetes" in res["only_b_skills"]


def test_missing_metric_handled_truthfully():
    """Verify missing values are never zero-filled or fabricated."""
    exp_metric = REGISTRY.get("years_of_experience")

    # Both missing
    res_both = compare_metric(exp_metric, None, None)
    assert res_both["status"] == "missing"
    assert res_both["val_a"] == "Not available in loaded data"
    assert res_both["val_b"] == "Not available in loaded data"

    # One missing
    res_one = compare_metric(exp_metric, 6.5, None, cand_a_name="A", cand_b_name="B")
    assert res_one["status"] == "partial"
    assert res_one["val_b"] == "Not available in loaded data"
    assert "Cannot compute difference" in res_one["interpretation"]


def test_format_metric_value():
    """Verify formatting helper outputs clean text."""
    metric = ComparisonMetric(id="test", label="Test", category="Test", value_type="numeric", description="desc")
    assert format_metric_value(metric, 10.0) == "10"
    assert format_metric_value(metric, 10.5) == "10.5"
    assert format_metric_value(metric, None) == "Not available in loaded data"
    assert format_metric_value(metric, "") == "Not available in loaded data"
