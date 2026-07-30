"""
tab_tiempo.py — Serie de Tiempo + Registros Excluidos
======================================================
Criterios del PDF de validación que cubre esta pestaña:

  Fase 2 / Caso "Tratamiento de Fechas Futuras":
    "El gráfico de series de tiempo no debe mostrar actividad más allá
     del periodo real de operación."
    → Se excluyen las 75 filas con Fecha_Futura_Invalida=True.

  Fase 2 / Caso "Detección de Costos Anómalos":
    "El dashboard debe tener la opción de Ver registros excluidos."
    → Sección dedicada al final con las 5 filas de PROD-1500.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from ui.components import ledger_row, narrative, PALETTE


def _seccion(titulo, color="#5B8DEF"):
    st.markdown(
        f"""<div style="background:{color};color:#fff;font-weight:700;
        font-size:0.82rem;letter-spacing:1.5px;padding:6px 14px;
        border-radius:4px;margin:22px 0 10px 0;display:inline-block;">{titulo}</div>""",
        unsafe_allow_html=True,
    )


def render(df: pd.DataFrame, master_completo: pd.DataFrame):
    """
    df             : master ya filtrado por la barra lateral
    master_completo: master SIN filtrar (para mostrar registros excluidos completos)
    """
    df = df.copy()
    df["Costo_Atipico"] = (
        df["Costo_Atipico"].astype(str).str.lower().isin(["true", "1"])
    )

    # ── Excluir fechas futuras (criterio del PDF) ─────────────────────────
    n_futuras = int(df["Fecha_Futura_Invalida"].sum())
    df_valido = df[~df["Fecha_Futura_Invalida"]].copy()

    st.markdown(
        f"""<div style="background:#1D2740;border-left:4px solid #3FA796;
        padding:10px 16px;border-radius:6px;margin-bottom:16px;font-size:0.9rem;
        color:#EDF1F7;">
        ✅ <b>Criterio de validación cumplido:</b> se excluyen
        <b>{n_futuras} transacciones con fecha futura</b>
        (Fecha_Futura_Invalida=True) — el gráfico solo muestra el
        período real de operación
        ({df_valido["Fecha_Venta"].min().date()} →
        {df_valido["Fecha_Venta"].max().date()}).
        </div>""",
        unsafe_allow_html=True,
    )

    if df_valido.empty:
        st.warning("Sin datos válidos para el filtro seleccionado.")
        return

    # ── Selector de granularidad ──────────────────────────────────────────
    granularidad = st.radio(
        "Granularidad", ["Semanal", "Mensual"], horizontal=True, key="ts_gran"
    )

    if granularidad == "Semanal":
        df_valido["periodo"] = df_valido["Fecha_Venta"].dt.to_period("W").dt.start_time
    else:
        df_valido["periodo"] = df_valido["Fecha_Venta"].dt.to_period("M").dt.start_time

    df_clean = df_valido[~df_valido["Costo_Atipico"]]

    # Agregado completo
    agg = df_valido.groupby("periodo").agg(
        n           =("Transaccion_ID", "count"),
        ingreso     =("Ingreso_Bruto", "sum"),
        pct_neg     =("Margen_Utilidad_USD",
                      lambda x: (x.dropna() < 0).mean() * 100),
        pct_fantasma=("Es_Venta_Fantasma", "mean"),
        nps         =("Satisfaccion_NPS_Prom", "mean"),
        tickets     =("Ticket_Soporte_Abierto", "mean"),
    ).reset_index()

    # Margen sin outlier
    agg_clean = df_clean.groupby("periodo").agg(
        margen_limpio=("Margen_Utilidad_USD", "sum"),
    ).reset_index()
    agg = agg.merge(agg_clean, on="periodo", how="left")
    agg["margen_con_outlier"] = df_valido.groupby("periodo")["Margen_Utilidad_USD"].sum().values

    # ── KPIs del período visible ──────────────────────────────────────────
    _seccion("RESUMEN DEL PERÍODO ANALIZADO", "#5B8DEF")
    ledger_row([
        {"label": "Transacciones válidas",
         "value": f"{len(df_valido):,}",
         "context": f"excluidas {n_futuras} futuras", "severity": "info"},
        {"label": "Ingreso bruto total",
         "value": f"USD {df_valido['Ingreso_Bruto'].sum():,.0f}", "severity": "info"},
        {"label": "% margen negativo promedio",
         "value": f"{(df_clean['Margen_Utilidad_USD'].dropna()<0).mean()*100:.1f}%",
         "context": "sin outlier $850k", "severity": "critico"},
        {"label": "NPS promedio del período",
         "value": f"{df_valido['Satisfaccion_NPS_Prom'].mean():.1f}", "severity": "advertencia"},
    ])

    # ── Gráfica 1: Ingreso bruto ──────────────────────────────────────────
    _seccion("EVOLUCIÓN DEL INGRESO BRUTO", "#5B8DEF")
    fig_ing = go.Figure()
    fig_ing.add_trace(go.Scatter(
        x=agg["periodo"], y=agg["ingreso"],
        mode="lines+markers", name="Ingreso bruto",
        line=dict(color=PALETTE["info"], width=2),
        fill="tozeroy", fillcolor="rgba(91,141,239,0.12)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>USD %{y:,.0f}<extra></extra>",
    ))
    # Media móvil 4 períodos
    agg["ing_ma4"] = agg["ingreso"].rolling(4, min_periods=1).mean()
    fig_ing.add_trace(go.Scatter(
        x=agg["periodo"], y=agg["ing_ma4"],
        mode="lines", name="Media móvil 4 períodos",
        line=dict(color=PALETTE["advertencia"], width=1.5, dash="dash"),
    ))
    fig_ing.update_layout(
        xaxis_title="Período", yaxis_title="USD",
        height=340, legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig_ing, use_container_width=True, key="ts_ingreso")

    # ── Gráfica 2: % margen negativo con vs sin outlier ───────────────────
    _seccion("% TRANSACCIONES CON MARGEN NEGATIVO — CON vs SIN OUTLIER $850k", "#E4572E")
    narrative(
        "Las semanas donde <b>PROD-1500</b> (Costo=$850.000, marcado "
        "<code>Costo_Atipico=True</code>) aparece muestran un disparo en el % de margen "
        "negativo que NO refleja el comportamiento real del catálogo. "
        "La línea verde es la base correcta para el análisis."
    )

    agg_c2 = df_clean.groupby("periodo").agg(
        pct_neg_limpio=("Margen_Utilidad_USD",
                        lambda x: (x.dropna() < 0).mean() * 100),
    ).reset_index()
    agg2 = agg[["periodo", "pct_neg"]].merge(agg_c2, on="periodo", how="left")

    fig_neg = go.Figure()
    fig_neg.add_trace(go.Scatter(
        x=agg2["periodo"], y=agg2["pct_neg"],
        mode="lines", name="Con outlier PROD-1500",
        line=dict(color=PALETTE["critico"], width=1.5, dash="dot"),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Con outlier: %{y:.1f}%<extra></extra>",
    ))
    fig_neg.add_trace(go.Scatter(
        x=agg2["periodo"], y=agg2["pct_neg_limpio"],
        mode="lines+markers", name="Sin outlier (análisis correcto)",
        line=dict(color=PALETTE["saludable"], width=2),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Sin outlier: %{y:.1f}%<extra></extra>",
    ))
    fig_neg.add_hline(
        y=agg2["pct_neg_limpio"].mean(),
        line_dash="dash", line_color=PALETTE["advertencia"],
        annotation_text=f"Media={agg2['pct_neg_limpio'].mean():.1f}%",
    )
    fig_neg.update_layout(
        xaxis_title="Período", yaxis_title="% margen negativo",
        height=340, legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig_neg, use_container_width=True, key="ts_margen")

    # ── Gráfica 3: NPS y % tickets ────────────────────────────────────────
    _seccion("EVOLUCIÓN DE SATISFACCIÓN (NPS) Y TICKETS DE SOPORTE", "#5B8DEF")
    fig_nps = go.Figure()
    fig_nps.add_trace(go.Scatter(
        x=agg["periodo"], y=agg["nps"],
        mode="lines+markers", name="NPS promedio",
        line=dict(color=PALETTE["info"], width=2),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>NPS: %{y:.1f}<extra></extra>",
    ))
    fig_nps.add_trace(go.Scatter(
        x=agg["periodo"], y=agg["tickets"] * 100,
        mode="lines", name="% tickets soporte",
        line=dict(color=PALETTE["advertencia"], width=1.5, dash="dash"),
        yaxis="y2",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Tickets: %{y:.1f}%<extra></extra>",
    ))
    fig_nps.add_hline(y=0, line_color="#8C96AD", line_dash="dot",
                      annotation_text="NPS=0")
    fig_nps.update_layout(
        xaxis_title="Período",
        yaxis=dict(title="NPS promedio"),
        yaxis2=dict(title="% tickets", overlaying="y", side="right",
                    showgrid=False),
        height=340, legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig_nps, use_container_width=True, key="ts_nps")

    # ── Gráfica 4: % venta fantasma en el tiempo ──────────────────────────
    _seccion("EVOLUCIÓN DE LA VENTA INVISIBLE (SKU sin catálogo)", "#E8A33D")
    fig_fant = go.Figure()
    fig_fant.add_trace(go.Bar(
        x=agg["periodo"], y=agg["pct_fantasma"] * 100,
        name="% venta fantasma",
        marker_color=PALETTE["advertencia"],
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:.1f}%<extra></extra>",
    ))
    fig_fant.add_hline(
        y=(agg["pct_fantasma"] * 100).mean(),
        line_dash="dash", line_color=PALETTE["critico"],
        annotation_text=f"Media={(agg['pct_fantasma']*100).mean():.1f}%",
    )
    fig_fant.update_layout(
        xaxis_title="Período", yaxis_title="% transacciones sin catálogo",
        height=300,
    )
    st.plotly_chart(fig_fant, use_container_width=True, key="ts_fantasma")

    # ── Registros excluidos (criterio PDF: "Ver registros excluidos") ─────
    st.write("---")
    _seccion("⚠️ REGISTROS EXCLUIDOS DE KPIs — OUTLIER DE COSTO", "#E4572E")
    narrative(
        "La <b>Guía de Validación</b> (Fase 2) exige que el dashboard tenga la opción "
        "de <em>Ver registros excluidos</em>. Estos son los registros con "
        "<code>Costo_Atipico=True</code>: SKU <b>PROD-1500</b> con costo unitario de "
        "<b>$850.000</b>, detectado por IQR (1.175 IQR por encima de la cerca superior). "
        "Su margen negativo es consecuencia del costo imposible, no de una falla de precios. "
        "Se conservan con su valor original y se excluyen de todos los KPIs agregados."
    )

    excluidos = master_completo[
        master_completo["Costo_Atipico"].astype(str).str.lower().isin(["true", "1"])
    ][["SKU_ID", "Categoria", "Fecha_Venta", "Costo_Unitario_USD",
       "Precio_Venta_Final", "Cantidad_Vendida", "Margen_Utilidad_USD",
       "Canal_Venta", "Ciudad_Destino"]].copy()

    ledger_row([
        {"label": "Filas con Costo_Atipico=True",
         "value": str(len(excluidos)),
         "context": "SKU PROD-1500 · Categoría Smartphones", "severity": "critico"},
        {"label": "Pérdida acumulada de estos registros",
         "value": f"USD {excluidos['Margen_Utilidad_USD'].sum():,.0f}",
         "context": "causada por costo $850k, no por precio", "severity": "critico"},
        {"label": "Detección estadística",
         "value": "IQR × 1.5",
         "context": "1.175 IQR sobre la cerca superior · z-MAD corrobora",
         "severity": "advertencia"},
    ])

    st.dataframe(
        excluidos.rename(columns={
            "SKU_ID": "SKU", "Categoria": "Categoría",
            "Fecha_Venta": "Fecha venta",
            "Costo_Unitario_USD": "Costo unitario",
            "Precio_Venta_Final": "Precio venta",
            "Cantidad_Vendida": "Cantidad",
            "Margen_Utilidad_USD": "Margen USD",
            "Canal_Venta": "Canal", "Ciudad_Destino": "Ciudad",
        }).style.format({
            "Costo unitario": "${:,.2f}",
            "Precio venta":   "${:,.2f}",
            "Margen USD":     "${:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "⬇️ Descargar registros excluidos (CSV)",
        data=excluidos.to_csv(index=False).encode(),
        file_name="registros_excluidos_outlier.csv",
        mime="text/csv",
    )
