# REDROB Recruit Intelligence — Candidate Discovery & Ranking Platform

This repository contains the candidate ranking pipeline and the **REDROB Recruit Intelligence** 7-page interactive Streamlit frontend built for the Redrob AI Hackathon.

---

## 🚀 Quickstart: Launching the Frontend

The application runs on **Python 3.11** and is designed to load instantly from disk-persisted artifacts without recalculating the ranking pipeline on UI navigation.

### 1. Install Dependencies
```powershell
# Using Python 3.11 virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Prepare / Verify Top-100 Artifacts (One-time Preparation)
The ranking pipeline takes ~4–5 minutes on 100,000 raw candidates. **You do NOT need to run it on every app launch.** The existing verified top-100 output is persisted on disk:
- `output/ranked_candidates.csv` (Canonical challenge output)
- `output/ranked_candidates_breakdown.csv` (Component score breakdown)
- `output/top_100_profiles.json` (Pre-extracted verified candidate attributes)
- `output/top_100_manifest.json` (Audit verification manifest)

To verify or regenerate the cached profiles at any time:
```powershell
python -m src.preparation
```

### 3. Launch Streamlit Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📱 Application Architecture & Features

The Streamlit frontend implements a restrained, high-density enterprise dashboard across 7 dedicated pages:

1. **Overview**
   - System status badge, loaded record counts, and data freshness.
   - Core KPI cards: Total candidates, highest score, mean score, validation status.
   - Interactive Plotly visualizations: Model score distribution histogram and rank-vs-score monotonicity curve.
   - Top 10 candidate leaderboard table with direct actions to inspect profile or compare.

2. **Candidate Explorer**
   - Real-time search by Candidate ID, Job Title, or Company name.
   - Domain filter (`ai_ml`, `devops`, `backend`, `frontend`), Rank slider (1–100), and Score range filter.
   - Multi-column sorting (Rank, Score, Experience) and configurable pagination (10, 25, 50, 100 per page).
   - Instant actions: View Full Profile, Set as Candidate A, Add/Remove Shortlist, and filtered CSV export.

3. **Candidate Profile**
   - Detailed inspection card with Candidate ID, Leaderboard Rank, Model Score, and Domain.
   - Model Explainability Card: Complete automated reasoning rationale, strengths, and honeypot quality checks.
   - Component Score Breakdown: Title alignment (25%), semantic match (20%), experience duration (15%), skill coverage (15%), behavioral stability (15%), and company tier (10%).
   - Full Career History timeline, verified skills inventory, academic background, and Redrob platform signals.
   - Truthful Data Availability checklist.

4. **Compare Candidates (Priority Feature)**
   - Side-by-side comparison of any two candidates from the top-100 cohort.
   - Guardrails against identical candidate selection.
   - **Dynamic Metric Selector**: Multi-select driven by a centralized `MetricRegistry`. Preselects `Rank`, `Model Score`, and `Reasoning`.
   - Discovers real optional metrics: scoring components, total experience, current role/company, skills overlap & differences, education, and platform availability.
   - Meaningful comparisons: numeric differences with delta (`Δ`), set-based skill overlap, and honest `Not available in loaded data` display (never zero-filled or fabricated).
   - Optional exploratory what-if reweighting tool, explicitly separated from official rankings.

5. **Talent Analytics**
   - Descriptive statistical summaries: Mean, median, standard deviation, interquartile range, and score spread.
   - Top 10 vs Ranks 11–100 cohort analysis table and grouped bar charts.
   - Domain distribution pie/donut chart and experience distribution histogram.
   - Score tie and plateau transition analysis.

6. **Data Quality & Audit**
   - Automated compliance audit checking file existence, required columns (`candidate_id`, `rank`, `score`, `reasoning`), exact 100 row count, ID regex (`CAND_XXXXXXX`), uniqueness, consecutive rank sequence (1–100), score monotonicity, and deterministic tie-breaking.
   - Pipeline transparency inspection tabs: Cleaning report, Quality flags report, Ranking weights, and manifest checksums.
   - Job description viewer.
   - Clear disclosure distinguishing technical compliance from empirical predictive hiring validity.

7. **Shortlist & Reports**
   - Recruiter working shortlist with customizable review statuses (`To Review`, `Shortlisted`, `Phone Screen`, `Interview`, `Not Selected`) and private notes.
   - Official Export Center:
     1. Official Challenge Submission CSV (`submission.csv`, strictly 100 rows).
     2. Component Score Breakdown CSV (`ranked_candidates_breakdown.csv`).
     3. Shortlisted Candidates CSV with custom review statuses.
     4. Complete Unified JSON Package (`top_100_candidate_profiles.json`).

---

## 🧪 Testing & Verification

Run the complete 65-test verification suite (including frontend unit tests and pipeline integrity tests):

```powershell
python -m pytest tests/ -v
```

### Frontend Test Coverage
- `tests/test_data_loader.py`: Verifies CSV parsing, string candidate IDs, 100 rows, score monotonicity, reports, and error handling.
- `tests/test_validation.py`: Verifies compliance auditor against the real submission CSV and validates rejection of malformed schemas, duplicate IDs, missing columns, and inverted score order.
- `tests/test_comparison.py`: Verifies metric registry defaults, delta calculations, rank direction interpretation, skills set overlap, and honest handling of missing attributes.

---

## 🔒 Model Integrity & Data Truthfulness

- **Preserved Ranks & Scores**: The frontend strictly displays original pipeline scores and ranks without recalculation, artificial smoothing, or bias modification.
- **No Hallucinated Data**: Missing metrics display as `Not available in loaded data`. No skills or credentials are ever invented.
- **Sub-Second Performance**: UI interactions read from persisted disk artifacts and Streamlit memory caches, never executing multi-minute ML pipelines during user browsing.
