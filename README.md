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

1. **Overview**: Status KPIs, score distribution histogram, rank vs. score decay curve, top 10 preview.
2. **Candidate Explorer**: Live search, domain filter, score & rank sliders, sorting, pagination, and quick actions.
3. **Candidate Profile**: Complete candidate record, model explainability text, radar/bar score breakdown, career history, skills, education, and platform availability signals.
4. **Compare Candidates**: Priority configurable comparison with dynamic `MetricRegistry` multi-select, numeric deltas, skills overlap/difference analysis, and guardrails against identical selection.
5. **Talent Analytics**: Descriptive statistics, cohort comparisons (Top 10 vs 11–100), domain pie chart, experience histogram, and score gap analysis.
6. **Data Quality & Audit**: Automated compliance testing against hackathon invariants, transparency reports inspector, and ground-truth disclaimers.
7. **Shortlist & Reports**: In-session shortlist review with status/notes, and official CSV/JSON downloads.

---

## 🧪 Testing & Verification

Run the complete 65-test verification suite (including frontend unit tests and pipeline integrity tests):

```powershell
python -m pytest tests/ -v
```
