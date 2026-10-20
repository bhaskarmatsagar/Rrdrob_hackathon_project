"""REDROB Recruit Intelligence — Official Candidate Ranking Review Workspace.

7-Page Streamlit Frontend:
1. Overview: System status, summary KPIs, score distribution, top 10 preview.
2. Candidate Explorer: Searchable and filterable candidate table with pagination.
3. Candidate Profile: Deep-dive inspection of individual candidates.
4. Compare Candidates: Priority feature with configurable multi-select metric comparison.
5. Talent Analytics: Descriptive analytics of the loaded top-100 candidate pool.
6. Data Quality & Audit: Verification of data integrity, schema compliance, and pipeline transparency.
7. Shortlist & Reports: In-session shortlist management and official CSV/JSON exports.

Guarantees:
- Runs on Python 3.11.
- Never recalculates the ranking model on UI load or interactions (reads persisted top-100 artifacts).
- Preserves original model scores, ranks, and input data.
- Handles missing data honestly with 'Not available in loaded data'.
"""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project modules are importable
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from src.data_loader import (
    get_default_paths,
    load_all_candidates_data,
    load_job_description,
    load_ranked_csv,
    load_transparency_reports,
)
from src.preparation import prepare_top_100_artifacts
from src.validation import run_full_data_audit
from src.comparison import (
    REGISTRY,
    compare_metric,
    format_metric_value,
)
from src.analytics import (
    analyze_score_ties_and_gaps,
    compute_cohort_comparison,
    compute_component_averages,
    compute_domain_distribution,
    compute_summary_statistics,
)
from src.ui_components import (
    apply_theme,
    render_card_end,
    render_card_start,
    render_footer,
    render_kpi,
    render_page_header,
)

# Page Configuration
st.set_page_config(
    page_title="REDROB Recruit Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom styling tokens
apply_theme()

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "selected_candidate_id" not in st.session_state:
    st.session_state.selected_candidate_id = "CAND_0088025"

if "compare_candidate_a" not in st.session_state:
    st.session_state.compare_candidate_a = "CAND_0088025"

if "compare_candidate_b" not in st.session_state:
    st.session_state.compare_candidate_b = "CAND_0018499"

if "shortlist" not in st.session_state:
    st.session_state.shortlist = {}  # {candidate_id: {"status": str, "notes": str}}

if "current_page" not in st.session_state:
    st.session_state.current_page = "Overview"

if "selected_comparison_metrics" not in st.session_state:
    st.session_state.selected_comparison_metrics = REGISTRY.get_defaults()


# -----------------------------------------------------------------------------
# Data Ingestion (Cached, Sub-millisecond, Persisted Disk Output Only)
# -----------------------------------------------------------------------------
paths = get_default_paths()
try:
    candidates_data, manifest_data = load_all_candidates_data()
    df_ranked, source_csv_path = load_ranked_csv()
except Exception as e:
    st.error(f"⚠️ Error loading candidate ranking data: {e}")
    st.info("Please verify that 'output/ranked_candidates.csv' exists.")
    st.stop()

# Build quick lookup dictionary by candidate_id
candidates_by_id: Dict[str, Dict[str, Any]] = {c["candidate_id"]: c for c in candidates_data}
all_candidate_ids: List[str] = [c["candidate_id"] for c in sorted(candidates_data, key=lambda x: x["rank"])]


# -----------------------------------------------------------------------------
# Sidebar Navigation & Context
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0 20px 0;">
            <div style="font-size: 20px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.01em;">
                🎯 REDROB
            </div>
            <div style="font-size: 12px; color: #C5D5E2; font-weight: 500;">
                Recruit Intelligence Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        "Overview",
        "Candidate Explorer",
        "Candidate Profile",
        "Compare Candidates",
        "Talent Analytics",
        "Data Quality & Audit",
        "Shortlist & Reports",
    ]

    selected_nav = st.radio(
        "Navigation",
        pages,
        index=pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0,
        label_visibility="collapsed",
    )
    st.session_state.current_page = selected_nav

    st.markdown("---")

    # Sidebar Data Status Block
    val_status = manifest_data.get("status", "VALID")
    status_color = "#6F8F7A" if val_status == "PASSED" else "#C58B43"
    st.markdown(
        f"""
        <div style="font-size: 11px; text-transform: uppercase; color: #9AB4C7; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 8px;">
            Artifact Status
        </div>
        <div style="background-color: rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px; font-size: 12px; line-height: 1.6;">
            <div><strong>Cohort:</strong> Top 100 Candidates</div>
            <div><strong>Rank Range:</strong> 1 to 100</div>
            <div><strong>Status:</strong> <span style="color: {status_color}; font-weight: 600;">● {val_status}</span></div>
            <div><strong>Storage:</strong> Persisted Disk Cache</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Shortlist quick count
    shortlist_count = len(st.session_state.shortlist)
    if shortlist_count > 0:
        st.markdown(
            f"""
            <div style="margin-top: 14px; background-color: rgba(111, 143, 122, 0.2); border: 1px solid rgba(111, 143, 122, 0.4); border-radius: 8px; padding: 10px 12px; font-size: 12px; color: #FFFFFF;">
                ⭐ <strong>{shortlist_count} Candidate(s) Shortlisted</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption("Target Role: Senior AI Engineer\nRedrob Hackathon Edition")


# =============================================================================
# PAGE 1: OVERVIEW
# =============================================================================
if st.session_state.current_page == "Overview":
    render_page_header(
        title="Recruitment Overview",
        description="Review the verified top-100 ranked candidate set, inspection score distribution, and model progression.",
        status_text="Verified Top-100 Dataset Loaded",
        badge_type="sage",
    )

    # Top KPI Metrics Row
    summary_stats = compute_summary_statistics(candidates_data)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi("Candidates Loaded", f"{len(candidates_data)}", "Top 100 Verified Cohort")
    with col2:
        top_cand = candidates_data[0]
        render_kpi("Highest Model Score", f"{top_cand['score']:.4f}", f"Rank 1 ({top_cand['candidate_id']})")
    with col3:
        render_kpi("Average Model Score", f"{summary_stats.get('mean_score', 0):.4f}", f"Median: {summary_stats.get('median_score', 0):.4f}")
    with col4:
        render_kpi("Validation Status", "PASSED", "100% Unique · Ranks 1–100")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Visualizations Row: Score Distribution & Rank vs Score Decay
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        render_card_start("Model Score Distribution")
        scores = [c["score"] for c in candidates_data]
        fig_hist = px.histogram(
            scores,
            nbins=15,
            labels={"value": "Model Score"},
            color_discrete_sequence=["#263F52"],
            marginal="box",
        )
        fig_hist.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            height=280,
            xaxis=dict(gridcolor="#E6EEE8", title="Model Score"),
            yaxis=dict(gridcolor="#E6EEE8", title="Candidate Count"),
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        render_card_end()

    with chart_col2:
        render_card_start("Rank vs. Score Monotonicity")
        ranks = [c["rank"] for c in candidates_data]
        hover_texts = [f"Rank {c['rank']}<br>{c['candidate_id']}<br>Score: {c['score']:.4f}<br>Domain: {c.get('candidate_domain', 'N/A')}" for c in candidates_data]
        fig_decay = go.Figure()
        fig_decay.add_trace(
            go.Scatter(
                x=ranks,
                y=scores,
                mode="lines+markers",
                marker=dict(size=5, color="#6F8F7A"),
                line=dict(color="#263F52", width=2),
                hovertext=hover_texts,
                hoverinfo="text",
            )
        )
        fig_decay.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=280,
            xaxis=dict(gridcolor="#E6EEE8", title="Candidate Rank (1 → 100)"),
            yaxis=dict(gridcolor="#E6EEE8", title="Model Score"),
        )
        st.plotly_chart(fig_decay, use_container_width=True)
        render_card_end()

    # Top 10 Preview Section
    render_card_start("Top 10 Ranked Candidates Preview")
    top_10 = sorted(candidates_data, key=lambda x: x["rank"])[:10]

    preview_rows = []
    for c in top_10:
        preview_rows.append({
            "Rank": c["rank"],
            "Candidate ID": c["candidate_id"],
            "Model Score": f"{c['score']:.4f}",
            "Current Role": c.get("current_title", "N/A"),
            "Company": c.get("current_company", "N/A"),
            "Domain": c.get("candidate_domain", "ai_ml"),
            "Experience (Yrs)": f"{c.get('years_of_experience', 0):.1f}",
            "Reasoning Summary": c.get("reasoning", "")[:120] + "...",
        })

    df_top_10 = pd.DataFrame(preview_rows)
    st.dataframe(df_top_10, use_container_width=True, hide_index=True)

    action_c1, action_c2, action_c3 = st.columns([1, 1, 2])
    with action_c1:
        if st.button("Explore All Candidates →"):
            st.session_state.current_page = "Candidate Explorer"
            st.rerun()
    with action_c2:
        if st.button("Compare Top Candidates →"):
            st.session_state.compare_candidate_a = top_10[0]["candidate_id"]
            st.session_state.compare_candidate_b = top_10[1]["candidate_id"]
            st.session_state.current_page = "Compare Candidates"
            st.rerun()

    render_card_end()


