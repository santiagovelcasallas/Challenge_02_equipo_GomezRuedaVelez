"""
tab_operaciones.py — Preguntas 1, 3 y 5
========================================
Arquitectura por pregunta:
  1. Enunciado EXACTO del PDF (sin parafrasear)
  2. Respuesta directa con KPIs
  3. Gráfica principal Plotly
  4. Cajón expandible: histograma/densidad Matplotlib + tabla de hipótesis
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import scipy.stats as sci
import streamlit as st

from ui.components import ledger_row, narrative, PALETTE

# ── Estilos Matplotlib coherentes con el dashboard oscuro ─────────────────
MPL_STYLE = {
    "figure.facecolor":  "#161D2F",
    "axes.facecolor":    "#1D2740",
    "axes.edgecolor":    "#2A3654",
    "axes.labelcolor":   "#EDF1F7",
    "xtick.color":       "#8C96AD",
    "ytick.color":       "#8C96AD",
    "text.color":        "#EDF1F7",
    "grid.color":        "#2A3654",
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
}

def _mpl_buf(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf.read()

def _enunciado(texto: str):
    st.markdown(
        f"""<div style="
            border-left: 4px solid #E8A33D;
            background: #1D2740;
            padding: 12px 18px;
            border-radius: 6px;
            margin-bottom: 14px;
            font-size: 0.97rem;
            color: #EDF1F7;
            font-style: italic;
        ">{texto}</div>""",
        unsafe_allow_html=True,
    )

def _respuesta(texto: str):
    st.markdown(
        f"""<div style="
            background: #0D1321;
            border: 1px solid #3FA796;
            border-radius: 6px;
            padding: 12px 18px;
            margin-bottom: 14px;
            font-size: 0.95rem;
            color: #EDF1F7;
        ">🎯 <b>Respuesta:</b> {texto}</div>""",
        unsafe_allow_html=True,
    )

