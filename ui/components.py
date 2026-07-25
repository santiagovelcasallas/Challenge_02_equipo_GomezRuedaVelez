"""Componentes de UI reutilizables para el dashboard TechLogistics."""

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

PALETTE = {
    "bg_base": "#0D1321",
    "bg_surface": "#161D2F",
    "bg_elevated": "#1D2740",
    "border": "#2A3654",
    "text_primary": "#EDF1F7",
    "text_muted": "#8C96AD",
    "critico": "#E4572E",
    "advertencia": "#E8A33D",
    "saludable": "#3FA796",
    "info": "#5B8DEF",
}


def inject_css(path: str = "assets/styles.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def register_plotly_theme():
    """Registra y activa una plantilla Plotly acorde a la identidad 'Sala de Control'."""
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor=PALETTE["bg_surface"],
        plot_bgcolor=PALETTE["bg_surface"],
        font=dict(family="Inter, sans-serif", color=PALETTE["text_primary"], size=13),
        title=dict(font=dict(family="Space Grotesk, sans-serif", size=16)),
        colorway=[PALETTE["info"], PALETTE["saludable"], PALETTE["advertencia"], PALETTE["critico"], "#9B7EDE", "#5AC8FA"],
        xaxis=dict(gridcolor=PALETTE["border"], zerolinecolor=PALETTE["border"]),
        yaxis=dict(gridcolor=PALETTE["border"], zerolinecolor=PALETTE["border"]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, l=10, r=10, b=10),
    )
    pio.templates["control_room"] = template
    pio.templates.default = "control_room"


def hero(eyebrow: str, title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="hero-eyebrow">{eyebrow}</div>
        <div class="hero-title">{title}</div>
        <div class="hero-subtitle">{subtitle}</div>
        <br/>
        """,
        unsafe_allow_html=True,
    )


def section_tag(text: str, severity: str = "info"):
    st.markdown(f'<span class="section-tag {severity}">{text}</span>', unsafe_allow_html=True)


def ledger_card(label: str, value: str, context: str = "", severity: str = "info"):
    st.markdown(
        f"""
        <div class="ledger-card {severity}">
            <div class="ledger-label">{label}</div>
            <div class="ledger-number">{value}</div>
            <div class="ledger-context">{context}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ledger_row(cards: list):
    """cards: lista de dicts {label, value, context, severity}"""
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            ledger_card(**card)


def narrative(html_text: str):
    st.markdown(f'<div class="narrative-box">{html_text}</div>', unsafe_allow_html=True)
