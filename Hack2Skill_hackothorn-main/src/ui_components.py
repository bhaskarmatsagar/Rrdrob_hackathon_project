"""Reusable UI Components and Themed Layout Helpers for REDROB Recruit Intelligence.

Implements the official design system:
- Palette: Ink (#243746), Navy (#263F52), Canvas (#F5F4EF), Surface (#FFFFFF),
  Sage (#6F8F7A), Amber (#C58B43), Slate (#667784), Line (#DCE2E3).
- Restrained editorial enterprise aesthetic.
- Compact functional header, clean KPI cards, status badges, and trustworthy footer.
"""

from __future__ import annotations

import streamlit as st
from typing import Optional, List, Dict, Any


CUSTOM_CSS = """
<style>
/* Global Styling & Typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #243746;
}

.stApp {
    background-color: #F5F4EF;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #263F52 !important;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.15) !important;
}

[data-testid="stSidebar"] .stRadio label {
    font-size: 14px;
    font-weight: 500;
    padding: 6px 10px;
    border-radius: 6px;
    transition: all 0.15s ease;
}

/* Top Navigation / Compact Header */
.redrob-header-container {
    background-color: #FFFFFF;
    border-bottom: 1px solid #DCE2E3;
    padding: 16px 24px;
    margin-bottom: 24px;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.redrob-header-title {
    font-size: 26px;
    font-weight: 700;
    color: #243746;
    margin: 0;
    letter-spacing: -0.02em;
}

.redrob-header-desc {
    font-size: 14px;
    color: #667784;
    margin: 4px 0 0 0;
}

.redrob-meta-bar {
    display: flex;
    gap: 16px;
    align-items: center;
    font-size: 12px;
    color: #667784;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #F0F2F3;
}

.redrob-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}

.badge-sage {
    background-color: #E6EEE8;
    color: #2D5A3C;
    border: 1px solid #C4D9CA;
}

.badge-navy {
    background-color: #E8EEF3;
    color: #263F52;
    border: 1px solid #C5D5E2;
}

.badge-amber {
    background-color: #F7EEDF;
    color: #8C5B1C;
    border: 1px solid #ECD5B5;
}

.badge-danger {
    background-color: #F8E9E7;
    color: #8A2D24;
    border: 1px solid #E6BDB9;
}

/* Restrained KPI Cards */
.redrob-kpi-card {
    background-color: #FFFFFF;
    border: 1px solid #DCE2E3;
    border-radius: 10px;
    padding: 16px 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    height: 100%;
}

.redrob-kpi-label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #667784;
    margin-bottom: 6px;
}

.redrob-kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #243746;
    line-height: 1.1;
}

.redrob-kpi-helper {
    font-size: 12px;
    color: #6F8F7A;
    margin-top: 6px;
    font-weight: 500;
}

/* Card panels */
.redrob-card {
    background-color: #FFFFFF;
    border: 1px solid #DCE2E3;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.redrob-card-title {
    font-size: 17px;
    font-weight: 600;
    color: #243746;
    margin-top: 0;
    margin-bottom: 14px;
    border-bottom: 1px solid #F0F2F3;
    padding-bottom: 8px;
}

/* Footer */
.redrob-footer {
    margin-top: 48px;
    padding-top: 20px;
    border-top: 1px solid #DCE2E3;
    font-size: 12px;
    color: #667784;
    text-align: center;
    line-height: 1.6;
}

/* Streamlit button overriding */
div.stButton > button:first-child {
    background-color: #263F52;
    color: #FFFFFF;
    border: 1px solid #1C3040;
    border-radius: 6px;
    font-weight: 500;
    padding: 6px 14px;
    transition: all 0.15s ease;
}

div.stButton > button:first-child:hover {
    background-color: #1F3444;
    border-color: #152430;
    color: #FFFFFF;
}

div.stDownloadButton > button:first-child {
    background-color: #6F8F7A;
    color: #FFFFFF;
    border: 1px solid #5C7B66;
    border-radius: 6px;
    font-weight: 500;
    padding: 6px 14px;
}

div.stDownloadButton > button:first-child:hover {
    background-color: #5E7D68;
    color: #FFFFFF;
}
</style>
"""


def apply_theme() -> None:
    """Inject CSS tokens into Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_page_header(
    title: str,
    description: str,
    status_text: Optional[str] = None,
    badge_type: str = "sage",
) -> None:
    """Render standardized compact functional header."""
    badge_html = ""
    if status_text:
        badge_html = f"""
        <div class="redrob-meta-bar">
            <span class="redrob-badge badge-{badge_type}">● {status_text}</span>
            <span>Dataset: Top 100 Candidates</span>
            <span>Evaluation: Decision Support Only</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="redrob-header-container">
            <h1 class="redrob-header-title">{title}</h1>
            <p class="redrob-header-desc">{description}</p>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str, helper: Optional[str] = None) -> None:
    """Render a single restrained KPI card."""
    helper_html = f'<div class="redrob-kpi-helper">{helper}</div>' if helper else ""
    st.markdown(
        f"""
        <div class="redrob-kpi-card">
            <div class="redrob-kpi-label">{label}</div>
            <div class="redrob-kpi-value">{value}</div>
            {helper_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card_start(title: str) -> None:
    """Start an open panel card."""
    st.markdown(
        f"""
        <div class="redrob-card">
            <div class="redrob-card-title">{title}</div>
        """,
        unsafe_allow_html=True,
    )


def render_card_end() -> None:
    """End a panel card."""
    st.markdown("</div>", unsafe_allow_html=True)


def render_footer() -> None:
    """Render trustworthy, minimal product footer."""
    st.markdown(
        """
        <div class="redrob-footer">
            <strong>REDROB Recruit Intelligence</strong> · Candidate-ranking review workspace<br>
            AI-generated rankings support human review and do not independently determine hiring decisions.
            Ground-truth validation required for production employment outcomes.
        </div>
        """,
        unsafe_allow_html=True,
    )