def _seccion(titulo: str, color: str = "#E4572E"):
    st.markdown(
        f"""<div style="
            background:{color};
            color:#fff;
            font-weight:700;
            font-size:0.82rem;
            letter-spacing:1.5px;
            padding:6px 14px;
            border-radius:4px;
            margin: 22px 0 10px 0;
            display:inline-block;
        ">{titulo}</div>""",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
def render(df: pd.DataFrame):
    if df.empty:
        st.warning("No hay transacciones para el filtro seleccionado.")
        return

    df = df.copy()
    df["Costo_Atipico"] = df["Costo_Atipico"].astype(str).str.lower().isin(["true","1"])

    # =========================================================================
    # PREGUNTA 1 — FUGA DE CAPITAL Y RENTABILIDAD
    # =========================================================================
    _seccion("PREGUNTA 1 · FUGA DE CAPITAL Y RENTABILIDAD", "#E4572E")
    _enunciado(
        "Localice los SKUs que se están vendiendo con margen negativo. "
        "¿Representan una pérdida aceptable por volumen o es una falla crítica "
        "de precios en el canal Online?"
    )

    con_margen = df.dropna(subset=["Margen_Utilidad_USD"])
    df_clean   = con_margen[~con_margen["Costo_Atipico"]]   # sin outlier $850k
    neg_clean  = df_clean[df_clean["Margen_Utilidad_USD"] < 0]

    if len(df_clean) == 0:
        st.info("Sin transacciones con costo conocido en este filtro.")
    else:
        pct_neg   = len(neg_clean) / len(df_clean) * 100
        perdida   = neg_clean["Margen_Utilidad_USD"].sum()
        margen_t  = df_clean["Margen_Utilidad_USD"].sum()

        ledger_row([
            {"label": "Transacciones margen negativo",
             "value": f"{len(neg_clean):,}",
             "context": f"{pct_neg:.1f}% del total con costo conocido (sin outlier)",
             "severity": "critico"},
            {"label": "Pérdida acumulada (sin outlier $850k)",
             "value": f"USD {perdida:,.0f}", "severity": "critico"},
            {"label": "Margen total del período",
             "value": f"USD {margen_t:,.0f}",
             "severity": "saludable" if margen_t > 0 else "critico"},
        ])

        # ── Gráfica principal: % neg por canal ───────────────────────────
        por_canal = df_clean.groupby("Canal_Venta").apply(
            lambda g: pd.Series({
                "pct_neg": (g["Margen_Utilidad_USD"] < 0).mean() * 100,
                "n": len(g),
            }), include_groups=False
        ).sort_values("pct_neg")

        fig1 = go.Figure(go.Bar(
            x=por_canal["pct_neg"], y=por_canal.index,
            orientation="h",
            marker_color=PALETTE["critico"],
            text=[f"{v:.1f}%" for v in por_canal["pct_neg"]],
            textposition="outside",
        ))
        fig1.update_layout(
            title="% de transacciones con margen negativo, por canal",
            xaxis_title="%", height=300,
            xaxis_range=[0, por_canal["pct_neg"].max() * 1.25],
        )
        st.plotly_chart(fig1, use_container_width=True, key="p1_canal")

        # ── Test chi-cuadrado ─────────────────────────────────────────────
        contingencia = df_clean.groupby("Canal_Venta").apply(
            lambda g: pd.Series({
                "neg": (g["Margen_Utilidad_USD"] < 0).sum(),
                "pos": (g["Margen_Utilidad_USD"] >= 0).sum(),
            }), include_groups=False
        )
        chi2, p_chi2, dof, _ = sci.chi2_contingency(contingencia.values)

        _respuesta(
            f"El {pct_neg:.1f}% de las transacciones tiene margen negativo (pérdida USD {perdida:,.0f}). "
            f"Los porcentajes por canal son similares (χ²={chi2:.2f}, p={p_chi2:.4f}, gl={dof}). "
            + ("La diferencia entre canales <b>es estadísticamente significativa (p&lt;0.05)</b>: hay un canal con falla de precios específica."
               if p_chi2 < 0.05 else
               "La diferencia entre canales <b>NO es significativa (p&gt;0.05)</b>: la fuga es <b>estructural en el catálogo</b>, no un problema de un canal específico.")
        )

        # ── Cajón estadístico ─────────────────────────────────────────────
        with st.expander("📊 Procedimiento estadístico — distribución del margen y test de hipótesis"):

            # Hipótesis en tabla
            st.markdown("**Hipótesis formuladas:**")
            st.dataframe(pd.DataFrame([
                {"": "H₀", "Hipótesis": "La proporción de transacciones con margen negativo es igual en todos los canales"},
                {"": "H₁", "Hipótesis": "Al menos un canal tiene una proporción significativamente distinta"},
            ]), hide_index=True, use_container_width=True)

            st.dataframe(pd.DataFrame([
                {"Estadístico": "Prueba", "Valor": "Chi-cuadrado de homogeneidad (scipy.stats.chi2_contingency)"},
                {"Estadístico": "χ²",     "Valor": f"{chi2:.4f}"},
                {"Estadístico": "p-valor","Valor": f"{p_chi2:.4f}"},
                {"Estadístico": "gl",     "Valor": str(dof)},
                {"Estadístico": "α",      "Valor": "0.05"},
                {"Estadístico": "Decisión","Valor": "Rechazar H₀" if p_chi2 < 0.05 else "No rechazar H₀"},
                {"Estadístico": "Fuente", "Valor": "analysis.pregunta_1_fuga_capital"},
            ]), hide_index=True, use_container_width=True)

            # Histograma + densidad + IC del margen
            margen_vals = df_clean["Margen_Utilidad_USD"].dropna().values
            skew_val  = sci.skew(margen_vals)
            kurt_val  = sci.kurtosis(margen_vals)
            media     = margen_vals.mean()
            se        = sci.sem(margen_vals)
            ic_low, ic_high = sci.t.interval(0.95, df=len(margen_vals)-1, loc=media, scale=se)

            # Test de normalidad (Shapiro si n<5000, KS si no)
            if len(margen_vals) <= 5000:
                stat_n, p_n = sci.shapiro(margen_vals[:5000])
                test_norm = f"Shapiro-Wilk W={stat_n:.4f}, p={p_n:.4f}"
            else:
                stat_n, p_n = sci.kstest(margen_vals, "norm",
                                          args=(media, margen_vals.std()))
                test_norm = f"KS stat={stat_n:.4f}, p={p_n:.4f}"

            with plt.rc_context(MPL_STYLE):
                fig_m, axes = plt.subplots(1, 2, figsize=(11, 4),
                                           facecolor="#161D2F")
                # Histograma + KDE
                ax = axes[0]
                ax.hist(margen_vals, bins=60, color="#5B8DEF", alpha=0.7,
                        density=True, edgecolor="#2A3654", linewidth=0.4)
                kde_x = np.linspace(margen_vals.min(), margen_vals.max(), 400)
                try:
                    kde = sci.gaussian_kde(margen_vals)
                    ax.plot(kde_x, kde(kde_x), color="#E8A33D", lw=2, label="KDE")
                except Exception:
                    pass
                ax.axvline(0, color="#E4572E", lw=1.5, linestyle="--", label="Margen=0")
                ax.axvline(media, color="#3FA796", lw=1.5, linestyle="--",
                           label=f"Media={media:,.0f}")
                ax.axvspan(ic_low, ic_high, alpha=0.15, color="#3FA796",
                           label=f"IC 95%: [{ic_low:,.0f}, {ic_high:,.0f}]")
                ax.set_xlabel("Margen Utilidad USD")
                ax.set_ylabel("Densidad")
                ax.set_title("Distribución del margen (KDE + IC 95%)")
                ax.legend(fontsize=7.5)
                ax.grid(True)

                # Q-Q plot para evaluar normalidad
                ax2 = axes[1]
                (osm, osr), (slope, intercept, r) = sci.probplot(margen_vals, dist="norm")
                ax2.scatter(osm, osr, s=4, alpha=0.4, color="#5B8DEF")
                ax2.plot(osm, slope * np.array(osm) + intercept,
                         color="#E8A33D", lw=1.5)
                ax2.set_xlabel("Cuantiles teóricos (normal)")
                ax2.set_ylabel("Cuantiles observados")
                ax2.set_title(f"Q-Q plot  |  skew={skew_val:.2f}  kurt={kurt_val:.2f}")
                ax2.grid(True)

                plt.tight_layout()
                st.image(_mpl_buf(fig_m), use_container_width=True)
                plt.close(fig_m)

            st.markdown(f"""
| Parámetro | Valor |
|---|---|
| n transacciones | {len(margen_vals):,} |
| Media | USD {media:,.2f} |
| Mediana | USD {np.median(margen_vals):,.2f} |
| Skewness | {skew_val:.3f} (distribución {'muy asimétrica → usar mediana' if abs(skew_val)>1 else 'moderada'}) |
| Kurtosis | {kurt_val:.3f} |
| IC 95% de la media | [{ic_low:,.2f}, {ic_high:,.2f}] |
| Test normalidad | {test_norm} |
| Fuente | `analysis.pregunta_1_fuga_capital` |
""")

    st.write("---")

    # =========================================================================
    # PREGUNTA 3 — ANÁLISIS DE LA VENTA INVISIBLE
    # =========================================================================
    _seccion("PREGUNTA 3 · ANÁLISIS DE LA VENTA INVISIBLE", "#E8A33D")
    _enunciado(
        "Cuantifique el impacto financiero (en USD) de las ventas cuyos SKUs no están "
        "en el maestro de inventario. ¿Qué porcentaje del ingreso total está en riesgo "
        "por falta de control de inventario?"
    )

    ing_total  = df["Ingreso_Bruto"].sum()
    fant       = df[df["Es_Venta_Fantasma"]]
    ing_fant   = fant["Ingreso_Bruto"].sum()
    pct_riesgo = ing_fant / ing_total * 100 if ing_total else 0
    n_skus     = fant["SKU_ID"].nunique()
    rep        = fant["SKU_ID"].value_counts()

    # Bootstrap IC 95% del % de transacciones fantasma
    np.random.seed(42)
    boots = [df.sample(len(df), replace=True)["Es_Venta_Fantasma"].mean() * 100
             for _ in range(1000)]
    ic_b_low, ic_b_high = np.percentile(boots, [2.5, 97.5])

    ledger_row([
        {"label": "Ingreso en riesgo (SKU sin catálogo)",
         "value": f"USD {ing_fant:,.0f}",
         "context": f"{pct_riesgo:.1f}% del ingreso total · IC 95%: [{ic_b_low:.1f}%, {ic_b_high:.1f}%]",
         "severity": "advertencia"},
        {"label": "Transacciones fantasma",
         "value": f"{len(fant):,}",
         "context": f"{len(fant)/len(df)*100:.1f}% del total",
         "severity": "advertencia"},
        {"label": "SKUs distintos sin catálogo",
         "value": f"{n_skus:,}", "severity": "advertencia"},
    ])

    c1, c2 = st.columns([1, 1.4])
    with c1:
        fig3 = go.Figure(go.Pie(
            labels=["Catalogado", "Sin catálogo (en riesgo)"],
            values=[ing_total - ing_fant, ing_fant],
            marker_colors=[PALETTE["info"], PALETTE["critico"]], hole=0.5,
        ))
        fig3.update_layout(height=260, margin=dict(t=10, b=10))
        st.plotly_chart(fig3, use_container_width=True, key="p3_pie")
    with c2:
        # Distribución de ingresos por SKU fantasma
        top_fant = (fant.groupby("SKU_ID")["Ingreso_Bruto"].sum()
                    .sort_values(ascending=False).head(10))
        fig3b = go.Figure(go.Bar(
            x=top_fant.values, y=top_fant.index, orientation="h",
            marker_color=PALETTE["advertencia"],
        ))
        fig3b.update_layout(title="Top 10 SKUs fantasma por ingreso",
                             xaxis_title="USD", height=260,
                             margin=dict(t=30, b=10))
        st.plotly_chart(fig3b, use_container_width=True, key="p3_top")

    _respuesta(
        f"USD {ing_fant:,.0f} ({pct_riesgo:.1f}% del ingreso total) "
        f"no tiene respaldo en el maestro de inventario. "
        f"IC 95% bootstrap: [{ic_b_low:.1f}%, {ic_b_high:.1f}%]. "
        f"Los {n_skus} SKUs distintos tienen recurrencia media de "
        f"{rep.mean():.1f} transacciones: patrón de <b>falla de catálogo</b>, no de fraude "
        f"(el fraude concentraría muchas transacciones en pocos SKUs)."
    )

    with st.expander("📊 Procedimiento estadístico — Bootstrap IC 95% y patrón de recurrencia"):
        st.dataframe(pd.DataFrame([
            {"Estadístico": "Método IC",       "Valor": "Bootstrap percentil (n=1.000 muestras, seed=42)"},
            {"Estadístico": "IC 95% (% transacciones fantasma)", "Valor": f"[{ic_b_low:.2f}%, {ic_b_high:.2f}%]"},
            {"Estadístico": "Media repeticiones por SKU fantasma", "Valor": f"{rep.mean():.2f}"},
            {"Estadístico": "Mediana repeticiones", "Valor": f"{rep.median():.1f}"},
            {"Estadístico": "Máximo repeticiones", "Valor": str(rep.max())},
            {"Estadístico": "Interpretación", "Valor": "Media baja y dispersa → falla de catálogo, no fraude concentrado"},
            {"Estadístico": "Fuente", "Valor": "analysis.pregunta_3_venta_invisible"},
        ]), hide_index=True, use_container_width=True)

        with plt.rc_context(MPL_STYLE):
            fig_b, axes = plt.subplots(1, 2, figsize=(11, 4), facecolor="#161D2F")
            # Distribución bootstrap
            axes[0].hist(boots, bins=40, color="#E8A33D", alpha=0.8,
                         edgecolor="#2A3654", linewidth=0.4)
            axes[0].axvline(pct_riesgo, color="#E4572E", lw=2,
                            label=f"Observado={pct_riesgo:.2f}%")
            axes[0].axvspan(ic_b_low, ic_b_high, alpha=0.2, color="#3FA796",
                            label=f"IC 95%: [{ic_b_low:.2f}%, {ic_b_high:.2f}%]")
            axes[0].set_xlabel("% transacciones fantasma (muestra bootstrap)")
            axes[0].set_ylabel("Frecuencia")
            axes[0].set_title("Distribución Bootstrap — IC 95%")
            axes[0].legend(fontsize=8)
            axes[0].grid(True)
            # Histograma de repeticiones por SKU
            axes[1].hist(rep.values, bins=30, color="#5B8DEF", alpha=0.8,
                         edgecolor="#2A3654", linewidth=0.4)
            axes[1].axvline(rep.mean(), color="#E8A33D", lw=2,
                            label=f"Media={rep.mean():.1f}")
            axes[1].set_xlabel("Repeticiones por SKU fantasma")
            axes[1].set_ylabel("Frecuencia (SKUs)")
            axes[1].set_title("Distribución de recurrencia por SKU sin catálogo")
            axes[1].legend(fontsize=8)
            axes[1].grid(True)
            plt.tight_layout()
            st.image(_mpl_buf(fig_b), use_container_width=True)
            plt.close(fig_b)

    st.write("---")

    # =========================================================================
    # PREGUNTA 5 — STORYTELLING DE RIESGO OPERATIVO
    # =========================================================================
    _seccion("PREGUNTA 5 · STORYTELLING DE RIESGO OPERATIVO", "#E8A33D")
    _enunciado(
        "Visualice la relación entre la antigüedad de la Última Revisión del stock "
        "y la tasa de Tickets de Soporte. ¿Qué bodegas están operando a ciegas "
        "y cómo impacta esto en la satisfacción final?"
    )

    df_bod = df[df["Bodega_Origen"] != "Sin Bodega"].copy()
    if len(df_bod) < 10:
        st.info("Sin datos de bodega suficientes en este filtro.")
        return

    resumen5 = df_bod.groupby("Bodega_Origen").agg(
        n               = ("Transaccion_ID",             "count"),
        dias_revision   = ("Dias_Desde_Ultima_Revision", "mean"),
        tasa_ticket_pct = ("Ticket_Soporte_Abierto",     lambda x: x.mean() * 100),
        nps_prom        = ("Satisfaccion_NPS_Prom",      "mean"),
        brecha_prom     = ("Brecha_Entrega_Dias",        "mean"),
    ).round(2).reset_index()

    fig5 = px.scatter(
        resumen5, x="dias_revision", y="tasa_ticket_pct",
        size="n", text="Bodega_Origen", color="tasa_ticket_pct",
        color_continuous_scale=[[0, PALETTE["saludable"]],
                                 [0.5, PALETTE["advertencia"]],
                                 [1, PALETTE["critico"]]],
        hover_data={"nps_prom": True, "brecha_prom": True, "n": True},
        labels={"dias_revision": "Días promedio desde última revisión",
                "tasa_ticket_pct": "% con ticket de soporte"},
    )
    fig5.update_traces(textposition="top center")
    fig5.update_layout(
        title="Antigüedad de revisión de stock vs. tasa de tickets de soporte",
        height=380,
    )
    st.plotly_chart(fig5, use_container_width=True, key="p5_scatter")

    # Pearson con p-value
    r5, p5 = sci.pearsonr(resumen5["dias_revision"], resumen5["tasa_ticket_pct"])
    bodega_ciega   = resumen5.loc[resumen5["dias_revision"].idxmax(), "Bodega_Origen"]
    bodega_tickets = resumen5.loc[resumen5["tasa_ticket_pct"].idxmax(), "Bodega_Origen"]

    _respuesta(
        f"<b>{bodega_ciega}</b> es la bodega más desactualizada "
        f"({resumen5.loc[resumen5['Bodega_Origen']==bodega_ciega, 'dias_revision'].values[0]:.0f} días). "
        f"<b>{bodega_tickets}</b> tiene la mayor tasa de tickets "
        f"({resumen5.loc[resumen5['Bodega_Origen']==bodega_tickets, 'tasa_ticket_pct'].values[0]:.1f}%). "
        f"Correlación antigüedad↔tickets: r={r5:.3f}, p={p5:.3f}. "
        + (f"<b>Significativa (p&lt;0.05)</b>: las bodegas más desactualizadas generan más soporte."
           if p5 < 0.05 else
           f"<b>Indicativa pero no significativa (p={p5:.3f}, n={len(resumen5)} bodegas)</b>: "
           "el patrón existe pero requiere más granularidad (nivel SKU-bodega) para ser concluyente.")
    )

    with st.expander("📊 Procedimiento estadístico — Correlación de Pearson y tabla de bodegas"):
        st.markdown("**Hipótesis formuladas:**")
        st.dataframe(pd.DataFrame([
            {"": "H₀", "Hipótesis": "No hay relación lineal entre días desde revisión y tasa de tickets (r=0)"},
            {"": "H₁", "Hipótesis": "A mayor antigüedad de revisión, mayor tasa de tickets (r>0)"},
        ]), hide_index=True, use_container_width=True)

        st.dataframe(pd.DataFrame([
            {"Estadístico": "Prueba",    "Valor": "Pearson r (scipy.stats.pearsonr)"},
            {"Estadístico": "r",         "Valor": f"{r5:.4f}"},
            {"Estadístico": "p-valor",   "Valor": f"{p5:.4f}"},
            {"Estadístico": "n bodegas", "Valor": str(len(resumen5))},
            {"Estadístico": "α",         "Valor": "0.05"},
            {"Estadístico": "Decisión",  "Valor": "Rechazar H₀" if p5 < 0.05 else "No rechazar H₀ (n pequeño)"},
            {"Estadístico": "Advertencia","Valor": "Con n=5 bodegas el test tiene baja potencia estadística"},
            {"Estadístico": "Fuente",    "Valor": "analysis.pregunta_5_riesgo_operativo"},
        ]), hide_index=True, use_container_width=True)

        st.markdown("**Detalle por bodega:**")
        st.dataframe(
            resumen5.rename(columns={
                "Bodega_Origen": "Bodega", "n": "Transacciones",
                "dias_revision": "Días desde revisión",
                "tasa_ticket_pct": "% Tickets",
                "nps_prom": "NPS prom", "brecha_prom": "Brecha entrega (días)",
            }).sort_values("Días desde revisión", ascending=False),
            hide_index=True, use_container_width=True,
        )

        with plt.rc_context(MPL_STYLE):
            fig_p5, ax = plt.subplots(figsize=(8, 4.5), facecolor="#161D2F")
            ax.scatter(resumen5["dias_revision"], resumen5["tasa_ticket_pct"],
                       s=resumen5["n"] / resumen5["n"].max() * 400 + 60,
                       color="#E8A33D", zorder=3, edgecolors="#EDF1F7", linewidth=0.8)
            for _, row in resumen5.iterrows():
                ax.annotate(row["Bodega_Origen"],
                            (row["dias_revision"], row["tasa_ticket_pct"]),
                            fontsize=9, xytext=(6, 5), textcoords="offset points")
            if len(resumen5) >= 3:
                m, b = np.polyfit(resumen5["dias_revision"], resumen5["tasa_ticket_pct"], 1)
                xr = np.linspace(resumen5["dias_revision"].min(),
                                 resumen5["dias_revision"].max(), 50)
                ax.plot(xr, m * xr + b, "--", color="#8C96AD", lw=1.3,
                        label=f"Tendencia (r={r5:.3f}, p={p5:.3f})")
            ax.set_xlabel("Días promedio desde última revisión de stock")
            ax.set_ylabel("% transacciones con ticket de soporte")
            ax.set_title("P5 · Bodegas a ciegas vs. tasa de tickets\n"
                         "(tamaño = volumen de transacciones)")
            ax.legend(fontsize=8)
            ax.grid(True)
            plt.tight_layout()
            st.image(_mpl_buf(fig_p5), use_container_width=True)
            plt.close(fig_p5)
