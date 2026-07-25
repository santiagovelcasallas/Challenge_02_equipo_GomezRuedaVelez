"""Pestaña Auditoría — Transparencia (Antes vs Después)."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ui.components import ledger_row, section_tag, narrative, PALETTE
from services.data_loader import cleaning_report_csv

NOMBRES = {"inventario": "Inventario Central", "transacciones": "Transacciones Logística", "feedback": "Feedback Clientes"}


def render(health: dict, decisiones: dict):
    section_tag("FASE 1 · AUDITORÍA DE CALIDAD", "info")
    st.markdown("### Health Score — Antes vs. Después de la limpieza")
    narrative(
        "Un consultor senior no limpia datos sin dejar rastro. Cada barra muestra "
        "<b>completitud</b>, <b>validez</b> y <b>unicidad</b> antes y después del "
        "pipeline de limpieza (ver <code>src/cleaning_*.py</code> para la justificación "
        "de cada decisión)."
    )
    st.write("")

    cards = []
    for ds in ("inventario", "transacciones", "feedback"):
        antes = health["antes"][ds]["health_score"]
        despues = health["despues"][ds]["health_score"]
        cards.append({
            "label": NOMBRES[ds],
            "value": f"{despues:.1f}",
            "context": f"antes: {antes:.1f} · Δ +{despues - antes:.1f}",
            "severity": "saludable" if despues - antes < 15 else "advertencia",
        })
    ledger_row(cards)

    st.write("")
    cols = st.columns(3)
    for col, ds in zip(cols, ("inventario", "transacciones", "feedback")):
        with col:
            antes, despues = health["antes"][ds], health["despues"][ds]
            metrics = ["completitud", "validez", "unicidad"]
            fig = go.Figure()
            fig.add_bar(name="Antes", x=metrics, y=[antes[m] for m in metrics], marker_color=PALETTE["critico"])
            fig.add_bar(name="Después", x=metrics, y=[despues[m] for m in metrics], marker_color=PALETTE["saludable"])
            fig.update_layout(title=NOMBRES[ds], barmode="group", height=300, yaxis_range=[0, 105])
            st.plotly_chart(fig, width="stretch", key=f"health_{ds}")

    st.write("")
    st.markdown("### Log de decisiones de limpieza")
    for ds in ("inventario", "transacciones", "feedback"):
        with st.expander(f"📋 {NOMBRES[ds]} — {len(decisiones[ds])} decisiones registradas"):
            rows = [{"Decisión": k.replace("_", " "), "Valor": str(v)} for k, v in decisiones[ds].items()
                    if not isinstance(v, dict)]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.write("")
    st.download_button(
        "⬇️ Descargar reporte de limpieza (CSV)",
        data=cleaning_report_csv(health, decisiones),
        file_name="reporte_limpieza_techlogistics.csv",
        mime="text/csv",
    )
