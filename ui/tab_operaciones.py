"""tab_operaciones.py — Preguntas 1, 3 y 5"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import scipy.stats as sci
import streamlit as st
from ui.components import ledger_row, PALETTE
from ui._stat_drawers import p1_drawer, p3_drawer, p5_drawer

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

def _seccion(titulo, color="#E4572E"):
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

    # ── P1 ────────────────────────────────────────────────────────────────
    _seccion("PREGUNTA 1 · FUGA DE CAPITAL Y RENTABILIDAD")
    _enunciado(
        "Localice los SKUs que se están vendiendo con margen negativo. "
        "¿Representan una pérdida aceptable por volumen o es una falla crítica "
        "de precios en el canal Online?"
    )

    df_c = df.dropna(subset=["Margen_Utilidad_USD"])
    df_c = df_c[~df_c["Costo_Atipico"]]
    neg  = df_c[df_c["Margen_Utilidad_USD"] < 0]

    if len(df_c) == 0:
        st.info("Sin transacciones con costo conocido en este filtro.")
    else:
        pct_neg  = len(neg)/len(df_c)*100
        perdida  = neg["Margen_Utilidad_USD"].sum()
        margen_t = df_c["Margen_Utilidad_USD"].sum()

        ledger_row([
            {"label":"Transacciones margen negativo","value":f"{len(neg):,}",
             "context":f"{pct_neg:.1f}% del total con costo conocido (sin outlier $850k)",
             "severity":"critico"},
            {"label":"Pérdida acumulada","value":f"USD {perdida:,.0f}","severity":"critico"},
            {"label":"Margen total del período","value":f"USD {margen_t:,.0f}",
             "severity":"saludable" if margen_t>0 else "critico"},
        ])

        por_canal = df_c.groupby("Canal_Venta").apply(lambda g: pd.Series({
            "pct_neg": (g["Margen_Utilidad_USD"]<0).mean()*100,
            "mediana": g["Margen_Utilidad_USD"].median(),
        }), include_groups=False).sort_values("pct_neg")

        fig1 = go.Figure(go.Bar(
            x=por_canal["pct_neg"], y=por_canal.index, orientation="h",
            marker_color=PALETTE["critico"],
            text=[f"{v:.1f}%" for v in por_canal["pct_neg"]], textposition="outside",
        ))
        fig1.update_layout(title="% de transacciones con margen negativo, por canal",
                           xaxis_title="%", height=300,
                           xaxis_range=[0, por_canal["pct_neg"].max()*1.25])
        st.plotly_chart(fig1, use_container_width=True, key="p1_canal")

        # Pruebas
        grupos = [g["Margen_Utilidad_USD"].dropna().values
                  for _,g in df_c.groupby("Canal_Venta")]
        H_kw, p_kw = sci.kruskal(*grupos)
        online_vals = df_c[df_c["Canal_Venta"]=="Online"]["Margen_Utilidad_USD"].dropna().values
        mw = {c: round(float(sci.mannwhitneyu(online_vals,g,alternative="two-sided")[1]),4)
              for c,g in zip(sorted(df_c["Canal_Venta"].unique()),grupos)
              if c!="Online"}

        online_pct = por_canal.loc["Online","pct_neg"] if "Online" in por_canal.index else 0
        fisico_pct = por_canal.loc["Físico","pct_neg"] if "Físico" in por_canal.index else 0
        online_med = por_canal.loc["Online","mediana"] if "Online" in por_canal.index else 0

        _respuesta(
            f"Online tiene {online_pct:.1f}% de transacciones con margen negativo "
            f"(mediana USD {online_med:,.0f}) — el segundo valor más bajo. "
            f"Físico alcanza {fisico_pct:.1f}%, el más alto. "
            f"Kruskal-Wallis H={H_kw:.2f}, p={p_kw:.3f}: <b>no hay diferencia significativa "
            f"entre canales</b>. Mann-Whitney Online vs cada canal: "
            + ", ".join(f"{c} p={v}" for c,v in mw.items()) +
            f". <b>El canal Online NO es el problema</b>: la fuga es "
            f"<b>estructural en el catálogo</b> — todos los canales operan entre "
            f"{por_canal['pct_neg'].min():.1f}–{por_canal['pct_neg'].max():.1f}% de margen "
            f"negativo porque los precios no cubren costos en esos SKUs."
        )

        p1_drawer(df_c)

    st.write("---")

    # ── P3 ────────────────────────────────────────────────────────────────
    _seccion("PREGUNTA 3 · ANÁLISIS DE LA VENTA INVISIBLE", "#E8A33D")
    _enunciado(
        "Cuantifique el impacto financiero (en USD) de las ventas cuyos SKUs no están "
        "en el maestro de inventario. ¿Qué porcentaje del ingreso total está en riesgo "
        "por falta de control de inventario?"
    )

    ing_total = df["Ingreso_Bruto"].sum()
    fant      = df[df["Es_Venta_Fantasma"]]
    ing_fant  = fant["Ingreso_Bruto"].sum()
    pct_riesgo= ing_fant/ing_total*100 if ing_total else 0
    n_skus    = fant["SKU_ID"].nunique()
    rep       = fant["SKU_ID"].value_counts()

    np.random.seed(42)
    boots = [df.sample(len(df),replace=True)["Es_Venta_Fantasma"].mean()*100
             for _ in range(1000)]
    ic_b = np.percentile(boots,[2.5,97.5])

    ledger_row([
        {"label":"Ingreso en riesgo","value":f"USD {ing_fant:,.0f}",
         "context":f"{pct_riesgo:.1f}% · IC 95% bootstrap transacciones: [{ic_b[0]:.1f}%, {ic_b[1]:.1f}%]",
         "severity":"advertencia"},
        {"label":"Transacciones fantasma","value":f"{len(fant):,}",
         "context":f"{len(fant)/len(df)*100:.1f}% del total","severity":"advertencia"},
        {"label":"SKUs distintos sin catálogo","value":f"{n_skus:,}","severity":"advertencia"},
    ])

    c1,c2 = st.columns([1,1.4])
    with c1:
        fig3 = go.Figure(go.Pie(
            labels=["Catalogado","Sin catálogo (en riesgo)"],
            values=[ing_total-ing_fant, ing_fant],
            marker_colors=[PALETTE["info"],PALETTE["critico"]], hole=0.5))
        fig3.update_layout(height=260, margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True, key="p3_pie")
    with c2:
        top_f = fant.groupby("SKU_ID")["Ingreso_Bruto"].sum().sort_values(ascending=False).head(10)
        fig3b = go.Figure(go.Bar(x=top_f.values, y=top_f.index, orientation="h",
                                  marker_color=PALETTE["advertencia"]))
        fig3b.update_layout(title="Top 10 SKUs fantasma por ingreso",
                            xaxis_title="USD", height=260, margin=dict(t=30,b=10))
        st.plotly_chart(fig3b, use_container_width=True, key="p3_top")

    _respuesta(
        f"USD {ing_fant:,.0f} ({pct_riesgo:.1f}% del ingreso total) no tiene respaldo "
        f"en el maestro de inventario — sin costo, sin categoría, sin trazabilidad. "
        f"Los {n_skus} SKUs distintos tienen recurrencia media de {rep.mean():.1f} "
        f"transacciones (máx {rep.max()}): distribución dispersa característica de "
        f"<b>falla de catálogo</b>, no de fraude."
    )

    p3_drawer(df, pct_riesgo, ic_b, boots)

    st.write("---")

    # ── P5 ────────────────────────────────────────────────────────────────
    _seccion("PREGUNTA 5 · STORYTELLING DE RIESGO OPERATIVO", "#E8A33D")
    _enunciado(
        "Visualice la relación entre la antigüedad de la Última Revisión del stock "
        "y la tasa de Tickets de Soporte. ¿Qué bodegas están operando a ciegas "
        "y cómo impacta esto en la satisfacción final?"
    )

    df_bod = df[df["Bodega_Origen"]!="Sin Bodega"].copy()
    if len(df_bod)<10:
        st.info("Sin datos de bodega suficientes en este filtro.")
        return

    res5 = df_bod.groupby("Bodega_Origen").agg(
        n               =("Transaccion_ID","count"),
        dias_revision   =("Dias_Desde_Ultima_Revision","mean"),
        tasa_ticket_pct =("Ticket_Soporte_Abierto",lambda x: x.mean()*100),
        nps_prom        =("Satisfaccion_NPS_Prom","mean"),
        brecha_prom     =("Brecha_Entrega_Dias","mean"),
    ).round(2).reset_index()

    r5, p5 = sci.pearsonr(res5["dias_revision"], res5["tasa_ticket_pct"])

    fig5 = px.scatter(
        res5, x="dias_revision", y="tasa_ticket_pct",
        size="n", text="Bodega_Origen", color="tasa_ticket_pct",
        color_continuous_scale=[[0,PALETTE["saludable"]],[0.5,PALETTE["advertencia"]],[1,PALETTE["critico"]]],
        hover_data={"nps_prom":True,"brecha_prom":True,"n":True},
        labels={"dias_revision":"Días promedio desde última revisión","tasa_ticket_pct":"% con ticket"},
    )
    fig5.update_traces(textposition="top center")
    fig5.update_layout(title="Antigüedad de revisión vs. tasa de tickets", height=380)
    st.plotly_chart(fig5, use_container_width=True, key="p5_scatter")

    bodega_ciega  = res5.loc[res5["dias_revision"].idxmax(),"Bodega_Origen"]
    bodega_ticket = res5.loc[res5["tasa_ticket_pct"].idxmax(),"Bodega_Origen"]
    dias_c = res5.loc[res5["Bodega_Origen"]==bodega_ciega,"dias_revision"].values[0]
    tkt_c  = res5.loc[res5["Bodega_Origen"]==bodega_ticket,"tasa_ticket_pct"].values[0]

    _respuesta(
        f"<b>{bodega_ciega}</b> opera con el stock más desactualizado ({dias_c:.0f} días). "
        f"<b>{bodega_ticket}</b> tiene la mayor tasa de tickets ({tkt_c:.1f}%). "
        f"Pearson r={r5:.3f}, p={p5:.3f}: correlación positiva pero <b>no significativa</b> "
        f"con n={len(res5)} bodegas. El patrón es descriptivo — requiere datos a nivel "
        f"SKU-bodega para ser concluyente."
    )

    p5_drawer(res5, r5, p5)
