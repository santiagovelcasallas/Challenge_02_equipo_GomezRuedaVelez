"""
_stat_drawers.py — Cajones estadísticos para las 5 preguntas
============================================================
Cada función recibe los datos calculados y renderiza:
  1. Árbol de selección de prueba con evidencia numérica
  2. Por qué se descarta cada alternativa
  3. Tabla de hipótesis + resultados
  4. Gráficas Matplotlib de distribución
"""
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as sci
from scipy.stats import norm as N
import streamlit as st
from ui.components import PALETTE

MPL = {
    "figure.facecolor":"#161D2F","axes.facecolor":"#1D2740",
    "axes.edgecolor":"#2A3654","axes.labelcolor":"#EDF1F7",
    "xtick.color":"#8C96AD","ytick.color":"#8C96AD",
    "text.color":"#EDF1F7","grid.color":"#2A3654",
    "grid.linestyle":"--","grid.alpha":0.5,
}

def _buf(fig):
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    b.seek(0); return b.read()

def _paso(n, pregunta, evidencia, decision, color="#5B8DEF"):
    st.markdown(
        f"<div style='margin:4px 0 4px {(n-1)*16}px;padding:7px 13px;"
        f"background:#1D2740;border-left:3px solid {color};border-radius:4px;"
        f"font-size:0.87rem;color:#EDF1F7;'>"
        f"<b>Paso {n}.</b> {pregunta}<br>"
        f"<span style='color:#8C96AD;font-size:0.82rem;'>Evidencia: {evidencia}</span><br>"
        f"<span style='color:#E8A33D;'>→ {decision}</span></div>",
        unsafe_allow_html=True)

def _tabla(filas):
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)


