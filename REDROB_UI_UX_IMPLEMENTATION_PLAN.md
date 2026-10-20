# REDROB Recruit Intelligence — UI/UX & Implementation Plan

**Document type:** Product brief, UI/UX specification, and technical implementation plan  
**Target framework:** Streamlit  
**Target Python:** Python 3.11  
**Primary purpose:** Turn the existing Redrob AI Hackathon candidate-ranking pipeline and its ranked-candidate output into a polished, practical recruiter-facing analytics application.

---

## 1. Product vision

Build **REDROB Recruit Intelligence**, a clear and trustworthy candidate-ranking review workspace. A recruiter should be able to understand the overall ranking, find a candidate, inspect the model-provided reasoning, compare two candidates using selected metrics, review data quality, and export useful reports.

This is a **data application**, not a marketing website. It should feel like a carefully crafted internal recruitment tool: restrained, readable, efficient, and credible. Avoid an oversized promotional hero, decorative charts without a purpose, exaggerated claims, flashy animations, or generic “AI product” styling.

### Primary users

- A recruiter reviewing the output of the existing ranking pipeline.
- A hiring manager comparing selected candidates.
- A project evaluator checking the ranking output, data quality, and transparency.

### Main product principle

**Make the existing model output easier to review without quietly changing the model.** The UI must not modify scores or ranks simply to make a chart look better. Distinguish the existing pipeline score/rank from any optional job-specific comparison or analysis added later.

---

## 2. Existing data and non-negotiable constraints

The current ranking output is a CSV and is known to contain these fields:

- `candidate_id`
- `rank`
- `score`
- `reasoning`

The project is intended to produce exactly 100 unique top-ranked candidates when at least 100 eligible candidates are available. The UI must verify the file it actually loads and must not represent a partial or incomplete file as the true top 100.

### Data truthfulness rules

1. Inspect the repository, pipeline documentation, scripts, configuration, and existing output before coding.
2. Reuse the current pipeline and output. Do not rewrite the model or change its ranking logic without a concrete defect and explicit explanation.
3. Treat the four fields above as the minimum supported profile. Never invent skills, years of experience, education, projects, certifications, job fit, or candidate history.
4. Additional metrics must be discovered from real input data, a documented feature output, or a supplied candidate-profile file. If a metric is not available, mark it **Not available in loaded data** and do not fill it with a guessed value.
5. `score` must be labeled **Model Score**, not “probability,” “accuracy,” or “chance of hire,” unless the original model documentation proves that interpretation.
6. Explain that technical ranking validation is not the same as proving real-world hiring success.
7. Do not describe the candidates as objectively “best hires.” Use terms such as “highest-ranked by the current model.”
8. Do not use protected or sensitive personal attributes as ranking or comparison criteria. Do not infer them. Avoid adding photos, age, religion, caste, race, disability, or other sensitive demographic data to the recruiter comparison UI.
9. Do not expose secrets, environment files, API keys, private raw files, or large datasets through the app or Git.

---

## 3. Information architecture and navigation

1. **Overview** — system status, summary KPIs, score distribution, top candidates.
2. **Candidate Explorer** — searchable and filterable candidate table.
3. **Candidate Profile** — detailed view of one selected candidate.
4. **Compare Candidates** — choose two candidates and choose which available metrics to compare.
5. **Talent Analytics** — descriptive analysis of the loaded ranking output.
6. **Data Quality & Audit** — source-file validation, data-quality checks, and clear warnings.
7. **Shortlist & Reports** — select, review, and export candidates.

---

## 4. Visual direction and design system

| Token | Hex | Use |
|---|---|---|
| `ink` | `#243746` | Primary text, headings, dark emphasis |
| `navy` | `#263F52` | Sidebar/primary brand area, selected navigation accents |
| `canvas` | `#F5F4EF` | Warm off-white page background where Streamlit theming allows |
| `surface` | `#FFFFFF` | Cards, tables, panels |
| `sage` | `#6F8F7A` | Positive/selected states and restrained primary action accents |
| `sage-light` | `#E6EEE8` | Subtle selected/positive backgrounds |
| `amber` | `#C58B43` | Warnings and secondary highlights only |
| `amber-light` | `#F7EEDF` | Warning backgrounds |
| `slate` | `#667784` | Secondary text and muted labels |
| `line` | `#DCE2E3` | Borders and dividers |
| `danger` | `#B9564D` | Errors or failed validation only |
| `danger-light` | `#F8E9E7` | Error backgrounds |
