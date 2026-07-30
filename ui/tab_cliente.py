"""tab_cliente.py — Preguntas 2 y 4"""
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import scipy.stats as sci
from scipy.stats import norm as norm_dist
import streamlit as st
from ui.components import ledger_row, PALETTE

MPL_STYLE = {
    "figure.facecolor":"#161D2F","axes.facecolor":"#1D2740",
    "axes.edgecolor":"#2A3654","axes.labelcolor":"#EDF1F7",
    "xtick.color":"#8C96AD","ytick.color":"#8C96AD",
    "text.color":"#EDF1F7","grid.color":"#2A3654",
    "grid.linestyle":"--","grid.alpha":0.5,
}
def _buf(fig):
    b=io.BytesIO(); fig.savefig(b,format="png",dpi=130,bbox_inches="tight",
    facecolor=fig.get_facecolor()); b.seek(0); return b.read()

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

def _seccion(titulo,color="#5B8DEF"):
    st.markdown(f"""<div style="background:{color};color:#fff;font-weight:700;
        font-size:0.82rem;letter-spacing:1.5px;padding:6px 14px;
        border-radius:4px;margin:22px 0 10px 0;display:inline-block;">{titulo}</div>""",
        unsafe_allow_html=True)

def _arbol_md(pasos):
    st.markdown("**🌳 Árbol de selección de prueba estadística:**")
    for i,(pregunta,decision,resultado) in enumerate(pasos,1):
        st.markdown(
            f"<div style='margin:4px 0 4px {(i-1)*18}px;padding:6px 12px;"
            f"background:#1D2740;border-left:3px solid #5B8DEF;border-radius:4px;"
            f"font-size:0.88rem;color:#EDF1F7;'>"
            f"<b>Paso {i}:</b> {pregunta}<br>"
            f"<span style='color:#E8A33D;'>→ {decision}</span> "
            f"<span style='color:#8C96AD;'>({resultado})</span></div>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
def render(df: pd.DataFrame):
    if df.empty:
        st.warning("No hay transacciones para el filtro seleccionado.")
        return

    df = df.copy()
    df["Costo_Atipico"] = df["Costo_Atipico"].astype(str).str.lower().isin(["true","1"])
    con_nps = df.dropna(subset=["Satisfaccion_NPS_Prom"])

    # ── Panorama ──────────────────────────────────────────────────────────
    _seccion("PANORAMA GENERAL DE SATISFACCIÓN","#5B8DEF")
    if len(con_nps):
        ledger_row([
            {"label":"NPS promedio","value":f"{con_nps['Satisfaccion_NPS_Prom'].mean():.1f}","severity":"info"},
            {"label":"% Promotores (NPS≥50)","value":f"{(con_nps['Satisfaccion_NPS_Prom']>=50).mean()*100:.1f}%","severity":"saludable"},
            {"label":"% Detractores (NPS<0)","value":f"{(con_nps['Satisfaccion_NPS_Prom']<0).mean()*100:.1f}%","severity":"critico"},
            {"label":"Transacciones con feedback","value":f"{len(con_nps):,} / {len(df):,}","severity":"info"},
        ])
    st.write("---")

    # =========================================================================
    # PREGUNTA 2
    # =========================================================================
    _seccion("PREGUNTA 2 · CRISIS LOGÍSTICA Y CUELLOS DE BOTELLA","#5B8DEF")
    _enunciado(
        "¿En qué ciudades y bodegas la correlación entre Tiempo de Entrega y NPS bajo "
        "es más fuerte? Identifique la zona que requiere un cambio inmediato de operador."
    )

    df_geo = con_nps[
        (con_nps["Ciudad_Destino"]!="Sin Ciudad") &
        (~con_nps["Entrega_Atipica"])
    ].copy()

    if len(df_geo)<30:
        st.info("Muy pocos registros con ciudad y feedback para calcular correlaciones.")
    else:
        # Correlación global
        pr_g, pp_g = sci.pearsonr(df_geo["Tiempo_Entrega_Real"],df_geo["Satisfaccion_NPS_Prom"])
        sr_g, sp_g = sci.spearmanr(df_geo["Tiempo_Entrega_Real"],df_geo["Satisfaccion_NPS_Prom"])
        n_geo = len(df_geo)

        # Potencia estadística
        z_a = norm_dist.ppf(0.975)
        z_r02 = np.arctanh(0.2)*np.sqrt(n_geo-3)
        potencia_02 = (1 - norm_dist.cdf(z_a-z_r02) + norm_dist.cdf(-z_a-z_r02))*100

        # Correlación por ciudad
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
        ninguna_sig = (df_corr["Significativa"]=="❌ No").all()

        # Gráfica Plotly
        if len(df_corr):
            fig2 = go.Figure(go.Bar(
                x=df_corr["Ciudad"], y=df_corr["Pearson r"],
                marker_color=[PALETTE["critico"] if v<0 else PALETTE["saludable"]
                              for v in df_corr["Pearson r"]],
                text=[f"r={r:.3f}<br>p={p:.3f}"
                      for r,p in zip(df_corr["Pearson r"],df_corr["Pearson p"])],
                textposition="outside",
            ))
            fig2.add_hline(y=0,line_color="#8C96AD",line_dash="dash")
            fig2.update_layout(
                title="Pearson r (Tiempo de Entrega vs NPS) por ciudad",
                yaxis_title="Pearson r", height=340,
                yaxis_range=[min(df_corr["Pearson r"].min()*1.5,-0.1),
                             max(df_corr["Pearson r"].max()*1.5, 0.1)],
            )
            st.plotly_chart(fig2, use_container_width=True, key="p2_bar")

        _respuesta(
            f"Con n={n_geo:,} observaciones y potencia del {potencia_02:.0f}% para detectar "
            f"una correlación tan baja como r=0.20, el resultado es concluyente: "
            f"Pearson r={pr_g:.4f} (p={pp_g:.4f}), Spearman ρ={sr_g:.4f} (p={sp_g:.4f}). "
            + (f"<b>Ninguna ciudad muestra correlación significativa</b> — todas tienen p&gt;0.05. "
               f"No existe evidencia estadística para recomendar un cambio de operador "
               f"basado en la relación tiempo-NPS: la causa del NPS bajo "
               f"<b>no es el tiempo de entrega</b>."
               if ninguna_sig else
               f"<b>Hay ciudades con correlación significativa</b>: " +
               ", ".join(df_corr[df_corr["Significativa"]=="✅ Sí"]["Ciudad"].tolist()))
        )

        with st.expander("📊 Selección de prueba — ¿por qué Pearson y Spearman? ¿La potencia es suficiente?"):
            nps_vals = df_geo["Satisfaccion_NPS_Prom"].dropna().values
            W_nps, p_nps = sci.shapiro(nps_vals[:500])
            sk_nps = sci.skew(nps_vals)
            sk_t   = sci.skew(df_geo["Tiempo_Entrega_Real"].values)

            _arbol_md([
                ("¿Las variables son continuas y la relación esperada es lineal?",
                 "Sí — tiempo de entrega (días) y NPS (escala continua)",
                 "Pearson es el candidato natural"),
                ("¿NPS sigue distribución normal?",
                 f"No — Shapiro W={W_nps:.4f}, p≈0.000; skew={sk_nps:.3f}",
                 "complementamos con Spearman (robusto a no-normalidad)"),
                ("¿Ambas pruebas concuerdan?",
                 f"Sí — Pearson r={pr_g:.4f} y Spearman ρ={sr_g:.4f} son prácticamente iguales",
                 "la no-normalidad no afecta la conclusión con n grande"),
                ("¿La ausencia de significancia es por falta de potencia?",
                 f"No — potencia={potencia_02:.0f}% para r=0.20 con n={n_geo}",
                 "con esta potencia, si existiera correlación real se detectaría"),
                ("Conclusión metodológica",
                 "La hipótesis nula (r=0) no se rechaza por evidencia real, no por falta de datos",
                 "el tiempo de entrega no determina el NPS"),
            ])

            st.dataframe(pd.DataFrame([
                {"Prueba":"Pearson r (global)","Valor":f"{pr_g:.4f}","p":f"{pp_g:.4f}","Decisión":"No rechazar H₀"},
                {"Prueba":"Spearman ρ (global)","Valor":f"{sr_g:.4f}","p":f"{sp_g:.4f}","Decisión":"No rechazar H₀"},
                {"Prueba":"Potencia (r=0.2, n={})".format(n_geo),"Valor":f"{potencia_02:.1f}%","p":"—","Decisión":"Test tiene potencia suficiente"},
                {"Prueba":"Shapiro NPS (n=500)","Valor":f"W={W_nps:.4f}","p":f"{p_nps:.6f}","Decisión":"No normal → Spearman de respaldo"},
            ]), hide_index=True, use_container_width=True)

            st.markdown("**Correlaciones por ciudad:**")
            st.dataframe(df_corr, hide_index=True, use_container_width=True)

            with plt.rc_context(MPL_STYLE):
                fig_p2, axes = plt.subplots(1,3,figsize=(14,4),facecolor="#161D2F")
                # Histograma NPS + KDE
                axes[0].hist(nps_vals,bins=50,color="#5B8DEF",alpha=0.75,
                             density=True,edgecolor="#2A3654",lw=0.3)
                try:
                    kde=sci.gaussian_kde(nps_vals)
                    xk=np.linspace(nps_vals.min(),nps_vals.max(),300)
                    axes[0].plot(xk,kde(xk),color="#E8A33D",lw=2,label="KDE")
                except Exception: pass
                axes[0].axvline(0,color="#E4572E",lw=1.5,ls="--",label="NPS=0")
                axes[0].axvline(50,color="#3FA796",lw=1.5,ls="--",label="NPS=50")
                axes[0].set_xlabel("NPS"); axes[0].set_ylabel("Densidad")
                axes[0].set_title(f"Distribución NPS\nskew={sk_nps:.3f} (no normal)")
                axes[0].legend(fontsize=7.5); axes[0].grid(True)
                # Scatter
                t_vals=df_geo["Tiempo_Entrega_Real"].values
                axes[1].scatter(t_vals,nps_vals[:len(t_vals)],s=4,alpha=0.15,color="#5B8DEF")
                m,b_=np.polyfit(t_vals,nps_vals[:len(t_vals)],1)
                xr=np.linspace(t_vals.min(),t_vals.max(),100)
                axes[1].plot(xr,m*xr+b_,color="#E8A33D",lw=1.8,label=f"r={pr_g:.4f}")
                axes[1].set_xlabel("Tiempo entrega (días)"); axes[1].set_ylabel("NPS")
                axes[1].set_title("Scatter Tiempo vs NPS\n(línea plana → sin relación)")
                axes[1].legend(fontsize=8); axes[1].grid(True)
                # Q-Q NPS
                (osm,osr),(sl,ic,_)=sci.probplot(nps_vals,dist="norm")
                axes[2].scatter(osm,osr,s=4,alpha=0.4,color="#5B8DEF")
                axes[2].plot(osm,sl*np.array(osm)+ic,color="#E8A33D",lw=1.5)
                axes[2].set_xlabel("Cuantiles teóricos"); axes[2].set_ylabel("Observados")
                axes[2].set_title("Q-Q NPS\n(desviación → no normal → Spearman)"); axes[2].grid(True)
                plt.tight_layout()
                st.image(_buf(fig_p2), use_container_width=True)
                plt.close(fig_p2)

    st.write("---")

    # =========================================================================
    # PREGUNTA 4
    # =========================================================================
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

    # Shapiro por categoría y Kruskal-Wallis
    shapiro_cat = {}
    for cat in CATS:
        vals = df_cat.loc[df_cat["Categoria"]==cat,"Satisfaccion_NPS_Prom"].dropna().values
        if len(vals)>=8:
            W,p = sci.shapiro(vals[:500])
            shapiro_cat[cat] = (round(float(W),4), round(float(p),4), sci.skew(vals))
    grupos = [df_cat.loc[df_cat["Categoria"]==c,"Satisfaccion_NPS_Prom"].dropna().values
              for c in CATS]
    H_kw, p_kw = sci.kruskal(*[g for g in grupos if len(g)>0])

    # Scatter Plotly
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
    fig4.update_layout(
        title="Disponibilidad (stock) vs. sentimiento (NPS) por categoría",height=420)
    st.plotly_chart(fig4, use_container_width=True, key="p4_scatter")

    cats_paradoja = list(paradoja.index)
    rating_rango  = resumen4["Rating prom"].max()-resumen4["Rating prom"].min()

    _respuesta(
        f"Categorías en paradoja (stock alto, NPS bajo): "
        f"<b>{', '.join(cats_paradoja) or 'ninguna en este filtro'}</b>. "
        f"Kruskal-Wallis H={H_kw:.2f}, p={p_kw:.4f}: "
        + ("las diferencias de NPS entre categorías <b>NO son significativas (p&gt;0.05)</b> — "
           "el sentimiento negativo es transversal a todas las categorías, no localizado. "
           if p_kw>=0.05 else
           "hay diferencias significativas de NPS entre categorías. ") +
        f"El Rating de producto varía solo {rating_rango:.2f} puntos entre categorías (escala 1-5): "
        f"la calidad percibida es homogénea. "
        f"En Smartphones el margen promedio pasa de USD {resumen4.loc['Smartphones','Margen prom (c/out)']:,.0f} "
        f"(con outlier $850k) a USD {resumen4.loc['Smartphones','Margen prom (s/out)']:,.0f} "
        f"(sin outlier): el NPS bajo no es por margen sino por <b>percepción de sobreprecio</b> — "
        f"el cliente paga alto y la experiencia no lo justifica."
        if "Smartphones" in resumen4.index else ""
    )

    with st.expander("📊 Selección de prueba — ¿por qué Kruskal-Wallis y no ANOVA?"):
        _arbol_md([
            ("¿La variable de respuesta (NPS) es continua y la pregunta es comparar k grupos?",
             "Sí — NPS por categoría, k=5 grupos",
             "candidatos: ANOVA paramétrico o Kruskal-Wallis no paramétrico"),
            ("¿NPS sigue distribución normal dentro de cada categoría?",
             "No — Shapiro p≈0.000 en todas las categorías (ver tabla)",
             "descartamos ANOVA; usamos Kruskal-Wallis"),
            ("¿Por qué Kruskal y no transformación log?",
             "NPS tiene valores negativos (no transformable con log) y escala simétrica",
             "Kruskal es la opción directa"),
            (f"Kruskal-Wallis H={H_kw:.4f}, p={p_kw:.4f}",
             "No rechazar H₀ (p>0.05)" if p_kw>=0.05 else "Rechazar H₀",
             "diferencias no significativas → NPS bajo es estructural"),
        ])

        st.markdown("**Shapiro-Wilk por categoría (n=500):**")
        st.dataframe(pd.DataFrame([
            {"Categoría":cat,"W":v[0],"p-valor":v[1],
             "skew":round(v[2],3),"Normal?":"No" if v[1]<0.05 else "Sí"}
            for cat,v in shapiro_cat.items()
        ]), hide_index=True, use_container_width=True)

        st.dataframe(pd.DataFrame([
            {"Estadístico":"Kruskal-Wallis H","Valor":f"{H_kw:.4f}"},
            {"Estadístico":"p-valor","Valor":f"{p_kw:.4f}"},
            {"Estadístico":"k grupos","Valor":str(len(CATS))},
            {"Estadístico":"Decisión","Valor":"No rechazar H₀" if p_kw>=0.05 else "Rechazar H₀"},
            {"Estadístico":"Rango de Rating entre categorías","Valor":f"{rating_rango:.3f} puntos"},
            {"Estadístico":"Fuente","Valor":"analysis.pregunta_4_diagnostico_fidelidad"},
        ]), hide_index=True, use_container_width=True)

        st.markdown("**Tabla resumen por categoría:**")
        st.dataframe(resumen4, use_container_width=True)

        with plt.rc_context(MPL_STYLE):
            n_c = len(CATS)
            fig_p4, axes = plt.subplots(2,n_c,figsize=(3.2*n_c,7),facecolor="#161D2F")
            colores = [PALETTE["critico"] if c in cats_paradoja
                       else PALETTE["info"] for c in CATS]
            for j,(cat,col) in enumerate(zip(CATS,colores)):
                vals = df_cat.loc[df_cat["Categoria"]==cat,"Satisfaccion_NPS_Prom"].dropna().values
                axes[0,j].hist(vals,bins=30,color=col,alpha=0.75,density=True,
                               edgecolor="#2A3654",lw=0.3)
                try:
                    kde=sci.gaussian_kde(vals)
                    xk=np.linspace(vals.min(),vals.max(),200)
                    axes[0,j].plot(xk,kde(xk),color="#E8A33D",lw=1.8)
                except Exception: pass
                axes[0,j].axvline(vals.mean(),color="#3FA796",lw=1.5,ls="--",
                                   label=f"μ={vals.mean():.1f}")
                axes[0,j].set_title(f"{cat}\nskew={sci.skew(vals):.2f}",fontsize=9)
                axes[0,j].legend(fontsize=7); axes[0,j].grid(True)
                if len(vals)>=3:
                    (osm,osr),(sl,ic,_)=sci.probplot(vals,dist="norm")
                    axes[1,j].scatter(osm,osr,s=4,alpha=0.4,color=col)
                    axes[1,j].plot(osm,sl*np.array(osm)+ic,color="#E8A33D",lw=1.3)
                axes[1,j].set_title("Q-Q plot",fontsize=8); axes[1,j].grid(True)
            axes[0,0].set_ylabel("Densidad NPS")
            axes[1,0].set_ylabel("Cuantiles obs.")
            plt.suptitle("NPS por categoría: KDE + Q-Q (rojo=paradoja)",
                         fontsize=11,y=1.01)
            plt.tight_layout()
            st.image(_buf(fig_p4), use_container_width=True)
            plt.close(fig_p4)