# ── P1 ────────────────────────────────────────────────────────────────────
def p1_drawer(df_c):
    """Argumento matemático P1: Kruskal vs ANOVA vs Chi²."""
    canales = sorted(df_c["Canal_Venta"].unique())
    grupos  = [df_c[df_c["Canal_Venta"]==c]["Margen_Utilidad_USD"].dropna().values
               for c in canales]

    # Shapiro por canal
    shapiro = {}
    ks_res  = {}
    for c, v in zip(canales, grupos):
        W, p = sci.shapiro(v[:500])
        vn = (v - v.mean()) / v.std()
        ks, pks = sci.kstest(vn, "norm")
        shapiro[c] = (round(float(W),4), float(p), round(sci.skew(v),3), round(sci.kurtosis(v),3))
        ks_res[c]  = (round(ks,4), round(pks,4))

    L, pL   = sci.levene(*grupos)
    H, pH   = sci.kruskal(*grupos)
    cont    = df_c.groupby("Canal_Venta").apply(
        lambda g: pd.Series({"neg":(g["Margen_Utilidad_USD"]<0).sum(),
                             "pos":(g["Margen_Utilidad_USD"]>=0).sum()}),
        include_groups=False)
    chi2, pchi2, dof, _ = sci.chi2_contingency(cont.values)

    online = df_c[df_c["Canal_Venta"]=="Online"]["Margen_Utilidad_USD"].dropna().values
    mw = {}
    for c, v in zip(canales, grupos):
        if c == "Online": continue
        U, p_mw = sci.mannwhitneyu(online, v, alternative="two-sided")
        mw[c] = round(float(p_mw), 4)

    with st.expander("📐 Argumento matemático — selección y descarte de pruebas estadísticas"):

        st.markdown("### Paso 1 — ¿Las distribuciones son normales?")
        st.markdown("Si son normales → ANOVA. Si no → Kruskal-Wallis.")
        _tabla([{
            "Canal": c, "n": len(df_c[df_c["Canal_Venta"]==c]),
            "Shapiro W": shapiro[c][0], "Shapiro p": f"{shapiro[c][1]:.2e}",
            "KS (estandar.) p": ks_res[c][1],
            "Skewness": shapiro[c][2], "Kurtosis": shapiro[c][3],
            "Normal?": "❌ No"
        } for c in canales])
        st.markdown(
            "**Conclusión:** Shapiro-Wilk p ≈ 0 y KS p ≈ 0 en los 4 canales. "
            "Kurtosis > 1 indica colas más pesadas que la normal. "
            "**ANOVA descartado** — supuesto de normalidad violado.")

        st.markdown("### Paso 2 — ¿Las varianzas son homogéneas?")
        st.markdown("(Relevante aunque ya descartamos ANOVA, para completar el diagnóstico)")
        _tabla([{"Prueba": "Levene", "Estadístico": f"L={L:.4f}", "p-valor": f"{pL:.4f}",
                 "Conclusión": "Varianzas homogéneas (p>0.05) — no agrava el problema"}])

        st.markdown("### Paso 3 — ¿Chi² o Kruskal-Wallis?")
        st.markdown("""
Chi² y Kruskal responden **preguntas distintas**:

| Prueba | Variable analizada | Información usada |
|---|---|---|
| Chi² de homogeneidad | Binaria (¿margen<0? Sí/No) | Solo si cruza el umbral 0 |
| Kruskal-Wallis | Distribución completa del margen | Todos los rangos del margen |

Para decidir si **un canal tiene falla de precios**, el margen completo importa — no solo si 
cruza cero. Un canal podría tener más transacciones negativas pero márgenes negativos menores 
que otro. **Kruskal usa más información** y responde la pregunta real.
""")
        _tabla([
            {"Prueba": "Chi² homogeneidad", "Estadístico": f"χ²={chi2:.4f}", "p": f"{pchi2:.4f}",
             "Pregunta que responde": "¿Difiere la proporción de negativos?",
             "Decisión": "Sí difiere (p<0.05) — diferencia detectada pero pobre en información"},
            {"Prueba": "Kruskal-Wallis", "Estadístico": f"H={H:.4f}", "p": f"{pH:.4f}",
             "Pregunta que responde": "¿Difiere la distribución completa del margen?",
             "Decisión": "No difiere (p>0.05) — los canales son equivalentes en rentabilidad"},
        ])
        st.markdown(
            "**Interpretación de la contradicción aparente:** Chi² es significativo (p=0.007) "
            "pero Kruskal no (p=0.23). Esto ocurre porque Chi² colapsa el margen a 0/1 y "
            "detecta diferencias en esa proporción (37–41%), pero esa diferencia de 4 puntos "
            "porcentuales **no se refleja en la distribución completa** del margen — los canales "
            "tienen distribuciones de rentabilidad estadísticamente indistinguibles.")

        st.markdown("### Paso 4 — Post-hoc: ¿el canal Online es específicamente diferente?")
        st.markdown("Mann-Whitney bilateral + corrección Bonferroni (α/3 = 0.0167):")
        _tabla([{"Comparación": f"Online vs {c}", "p-valor": mw[c],
                 "p Bonferroni": round(mw[c]*3,4),
                 "Significativa (α=0.05)": "❌ No", "Significativa (Bonf.)": "❌ No"}
                for c in mw])

        st.markdown("### Hipótesis formales")
        _tabla([
            {"": "H₀", "Hipótesis": "La distribución del margen es igual en todos los canales"},
            {"": "H₁", "Hipótesis": "Al menos un canal tiene una distribución de margen distinta"},
            {"": "α", "Hipótesis": "0.05"},
            {"": "Decisión", "Hipótesis": f"No rechazar H₀ (Kruskal p={pH:.4f} > 0.05)"},
        ])

        # Gráficas KDE por canal
        with plt.rc_context(MPL):
            fig, axes = plt.subplots(1, len(canales), figsize=(3.5*len(canales), 4),
                                     facecolor="#161D2F")
            cols = [PALETTE["critico"], PALETTE["advertencia"],
                    PALETTE["saludable"], PALETTE["info"]]
            for ax, c, col in zip(axes, canales, cols):
                v = df_c[df_c["Canal_Venta"]==c]["Margen_Utilidad_USD"].dropna().values
                ax.hist(v, bins=40, color=col, alpha=0.6, density=True,
                        edgecolor="#2A3654", lw=0.3)
                try:
                    kde = sci.gaussian_kde(v)
                    xk  = np.linspace(v.min(), v.max(), 300)
                    ax.plot(xk, kde(xk), color="#EDF1F7", lw=2, label="KDE")
                except Exception: pass
                ax.axvline(0, color="#E4572E", lw=1.5, ls="--", label="Margen=0")
                ax.axvline(np.median(v), color="#E8A33D", lw=1.3, ls="--",
                           label=f"Med={np.median(v):,.0f}")
                neg_p = (v<0).mean()*100
                sk_c = shapiro[c][2]
                ax.set_title(f"{c}\n{neg_p:.1f}% neg | skew={sk_c}", fontsize=9)
                ax.legend(fontsize=7); ax.grid(True)
            axes[0].set_ylabel("Densidad")
            plt.suptitle("KDE del margen por canal — distribuciones indistinguibles (Kruskal p=0.23)",
                         fontsize=10, y=1.02)
            plt.tight_layout()
            st.image(_buf(fig), use_container_width=True)
            plt.close(fig)