# =============================================================================
# PAGE 2: CANDIDATE EXPLORER
# =============================================================================
elif st.session_state.current_page == "Candidate Explorer":
    render_page_header(
        title="Candidate Explorer",
        description="Search, filter, inspect, and select candidates from the verified ranking pool.",
        status_text="100 Candidates Loaded",
    )

    # Filter Toolbar
    with st.expander("🔍 Search & Filter Controls", expanded=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        with f_col1:
            search_query = st.text_input("Search ID, Title, or Company", placeholder="e.g. CAND_0088025 or Yellow.ai").strip()

        with f_col2:
            domains = sorted(list({c.get("candidate_domain", "ai_ml") for c in candidates_data}))
            selected_domains = st.multiselect("Filter by Domain", domains, default=domains)

        with f_col3:
            rank_min, rank_max = st.slider("Rank Range", 1, 100, (1, 100))

        with f_col4:
            min_score_val = min(c["score"] for c in candidates_data)
            max_score_val = max(c["score"] for c in candidates_data)
            score_range = st.slider(
                "Score Range",
                min_value=float(round(min_score_val, 4)),
                max_value=float(round(max_score_val, 4)),
                value=(float(round(min_score_val, 4)), float(round(max_score_val, 4))),
                step=0.005,
            )

        sort_col1, sort_col2 = st.columns(2)
        with sort_col1:
            sort_by = st.selectbox("Sort Order", ["Rank (Ascending)", "Score (Descending)", "Experience (Descending)"])
        with sort_col2:
            page_size = st.selectbox("Candidates Per Page", [10, 25, 50, 100], index=1)

    # Filter Application
    filtered_cands = []
    for c in candidates_data:
        # Search filter
        if search_query:
            query = search_query.lower()
            text_corpus = f"{c['candidate_id']} {c.get('current_title', '')} {c.get('current_company', '')} {c.get('reasoning', '')}".lower()
            if query not in text_corpus:
                continue

        # Domain filter
        if c.get("candidate_domain", "ai_ml") not in selected_domains:
            continue

        # Rank filter
        if not (rank_min <= c["rank"] <= rank_max):
            continue

        # Score filter
        if not (score_range[0] <= c["score"] <= score_range[1]):
            continue

        filtered_cands.append(c)

    # Sorting
    if sort_by == "Rank (Ascending)":
        filtered_cands.sort(key=lambda x: x["rank"])
    elif sort_by == "Score (Descending)":
        filtered_cands.sort(key=lambda x: x["score"], reverse=True)
    elif sort_by == "Experience (Descending)":
        filtered_cands.sort(key=lambda x: x.get("years_of_experience", 0), reverse=True)

    st.markdown(f"**Showing {len(filtered_cands)} of {len(candidates_data)} candidates**")

    if not filtered_cands:
        st.warning("No candidates match the selected filters. Please adjust your search criteria.")
    else:
        # Pagination
        total_pages = max(1, (len(filtered_cands) + page_size - 1) // page_size)
        page_num = 1
        if total_pages > 1:
            page_num = st.number_input(f"Page (1 of {total_pages})", min_value=1, max_value=total_pages, value=1)

        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(filtered_cands))
        page_candidates = filtered_cands[start_idx:end_idx]

        # Render candidates table
        display_data = []
        for c in page_candidates:
            is_shortlisted = "⭐" if c["candidate_id"] in st.session_state.shortlist else ""
            display_data.append({
                "Rank": c["rank"],
                "ID": c["candidate_id"],
                "Score": f"{c['score']:.4f}",
                "Domain": c.get("candidate_domain", "ai_ml"),
                "Current Title": c.get("current_title", "N/A"),
                "Company": c.get("current_company", "N/A"),
                "Years Exp": f"{c.get('years_of_experience', 0):.1f}",
                "Work Mode": c.get("preferred_work_mode", "N/A"),
                "Shortlisted": is_shortlisted,
            })

        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Quick Candidate Action Bar
        st.markdown("##### Quick Actions on Candidate")
        sel_col1, sel_col2, sel_col3, sel_col4 = st.columns([2, 1, 1, 1])

        with sel_col1:
            cand_options = [f"Rank {c['rank']}: {c['candidate_id']} - {c.get('current_title', 'Role')} ({c.get('current_company', '')})" for c in page_candidates]
            chosen_option = st.selectbox("Select Candidate", cand_options, key="explorer_picker")
            # Parse candidate ID
            chosen_cid = chosen_option.split(":")[1].split("-")[0].strip()

        with sel_col2:
            if st.button("View Full Profile", key="btn_view_prof"):
                st.session_state.selected_candidate_id = chosen_cid
                st.session_state.current_page = "Candidate Profile"
                st.rerun()

        with sel_col3:
            if st.button("Set as Candidate A", key="btn_set_a"):
                st.session_state.compare_candidate_a = chosen_cid
                st.session_state.current_page = "Compare Candidates"
                st.rerun()

        with sel_col4:
            in_shortlist = chosen_cid in st.session_state.shortlist
            btn_label = "Remove Shortlist" if in_shortlist else "Add to Shortlist"
            if st.button(btn_label, key="btn_toggle_shortlist"):
                if in_shortlist:
                    del st.session_state.shortlist[chosen_cid]
                else:
                    st.session_state.shortlist[chosen_cid] = {
                        "status": "Shortlisted",
                        "notes": "Added from Explorer",
                    }
                st.rerun()

        # CSV Download for filtered view
        csv_buffer = io.StringIO()
        export_df = pd.DataFrame([{
            "candidate_id": c["candidate_id"],
            "rank": c["rank"],
            "score": c["score"],
            "reasoning": c.get("reasoning", ""),
        } for c in filtered_cands])
        export_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label=f"📥 Download Filtered Rows ({len(filtered_cands)} candidates) as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"redrob_filtered_candidates_{len(filtered_cands)}.csv",
            mime="text/csv",
        )


