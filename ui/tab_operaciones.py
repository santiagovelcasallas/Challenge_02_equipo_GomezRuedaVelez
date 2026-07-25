"""Pestaña Operaciones — Preguntas 1, 3 y 5 (recalculadas en vivo sobre el filtro activo)."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ui.components import ledger_row, section_tag, narrative, PALETTE


def render(df: pd.DataFrame):
    if df.empty:
        st.warning("No hay transacciones para el filtro seleccionado.")
        return

    # ---------------- Pregunta 1: Fuga de Capital ----------------
    section_tag("PREGUNTA 1 · FUGA DE CAPITAL Y RENTABILIDAD", "critico")
    con_margen = df.dropna(subset=["Margen_Utilidad_USD"])
    if len(con_margen):
        negativos = con_margen[con_margen["Margen_Utilidad_USD"] < 0]
        pct_neg = len(negativos) / len(con_margen) * 100
        perdida = negativos["Margen_Utilidad_USD"].sum()

        ledger_row([
            {"label": "Transacciones con margen negativo", "value": f"{len(negativos):,}",
             "context": f"{pct_neg:.1f}% del total con costo conocido", "severity": "critico"},
            {"label": "Pérdida acumulada", "value": f"USD {perdida:,.0f}", "severity": "critico"},
            {"label": "Margen total del período", "value": f"USD {con_margen['Margen_Utilidad_USD'].sum():,.0f}",
             "severity": "saludable" if con_margen['Margen_Utilidad_USD'].sum() > 0 else "critico"},
        ])

        por_canal = con_margen.groupby("Canal_Venta").apply(
            lambda g: (g["Margen_Utilidad_USD"] < 0).mean() * 100, include_groups=False
        ).sort_values()
        fig1 = go.Figure(go.Bar(x=por_canal.values, y=por_canal.index, orientation="h",
                                 marker_color=PALETTE["critico"]))
        fig1.update_layout(title="% de transacciones con margen negativo, por canal",
                            xaxis_title="%", height=280)
        st.plotly_chart(fig1, width="stretch", key="p1_canal")
        narrative(
            "Si el porcentaje es similar entre canales, la fuga de capital <b>no es un "
            "problema de precios de un canal específico</b> — es estructural en el catálogo."
        )
    else:
        st.info("No hay transacciones con costo conocido en este filtro (posiblemente solo ventas fantasma).")

    st.write("---")

    # ---------------- Pregunta 3: Venta Invisible ----------------
    section_tag("PREGUNTA 3 · LA VENTA INVISIBLE", "advertencia")
    ingreso_total = df["Ingreso_Bruto"].sum()
    fantasma = df[df["Es_Venta_Fantasma"]]
    ingreso_fantasma = fantasma["Ingreso_Bruto"].sum()
    pct_riesgo = (ingreso_fantasma / ingreso_total * 100) if ingreso_total else 0

    c1, c2 = st.columns([1, 1.4])
    with c1:
        ledger_row([
            {"label": "Ingreso en riesgo (SKU no catalogado)", "value": f"USD {ingreso_fantasma:,.0f}",
             "context": f"{pct_riesgo:.1f}% del ingreso total", "severity": "advertencia"},
            {"label": "SKUs fantasma distintos", "value": f"{fantasma['SKU_ID'].nunique():,}", "severity": "advertencia"},
        ])
    with c2:
        fig3 = go.Figure(go.Pie(
            labels=["Catalogado", "Venta Fantasma (en riesgo)"],
            values=[ingreso_total - ingreso_fantasma, ingreso_fantasma],
            marker_colors=[PALETTE["info"], PALETTE["critico"]], hole=0.5,
        ))
        fig3.update_layout(height=260, margin=dict(t=10, b=10))
        st.plotly_chart(fig3, width="stretch", key="p3_pie")

    st.write("---")

    # ---------------- Pregunta 5: Riesgo Operativo ----------------
    section_tag("PREGUNTA 5 · RIESGO OPERATIVO POR BODEGA", "advertencia")
    df_bod = df[df["Bodega_Origen"] != "Sin Bodega"]
    if len(df_bod):
        resumen = df_bod.groupby("Bodega_Origen").agg(
            Dias_Revision=("Dias_Desde_Ultima_Revision", "mean"),
            Tasa_Ticket=("Ticket_Soporte_Abierto", "mean"),
            N=("Transaccion_ID", "count"),
        )
        resumen["Tasa_Ticket"] *= 100
        fig5 = px.scatter(
            resumen.reset_index(), x="Dias_Revision", y="Tasa_Ticket", size="N", text="Bodega_Origen",
            color="Tasa_Ticket", color_continuous_scale=[PALETTE["saludable"], PALETTE["advertencia"], PALETTE["critico"]],
        )
        fig5.update_traces(textposition="top center")
        fig5.update_layout(title="Antigüedad de revisión de stock vs. tasa de tickets de soporte",
                            xaxis_title="Días promedio desde última revisión",
                            yaxis_title="% transacciones con ticket de soporte", height=350)
        st.plotly_chart(fig5, width="stretch", key="p5_scatter")
        bodega_riesgo = resumen["Dias_Revision"].idxmax()
        narrative(f"La bodega con mayor antigüedad de revisión en este filtro es <b>{bodega_riesgo}</b>.")
    else:
        st.info("No hay datos de bodega para este filtro.")