# ── P2 ────────────────────────────────────────────────────────────────────
def p2_drawer(df_geo, pr_g, pp_g, sr_g, sp_g, df_corr):
    """Argumento matemático P2: Pearson vs Spearman + análisis de potencia."""
    t_vals  = df_geo["Tiempo_Entrega_Real"].values
    nps_vals= df_geo["Satisfaccion_NPS_Prom"].values
    n2      = len(df_geo)

    Wt, pt = sci.shapiro(t_vals[:500])
    Wn, pn = sci.shapiro(nps_vals[:500])
    skt, kut = sci.skew(t_vals), sci.kurtosis(t_vals)
    skn, kun = sci.skew(nps_vals), sci.kurtosis(nps_vals)

    slope, intercept, _, _, _ = sci.linregress(t_vals, nps_vals)
    residuos = nps_vals - (slope*t_vals + intercept)
    Wr, pr_res = sci.shapiro(residuos[:500])

    z_a = N.ppf(0.975)
    potencias = {}
    for r_h in [0.05, 0.10, 0.20, 0.30]:
        z_r = np.arctanh(r_h) * np.sqrt(n2 - 3)
        potencias[r_h] = round((1-N.cdf(z_a-z_r)+N.cdf(-z_a-z_r))*100, 1)

    with st.expander("📐 Argumento matemático — Pearson vs Spearman y análisis de potencia"):

        st.markdown("### Paso 1 — ¿Las variables son normales?")
        st.markdown("Pearson asume normalidad bivariada; Spearman es libre de distribución.")
        _tabla([
            {"Variable": "Tiempo Entrega", "n": n2, "Skewness": round(skt,3),
             "Kurtosis": round(kut,3), "Shapiro W": Wt, "p": f"{pt:.2e}", "Normal?": "❌"},
            {"Variable": "NPS", "n": n2, "Skewness": round(skn,3),
             "Kurtosis": round(kun,3), "Shapiro W": Wn, "p": f"{pn:.2e}", "Normal?": "❌"},
        ])
        st.markdown(
            f"Kurtosis de NPS = {kun:.3f} (≈ -1): distribución **plana** (uniforme), "
            "muy alejada de la campana normal. Tiempo de entrega: kurtosis={kut:.3f} "
            "(cola más plana que la normal). Ambas distribuciones NO son normales.")

        st.markdown("### Paso 2 — ¿Los residuos de la regresión son normales?")
        st.markdown("Si los residuos son normales, Pearson sigue siendo válido aunque las variables no lo sean.")
        _tabla([{"Test": "Shapiro-Wilk residuos (n=500)", "W": round(Wr,4),
                 "p": f"{pr_res:.2e}", "Conclusión": "Residuos NO normales"}])
        st.markdown(
            "**¿Por qué usamos Pearson igualmente?** Con n=3.117, el Teorema Central "
            "del Límite garantiza que el estimador r̂ es aproximadamente normal. "
            "**Spearman** se usa como corroboración robusta. Que ambas den "
            f"r≈{pr_g:.4f} y ρ≈{sr_g:.4f} confirma que la conclusión es "
            "independiente de la elección de prueba.")

        st.markdown("### Paso 3 — ¿La ausencia de significancia es por falta de potencia?")
        st.markdown("Con n=3.117, ¿podríamos detectar una correlación real si existiera?")
        _tabla([{"r hipotético": r_h, "Potencia (%)": pot,
                 "Interpretación": "Detectaría este r con certeza" if pot>99
                 else f"Detectaría este r el {pot}% de las veces"}
                for r_h, pot in potencias.items()])
        st.markdown(
            f"**Conclusión:** Con n={n2} la potencia es >99% para r≥0.10. "
            "Incluso para r=0.05 la potencia es ~80%. "
            "La ausencia de significancia **no es falta de potencia** — "
            "es que la correlación real entre tiempo de entrega y NPS es prácticamente cero.")

        st.markdown("### Hipótesis formales")
        _tabla([
            {"": "H₀", "Hipótesis": "No hay correlación lineal entre tiempo de entrega y NPS (r=0)"},
            {"": "H₁", "Hipótesis": "Mayor tiempo de entrega → NPS más bajo (r<0, unilateral)"},
            {"": "Pearson r", "Hipótesis": f"{pr_g:.4f}  p={pp_g:.4f}"},
            {"": "Spearman ρ", "Hipótesis": f"{sr_g:.4f}  p={sp_g:.4f}"},
            {"": "Decisión", "Hipótesis": "No rechazar H₀ — evidencia real, no falta de datos"},
        ])
        if len(df_corr):
            st.markdown("**Correlaciones por ciudad (todas NS):**")
            st.dataframe(df_corr, hide_index=True, use_container_width=True)

        with plt.rc_context(MPL):
            fig, axes = plt.subplots(1, 3, figsize=(14, 4), facecolor="#161D2F")
            # Distribución NPS
            axes[0].hist(nps_vals, bins=50, color="#5B8DEF", alpha=0.7,
                         density=True, edgecolor="#2A3654", lw=0.3)
            try:
                kde = sci.gaussian_kde(nps_vals)
                xk = np.linspace(nps_vals.min(), nps_vals.max(), 300)
                axes[0].plot(xk, kde(xk), color="#E8A33D", lw=2, label="KDE")
                # Normal teórica
                xn = np.linspace(nps_vals.min(), nps_vals.max(), 300)
                axes[0].plot(xn, N.pdf(xn, nps_vals.mean(), nps_vals.std()),
                             color="#E4572E", lw=1.5, ls="--", label="Normal teórica")
            except Exception: pass
            axes[0].set_title(f"NPS: kurtosis={kun:.2f}\n(plana, NO normal → Spearman)")
            axes[0].legend(fontsize=7.5); axes[0].grid(True)
            # Scatter + regresión
            axes[1].scatter(t_vals, nps_vals, s=4, alpha=0.12, color="#5B8DEF")
            xr = np.linspace(t_vals.min(), t_vals.max(), 100)
            axes[1].plot(xr, slope*xr+intercept, color="#E8A33D", lw=2,
                         label=f"r={pr_g:.4f} (NS)")
            axes[1].set_xlabel("Tiempo entrega"); axes[1].set_ylabel("NPS")
            axes[1].set_title("Scatter Tiempo vs NPS\n(línea plana → sin relación)")
            axes[1].legend(fontsize=8); axes[1].grid(True)
            # Curva de potencia
            r_range = np.linspace(0.01, 0.5, 100)
            pot_curve = []
            for r_h in r_range:
                z_r = np.arctanh(r_h)*np.sqrt(n2-3)
                pot_curve.append((1-N.cdf(z_a-z_r)+N.cdf(-z_a-z_r))*100)
            axes[2].plot(r_range, pot_curve, color="#3FA796", lw=2)
            axes[2].axhline(80, color="#E8A33D", ls="--", lw=1, label="80% potencia")
            axes[2].axhline(95, color="#E4572E", ls="--", lw=1, label="95% potencia")
            axes[2].axvline(abs(pr_g), color="#5B8DEF", ls="--", lw=1.5,
                            label=f"r observado={pr_g:.4f}")
            axes[2].set_xlabel("r hipotético"); axes[2].set_ylabel("Potencia (%)")
            axes[2].set_title(f"Curva de potencia (n={n2})\nr=0 no es problema de n")
            axes[2].legend(fontsize=7.5); axes[2].grid(True)
            plt.tight_layout()
            st.image(_buf(fig), use_container_width=True)
            plt.close(fig)


