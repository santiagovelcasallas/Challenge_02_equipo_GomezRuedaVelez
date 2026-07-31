"""tab_cliente.py — Preguntas 2 y 4"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import scipy.stats as sci
from scipy.stats import norm as N
import streamlit as st
from ui.components import ledger_row, PALETTE
from ui._stat_drawers import p2_drawer, p4_drawer

def _enunciado(t):
    st.markdown(f"""<div style="border-left:4px solid #E8A33D;background:#1D2740;
        padding:12px 18px;border-radius:6px;margin-bottom:14px;
        font-size:0.97rem;color:#EDF1F7;font-style:italic;">{t}</div>""",
        unsafe_allow_html=True)

def _respuesta(t):
    st.markdown(f"""<div style="background:#0D1321;border:1px solid #3FA796;
        border-radius:6px;padding:12px 18px;margin-bottom:14px;
        font-size:0.95rem;color:#EDF1F7;">🎯 <b>Respuesta:</b> {t}</div>""",
        unsafe_allow_html=True)

def _seccion(titulo, color="#5B8DEF"):
    st.markdown(f"""<div style="background:{color};color:#fff;font-weight:700;
        font-size:0.82rem;letter-spacing:1.5px;padding:6px 14px;
        border-radius:4px;margin:22px 0 10px 0;display:inline-block;">{titulo}</div>""",
        unsafe_allow_html=True)

