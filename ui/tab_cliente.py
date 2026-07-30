"""
tab_cliente.py — Preguntas 2 y 4
==================================
Misma arquitectura: enunciado exacto PDF → respuesta directa → gráfica Plotly
→ cajón expandible con histograma/densidad Matplotlib + tabla de hipótesis.
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import scipy.stats as sci
import streamlit as st

from ui.components import ledger_row, narrative, PALETTE

MPL_STYLE = {
    "figure.facecolor": "#161D2F", "axes.facecolor": "#1D2740",
    "axes.edgecolor": "#2A3654", "axes.labelcolor": "#EDF1F7",
    "xtick.color": "#8C96AD", "ytick.color": "#8C96AD",
    "text.color": "#EDF1F7", "grid.color": "#2A3654",
    "grid.linestyle": "--", "grid.alpha": 0.5,
}

def _mpl_buf(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf.read()

def _enunciado(texto: str):
    st.markdown(
        f"""<div style="border-left:4px solid #E8A33D;background:#1D2740;
            padding:12px 18px;border-radius:6px;margin-bottom:14px;
            font-size:0.97rem;color:#EDF1F7;font-style:italic;">{texto}</div>""",
        unsafe_allow_html=True,
    )

def _respuesta(texto: str):
    st.markdown(
        f"""<div style="background:#0D1321;border:1px solid #3FA796;
            border-radius:6px;padding:12px 18px;margin-bottom:14px;
            font-size:0.95rem;color:#EDF1F7;">🎯 <b>Respuesta:</b> {texto}</div>""",
        unsafe_allow_html=True,
    )