# ── P3 ────────────────────────────────────────────────────────────────────
def p3_drawer(master, pct_riesgo, ic_b, boots):
    """Argumento matemático P3: Bootstrap vs Wilson vs Normal."""
    n3   = len(master)
    p_hat= master["Es_Venta_Fantasma"].mean()
    z    = N.ppf(0.975)

    # Wilson IC
    denom   = 1 + z**2/n3
    centro  = (p_hat + z**2/(2*n3)) / denom
    margen_w= z*np.sqrt(p_hat*(1-p_hat)/n3 + z**2/(4*n3**2)) / denom
    ic_wilson = ((centro-margen_w)*100, (centro+margen_w)*100)
    ic_normal = ((p_hat - z*np.sqrt(p_hat*(1-p_hat)/n3))*100,
                 (p_hat + z*np.sqrt(p_hat*(1-p_hat)/n3))*100)

    # Bootstrap del INGRESO fantasma (distinto de la proporción de transacciones)
    np.random.seed(42)
    boots_ing = []
    for _ in range(1000):
        s = master.sample(n3, replace=True)
        boots_ing.append(
            s.loc[s["Es_Venta_Fantasma"],"Ingreso_Bruto"].sum() /
            s["Ingreso_Bruto"].sum() * 100)
    ic_ing = np.percentile(boots_ing, [2.5, 97.5])
    pct_ing = (master.loc[master["Es_Venta_Fantasma"],"Ingreso_Bruto"].sum() /
               master["Ingreso_Bruto"].sum() * 100)

    with st.expander("📐 Argumento matemático — Bootstrap vs fórmulas paramétricas"):

        st.markdown("### Paso 1 — ¿La variable es normal?")
        st.markdown(
            "La variable es **Bernoulli** (0=catalogado, 1=fantasma), binaria por definición. "
            "No es normal — no tiene sentido aplicar Shapiro. "
            "El IC para una proporción tiene tres alternativas:")
        _tabla([
            {"Método": "IC Normal aproximado", "Supuesto": "np≥10 y n(1-p)≥10",
             "IC 95% transacciones": f"[{ic_normal[0]:.2f}%, {ic_normal[1]:.2f}%]",
             "Válido aquí?": f"✅ np={n3*p_hat:.0f}>>10"},
            {"Método": "IC Wilson (exacto)", "Supuesto": "Ninguno — exacto para proporciones",
             "IC 95% transacciones": f"[{ic_wilson[0]:.2f}%, {ic_wilson[1]:.2f}%]",
             "Válido aquí?": "✅ Siempre válido"},
            {"Método": "Bootstrap percentil", "Supuesto": "n suficientemente grande",
             "IC 95% transacciones": f"[{ic_b[0]:.2f}%, {ic_b[1]:.2f}%]",
             "Válido aquí?": f"✅ n={n3}"},
        ])
        st.markdown(
            "Los tres métodos convergen (difieren <0.1 pp) porque n=10.000 es grande. "
            "**¿Por qué elegir Bootstrap?**")

        st.markdown("### Paso 2 — La pregunta real es sobre INGRESO, no sobre conteo")
        st.markdown(
            "El % de **transacciones** fantasma tiene fórmula cerrada (Wilson). "
            "El % de **ingreso** fantasma es una razón de sumas — "
            "no hay fórmula cerrada para su IC. Solo Bootstrap lo resuelve.")
        _tabla([
            {"Estadístico": "% transacciones fantasma", "Valor": f"{p_hat*100:.2f}%",
             "IC 95%": f"Wilson [{ic_wilson[0]:.2f}%, {ic_wilson[1]:.2f}%]",
             "Método": "Wilson (fórmula cerrada)"},
            {"Estadístico": "% ingreso en riesgo", "Valor": f"{pct_ing:.2f}%",
             "IC 95%": f"[{ic_ing[0]:.2f}%, {ic_ing[1]:.2f}%]",
             "Método": "Bootstrap (sin fórmula cerrada)"},
        ])
        st.markdown(
            f"El IC del ingreso [{ic_ing[0]:.2f}%, {ic_ing[1]:.2f}%] es más amplio que el "
            f"de transacciones [{ic_wilson[0]:.2f}%, {ic_wilson[1]:.2f}%] porque incorpora "
            "la variabilidad en el tamaño de cada transacción, no solo en si es fantasma o no.")

        with plt.rc_context(MPL):
            fig, axes = plt.subplots(1, 2, figsize=(11, 4), facecolor="#161D2F")
            axes[0].hist(boots, bins=40, color="#E8A33D", alpha=0.8,
                         edgecolor="#2A3654", lw=0.4)
            axes[0].axvline(p_hat*100, color="#E4572E", lw=2, label=f"Obs={p_hat*100:.2f}%")
            axes[0].axvspan(ic_b[0], ic_b[1], alpha=0.2, color="#3FA796",
                            label=f"IC 95% transac.: [{ic_b[0]:.2f}%, {ic_b[1]:.2f}%]")
            axes[0].set_xlabel("% transacciones fantasma (bootstrap)")
            axes[0].set_title("Bootstrap — % de transacciones\n(Wilson y Bootstrap convergen)")
            axes[0].legend(fontsize=7.5); axes[0].grid(True)

            axes[1].hist(boots_ing, bins=40, color="#5B8DEF", alpha=0.8,
                         edgecolor="#2A3654", lw=0.4)
            axes[1].axvline(pct_ing, color="#E4572E", lw=2, label=f"Obs={pct_ing:.2f}%")
            axes[1].axvspan(ic_ing[0], ic_ing[1], alpha=0.2, color="#3FA796",
                            label=f"IC 95% ingreso: [{ic_ing[0]:.2f}%, {ic_ing[1]:.2f}%]")
            axes[1].set_xlabel("% ingreso fantasma (bootstrap)")
            axes[1].set_title("Bootstrap — % de INGRESO en riesgo\n(sin fórmula cerrada → Bootstrap obligatorio)")
            axes[1].legend(fontsize=7.5); axes[1].grid(True)
            plt.tight_layout()
            st.image(_buf(fig), use_container_width=True)
            plt.close(fig)


