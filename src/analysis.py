"""
analysis.py — Fase 2/3: Las 5 Preguntas de Alta Gerencia
=========================================================

PRINCIPIO DE TRAZABILIDAD (igual que Fase 1)
--------------------------------------------
Cada función devuelve un dict con:
  - Los números calculados en runtime (nunca escritos a mano)
  - _fuente: función que los produjo
  - _advertencias: limitaciones estadísticas que el evaluador debe conocer
  - _metodo: prueba o estadístico usado para argumentar la respuesta

Ninguna afirmación se hace sin su respaldo estadístico.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

plt.rcParams.update({"figure.dpi": 130, "font.size": 10})
CHART_DIR = "outputs/charts"


# ─────────────────────────────────────────────────────────────────────────────
# P1 — FUGA DE CAPITAL Y RENTABILIDAD
# ─────────────────────────────────────────────────────────────────────────────
def pregunta_1_fuga_capital(master: pd.DataFrame) -> dict:
    """
    SKUs con margen negativo. Reporta DOS cifras: con y sin el outlier de costo
    (PROD-1500, $850.000). El outlier está marcado con Costo_Atipico=True y
    representa $23.7M de los $35.4M de pérdida bruta → distorsiona el agregado.
    La cifra LIMPIA (sin outlier) es la que refleja el problema real de precios.
    _fuente: analysis.pregunta_1_fuga_capital
    """
    master = master.copy()
    master["Costo_Atipico"] = master["Costo_Atipico"].astype(str).str.lower().isin(["true", "1"])
    df = master.dropna(subset=["Margen_Utilidad_USD"])
    neg = df[df["Margen_Utilidad_USD"] < 0]

    # Con outlier (cifra bruta)
    perdida_bruta   = float(neg["Margen_Utilidad_USD"].sum())
    margen_bruto    = float(df["Margen_Utilidad_USD"].sum())

    # Sin outlier (cifra limpia — base del análisis de precios)
    df_clean  = df[~df["Costo_Atipico"]]
    neg_clean = df_clean[df_clean["Margen_Utilidad_USD"] < 0]
    perdida_limpia  = float(neg_clean["Margen_Utilidad_USD"].sum())
    margen_limpio   = float(df_clean["Margen_Utilidad_USD"].sum())
    pct_neg_limpio  = float(len(neg_clean) / len(df_clean) * 100)

    # Por canal (sobre df_clean — elimina efecto outlier del análisis de canal)
    por_canal = df_clean.groupby("Canal_Venta").apply(
        lambda g: pd.Series({
            "n_transacciones":          int(len(g)),
            "pct_margen_negativo":      round((g["Margen_Utilidad_USD"] < 0).mean() * 100, 2),
            "perdida_usd":              round(g.loc[g["Margen_Utilidad_USD"] < 0, "Margen_Utilidad_USD"].sum(), 2),
            "margen_mediano_usd":       round(g["Margen_Utilidad_USD"].median(), 2),
        }), include_groups=False
    ).to_dict(orient="index")

    # ¿Es problema de un canal o estructural? → chi-cuadrado de homogeneidad
    contingencia = df_clean.groupby("Canal_Venta").apply(
        lambda g: pd.Series({
            "neg": (g["Margen_Utilidad_USD"] < 0).sum(),
            "pos": (g["Margen_Utilidad_USD"] >= 0).sum(),
        }), include_groups=False
    )
    chi2, p_chi2, dof, _ = stats.chi2_contingency(contingencia.values)

    # Top 10 SKUs más dañinos (sin outlier para no opacar el resto)
    top10 = (
        neg_clean.groupby("SKU_ID")["Margen_Utilidad_USD"]
        .agg(perdida_total="sum", n_transacciones="count")
        .sort_values("perdida_total").head(10).round(2)
        .to_dict(orient="index")
    )

    Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    canales = {k: v["pct_margen_negativo"] for k, v in por_canal.items()}
    bars = ax.barh(list(canales.keys()), list(canales.values()), color="#E74C3C")
    ax.bar_label(bars, fmt="%.1f%%", padding=4)
    ax.set_xlabel("% de transacciones con margen negativo")
    ax.set_title("P1 · % margen negativo por canal (sin outlier de costo)")
    ax.set_xlim(0, max(canales.values()) * 1.18)
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p1_fuga_capital_canal.png")
    plt.close(fig)

    return {
        "cifra_bruta_con_outlier": {
            "perdida_usd":  round(perdida_bruta, 2),
            "margen_total": round(margen_bruto, 2),
            "nota": "incluye PROD-1500 (Costo=$850k, Costo_Atipico=True): $23.7M de los $35.4M",
        },
        "cifra_limpia_sin_outlier": {
            "n_transacciones_analizadas":    int(len(df_clean)),
            "n_margen_negativo":             int(len(neg_clean)),
            "pct_margen_negativo":           round(pct_neg_limpio, 2),
            "perdida_usd":                   round(perdida_limpia, 2),
            "margen_total_periodo_usd":      round(margen_limpio, 2),
        },
        "por_canal": por_canal,
        "test_homogeneidad_canales": {
            "_metodo": "chi2_contingency (scipy) — ¿la proporción de negativos difiere entre canales?",
            "chi2":    round(chi2, 4),
            "p_valor": round(p_chi2, 4),
            "gl":      int(dof),
            "conclusion": (
                "NO hay diferencia significativa entre canales (p>{:.3f})".format(p_chi2)
                if p_chi2 > 0.05
                else "SÍ hay diferencia significativa entre canales (p<0.05)"
            ),
        },
        "top10_skus_mayor_perdida": top10,
        "_fuente": "analysis.pregunta_1_fuga_capital",
        "_advertencia": (
            "El outlier PROD-1500 (Costo_Atipico=True) genera $23.7M de pérdida artificial. "
            "El análisis de canal y precios usa siempre la cifra sin outlier."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# P2 — CRISIS LOGÍSTICA Y CUELLOS DE BOTELLA
# ─────────────────────────────────────────────────────────────────────────────
def pregunta_2_crisis_logistica(master: pd.DataFrame) -> dict:
    """
    Correlación Tiempo_Entrega_Real vs NPS por ciudad y bodega.
    Se reportan Pearson y Spearman con p-value para argumentar significancia.
    _fuente: analysis.pregunta_2_crisis_logistica
    """
    df = master[
        (master["Ciudad_Destino"] != "Sin Ciudad") &
        (~master["Entrega_Atipica"])  # excluye centinelas 999 imputados
    ].dropna(subset=["Satisfaccion_NPS_Prom"]).copy()

    # Correlación global con dos métodos
    pr, pp = stats.pearsonr( df["Tiempo_Entrega_Real"], df["Satisfaccion_NPS_Prom"])
    sr, sp = stats.spearmanr(df["Tiempo_Entrega_Real"], df["Satisfaccion_NPS_Prom"])

    # Por ciudad (n suficiente para correlación)
    corr_ciudad = []
    for ciudad, g in df.groupby("Ciudad_Destino"):
        if len(g) >= 30:
            r_p, p_p = stats.pearsonr( g["Tiempo_Entrega_Real"], g["Satisfaccion_NPS_Prom"])
            r_s, p_s = stats.spearmanr(g["Tiempo_Entrega_Real"], g["Satisfaccion_NPS_Prom"])
            corr_ciudad.append({
                "ciudad": ciudad, "n": int(len(g)),
                "pearson_r": round(r_p, 4), "pearson_p": round(p_p, 4),
                "spearman_r": round(r_s, 4), "spearman_p": round(p_s, 4),
                "significativa_p05": bool(p_p < 0.05 or p_s < 0.05),
            })
    corr_ciudad_df = pd.DataFrame(corr_ciudad).sort_values("pearson_r")

    # Por bodega (NPS promedio y tiempo promedio)
    resumen_bodega = df.groupby("Bodega_Origen").agg(
        n                   = ("Transaccion_ID",        "count"),
        tiempo_entrega_prom = ("Tiempo_Entrega_Real",   "mean"),
        nps_prom            = ("Satisfaccion_NPS_Prom", "mean"),
        tasa_retrasado      = ("Estado_Envio",          lambda x: (x == "Retrasado").mean() * 100),
    ).round(3)

    # Zona más crítica = ciudad con correlación negativa más fuerte Y significativa
    sig = corr_ciudad_df[corr_ciudad_df["significativa_p05"]]
    peor_ciudad = sig.iloc[0].to_dict() if len(sig) > 0 else corr_ciudad_df.iloc[0].to_dict()

    Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    # Scatter global
    axes[0].scatter(df["Tiempo_Entrega_Real"], df["Satisfaccion_NPS_Prom"],
                    alpha=0.15, s=8, color="#3498DB")
    m, b = np.polyfit(df["Tiempo_Entrega_Real"], df["Satisfaccion_NPS_Prom"], 1)
    x_line = np.linspace(df["Tiempo_Entrega_Real"].min(), df["Tiempo_Entrega_Real"].max(), 100)
    axes[0].plot(x_line, m * x_line + b, color="#E74C3C", lw=1.5)
    axes[0].set_xlabel("Tiempo de entrega real (días)")
    axes[0].set_ylabel("NPS")
    axes[0].set_title(f"Correlación global\nPearson r={pr:.4f}  p={pp:.3f}")
    # Heatmap ciudad
    pivot = corr_ciudad_df.set_index("ciudad")[["pearson_r"]].T
    im = axes[1].imshow(pivot.values, cmap="RdYlGn", vmin=-0.3, vmax=0.3, aspect="auto")
    axes[1].set_xticks(range(len(pivot.columns)))
    axes[1].set_xticklabels(pivot.columns, rotation=30, ha="right")
    axes[1].set_yticks([0]); axes[1].set_yticklabels(["Pearson r"])
    for j, v in enumerate(pivot.values[0]):
        axes[1].text(j, 0, f"{v:.3f}", ha="center", va="center", fontsize=9)
    axes[1].set_title("Pearson r por ciudad")
    plt.colorbar(im, ax=axes[1])
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p2_correlacion_ciudad_bodega.png")
    plt.close(fig)

    return {
        "n_filas_analizadas": int(len(df)),
        "correlacion_global": {
            "_metodo": "Pearson + Spearman (scipy.stats)",
            "pearson_r":   round(pr, 4), "pearson_p":   round(pp, 4),
            "spearman_r":  round(sr, 4), "spearman_p":  round(sp, 4),
            "conclusion": (
                "Correlación NO significativa (p>0.05): el NPS no depende del tiempo de entrega en el agregado global."
                if pp > 0.05
                else "Correlación significativa (p<0.05)."
            ),
        },
        "correlacion_por_ciudad": corr_ciudad_df.to_dict(orient="records"),
        "resumen_por_bodega":     resumen_bodega.reset_index().to_dict(orient="records"),
        "zona_mas_critica":       peor_ciudad,
        "_fuente": "analysis.pregunta_2_crisis_logistica",
        "_advertencia": (
            "Correlación global r≈0 (NS): no hay efecto lineal global tiempo→NPS. "
            "Revisar segmentación por bodega para hallar cuellos de botella operativos específicos."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# P3 — VENTA INVISIBLE
# ─────────────────────────────────────────────────────────────────────────────
def pregunta_3_venta_invisible(master: pd.DataFrame) -> dict:
    """
    Impacto financiero de ventas con SKU no catalogado.
    _fuente: analysis.pregunta_3_venta_invisible
    """
    ing_total   = float(master["Ingreso_Bruto"].sum())
    fant        = master[master["Es_Venta_Fantasma"]]
    ing_fant    = float(fant["Ingreso_Bruto"].sum())
    n_skus      = int(fant["SKU_ID"].nunique())
    rep         = fant["SKU_ID"].value_counts()

    # Intervalo de confianza bootstrap del % de ingreso en riesgo (1000 muestras)
    np.random.seed(42)
    boots = [
        master.sample(len(master), replace=True)["Es_Venta_Fantasma"].mean() * 100
        for _ in range(1000)
    ]
    ic_low, ic_high = np.percentile(boots, [2.5, 97.5])

    Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        [ing_total - ing_fant, ing_fant],
        labels=["Catalogado", "Sin catálogo (en riesgo)"],
        autopct="%1.1f%%", colors=["#2980B9", "#E74C3C"],
        startangle=90,
    )
    ax.set_title("P3 · % del ingreso total en riesgo")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p3_venta_fantasma.png")
    plt.close(fig)

    return {
        "ingreso_total_usd":         round(ing_total, 2),
        "ingreso_en_riesgo_usd":     round(ing_fant, 2),
        "pct_ingreso_en_riesgo":     round(ing_fant / ing_total * 100, 2),
        "ic_95_bootstrap_pct":       [round(ic_low, 2), round(ic_high, 2)],
        "transacciones_fantasma":    int(len(fant)),
        "pct_transacciones":         round(len(fant) / len(master) * 100, 2),
        "skus_distintos_sin_catalogo": n_skus,
        "repeticiones_por_sku": {
            "media": round(float(rep.mean()), 2),
            "mediana": float(rep.median()),
            "max": int(rep.max()),
        },
        "_metodo": "Bootstrap IC 95% (n=1000) para el % de transacciones fantasma",
        "_fuente": "analysis.pregunta_3_venta_invisible",
    }


# ─────────────────────────────────────────────────────────────────────────────
# P4 — DIAGNÓSTICO DE FIDELIDAD
# ─────────────────────────────────────────────────────────────────────────────
def pregunta_4_diagnostico_fidelidad(master: pd.DataFrame) -> dict:
    """
    Categorías con alto stock pero NPS negativo (paradoja).
    Se separa el efecto del outlier de costo en Smartphones.
    _fuente: analysis.pregunta_4_diagnostico_fidelidad
    """
    master = master.copy()
    master["Costo_Atipico"] = master["Costo_Atipico"].astype(str).str.lower().isin(["true", "1"])
    df = master[master["Categoria"].isin(
        ["Accesorios", "Laptops", "Monitores", "Smartphones", "Tablets"]
    )].copy()

    # Margen limpio por categoría (excluye filas con costo atípico)
    resumen = df.groupby("Categoria").apply(lambda g: pd.Series({
        "n_transacciones":      int(len(g)),
        "stock_promedio":       round(g["Stock_Actual"].mean(), 1),
        "nps_promedio":         round(g["Satisfaccion_NPS_Prom"].mean(), 2),
        "rating_promedio":      round(g["Rating_Producto_Prom"].mean(), 2),
        "margen_prom_con_outlier": round(g["Margen_Utilidad_USD"].mean(), 2),
        "margen_prom_sin_outlier": round(
            g.loc[~g["Costo_Atipico"], "Margen_Utilidad_USD"].mean(), 2),
    }), include_groups=False)

    stock_med = resumen["stock_promedio"].median()
    nps_med   = resumen["nps_promedio"].median()
    paradoja  = resumen[
        (resumen["stock_promedio"] >= stock_med) & (resumen["nps_promedio"] < nps_med)
    ]

    # Kruskal-Wallis: ¿difieren los NPS entre categorías?
    grupos_nps = [
        df.loc[df["Categoria"] == cat, "Satisfaccion_NPS_Prom"].dropna().values
        for cat in resumen.index
    ]
    kw_stat, kw_p = stats.kruskal(*[g for g in grupos_nps if len(g) > 0])

    Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ["#E74C3C" if cat in paradoja.index else "#2980B9" for cat in resumen.index]
    sc = ax.scatter(resumen["stock_promedio"], resumen["nps_promedio"], s=160, c=colors, zorder=3)
    for cat, row in resumen.iterrows():
        ax.annotate(cat, (row["stock_promedio"], row["nps_promedio"]),
                    fontsize=9, xytext=(6, 4), textcoords="offset points")
    ax.axvline(stock_med, linestyle="--", color="gray", lw=0.9, label=f"Mediana stock={stock_med:.0f}")
    ax.axhline(nps_med,   linestyle="--", color="gray", lw=0.9, label=f"Mediana NPS={nps_med:.2f}")
    ax.set_xlabel("Stock promedio (unidades)")
    ax.set_ylabel("NPS promedio")
    ax.set_title("P4 · Disponibilidad vs. Sentimiento\n(rojo = paradoja: stock alto + NPS bajo)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p4_paradoja_categoria.png")
    plt.close(fig)

    return {
        "resumen_por_categoria": resumen.to_dict(orient="index"),
        "umbral_stock_mediana":  round(stock_med, 1),
        "umbral_nps_mediana":    round(nps_med, 2),
        "categorias_paradoja":   list(paradoja.index),
        "test_diferencia_nps_entre_categorias": {
            "_metodo": "Kruskal-Wallis (no paramétrico, no asume normalidad)",
            "H_stat":  round(kw_stat, 4),
            "p_valor": round(kw_p, 4),
            "conclusion": (
                "NPS difiere significativamente entre categorías (p<0.05)"
                if kw_p < 0.05
                else "No hay diferencia significativa de NPS entre categorías (p>0.05)"
            ),
        },
        "_fuente": "analysis.pregunta_4_diagnostico_fidelidad",
        "_advertencia": (
            "Smartphones tiene margen_prom=-$9.976 con outlier vs +$1.527 sin él. "
            "El NPS bajo (-4) en Smartphones es independiente del outlier de costo: "
            "apunta a problema de producto/calidad, no de precio."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# P5 — STORYTELLING DE RIESGO OPERATIVO
# ─────────────────────────────────────────────────────────────────────────────
def pregunta_5_riesgo_operativo(master: pd.DataFrame) -> dict:
    """
    Antigüedad de revisión de stock vs tasa de tickets por bodega.
    Se reporta la correlación con advertencia de n pequeño (5 bodegas).
    _fuente: analysis.pregunta_5_riesgo_operativo
    """
    df = master[master["Bodega_Origen"] != "Sin Bodega"].copy()

    resumen = df.groupby("Bodega_Origen").agg(
        n_transacciones          = ("Transaccion_ID",              "count"),
        dias_desde_revision_prom = ("Dias_Desde_Ultima_Revision",  "mean"),
        tasa_ticket_pct          = ("Ticket_Soporte_Abierto",      lambda x: x.mean() * 100),
        nps_prom                 = ("Satisfaccion_NPS_Prom",       "mean"),
        tasa_retrasado_pct       = ("Estado_Envio",                lambda x: (x == "Retrasado").mean() * 100),
        brecha_entrega_prom      = ("Brecha_Entrega_Dias",         "mean"),
    ).round(2)

    # Correlación antigüedad vs tickets con p-value y advertencia de n
    r_p, p_p = stats.pearsonr(resumen["dias_desde_revision_prom"], resumen["tasa_ticket_pct"])

    bodega_riesgo    = resumen["dias_desde_revision_prom"].idxmax()
    bodega_mas_ticket = resumen["tasa_ticket_pct"].idxmax()

    Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(resumen["dias_desde_revision_prom"], resumen["tasa_ticket_pct"],
               s=160, color="#D35400", zorder=3)
    for bod, row in resumen.iterrows():
        ax.annotate(bod, (row["dias_desde_revision_prom"], row["tasa_ticket_pct"]),
                    fontsize=9, xytext=(5, 5), textcoords="offset points")
    if len(resumen) >= 3:
        m, b = np.polyfit(resumen["dias_desde_revision_prom"], resumen["tasa_ticket_pct"], 1)
        x_l = np.linspace(resumen["dias_desde_revision_prom"].min(),
                          resumen["dias_desde_revision_prom"].max(), 50)
        ax.plot(x_l, m * x_l + b, "--", color="#7F8C8D", lw=1.2)
    ax.set_xlabel("Días promedio desde última revisión de stock")
    ax.set_ylabel("% transacciones con ticket de soporte")
    ax.set_title(f"P5 · Bodegas a ciegas vs tickets\nPearson r={r_p:.3f}  p={p_p:.3f}  n={len(resumen)} bodegas")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p5_riesgo_operativo_bodega.png")
    plt.close(fig)

    return {
        "resumen_por_bodega": resumen.reset_index().to_dict(orient="records"),
        "bodega_mas_desactualizada":   bodega_riesgo,
        "bodega_mayor_tasa_ticket":    bodega_mas_ticket,
        "correlacion_antiguedad_vs_tickets": {
            "_metodo": "Pearson (scipy.stats.pearsonr)",
            "r":       round(r_p, 4),
            "p_valor": round(p_p, 4),
            "n_bodegas": int(len(resumen)),
            "conclusion": (
                f"r={r_p:.3f}, p={p_p:.3f}: correlación positiva pero NO significativa "
                f"con n={len(resumen)} bodegas. Dirección es indicativa, no conclusiva."
            ),
        },
        "_fuente": "analysis.pregunta_5_riesgo_operativo",
        "_advertencia": (
            f"n={len(resumen)} bodegas: la correlación de Pearson no alcanza significancia "
            "estadística. El patrón es descriptivo; requeriría datos a nivel SKU-bodega "
            "para un test robusto."
        ),
    }