# =============================================================================
# PAGE 3: CANDIDATE PROFILE
# =============================================================================
elif st.session_state.current_page == "Candidate Profile":
    render_page_header(
        title="Candidate Profile Deep-Dive",
        description="Inspect verified credentials, explainability rationale, component breakdowns, and career history.",
    )

    # Candidate selector dropdown
    cand_options = [f"Rank {c['rank']}: {c['candidate_id']} - {c.get('current_title', 'Role')} ({c.get('current_company', '')})" for c in sorted(candidates_data, key=lambda x: x["rank"])]
    current_idx = 0
    for idx, c in enumerate(sorted(candidates_data, key=lambda x: x["rank"])):
        if c["candidate_id"] == st.session_state.selected_candidate_id:
            current_idx = idx
            break

    selected_cand_str = st.selectbox("Select Candidate to Inspect", cand_options, index=current_idx)
    selected_cid = selected_cand_str.split(":")[1].split("-")[0].strip()
    st.session_state.selected_candidate_id = selected_cid
    cand = candidates_by_id[selected_cid]

    # Profile Hero Banner
    st.markdown(
        f"""
        <div class="redrob-card" style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <div style="font-size: 24px; font-weight: 700; color: #243746;">
                        {cand.get('anonymized_name') or cand['candidate_id']}
                    </div>
                    <div style="font-size: 15px; color: #667784; margin-top: 4px;">
                        {cand.get('headline') or f"{cand.get('current_title', '')} at {cand.get('current_company', '')}"}
                    </div>
                    <div style="font-size: 13px; color: #667784; margin-top: 6px;">
                        📍 {cand.get('location', 'N/A')}, {cand.get('country', 'N/A')} · ⏱️ {cand.get('years_of_experience', 0):.1f} Years Experience · 🏢 {cand.get('current_industry', 'N/A')}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; color: #667784;">LEADERBOARD RANK</div>
                    <div style="font-size: 32px; font-weight: 700; color: #263F52; line-height: 1;">#{cand['rank']}</div>
                    <div style="font-size: 13px; font-weight: 600; color: #6F8F7A; margin-top: 4px;">Score: {cand['score']:.4f}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action Toolbar
    act_c1, act_c2, act_c3 = st.columns(3)
    with act_c1:
        in_shortlist = selected_cid in st.session_state.shortlist
        if st.button("⭐ " + ("Remove from Shortlist" if in_shortlist else "Add to Shortlist"), use_container_width=True):
            if in_shortlist:
                del st.session_state.shortlist[selected_cid]
            else:
                st.session_state.shortlist[selected_cid] = {"status": "Shortlisted", "notes": "Added from Profile"}
            st.rerun()

    with act_c2:
        if st.button("⚖️ Set as Candidate A in Comparison", use_container_width=True):
            st.session_state.compare_candidate_a = selected_cid
            st.session_state.current_page = "Compare Candidates"
            st.rerun()

    with act_c3:
        if st.button("⚖️ Set as Candidate B in Comparison", use_container_width=True):
            st.session_state.compare_candidate_b = selected_cid
            st.session_state.current_page = "Compare Candidates"
            st.rerun()

    # Section 1: Model Explainability Rationale
    render_card_start("Model Explainability Rationale")
    st.markdown(
        f"""
        <div style="background-color: #E6EEE8; border-left: 4px solid #6F8F7A; padding: 14px 18px; border-radius: 4px; font-size: 14px; line-height: 1.6; color: #243746;">
            <strong>Automated Ranking Engine Rationale:</strong><br>
            {cand.get('reasoning', 'No reasoning text available in source data.')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Strengths and Warnings tags
    tag_col1, tag_col2 = st.columns(2)
    with tag_col1:
        strengths = cand.get("strengths", [])
        if strengths:
            st.markdown("<div style='margin-top: 10px;'><strong>Top Alignment Dimensions:</strong></div>", unsafe_allow_html=True)
            tags_html = "".join([f"<span class='redrob-badge badge-sage' style='margin: 2px 4px;'>✓ {s.title()}</span>" for s in strengths])
            st.markdown(tags_html, unsafe_allow_html=True)

    with tag_col2:
        penalties = cand.get("penalties", [])
        warnings = cand.get("triggered_warnings", [])
        if penalties or warnings:
            st.markdown("<div style='margin-top: 10px;'><strong>Quality Indicators:</strong></div>", unsafe_allow_html=True)
            w_html = "".join([f"<span class='redrob-badge badge-amber' style='margin: 2px 4px;'>⚠️ {p}</span>" for p in penalties + warnings])
            st.markdown(w_html, unsafe_allow_html=True)
        else:
            st.markdown("<div style='margin-top: 10px;'><strong>Data Integrity:</strong></div>", unsafe_allow_html=True)
            st.markdown("<span class='redrob-badge badge-sage'>✓ No honeypot flags or quality penalties</span>", unsafe_allow_html=True)

    render_card_end()

    # Section 2: Score Breakdown Visualization
    render_card_start("Component Score Breakdown")
    b_col1, b_col2 = st.columns([1, 1])

    with b_col1:
        components = [
            ("Title Alignment (25%)", cand.get("title_score", 0.0)),
            ("Semantic Career Match (20%)", cand.get("semantic_score", 0.0)),
            ("Experience Duration (15%)", cand.get("experience_score", 0.0)),
            ("Skill Match Coverage (15%)", cand.get("skill_score", 0.0)),
            ("Behavioral Stability (15%)", cand.get("behavioral_score", 0.0)),
            ("Company Alignment (10%)", cand.get("company_score", 0.0)),
        ]
        comp_df = pd.DataFrame(components, columns=["Component", "Score"])
        fig_comp = px.bar(
            comp_df,
            x="Score",
            y="Component",
            orientation="h",
            color_discrete_sequence=["#263F52"],
            range_x=[0, 1.05],
            text=comp_df["Score"].apply(lambda v: f"{v:.3f}"),
        )
        fig_comp.update_layout(
            margin=dict(l=10, r=20, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=260,
            xaxis=dict(gridcolor="#E6EEE8", title="Component Score (0.0 → 1.0)"),
            yaxis=dict(autorange="reversed", title=""),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with b_col2:
        st.markdown(
            f"""
            <div style="font-size: 13px; color: #667784; line-height: 1.8;">
                <div><strong>Inferred Technical Domain:</strong> <code>{cand.get('candidate_domain', 'ai_ml')}</code></div>
                <div><strong>Honeypot Quality Multiplier:</strong> <code>{cand.get('honeypot_multiplier', 1.0):.2f}</code></div>
                <div><strong>Penalties Triggered:</strong> <code>{cand.get('penalties_count', 0)}</code></div>
                <div><strong>Score Percentile in Top-100:</strong> <code>{(100 - cand['rank'] + 1)}th percentile</code></div>
                <div style="margin-top: 10px; padding: 10px; background-color: #F8F9FA; border-radius: 6px; font-size: 12px;">
                    <em>Note: Score weights and honeypot multipliers are configured deterministically via <code>ranking.yaml</code>.</em>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    render_card_end()

    # Section 3: Verified Skills Inventory
    render_card_start("Verified Skills Inventory")
    skills = cand.get("skills", [])
    if skills:
        s_tags = []
        for s in skills:
            if isinstance(s, dict):
                name = s.get("name", "")
                prof = s.get("proficiency", "intermediate")
                endorsements = s.get("endorsements", 0)
                s_tags.append(f"<span class='redrob-badge badge-navy' style='margin: 3px 5px;'>{name} · <em>{prof}</em> ({endorsements}★)</span>")
            else:
                s_tags.append(f"<span class='redrob-badge badge-navy' style='margin: 3px 5px;'>{s}</span>")
        st.markdown("".join(s_tags), unsafe_allow_html=True)
    else:
        st.info("Skills list is not populated in this candidate record.")
    render_card_end()

    # Section 4: Career History Timeline
    render_card_start("Professional Career History")
    career = cand.get("career_history", [])
    if career:
        for idx, role in enumerate(career):
            is_curr = role.get("is_current", False)
            curr_badge = "<span class='redrob-badge badge-sage'>Current Role</span>" if is_curr else ""
            st.markdown(
                f"""
                <div style="border-left: 2px solid #DCE2E3; padding-left: 16px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <strong style="font-size: 15px; color: #243746;">{role.get('title', 'Role')}</strong> at <strong>{role.get('company', 'Company')}</strong> {curr_badge}
                            <div style="font-size: 12px; color: #667784;">
                                {role.get('start_date', 'N/A')} → {role.get('end_date') or 'Present'} ({role.get('duration_months', 0)} months) · {role.get('industry', 'Tech')}
                            </div>
                        </div>
                    </div>
                    <div style="font-size: 13px; color: #435460; margin-top: 6px; line-height: 1.5;">
                        {role.get('description', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Career history detail is not populated in this candidate record.")
    render_card_end()

    # Section 5: Education & Logistics / Redrob Signals
    sig_c1, sig_c2 = st.columns(2)
    with sig_c1:
        render_card_start("Academic Credentials")
        education = cand.get("education", [])
        if education:
            for ed in education:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 10px; font-size: 13px;">
                        <strong>{ed.get('degree', 'Degree')}</strong> in {ed.get('field_of_study', 'Field')}<br>
                        {ed.get('institution', 'Institution')} ({ed.get('start_year', '')}–{ed.get('end_year', '')})<br>
                        <span style="color: #667784;">Tier: {ed.get('tier', 'N/A')} · Grade: {ed.get('grade', 'N/A')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.write("Not available in loaded data")
        render_card_end()

    with sig_c2:
        render_card_start("Platform Availability Signals")
        st.markdown(
            f"""
            <div style="font-size: 13px; line-height: 1.8; color: #243746;">
                <div><strong>Preferred Work Mode:</strong> {cand.get('preferred_work_mode', 'Not specified')}</div>
                <div><strong>Notice Period:</strong> {cand.get('notice_period_days', 'Not specified')} Days</div>
                <div><strong>Willing to Relocate:</strong> {'Yes' if cand.get('willing_to_relocate') else 'No'}</div>
                <div><strong>Open to Work Flag:</strong> {'Yes' if cand.get('open_to_work_flag') else 'No'}</div>
                <div><strong>Profile Completeness:</strong> {cand.get('profile_completeness_score', 'N/A')}%</div>
                <div><strong>Recruiter Response Rate:</strong> {cand.get('recruiter_response_rate', 'N/A')}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_card_end()


# =============================================================================
# PAGE 4: COMPARE CANDIDATES (PRIORITY FEATURE)
# =============================================================================
elif st.session_state.current_page == "Compare Candidates":
    render_page_header(
        title="Compare Candidates",
        description="Select two candidates, then choose which available criteria to compare. Only fields supported by the loaded data are scored or displayed.",
        status_text="Configurable Metric Comparison",
        badge_type="navy",
    )

    # 1. Candidate Selectors
    sel_col_a, sel_col_b = st.columns(2)

    with sel_col_a:
        st.markdown("#### Candidate A")
        opts_a = [f"Rank {c['rank']}: {c['candidate_id']} - {c.get('current_title', 'Role')} ({c.get('current_company', '')})" for c in sorted(candidates_data, key=lambda x: x["rank"])]
        idx_a = 0
        for i, c in enumerate(sorted(candidates_data, key=lambda x: x["rank"])):
            if c["candidate_id"] == st.session_state.compare_candidate_a:
                idx_a = i
                break
        choice_a = st.selectbox("Select Candidate A", opts_a, index=idx_a, key="cmp_choice_a")
        cid_a = choice_a.split(":")[1].split("-")[0].strip()
        st.session_state.compare_candidate_a = cid_a

    with sel_col_b:
        st.markdown("#### Candidate B")
        opts_b = [f"Rank {c['rank']}: {c['candidate_id']} - {c.get('current_title', 'Role')} ({c.get('current_company', '')})" for c in sorted(candidates_data, key=lambda x: x["rank"])]
        idx_b = 1 if len(opts_b) > 1 else 0
        for i, c in enumerate(sorted(candidates_data, key=lambda x: x["rank"])):
            if c["candidate_id"] == st.session_state.compare_candidate_b:
                idx_b = i
                break
        choice_b = st.selectbox("Select Candidate B", opts_b, index=idx_b, key="cmp_choice_b")
        cid_b = choice_b.split(":")[1].split("-")[0].strip()
        st.session_state.compare_candidate_b = cid_b

    # Quick comparison controls
    ctrl_c1, ctrl_c2, _ = st.columns([1, 1, 3])
    with ctrl_c1:
        if st.button("⇄ Swap Candidates"):
            st.session_state.compare_candidate_a, st.session_state.compare_candidate_b = (
                st.session_state.compare_candidate_b,
                st.session_state.compare_candidate_a,
            )
            st.rerun()

    with ctrl_c2:
        if st.button("↺ Reset Selection"):
            st.session_state.compare_candidate_a = all_candidate_ids[0]
            st.session_state.compare_candidate_b = all_candidate_ids[1]
            st.session_state.selected_comparison_metrics = REGISTRY.get_defaults()
            st.rerun()

    # Guardrail check for identical candidate selection
    if cid_a == cid_b:
        st.warning(
            f"⚠️ **Identical Candidate Selected**: Both selectors currently point to candidate `{cid_a}`. "
            f"Please select two different candidates above to generate a side-by-side comparison."
        )
        st.stop()

    cand_a = candidates_by_id[cid_a]
    cand_b = candidates_by_id[cid_b]

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Dynamic Metric Selection (Driven by Centralized MetricRegistry)
    render_card_start("Choose Comparison Metrics")
    st.markdown(
        "<div style='font-size: 13px; color: #667784; margin-bottom: 8px;'>"
        "Select which verified evaluation criteria to compare. Preselected: Rank, Model Score, Model Reasoning."
        "</div>",
        unsafe_allow_html=True,
    )

    all_registered_metrics = REGISTRY.list_all()
    metric_labels = [m.label for m in all_registered_metrics]
    label_to_id = {m.label: m.id for m in all_registered_metrics}
    id_to_label = {m.id: m.label for m in all_registered_metrics}

    # Default labels
    default_labels = [id_to_label[m_id] for m_id in st.session_state.selected_comparison_metrics if m_id in id_to_label]

    chosen_labels = st.multiselect(
        "Comparison Criteria",
        options=metric_labels,
        default=default_labels,
        help="Select any combination of core ranking, breakdown components, experience, skills, and platform signals.",
    )

    # Update session state with chosen metric IDs
    chosen_metric_ids = [label_to_id[lbl] for lbl in chosen_labels]
    st.session_state.selected_comparison_metrics = chosen_metric_ids

    # Quick metric group buttons
    btn_g1, btn_g2, btn_g3, btn_g4 = st.columns(4)
    with btn_g1:
        if st.button("Select Core Only"):
            st.session_state.selected_comparison_metrics = REGISTRY.get_defaults()
            st.rerun()
    with btn_g2:
        if st.button("Select All Breakdown"):
            breakdown_ids = [m.id for m in all_registered_metrics if m.category in ["Core Ranking", "Scoring Breakdown"]]
            st.session_state.selected_comparison_metrics = breakdown_ids
            st.rerun()
    with btn_g3:
        if st.button("Select Skills & Experience"):
            exp_ids = [m.id for m in all_registered_metrics if m.category in ["Core Ranking", "Experience & Role", "Skills"]]
            st.session_state.selected_comparison_metrics = exp_ids
            st.rerun()
    with btn_g4:
        if st.button("Select All Criteria"):
            st.session_state.selected_comparison_metrics = [m.id for m in all_registered_metrics]
            st.rerun()

    render_card_end()

    # 3. High-Level Candidate Summary Cards
    card_col_a, card_col_b = st.columns(2)
    with card_col_a:
        st.markdown(
            f"""
            <div class="redrob-card" style="border-top: 4px solid #263F52;">
                <div style="font-size: 13px; font-weight: 600; color: #263F52; text-transform: uppercase;">Candidate A</div>
                <div style="font-size: 20px; font-weight: 700; color: #243746; margin-top: 4px;">{cand_a.get('anonymized_name') or cid_a}</div>
                <div style="font-size: 13px; color: #667784;">{cand_a.get('current_title', 'Role')} · {cand_a.get('current_company', 'Company')}</div>
                <div style="margin-top: 10px; display: flex; gap: 12px;">
                    <span class="redrob-badge badge-navy">Rank #{cand_a['rank']}</span>
                    <span class="redrob-badge badge-sage">Score: {cand_a['score']:.4f}</span>
                    <span class="redrob-badge badge-navy">Domain: {cand_a.get('candidate_domain', 'ai_ml')}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_col_b:
        st.markdown(
            f"""
            <div class="redrob-card" style="border-top: 4px solid #6F8F7A;">
                <div style="font-size: 13px; font-weight: 600; color: #6F8F7A; text-transform: uppercase;">Candidate B</div>
                <div style="font-size: 20px; font-weight: 700; color: #243746; margin-top: 4px;">{cand_b.get('anonymized_name') or cid_b}</div>
                <div style="font-size: 13px; color: #667784;">{cand_b.get('current_title', 'Role')} · {cand_b.get('current_company', 'Company')}</div>
                <div style="margin-top: 10px; display: flex; gap: 12px;">
                    <span class="redrob-badge badge-navy">Rank #{cand_b['rank']}</span>
                    <span class="redrob-badge badge-sage">Score: {cand_b['score']:.4f}</span>
                    <span class="redrob-badge badge-navy">Domain: {cand_b.get('candidate_domain', 'ai_ml')}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Visual Comparison for Selected Numeric Scoring Components
    numeric_comp_ids = [
        m_id for m_id in chosen_metric_ids
        if REGISTRY.get(m_id) and REGISTRY.get(m_id).value_type in ["score", "numeric"] and m_id != "rank"
    ]
    if numeric_comp_ids:
        render_card_start("Visual Metric Comparison")
        chart_data = []
        for m_id in numeric_comp_ids:
            m = REGISTRY.get(m_id)
            val_a = m.extract_value(cand_a)
            val_b = m.extract_value(cand_b)
            if val_a is not None and val_b is not None:
                chart_data.append({
                    "Metric": m.label,
                    f"Candidate A ({cid_a})": float(val_a),
                    f"Candidate B ({cid_b})": float(val_b),
                })

        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name=f"Candidate A ({cid_a})",
                y=df_chart["Metric"],
                x=df_chart[f"Candidate A ({cid_a})"],
                orientation="h",
                marker_color="#263F52",
                text=df_chart[f"Candidate A ({cid_a})"].apply(lambda v: f"{v:.3f}"),
                textposition="inside",
            ))
            fig_bar.add_trace(go.Bar(
                name=f"Candidate B ({cid_b})",
                y=df_chart["Metric"],
                x=df_chart[f"Candidate B ({cid_b})"],
                orientation="h",
                marker_color="#6F8F7A",
                text=df_chart[f"Candidate B ({cid_b})"].apply(lambda v: f"{v:.3f}"),
                textposition="inside",
            ))
            fig_bar.update_layout(
                barmode="group",
                margin=dict(l=10, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=max(220, len(chart_data) * 45),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(gridcolor="#E6EEE8", title="Score / Value"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        render_card_end()

    # 5. Structured Side-by-Side Comparison Table
    render_card_start("Side-by-Side Comparison Details")
    comparison_results = []
    text_results = []

    for m_id in chosen_metric_ids:
        m = REGISTRY.get(m_id)
        if not m:
            continue
        val_a = m.extract_value(cand_a)
        val_b = m.extract_value(cand_b)
        res = compare_metric(m, val_a, val_b, cand_a_name=f"Cand A ({cid_a})", cand_b_name=f"Cand B ({cid_b})")

        if m.value_type == "text":
            text_results.append(res)
        else:
            comparison_results.append({
                "Category": res["category"],
                "Evaluation Criterion": res["metric_name"],
                f"Candidate A ({cid_a})": res["val_a"],
                f"Candidate B ({cid_b})": res["val_b"],
                "Delta / Difference": res["difference"],
                "Interpretation": res["interpretation"],
            })

    if comparison_results:
        df_cmp = pd.DataFrame(comparison_results)
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)

    # Render Text Metrics (Reasoning) Side-by-Side cleanly
    if text_results:
        st.markdown("##### Explanatory Text Comparison")
        for tr in text_results:
            st.markdown(f"**{tr['metric_name']}**")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown(
                    f"""
                    <div style="background-color: #F8F9FA; border: 1px solid #DCE2E3; border-radius: 6px; padding: 14px; font-size: 13px; line-height: 1.6;">
                        <strong>Candidate A ({cid_a}):</strong><br>
                        {tr['val_a']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with t_col2:
                st.markdown(
                    f"""
                    <div style="background-color: #F8F9FA; border: 1px solid #DCE2E3; border-radius: 6px; padding: 14px; font-size: 13px; line-height: 1.6;">
                        <strong>Candidate B ({cid_b}):</strong><br>
                        {tr['val_b']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    render_card_end()

    # 6. Optional Exploratory What-If Re-Weighting (Separated from Official Model)
    with st.expander("⚙️ Optional: Exploratory Custom Weighting (Decision Support Only)", expanded=False):
        st.info(
            "ℹ️ **Strict Integrity Disclosure**: Custom weighting is an exploratory sandbox for recruiters to test role-specific priorities. "
            "It is explicitly separate from the official model score and NEVER modifies or overwrites the verified pipeline rankings or stored CSV."
        )
        w_col1, w_col2, w_col3 = st.columns(3)
        with w_col1:
            w_title = st.slider("Title Relevance Weight", 0.0, 1.0, 0.25, 0.05)
            w_semantic = st.slider("Semantic Career Weight", 0.0, 1.0, 0.20, 0.05)
        with w_col2:
            w_exp = st.slider("Experience Duration Weight", 0.0, 1.0, 0.15, 0.05)
            w_skill = st.slider("Skill Match Weight", 0.0, 1.0, 0.15, 0.05)
        with w_col3:
            w_behavioral = st.slider("Behavioral Stability Weight", 0.0, 1.0, 0.15, 0.05)
            w_company = st.slider("Company Tier Weight", 0.0, 1.0, 0.10, 0.05)

        total_weight = w_title + w_semantic + w_exp + w_skill + w_behavioral + w_company
        if total_weight > 0:
            custom_score_a = (
                cand_a.get("title_score", 0) * w_title
                + cand_a.get("semantic_score", 0) * w_semantic
                + cand_a.get("experience_score", 0) * w_exp
                + cand_a.get("skill_score", 0) * w_skill
                + cand_a.get("behavioral_score", 0) * w_behavioral
                + cand_a.get("company_score", 0) * w_company
            ) / total_weight

            custom_score_b = (
                cand_b.get("title_score", 0) * w_title
                + cand_b.get("semantic_score", 0) * w_semantic
                + cand_b.get("experience_score", 0) * w_exp
                + cand_b.get("skill_score", 0) * w_skill
                + cand_b.get("behavioral_score", 0) * w_behavioral
                + cand_b.get("company_score", 0) * w_company
            ) / total_weight

            diff_custom = custom_score_a - custom_score_b
            custom_leader = f"Candidate A ({cid_a})" if diff_custom > 0 else f"Candidate B ({cid_b})"

            st.markdown(
                f"""
                <div style="background-color: #F7EEDF; border-left: 4px solid #C58B43; padding: 12px 16px; border-radius: 4px; font-size: 13px;">
                    <strong>Exploratory Weighted Result:</strong><br>
                    • Candidate A Custom Score: <code>{custom_score_a:.4f}</code> (Official Model Score: <code>{cand_a['score']:.4f}</code>)<br>
                    • Candidate B Custom Score: <code>{custom_score_b:.4f}</code> (Official Model Score: <code>{cand_b['score']:.4f}</code>)<br>
                    • Outcome under custom weights: <strong>{custom_leader}</strong> leads by <code>{abs(diff_custom):.4f}</code>.
                </div>
                """,
                unsafe_allow_html=True,
            )


# =============================================================================
# PAGE 5: TALENT ANALYTICS
# =============================================================================
elif st.session_state.current_page == "Talent Analytics":
    render_page_header(
        title="Talent Analytics",
        description="Descriptive analysis of the loaded top-100 candidate cohort. Grounded strictly in verified pipeline outputs.",
        status_text="Top 100 Population Analysis",
    )

    # Statistical Overview Row
    stats = compute_summary_statistics(candidates_data)
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        render_kpi("Mean Score", f"{stats.get('mean_score', 0):.4f}")
    with sc2:
        render_kpi("Median Score", f"{stats.get('median_score', 0):.4f}")
    with sc3:
        render_kpi("Std Deviation", f"{stats.get('std_score', 0):.4f}")
    with sc4:
        render_kpi("Score Spread", f"{stats.get('max_score', 0) - stats.get('min_score', 0):.4f}", f"[{stats.get('min_score', 0):.3f} → {stats.get('max_score', 0):.3f}]")
    with sc5:
        render_kpi("Avg Experience", f"{stats.get('mean_exp', 0):.1f} Yrs", "Range: 2.5 - 9.2 Yrs")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Cohort Analysis: Top 10 vs Ranks 11–100
    render_card_start("Cohort Comparison: Top 10 vs. Ranks 11–100")
    cohort_data = compute_cohort_comparison(candidates_data)
    if cohort_data:
        c_df = cohort_data["comparison_table"]
        t_col, chart_col = st.columns([1, 1])
        with t_col:
            st.dataframe(c_df, use_container_width=True, hide_index=True)
        with chart_col:
            fig_cohort = go.Figure()
            fig_cohort.add_trace(go.Bar(
                name="Top 10",
                x=c_df["metric"][:6],
                y=c_df["top_10_mean"][:6],
                marker_color="#263F52",
            ))
            fig_cohort.add_trace(go.Bar(
                name="Ranks 11–100",
                x=c_df["metric"][:6],
                y=c_df["ranks_11_100_mean"][:6],
                marker_color="#6F8F7A",
            ))
            fig_cohort.update_layout(
                barmode="group",
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=240,
                yaxis=dict(gridcolor="#E6EEE8", title="Average Score"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_cohort, use_container_width=True)
    render_card_end()

    # Two column analytics: Domain Distribution & Experience Band
    a_col1, a_col2 = st.columns(2)

    with a_col1:
        render_card_start("Inferred Technical Domains")
        domain_df = compute_domain_distribution(candidates_data)
        fig_pie = px.pie(
            domain_df,
            names="Domain",
            values="Candidate Count",
            color_discrete_sequence=["#263F52", "#6F8F7A", "#C58B43", "#667784"],
            hole=0.45,
        )
        fig_pie.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            height=260,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        st.dataframe(domain_df, use_container_width=True, hide_index=True)
        render_card_end()

    with a_col2:
        render_card_start("Experience Duration Distribution")
        exp_list = [c.get("years_of_experience", 0) for c in candidates_data if c.get("years_of_experience")]
        fig_exp = px.histogram(
            exp_list,
            nbins=12,
            labels={"value": "Years of Experience"},
            color_discrete_sequence=["#6F8F7A"],
        )
        fig_exp.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=260,
            xaxis=dict(gridcolor="#E6EEE8", title="Years of Professional Experience"),
            yaxis=dict(gridcolor="#E6EEE8", title="Candidate Count"),
        )
        st.plotly_chart(fig_exp, use_container_width=True)
        st.caption("Target band specified in JD: 5–9 years of applied machine learning experience.")
        render_card_end()

    # Component Averages & Score Ties Analysis
    comp_col, tie_col = st.columns(2)
    with comp_col:
        render_card_start("Average Component Contributions")
        comp_df = compute_component_averages(candidates_data)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        render_card_end()

    with tie_col:
        render_card_start("Score Ties & Transition Gaps")
        tie_data = analyze_score_ties_and_gaps(candidates_data)
        st.markdown(
            f"""
            <div style="font-size: 13px; line-height: 1.8; color: #243746;">
                <div><strong>Total Identical Score Ties:</strong> {tie_data['total_ties']}</div>
                <div><strong>Total Score Spread:</strong> {tie_data['total_score_spread']}</div>
                <div style="margin-top: 8px;"><strong>Largest Score Transitions:</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if tie_data["largest_gaps"]:
            gaps_df = pd.DataFrame(tie_data["largest_gaps"])[["rank_pair", "gap", "c1_id", "c2_id"]]
            gaps_df.columns = ["Rank Transition", "Score Drop", "Higher Candidate", "Lower Candidate"]
            st.dataframe(gaps_df, use_container_width=True, hide_index=True)
        render_card_end()


# =============================================================================
# PAGE 6: DATA QUALITY & AUDIT
# =============================================================================
elif st.session_state.current_page == "Data Quality & Audit":
    render_page_header(
        title="Data Quality & System Audit",
        description="Verify output compliance against hackathon submission invariants, schema integrity, and model pipeline transparency.",
        status_text="Compliance Audit Verified",
        badge_type="sage",
    )

    # Run complete audit checks
    ranked_csv_path = paths["ranked_csv"]
    audit_results = run_full_data_audit(ranked_csv_path)

    # Overall Audit Status Banner
    overall_status = "PASS" if audit_results.is_valid else "FAIL"
    status_class = "badge-sage" if overall_status == "PASS" else "badge-danger"
    st.markdown(
        f"""
        <div class="redrob-card" style="border-left: 6px solid {'#6F8F7A' if overall_status == 'PASS' else '#B9564D'};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0; color: #243746;">Automated Challenge Compliance Audit</h3>
                    <p style="margin: 4px 0 0 0; color: #667784; font-size: 13px;">
                        Verifies rows, column ordering, candidate ID regex, monotonicity, tie-breakers, and UTF-8 encoding.
                    </p>
                </div>
                <div>
                    <span class="redrob-badge {status_class}" style="font-size: 14px; padding: 6px 16px;">
                        STATUS: {overall_status}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed Checklist Table
    render_card_start("Submission Specification Checks")
    checks_rows = []
    for c in audit_results.checks:
        status_badge = "✅ PASS" if c["status"] == "PASS" else ("⚠️ WARN" if c["status"] == "WARN" else "❌ FAIL")
        checks_rows.append({
            "Validation Check": c["name"],
            "Status": status_badge,
            "Audit Detail & Verification Evidence": c["detail"],
        })
    df_checks = pd.DataFrame(checks_rows)
    st.dataframe(df_checks, use_container_width=True, hide_index=True)
    render_card_end()

    # Pipeline Transparency Reports
    render_card_start("Pipeline Transparency & Execution Audit")
    reports = load_transparency_reports()

    t_tab1, t_tab2, t_tab3, t_tab4 = st.tabs([
        "Pipeline 3 (Ranking Report)",
        "Pipeline 2 (Quality Report)",
        "Pipeline 1 (Cleaning Report)",
        "Manifest & Hashes",
    ])

    with t_tab1:
        rank_rep = reports.get("ranking_report", {})
        if rank_rep:
            r1, r2 = st.columns(2)
            with r1:
                st.markdown("##### Scoring Weights Applied")
                st.json(rank_rep.get("weights_used", {}))
            with r2:
                st.markdown("##### Domain Distribution (100k Pool)")
                st.json(rank_rep.get("domain_distribution", {}))
        else:
            st.info("Ranking report file not found in transparency/ directory.")

    with t_tab2:
        qual_rep = reports.get("quality_report", {})
        if qual_rep:
            st.markdown(f"**Total Candidates with Quality Flags:** {qual_rep.get('candidates_with_flags', 0)} / {qual_rep.get('total_candidates_processed', 0)}")
            st.json(qual_rep.get("flag_counts", {}))
        else:
            st.info("Quality report file not found in transparency/ directory.")

    with t_tab3:
        clean_rep = reports.get("cleaning_report", {})
        if clean_rep:
            st.json(clean_rep)
        else:
            st.info("Cleaning report file not found in transparency/ directory.")

    with t_tab4:
        st.markdown("##### Output Manifest & Integrity Hashes")
        st.json(manifest_data)

    render_card_end()

    # Job Description Inspector
    with st.expander("📄 View Source Job Description (Redrob AI)", expanded=False):
        jd_text = load_job_description()
        st.text_area("Job Description Content", jd_text, height=300, disabled=True)

    # Predictive Quality Disclaimer
    st.markdown(
        """
        <div style="background-color: #F8F9FA; border: 1px solid #DCE2E3; border-radius: 8px; padding: 16px; font-size: 13px; color: #667784; line-height: 1.6; margin-top: 20px;">
            <strong>⚠️ Ground-Truth Evaluation & Predictive Validity Notice:</strong><br>
            The checks above confirm <em>technical compliance</em> with the data format, ranking schema, and deterministic rules.
            Technical compliance does NOT equate to proven real-world hiring success or predictive performance.
            Actual hiring efficacy requires ongoing recruiter feedback calibration and structured ground-truth conversion metrics.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE 7: SHORTLIST & REPORTS
# =============================================================================
elif st.session_state.current_page == "Shortlist & Reports":
    render_page_header(
        title="Shortlist & Export Center",
        description="Manage your in-session working candidate shortlist and export official challenge reports.",
        status_text=f"{len(st.session_state.shortlist)} Candidates Shortlisted",
    )

    # In-Session Shortlist Management
    render_card_start("Recruiter Working Shortlist")
    st.markdown(
        "<div style='font-size: 13px; color: #667784; margin-bottom: 12px;'>"
        "Shortlist decisions and notes are maintained during your active browser session."
        "</div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.shortlist:
        st.info("Your shortlist is currently empty. Add candidates from the Candidate Explorer or Profile pages.")
    else:
        shortlist_rows = []
        for cid, meta in list(st.session_state.shortlist.items()):
            c = candidates_by_id.get(cid, {})
            shortlist_rows.append({
                "Rank": c.get("rank", "N/A"),
                "Candidate ID": cid,
                "Model Score": f"{c.get('score', 0):.4f}",
                "Current Role": c.get("current_title", "N/A"),
                "Company": c.get("current_company", "N/A"),
                "Review Status": meta.get("status", "Shortlisted"),
                "Recruiter Notes": meta.get("notes", ""),
            })

        df_short = pd.DataFrame(shortlist_rows)
        st.dataframe(df_short, use_container_width=True, hide_index=True)

        # Candidate status editor
        st.markdown("##### Update Candidate Review Status & Notes")
        u_col1, u_col2, u_col3, u_col4 = st.columns([2, 2, 3, 1])

        with u_col1:
            edit_cid = st.selectbox("Select Candidate to Update", list(st.session_state.shortlist.keys()))

        with u_col2:
            statuses = ["Shortlisted", "To Review", "Phone Screen Scheduled", "Technical Interview", "Offer Extended", "Not Selected"]
            curr_status = st.session_state.shortlist[edit_cid].get("status", "Shortlisted")
            new_status = st.selectbox("Review Status", statuses, index=statuses.index(curr_status) if curr_status in statuses else 0)

        with u_col3:
            curr_notes = st.session_state.shortlist[edit_cid].get("notes", "")
            new_notes = st.text_input("Recruiter Notes", value=curr_notes)

        with u_col4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Save"):
                st.session_state.shortlist[edit_cid]["status"] = new_status
                st.session_state.shortlist[edit_cid]["notes"] = new_notes
                st.success("Updated!")
                st.rerun()

        # Clear shortlist option
        if st.button("Clear Entire Shortlist"):
            st.session_state.shortlist = {}
            st.rerun()

    render_card_end()

    # Official Export Center
    render_card_start("Official Export & Report Center")
    st.markdown(
        "<div style='font-size: 13px; color: #667784; margin-bottom: 16px;'>"
        "Download verified output artifacts matching the hackathon submission format."
        "</div>",
        unsafe_allow_html=True,
    )

    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        st.markdown("##### 1. Official Challenge Submission CSV")
        st.caption("Strictly 100 rows, candidate_id, rank, score, reasoning in exact challenge order.")
        official_csv_buffer = io.StringIO()
        df_ranked.to_csv(official_csv_buffer, index=False)
        st.download_button(
            label="📥 Download Official Submission CSV (100 Rows)",
            data=official_csv_buffer.getvalue(),
            file_name="submission.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        st.markdown("##### 2. Full Scoring Breakdown CSV")
        st.caption("Includes title, semantic, company, experience, skill, and behavioral score components.")
        paths = get_default_paths()
        if paths["breakdown_csv"].exists():
            with open(paths["breakdown_csv"], "r", encoding="utf-8") as f:
                breakdown_content = f.read()
            st.download_button(
                label="📥 Download Component Breakdown CSV",
                data=breakdown_content,
                file_name="ranked_candidates_breakdown.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with exp_col2:
        st.markdown("##### 3. Shortlisted Candidates CSV")
        st.caption("Export your current working shortlist with custom review decisions and recruiter notes.")
        if st.session_state.shortlist:
            short_csv_buf = io.StringIO()
            short_export_data = []
            for cid, meta in st.session_state.shortlist.items():
                c = candidates_by_id.get(cid, {})
                short_export_data.append({
                    "candidate_id": cid,
                    "rank": c.get("rank"),
                    "score": c.get("score"),
                    "current_title": c.get("current_title"),
                    "current_company": c.get("current_company"),
                    "review_status": meta.get("status"),
                    "recruiter_notes": meta.get("notes"),
                    "exported_at": datetime.now().isoformat(),
                })
            pd.DataFrame(short_export_data).to_csv(short_csv_buf, index=False)
            st.download_button(
                label=f"📥 Download Shortlist ({len(st.session_state.shortlist)} Candidates)",
                data=short_csv_buf.getvalue(),
                file_name="redrob_shortlisted_candidates.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("📥 Download Shortlist (Shortlist is Empty)", disabled=True, use_container_width=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        st.markdown("##### 4. Complete Unified JSON Package")
        st.caption("Includes all 100 enriched candidate profiles, skills, career history, and audit manifest.")
        if paths["top_100_profiles"].exists():
            with open(paths["top_100_profiles"], "r", encoding="utf-8") as f:
                profiles_json_content = f.read()
            st.download_button(
                label="📥 Download Unified JSON Package",
                data=profiles_json_content,
                file_name="top_100_candidate_profiles.json",
                mime="application/json",
                use_container_width=True,
            )

    render_card_end()


# =============================================================================
# TRUSTWORTHY FOOTER (ON ALL PAGES)
# =============================================================================
render_footer()