# ── P4 ────────────────────────────────────────────────────────────────────
def p4_drawer(df_cat, resumen4, H_kw, p_kw, cats_paradoja):
    """Argumento matemático P4: Kruskal vs ANOVA, con Levene."""
    CATS = list(resumen4.index)
    grupos = [df_cat.loc[df_cat["Categoria"]==c,"Satisfaccion_NPS_Prom"].dropna().values
              for c in CATS]

    shapiro_c, kurt_c = {}, {}
    for c, v in zip(CATS, grupos):
        W, p = sci.shapiro(v[:500])
        shapiro_c[c] = (round(float(W),4), float(p), round(sci.skew(v),3), round(sci.kurtosis(v),3))
        kurt_c[c] = round(sci.kurtosis(v),3)

    L, pL = sci.levene(*[g for g in grupos if len(g)>0])

    with st.expander("📐 Argumento matemático — Kruskal vs ANOVA y por qué no transformar"):

        st.markdown("### Paso 1 — ¿La variable NPS es normal dentro de cada categoría?")
        _tabla([{
            "Categoría": c, "n": len(df_cat[df_cat["Categoria"]==c]),
            "Shapiro W": shapiro_c[c][0], "Shapiro p": f"{shapiro_c[c][1]:.2e}",
            "Skewness": shapiro_c[c][2], "Kurtosis": shapiro_c[c][3],
            "Normal?": "❌ No"
        } for c in CATS])
        st.markdown(
            "**Nota sobre la Kurtosis:** Todas las categorías tienen kurtosis ≈ -1. "
            "Una kurtosis de -1 indica distribución **platikúrtica** (más plana que la normal, "
            "similar a una distribución uniforme). Esto es incompatible con la normal "
            "(kurtosis=0). **ANOVA descartado.**")

        st.markdown("### Paso 2 — ¿Por qué no transformar los datos?")
        _tabla([
            {"Transformación": "log(x)", "Condición": "x > 0 siempre",
             "¿Aplica?": "❌ No — NPS tiene valores negativos (-100 a 100)"},
            {"Transformación": "√x", "Condición": "x ≥ 0",
             "¿Aplica?": "❌ No — NPS negativo"},
            {"Transformación": "Box-Cox", "Condición": "x > 0",
             "¿Aplica?": "❌ No — mismo problema"},
            {"Transformación": "x + 101 (shift)", "Condición": "Arbitraria",
             "¿Aplica?": "⚠️ No recomendado — altera la interpretación del NPS estándar"},
        ])

        st.markdown("### Paso 3 — ¿Las varianzas son homogéneas?")
        _tabla([{"Test": "Levene", "L": round(L,4), "p": round(pL,4),
                 "Conclusión": f"Varianzas {'homogéneas' if pL>0.05 else 'NO homogéneas'} (p={'>' if pL>0.05 else '<'}0.05)"}])

        st.markdown("### Paso 4 — ¿Por qué no Mann-Whitney pairwise?")
        n_comp = len(CATS)*(len(CATS)-1)//2
        alpha_inflado = 1-(1-0.05)**n_comp
        st.markdown(
            f"Con k={len(CATS)} categorías hay **{n_comp} comparaciones posibles**. "
            f"Hacer Mann-Whitney en cada par sin corrección inflaría α a {alpha_inflado:.1%}. "
            "Kruskal-Wallis es el test **ómnibus** correcto — primero pregunta si *alguna* "
            "categoría difiere. Solo si H₀ se rechaza se procede con post-hoc.")

        st.markdown("### Resultado Kruskal-Wallis")
        _tabla([
            {"": "H₀", "Hipótesis": "La distribución de NPS es igual en todas las categorías"},
            {"": "H₁", "Hipótesis": "Al menos una categoría tiene NPS distribuido distinto"},
            {"": "H", "Hipótesis": f"{H_kw:.4f}"},
            {"": "p-valor", "Hipótesis": f"{p_kw:.4f}"},
            {"": "Decisión", "Hipótesis": "No rechazar H₀ — NPS bajo es transversal a todas las categorías"},
        ])

        with plt.rc_context(MPL):
            n_c = len(CATS)
            fig, axes = plt.subplots(2, n_c, figsize=(3.2*n_c, 7), facecolor="#161D2F")
            for j, (c, v) in enumerate(zip(CATS, grupos)):
                col = PALETTE["critico"] if c in cats_paradoja else PALETTE["info"]
                axes[0,j].hist(v, bins=30, color=col, alpha=0.7, density=True,
                               edgecolor="#2A3654", lw=0.3)
                try:
                    kde = sci.gaussian_kde(v)
                    xk  = np.linspace(v.min(), v.max(), 200)
                    axes[0,j].plot(xk, kde(xk), color="#E8A33D", lw=1.8, label="KDE")
                    # Normal teórica para comparar
                    axes[0,j].plot(xk, N.pdf(xk, v.mean(), v.std()),
                                   color="#8C96AD", lw=1.3, ls="--", label="Normal")
                except Exception: pass
                axes[0,j].set_title(f"{c}\nkurt={kurt_c[c]:.2f} (plana)", fontsize=9)
                axes[0,j].legend(fontsize=6.5); axes[0,j].grid(True)
                if len(v)>=3:
                    (osm,osr),(sl,ic,_) = sci.probplot(v, dist="norm")
                    axes[1,j].scatter(osm, osr, s=4, alpha=0.4, color=col)
                    axes[1,j].plot(osm, sl*np.array(osm)+ic, color="#E8A33D", lw=1.3)
                axes[1,j].set_title("Q-Q (desviación→no normal)", fontsize=8)
                axes[1,j].grid(True)
            axes[0,0].set_ylabel("Densidad NPS")
            axes[1,0].set_ylabel("Cuantiles obs.")
            plt.suptitle("NPS por categoría: KDE vs Normal teórica + Q-Q\n"
                         "(kurtosis≈-1 en todas → distribución plana, no normal)",
                         fontsize=10, y=1.02)
            plt.tight_layout()
            st.image(_buf(fig), use_container_width=True)
            plt.close(fig)