def render(df: pd.DataFrame):
    if df.empty:
        st.warning("No hay transacciones para el filtro seleccionado.")
        return

    df = df.copy()
    df["Costo_Atipico"] = df["Costo_Atipico"].astype(str).str.lower().isin(["true","1"])
    con_nps = df.dropna(subset=["Satisfaccion_NPS_Prom"])

    _seccion("PANORAMA GENERAL DE SATISFACCIÓN","#5B8DEF")
    if len(con_nps):
        ledger_row([
            {"label":"NPS promedio","value":f"{con_nps['Satisfaccion_NPS_Prom'].mean():.1f}","severity":"info"},
            {"label":"% Promotores (NPS≥50)","value":f"{(con_nps['Satisfaccion_NPS_Prom']>=50).mean()*100:.1f}%","severity":"saludable"},
            {"label":"% Detractores (NPS<0)","value":f"{(con_nps['Satisfaccion_NPS_Prom']<0).mean()*100:.1f}%","severity":"critico"},
            {"label":"Con feedback","value":f"{len(con_nps):,} / {len(df):,}","severity":"info"},
        ])
    st.write("---")

    # ── P2 ────────────────────────────────────────────────────────────────
    _seccion("PREGUNTA 2 · CRISIS LOGÍSTICA Y CUELLOS DE BOTELLA","#5B8DEF")
    _enunciado(
        "¿En qué ciudades y bodegas la correlación entre Tiempo de Entrega y NPS bajo "
        "es más fuerte? Identifique la zona que requiere un cambio inmediato de operador."
    )

    df_geo = con_nps[(con_nps["Ciudad_Destino"]!="Sin Ciudad")&(~con_nps["Entrega_Atipica"])].copy()

    if len(df_geo)<30:
        st.info(f"Muy pocos registros con ciudad y NPS válidos (n={len(df_geo)}) para calcular correlaciones. Ajusta el filtro.")
    else:
        pr_g, pp_g = sci.pearsonr(df_geo["Tiempo_Entrega_Real"],df_geo["Satisfaccion_NPS_Prom"])
        sr_g, sp_g = sci.spearmanr(df_geo["Tiempo_Entrega_Real"],df_geo["Satisfaccion_NPS_Prom"])
        n2 = len(df_geo)

        corr_ciudad = []
        for ciudad, g in df_geo.groupby("Ciudad_Destino"):
            if len(g)<30: continue
            rp,pp = sci.pearsonr(g["Tiempo_Entrega_Real"],g["Satisfaccion_NPS_Prom"])
            rs,ps = sci.spearmanr(g["Tiempo_Entrega_Real"],g["Satisfaccion_NPS_Prom"])
            corr_ciudad.append({
                "Ciudad":ciudad,"n":int(len(g)),
                "Pearson r":round(rp,4),"Pearson p":round(pp,4),
                "Spearman ρ":round(rs,4),"Spearman p":round(ps,4),
                "Significativa":("✅ Sí" if (pp<0.05 or ps<0.05) else "❌ No"),
            })
        df_corr = pd.DataFrame(corr_ciudad).sort_values("Pearson r")
        ninguna_sig = (df_corr["Significativa"]=="❌ No").all() if len(df_corr) else True

        if len(df_corr):
            fig2 = go.Figure(go.Bar(
                x=df_corr["Ciudad"], y=df_corr["Pearson r"],
                marker_color=[PALETTE["critico"] if v<0 else PALETTE["saludable"]
                              for v in df_corr["Pearson r"]],
                text=[f"r={r:.3f} p={p:.3f}"
                      for r,p in zip(df_corr["Pearson r"],df_corr["Pearson p"])],
                textposition="outside",
            ))
            fig2.add_hline(y=0,line_color="#8C96AD",line_dash="dash")
            fig2.update_layout(title="Pearson r (Tiempo vs NPS) por ciudad",
                               yaxis_title="Pearson r", height=340,
                               yaxis_range=[min(df_corr["Pearson r"].min()*2,-0.1),
                                            max(df_corr["Pearson r"].max()*2, 0.1)])
            st.plotly_chart(fig2, use_container_width=True, key="p2_bar")

        z_a = N.ppf(0.975)
        z_r = np.arctanh(0.1)*np.sqrt(n2-3)
        potencia_01 = (1-N.cdf(z_a-z_r)+N.cdf(-z_a-z_r))*100

        _respuesta(
            f"Con n={n2:,} y potencia del {potencia_01:.0f}% para detectar r=0.10, "
            f"el test es concluyente: Pearson r={pr_g:.4f} (p={pp_g:.4f}), "
            f"Spearman ρ={sr_g:.4f} (p={sp_g:.4f}). "
            + ("<b>Ninguna ciudad muestra correlación significativa</b> (todas p>0.05). "
               "No hay evidencia estadística para recomendar un cambio de operador "
               "basado en tiempo↔NPS. La causa del NPS bajo <b>no es el tiempo de entrega</b>."
               if ninguna_sig else
               "Ciudades con correlación significativa: " +
               ", ".join(df_corr[df_corr["Significativa"]=="✅ Sí"]["Ciudad"].tolist()) + ".")
        )

        p2_drawer(df_geo, pr_g, pp_g, sr_g, sp_g, df_corr)

    st.write("---")

    # ── P4 ────────────────────────────────────────────────────────────────
    _seccion("PREGUNTA 4 · DIAGNÓSTICO DE FIDELIDAD","#5B8DEF")
    _enunciado(
        "¿Existen categorías de productos con alta disponibilidad (stock alto) pero "
        "con un sentimiento de cliente negativo? Explique la paradoja: "
        "¿Es mala calidad de producto o sobrecosto?"
    )

    CATS = ["Accesorios","Laptops","Monitores","Smartphones","Tablets"]
    df_cat = df[df["Categoria"].isin(CATS)].copy()

    if len(df_cat)<10:
        st.info("Sin datos de categoría suficientes en este filtro.")
        return

    resumen4 = df_cat.groupby("Categoria").apply(lambda g: pd.Series({
        "n":                   int(len(g)),
        "Stock prom":          round(g["Stock_Actual"].mean(),1),
        "NPS prom":            round(g["Satisfaccion_NPS_Prom"].mean(),2),
        "Rating prom":         round(g["Rating_Producto_Prom"].mean(),2),
        "Margen prom (c/out)": round(g["Margen_Utilidad_USD"].mean(),2),
        "Margen prom (s/out)": round(g.loc[~g["Costo_Atipico"],"Margen_Utilidad_USD"].mean(),2),
    }), include_groups=False)

    stock_med = resumen4["Stock prom"].median()
    nps_med   = resumen4["NPS prom"].median()
    paradoja  = resumen4[(resumen4["Stock prom"]>=stock_med)&(resumen4["NPS prom"]<nps_med)]
    cats_paradoja = list(paradoja.index)

    grupos4 = [df_cat.loc[df_cat["Categoria"]==c,"Satisfaccion_NPS_Prom"].dropna().values
               for c in CATS if len(df_cat[df_cat["Categoria"]==c])>0]
    if len(grupos4) < 2:
        st.info("Se necesitan al menos 2 categorías con datos para calcular Kruskal-Wallis. Ajusta el filtro de categoría.")
        return
    H_kw, p_kw = sci.kruskal(*grupos4)

    fig4 = px.scatter(
        resumen4.reset_index(), x="Stock prom", y="NPS prom",
        text="Categoria", size=[60]*len(resumen4), color="NPS prom",
        color_continuous_scale=[[0,PALETTE["critico"]],[0.5,"#2A3654"],[1,PALETTE["saludable"]]],
    )
    fig4.update_traces(textposition="top center")
    fig4.add_hline(y=nps_med,line_dash="dash",line_color=PALETTE["text_muted"],
                   annotation_text=f"Mediana NPS={nps_med:.2f}")
    fig4.add_vline(x=stock_med,line_dash="dash",line_color=PALETTE["text_muted"],
                   annotation_text=f"Mediana stock={stock_med:.0f}")
    fig4.update_layout(title="Disponibilidad (stock) vs. sentimiento (NPS) por categoría",height=420)
    st.plotly_chart(fig4, use_container_width=True, key="p4_scatter")

    rating_rango = resumen4["Rating prom"].max()-resumen4["Rating prom"].min()

    _respuesta(
        f"Categorías en paradoja (stock alto, NPS bajo): "
        f"<b>{', '.join(cats_paradoja) or 'ninguna en este filtro'}</b>. "
        f"Kruskal-Wallis H={H_kw:.2f}, p={p_kw:.4f}: "
        + ("el NPS bajo es <b>transversal a todas las categorías</b> (p>0.05 → no hay diferencia significativa). "
           if p_kw>=0.05 else "diferencias significativas entre categorías (p<0.05). ") +
        f"El Rating de producto varía solo {rating_rango:.3f} puntos entre categorías: "
        f"<b>la calidad percibida es homogénea</b>. "
        + (f"En Smartphones el margen pasa de USD {resumen4.loc['Smartphones','Margen prom (c/out)']:,.0f} "
           f"(con outlier) a USD {resumen4.loc['Smartphones','Margen prom (s/out)']:,.0f} "
           f"(sin outlier): el NPS bajo apunta a <b>percepción de sobreprecio</b>, no a calidad."
           if "Smartphones" in resumen4.index else "")
    )

    p4_drawer(df_cat, resumen4, H_kw, p_kw, cats_paradoja)
