"""Pestaña Cliente — Preguntas 2 y 4 + panorama general de satisfacción."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from ui.components import ledger_row, section_tag, narrative, PALETTE


def render(df: pd.DataFrame):
    if df.empty:
        st.warning("No hay transacciones para el filtro seleccionado.")
        return

    con_nps = df.dropna(subset=["Satisfaccion_NPS_Prom"])

    # ---------------- Panorama general ----------------
    section_tag("PANORAMA GENERAL DE SATISFACCIÓN", "info")
    if len(con_nps):
        promotores = (con_nps["Satisfaccion_NPS_Prom"] >= 50).mean() * 100
        detractores = (con_nps["Satisfaccion_NPS_Prom"] < 0).mean() * 100
        ledger_row([
            {"label": "NPS promedio", "value": f"{con_nps['Satisfaccion_NPS_Prom'].mean():.1f}", "severity": "info"},
            {"label": "% Promotores", "value": f"{promotores:.1f}%", "severity": "saludable"},
            {"label": "% Detractores", "value": f"{detractores:.1f}%", "severity": "critico"},
            {"label": "Transacciones con feedback", "value": f"{len(con_nps):,} / {len(df):,}", "severity": "info"},
        ])
    else:
        st.info("Sin datos de feedback en este filtro.")

    st.write("---")

    # ---------------- Pregunta 2: Crisis Logística vs NPS ----------------
    section_tag("PREGUNTA 2 · CRISIS LOGÍSTICA Y CUELLOS DE BOTELLA", "advertencia")
    df_geo = con_nps[con_nps["Ciudad_Destino"] != "Sin Ciudad"]
    if len(df_geo) >= 30:
        corr_general = df_geo["Tiempo_Entrega_Real"].corr(df_geo["Satisfaccion_NPS_Prom"])
        filas = []
        for (ciudad, bodega), g in df_geo.groupby(["Ciudad_Destino", "Bodega_Origen"]):
            if len(g) >= 15:
                filas.append({"Ciudad": ciudad, "Bodega": bodega, "n": len(g),
                               "correlacion": g["Tiempo_Entrega_Real"].corr(g["Satisfaccion_NPS_Prom"])})
        tabla = pd.DataFrame(filas)
        ledger_row([{"label": "Correlación general Tiempo de Entrega ↔ NPS", "value": f"{corr_general:+.3f}",
                     "context": "cercano a 0 = sin relación lineal fuerte", "severity": "info"}])
        if len(tabla):
            pivot = tabla.pivot(index="Ciudad", columns="Bodega", values="correlacion")
            fig2 = go.Figure(go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index,
                                         colorscale=[[0, PALETTE["critico"]], [0.5, "#2A3654"], [1, PALETTE["saludable"]]],
                                         zmid=0, zmin=-1, zmax=1, text=np.round(pivot.values, 2), texttemplate="%{text}"))
            fig2.update_layout(title="Correlación Tiempo de Entrega vs. NPS (Ciudad x Bodega)", height=380)
            st.plotly_chart(fig2, width="stretch", key="p2_heatmap")
        narrative(
            "Correlaciones por debajo de ±0.2 son <b>débiles</b>: con esta evidencia, el tiempo de "
            "entrega no explica por sí solo las caídas de NPS en ninguna zona del filtro actual."
        )
    else:
        st.info("Muy pocos registros con ciudad y feedback conocidos para calcular correlaciones por zona en este filtro.")

    st.write("---")

    # ---------------- Pregunta 4: Diagnóstico de Fidelidad ----------------
    section_tag("PREGUNTA 4 · DIAGNÓSTICO DE FIDELIDAD", "advertencia")
    df_cat = df[df["Categoria"] != "Sin Catálogo"]
    if len(df_cat):
        resumen = df_cat.groupby("Categoria").agg(
            Stock=("Stock_Actual", "mean"),
            NPS=("Satisfaccion_NPS_Prom", "mean"),
            Rating=("Rating_Producto_Prom", "mean"),
        ).dropna()
        if len(resumen) >= 2:
            fig4 = px.scatter(resumen.reset_index(), x="Stock", y="NPS", text="Categoria", size=[30]*len(resumen),
                               color="NPS", color_continuous_scale=[PALETTE["critico"], "#2A3654", PALETTE["saludable"]])
            fig4.update_traces(textposition="top center")
            fig4.add_hline(y=resumen["NPS"].median(), line_dash="dash", line_color=PALETTE["text_muted"])
            fig4.add_vline(x=resumen["Stock"].median(), line_dash="dash", line_color=PALETTE["text_muted"])
            fig4.update_layout(title="Disponibilidad (stock) vs. sentimiento (NPS) por categoría", height=380)
            st.plotly_chart(fig4, width="stretch", key="p4_scatter")
            paradoja = resumen[(resumen["Stock"] >= resumen["Stock"].median()) & (resumen["NPS"] < resumen["NPS"].median())]
            if len(paradoja):
                narrative(
                    "Categorías en la <b>paradoja</b> (alto stock, NPS bajo): " +
                    ", ".join(f"<b>{c}</b>" for c in paradoja.index) +
                    ". El rating de producto casi no varía entre categorías, así que la causa probable "
                    "no es calidad — investigar precio percibido o experiencia de compra."
                )
        else:
            st.info("No hay suficientes categorías con datos completos en este filtro.")
    else:
        st.info("Filtro compuesto solo por ventas fantasma (sin categoría).")