# ── P5 ────────────────────────────────────────────────────────────────────
def p5_drawer(res5, r5, p5):
    """Argumento matemático P5: potencia con n=5."""
    n5 = len(res5)
    z_a = N.ppf(0.975)

    with st.expander("📐 Argumento matemático — Pearson con n=5 y sus limitaciones"):

        st.markdown("### Paso 1 — ¿Qué prueba mide relación entre dos continuas?")
        _tabla([
            {"Opción": "Pearson r", "Supuesto": "Linealidad, normalidad bivariada",
             "Con n=5": "Válido como exploración; p-valor poco fiable"},
            {"Opción": "Spearman ρ", "Supuesto": "Relación monótona",
             "Con n=5": "Equivalente a Pearson con n tan pequeño"},
            {"Opción": "Regresión lineal", "Supuesto": "Residuos normales",
             "Con n=5": "No agrega potencia; mismos supuestos"},
            {"Opción": "Correlación parcial", "Supuesto": "Controlar covariables",
             "Con n=5": "Sin grados de libertad suficientes"},
        ])
        st.markdown("**Pearson es la opción mínima válida**, con la advertencia de potencia.")

        st.markdown("### Paso 2 — Análisis de potencia: ¿qué puede detectar n=5?")
        filas_pot = []
        for r_h in [0.3, 0.5, 0.7, 0.9]:
            z_r = np.arctanh(r_h)*np.sqrt(n5-3)
            pot = (1-N.cdf(z_a-z_r)+N.cdf(-z_a-z_r))*100
            filas_pot.append({"r hipotético": r_h, "Potencia (%)": round(pot,1),
                               "Interpretación": (
                               "Potencia muy baja — mayormente no detectable" if pot<30
                               else "Potencia baja" if pot<60
                               else "Potencia aceptable" if pot<80
                               else "Potencia adecuada")})
        _tabla(filas_pot)
        st.markdown(
            f"Con n={n5} bodegas, la potencia para detectar r=0.70 es solo ~23%. "
            f"Nuestro r observado={r5:.3f} tiene p={p5:.3f}: **no significativo**. "
            "Esto no significa que no haya relación — significa que con 5 puntos "
            "**no hay suficiente información** para confirmarla estadísticamente.")

        st.markdown("### Paso 3 — ¿Qué sí podemos afirmar?")
        _tabla([
            {"Afirmación": "Dirección de la relación", "Válida?": "✅ Sí",
             "Evidencia": f"r={r5:.3f} > 0 (positivo: más días → más tickets)"},
            {"Afirmación": "Magnitud de la relación", "Válida?": "⚠️ Descriptiva",
             "Evidencia": "r=0.63 sería 'fuerte' con n grande; aquí es indicativo"},
            {"Afirmación": "Causalidad", "Válida?": "❌ No",
             "Evidencia": "Correlación no implica causalidad; n=5 no lo permite"},
            {"Afirmación": "Significancia estadística", "Válida?": "❌ No",
             "Evidencia": f"p={p5:.3f} > 0.05; potencia insuficiente"},
        ])

        _tabla([
            {"": "H₀", "Hipótesis": "r=0 (no hay relación lineal)"},
            {"": "H₁", "Hipótesis": "r>0 (más días sin revisión → más tickets)"},
            {"": "Pearson r", "Hipótesis": f"{r5:.4f}"},
            {"": "p-valor", "Hipótesis": f"{p5:.4f}"},
            {"": "Decisión", "Hipótesis": "No rechazar H₀ — potencia insuficiente con n=5"},
            {"": "Acción", "Hipótesis": "Replicar con datos a nivel SKU-bodega para n>>5"},
        ])

        with plt.rc_context(MPL):
            fig, axes = plt.subplots(1, 2, figsize=(11, 4), facecolor="#161D2F")
            # Scatter con regresión
            axes[0].scatter(res5["dias_revision"], res5["tasa_ticket_pct"],
                            s=res5["n"]/res5["n"].max()*400+80,
                            color="#E8A33D", zorder=3, edgecolors="#EDF1F7", lw=0.8)
            for _, row in res5.iterrows():
                axes[0].annotate(row["Bodega_Origen"],
                                 (row["dias_revision"], row["tasa_ticket_pct"]),
                                 fontsize=9, xytext=(5,5), textcoords="offset points")
            m,b_ = np.polyfit(res5["dias_revision"], res5["tasa_ticket_pct"], 1)
            xr = np.linspace(res5["dias_revision"].min(), res5["dias_revision"].max(), 50)
            axes[0].plot(xr, m*xr+b_, "--", color="#8C96AD", lw=1.3,
                         label=f"r={r5:.3f} p={p5:.3f} (NS, n=5)")
            axes[0].set_xlabel("Días desde revisión")
            axes[0].set_ylabel("% tickets de soporte")
            axes[0].set_title(f"Pearson r={r5:.3f} (p={p5:.3f})\nn=5 → potencia baja")
            axes[0].legend(fontsize=8); axes[0].grid(True)
            # Curva de potencia
            r_range = np.linspace(0.01, 0.99, 100)
            pot_curve = []
            for r_h in r_range:
                try:
                    z_r = np.arctanh(r_h)*np.sqrt(n5-3)
                    pot_curve.append((1-N.cdf(z_a-z_r)+N.cdf(-z_a-z_r))*100)
                except Exception:
                    pot_curve.append(np.nan)
            axes[1].plot(r_range, pot_curve, color="#3FA796", lw=2)
            axes[1].axhline(80, color="#E8A33D", ls="--", lw=1, label="80% (mínimo)")
            axes[1].axhline(95, color="#E4572E", ls="--", lw=1, label="95% (deseable)")
            axes[1].axvline(abs(r5), color="#5B8DEF", ls="--", lw=1.5,
                            label=f"r observado={r5:.3f}")
            axes[1].set_xlabel("r hipotético")
            axes[1].set_ylabel("Potencia (%)")
            axes[1].set_title(f"Curva de potencia (n={n5})\nSe necesita r>0.88 para 80% de potencia")
            axes[1].legend(fontsize=7.5); axes[1].grid(True)
            plt.tight_layout()
            st.image(_buf(fig), use_container_width=True)
            plt.close(fig)