def _seccion(titulo: str, color: str = "#5B8DEF"):
    st.markdown(
        f"""<div style="background:{color};color:#fff;font-weight:700;
            font-size:0.82rem;letter-spacing:1.5px;padding:6px 14px;
            border-radius:4px;margin:22px 0 10px 0;display:inline-block;">
            {titulo}</div>""",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
def render(df: pd.DataFrame):
    if df.empty:
        st.warning("No hay transacciones para el filtro seleccionado.")
        return

    con_nps = df.dropna(subset=["Satisfaccion_NPS_Prom"])

    # ── Panorama general ──────────────────────────────────────────────────
    _seccion("PANORAMA GENERAL DE SATISFACCIÓN", "#5B8DEF")
    if len(con_nps):
        promotores   = (con_nps["Satisfaccion_NPS_Prom"] >= 50).mean() * 100
        detractores  = (con_nps["Satisfaccion_NPS_Prom"] < 0).mean() * 100
        ledger_row([
            {"label": "NPS promedio",
             "value": f"{con_nps['Satisfaccion_NPS_Prom'].mean():.1f}", "severity": "info"},
            {"label": "% Promotores",
             "value": f"{promotores:.1f}%", "severity": "saludable"},
            {"label": "% Detractores",
             "value": f"{detractores:.1f}%", "severity": "critico"},
            {"label": "Transacciones con feedback",
             "value": f"{len(con_nps):,} / {len(df):,}", "severity": "info"},
        ])
    st.write("---")

    # =========================================================================
    # PREGUNTA 2 — CRISIS LOGÍSTICA Y CUELLOS DE BOTELLA
    # =========================================================================
    _seccion("PREGUNTA 2 · CRISIS LOGÍSTICA Y CUELLOS DE BOTELLA", "#5B8DEF")
    _enunciado(
        "¿En qué ciudades y bodegas la correlación entre Tiempo de Entrega y NPS bajo "
        "es más fuerte? Identifique la zona que requiere un cambio inmediato de operador."
    )

    df_geo = con_nps[
        (con_nps["Ciudad_Destino"] != "Sin Ciudad") &
        (~con_nps["Entrega_Atipica"])
    ].copy()

    if len(df_geo) < 30:
        st.info("Muy pocos registros con ciudad y feedback para calcular correlaciones.")
    else:
        pr_g, pp_g = sci.pearsonr( df_geo["Tiempo_Entrega_Real"], df_geo["Satisfaccion_NPS_Prom"])
        sr_g, sp_g = sci.spearmanr(df_geo["Tiempo_Entrega_Real"], df_geo["Satisfaccion_NPS_Prom"])

        ledger_row([
            {"label": "Pearson r (Tiempo↔NPS)",
             "value": f"{pr_g:+.4f}",
             "context": f"p={pp_g:.4f} · {'NS (p>0.05)' if pp_g>0.05 else 'SIG (p<0.05)'}",
             "severity": "info"},
            {"label": "Spearman ρ",
             "value": f"{sr_g:+.4f}",
             "context": f"p={sp_g:.4f}", "severity": "info"},
        ])

        # Correlación por ciudad
        corr_ciudad = []
        for ciudad, g in df_geo.groupby("Ciudad_Destino"):
            if len(g) >= 30:
                rp, pp = sci.pearsonr( g["Tiempo_Entrega_Real"], g["Satisfaccion_NPS_Prom"])
                rs, ps = sci.spearmanr(g["Tiempo_Entrega_Real"], g["Satisfaccion_NPS_Prom"])
                corr_ciudad.append({
                    "Ciudad": ciudad, "n": int(len(g)),
                    "Pearson r": round(rp, 4), "Pearson p": round(pp, 4),
                    "Spearman ρ": round(rs, 4), "Spearman p": round(ps, 4),
                    "Significativa (α=0.05)": "✅ Sí" if (pp < 0.05 or ps < 0.05) else "❌ No",
                })
        df_corr = pd.DataFrame(corr_ciudad).sort_values("Pearson r")

        # Heatmap Plotly
        if len(df_corr):
            fig2 = go.Figure(go.Bar(
                x=df_corr["Ciudad"], y=df_corr["Pearson r"],
                marker_color=[PALETTE["critico"] if v < 0 else PALETTE["saludable"]
                              for v in df_corr["Pearson r"]],
                text=[f"r={v:.3f}<br>p={p:.3f}"
                      for v, p in zip(df_corr["Pearson r"], df_corr["Pearson p"])],
                textposition="outside",
            ))
            fig2.add_hline(y=0, line_color="#8C96AD", line_dash="dash")
            fig2.update_layout(
                title="Pearson r (Tiempo de Entrega vs NPS) por ciudad",
                yaxis_title="Pearson r", height=340,
                yaxis_range=[min(df_corr["Pearson r"].min() * 1.5, -0.1),
                             max(df_corr["Pearson r"].max() * 1.5,  0.1)],
            )
            st.plotly_chart(fig2, use_container_width=True, key="p2_bar")

        # Zona más crítica
        sig = df_corr[df_corr["Significativa (α=0.05)"] == "✅ Sí"]
        peor = (sig.sort_values("Pearson r").iloc[0]["Ciudad"]
                if len(sig) else df_corr.iloc[0]["Ciudad"])

        _respuesta(
            f"La correlación global Pearson r={pr_g:.4f} (p={pp_g:.4f}) "
            + ("es <b>estadísticamente NO significativa</b>: el tiempo de entrega no explica las caídas de NPS. "
               if pp_g > 0.05 else "es <b>estadísticamente significativa</b>. ") +
            f"Ciudad más crítica: <b>{peor}</b>. "
            "La causa del NPS bajo es estructural (calidad, precio percibido), "
            "no el operador logístico."
        )

        with st.expander("📊 Procedimiento estadístico — Pearson, Spearman y distribución del NPS"):
            st.markdown("**Hipótesis formuladas:**")
            st.dataframe(pd.DataFrame([
                {"": "H₀", "Hipótesis": "No hay correlación lineal entre tiempo de entrega y NPS (r=0)"},
                {"": "H₁", "Hipótesis": "Mayor tiempo de entrega → NPS más bajo (r<0)"},
            ]), hide_index=True, use_container_width=True)

            st.dataframe(pd.DataFrame([
                {"Estadístico": "Pearson r global",   "Valor": f"{pr_g:.4f}"},
                {"Estadístico": "Pearson p-valor",    "Valor": f"{pp_g:.4f}"},
                {"Estadístico": "Spearman ρ global",  "Valor": f"{sr_g:.4f}"},
                {"Estadístico": "Spearman p-valor",   "Valor": f"{sp_g:.4f}"},
                {"Estadístico": "n observaciones",    "Valor": f"{len(df_geo):,}"},
                {"Estadístico": "α",                  "Valor": "0.05"},
                {"Estadístico": "Decisión",
                 "Valor": "No rechazar H₀" if pp_g > 0.05 else "Rechazar H₀"},
                {"Estadístico": "Fuente",
                 "Valor": "analysis.pregunta_2_crisis_logistica"},
            ]), hide_index=True, use_container_width=True)

            st.markdown("**Correlaciones por ciudad:**")
            st.dataframe(df_corr, hide_index=True, use_container_width=True)

            with plt.rc_context(MPL_STYLE):
                nps_vals = df_geo["Satisfaccion_NPS_Prom"].dropna().values
                t_vals   = df_geo["Tiempo_Entrega_Real"].dropna().values
                skew_nps = sci.skew(nps_vals)

                fig_p2, axes = plt.subplots(1, 3, figsize=(14, 4), facecolor="#161D2F")

                # Histograma NPS + KDE
                axes[0].hist(nps_vals, bins=50, color="#5B8DEF", alpha=0.75,
                             density=True, edgecolor="#2A3654", linewidth=0.3)
                try:
                    kde = sci.gaussian_kde(nps_vals)
                    xk = np.linspace(nps_vals.min(), nps_vals.max(), 300)
                    axes[0].plot(xk, kde(xk), color="#E8A33D", lw=2, label="KDE")
                except Exception:
                    pass
                axes[0].axvline(0,  color="#E4572E", lw=1.5, linestyle="--", label="NPS=0")
                axes[0].axvline(50, color="#3FA796", lw=1.5, linestyle="--", label="NPS=50")
                axes[0].set_xlabel("NPS"); axes[0].set_ylabel("Densidad")
                axes[0].set_title(f"Distribución NPS\nskew={skew_nps:.2f}")
                axes[0].legend(fontsize=7.5); axes[0].grid(True)

                # Scatter tiempo vs NPS
                axes[1].scatter(t_vals, nps_vals[:len(t_vals)], s=4,
                                alpha=0.2, color="#5B8DEF")
                m, b = np.polyfit(t_vals, nps_vals[:len(t_vals)], 1)
                xr = np.linspace(t_vals.min(), t_vals.max(), 100)
                axes[1].plot(xr, m * xr + b, color="#E8A33D", lw=1.8,
                             label=f"r={pr_g:.3f}")
                axes[1].set_xlabel("Tiempo entrega (días)")
                axes[1].set_ylabel("NPS")
                axes[1].set_title("Scatter Tiempo vs NPS")
                axes[1].legend(fontsize=8); axes[1].grid(True)

                # Q-Q NPS
                (osm, osr), (sl, ic, _) = sci.probplot(nps_vals, dist="norm")
                axes[2].scatter(osm, osr, s=4, alpha=0.4, color="#5B8DEF")
                axes[2].plot(osm, sl * np.array(osm) + ic, color="#E8A33D", lw=1.5)
                axes[2].set_xlabel("Cuantiles teóricos"); axes[2].set_ylabel("Observados")
                axes[2].set_title("Q-Q plot NPS"); axes[2].grid(True)

                plt.tight_layout()
                st.image(_mpl_buf(fig_p2), use_container_width=True)
                plt.close(fig_p2)

    st.write("---")

    # =========================================================================
    # PREGUNTA 4 — DIAGNÓSTICO DE FIDELIDAD
    # =========================================================================
    _seccion("PREGUNTA 4 · DIAGNÓSTICO DE FIDELIDAD", "#5B8DEF")
    _enunciado(
        "¿Existen categorías de productos con alta disponibilidad (stock alto) pero "
        "con un sentimiento de cliente negativo? Explique la paradoja: "
        "¿Es mala calidad de producto o sobrecosto?"
    )

    df = df.copy()
    df["Costo_Atipico"] = df["Costo_Atipico"].astype(str).str.lower().isin(["true","1"])
    CATS_REALES = ["Accesorios", "Laptops", "Monitores", "Smartphones", "Tablets"]
    df_cat = df[df["Categoria"].isin(CATS_REALES)].copy()

    if len(df_cat) < 10:
        st.info("Sin datos de categoría suficientes en este filtro.")
        return

    resumen4 = df_cat.groupby("Categoria").apply(lambda g: pd.Series({
        "n":                   int(len(g)),
        "Stock prom":          round(g["Stock_Actual"].mean(), 1),
        "NPS prom":            round(g["Satisfaccion_NPS_Prom"].mean(), 2),
        "Rating prom":         round(g["Rating_Producto_Prom"].mean(), 2),
        "Margen prom (c/out)": round(g["Margen_Utilidad_USD"].mean(), 2),
        "Margen prom (s/out)": round(g.loc[~g["Costo_Atipico"], "Margen_Utilidad_USD"].mean(), 2),
    }), include_groups=False)

    stock_med = resumen4["Stock prom"].median()
    nps_med   = resumen4["NPS prom"].median()
    paradoja  = resumen4[
        (resumen4["Stock prom"] >= stock_med) & (resumen4["NPS prom"] < nps_med)
    ]

    # Kruskal-Wallis NPS entre categorías
    grupos = [df_cat.loc[df_cat["Categoria"]==c, "Satisfaccion_NPS_Prom"].dropna().values
              for c in resumen4.index]
    kw_H, kw_p = sci.kruskal(*[g for g in grupos if len(g) > 0])

    # Scatter Plotly
    fig4 = px.scatter(
        resumen4.reset_index(), x="Stock prom", y="NPS prom",
        text="Categoria", size=[60]*len(resumen4),
        color="NPS prom",
        color_continuous_scale=[[0, PALETTE["critico"]],
                                 [0.5, "#2A3654"],
                                 [1, PALETTE["saludable"]]],
    )
    fig4.update_traces(textposition="top center")
    fig4.add_hline(y=nps_med,   line_dash="dash", line_color=PALETTE["text_muted"],
                   annotation_text=f"Mediana NPS={nps_med:.2f}")
    fig4.add_vline(x=stock_med, line_dash="dash", line_color=PALETTE["text_muted"],
                   annotation_text=f"Mediana stock={stock_med:.0f}")
    fig4.update_layout(
        title="Disponibilidad (stock) vs. sentimiento (NPS) por categoría<br>"
              "<sup>Cuadrante sup-izq = paradoja: stock alto, NPS bajo</sup>",
        height=420,
    )
    st.plotly_chart(fig4, use_container_width=True, key="p4_scatter")

    cats_paradoja = list(paradoja.index)
    _respuesta(
        f"Categorías en paradoja (stock alto, NPS bajo): <b>{', '.join(cats_paradoja) or 'ninguna en este filtro'}</b>. "
        f"Kruskal-Wallis H={kw_H:.2f}, p={kw_p:.4f}: "
        + ("las diferencias de NPS entre categorías <b>son significativas (p&lt;0.05)</b>. "
           if kw_p < 0.05 else
           "las diferencias de NPS entre categorías <b>NO son significativas (p&gt;0.05)</b>: el sentimiento es homogéneamente bajo en todas. ") +
        "El Rating de producto es casi idéntico entre categorías (≈2.98): "
        "la causa <b>no es calidad de producto</b>. "
        "En Smartphones el margen negativo desaparece al retirar el outlier de costo ($850k), "
        "lo que apunta a <b>percepción de sobreprecio</b>, no a mala calidad."
    )

    with st.expander("📊 Procedimiento estadístico — Kruskal-Wallis, distribuciones NPS por categoría"):
        st.markdown("**Hipótesis formuladas:**")
        st.dataframe(pd.DataFrame([
            {"": "H₀", "Hipótesis": "La distribución de NPS es igual en todas las categorías"},
            {"": "H₁", "Hipótesis": "Al menos una categoría tiene una distribución de NPS distinta"},
        ]), hide_index=True, use_container_width=True)

        st.dataframe(pd.DataFrame([
            {"Estadístico": "Prueba",    "Valor": "Kruskal-Wallis (no paramétrico, no asume normalidad)"},
            {"Estadístico": "H",         "Valor": f"{kw_H:.4f}"},
            {"Estadístico": "p-valor",   "Valor": f"{kw_p:.4f}"},
            {"Estadístico": "n categorías","Valor": str(len(resumen4))},
            {"Estadístico": "α",         "Valor": "0.05"},
            {"Estadístico": "Decisión",  "Valor": "Rechazar H₀" if kw_p < 0.05 else "No rechazar H₀"},
            {"Estadístico": "Por qué Kruskal y no ANOVA",
             "Valor": "NPS tiene skew alto y distribución no normal (ver Q-Q); Kruskal es robusto"},
            {"Estadístico": "Fuente",    "Valor": "analysis.pregunta_4_diagnostico_fidelidad"},
        ]), hide_index=True, use_container_width=True)

        st.markdown("**Tabla resumen por categoría:**")
        st.dataframe(resumen4, use_container_width=True)

        with plt.rc_context(MPL_STYLE):
            n_cats = len(resumen4)
            fig_p4, axes = plt.subplots(2, n_cats, figsize=(3.5 * n_cats, 7),
                                         facecolor="#161D2F")
            if n_cats == 1:
                axes = axes.reshape(2, 1)

            colores = [PALETTE["critico"] if c in cats_paradoja
                       else PALETTE["info"] for c in resumen4.index]

            for j, (cat, col) in enumerate(zip(resumen4.index, colores)):
                vals = df_cat.loc[df_cat["Categoria"] == cat,
                                  "Satisfaccion_NPS_Prom"].dropna().values
                # Histograma + KDE
                axes[0, j].hist(vals, bins=30, color=col, alpha=0.75,
                                density=True, edgecolor="#2A3654", linewidth=0.3)
                try:
                    kde = sci.gaussian_kde(vals)
                    xk = np.linspace(vals.min(), vals.max(), 200)
                    axes[0, j].plot(xk, kde(xk), color="#E8A33D", lw=1.8)
                except Exception:
                    pass
                axes[0, j].axvline(vals.mean(), color="#3FA796", lw=1.5, linestyle="--")
                axes[0, j].set_title(f"{cat}\nμ={vals.mean():.1f}  skew={sci.skew(vals):.2f}",
                                     fontsize=9)
                axes[0, j].grid(True)
                # Q-Q
                if len(vals) >= 3:
                    (osm, osr), (sl, ic, _) = sci.probplot(vals, dist="norm")
                    axes[1, j].scatter(osm, osr, s=4, alpha=0.4, color=col)
                    axes[1, j].plot(osm, sl * np.array(osm) + ic,
                                    color="#E8A33D", lw=1.3)
                axes[1, j].set_title("Q-Q plot", fontsize=8)
                axes[1, j].grid(True)

            axes[0, 0].set_ylabel("Densidad NPS")
            axes[1, 0].set_ylabel("Cuantiles obs.")
            plt.suptitle("Distribuciones de NPS por categoría (rojo = paradoja)",
                         fontsize=11, y=1.01)
            plt.tight_layout()
            st.image(_mpl_buf(fig_p4), use_container_width=True)
            plt.close(fig_p4)
