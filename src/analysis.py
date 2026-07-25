"""
Fase 2/3 — Las 5 Preguntas de Alta Gerencia
=============================================
Cada función calcula evidencia numérica real sobre master_table y genera
un gráfico de soporte en outputs/charts/. Los números aquí son los que
deben citarse en el documento de hallazgos (PDF) y en el dashboard.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.rcParams.update({"figure.dpi": 120, "font.size": 10})
CHART_DIR = "outputs/charts"


def pregunta_1_fuga_capital(master: pd.DataFrame) -> dict:
    """SKUs con margen negativo: ¿pérdida aceptable por volumen o falla de precios online?"""
    df = master.dropna(subset=["Margen_Utilidad_USD"])  # excluye ventas fantasma (sin costo de referencia)
    negativos = df[df["Margen_Utilidad_USD"] < 0]

    por_canal = df.groupby("Canal_Venta").apply(
        lambda g: pd.Series({
            "pct_transacciones_negativas": (g["Margen_Utilidad_USD"] < 0).mean() * 100,
            "perdida_total_usd": g.loc[g["Margen_Utilidad_USD"] < 0, "Margen_Utilidad_USD"].sum(),
        }),
        include_groups=False,
    ).round(2)

    top_skus_negativos = (
        negativos.groupby("SKU_ID")["Margen_Utilidad_USD"].agg(["sum", "count"])
        .sort_values("sum").head(10).round(2)
    )

    resultado = {
        "transacciones_con_margen_negativo": int(len(negativos)),
        "pct_transacciones_negativas": round(len(negativos) / len(df) * 100, 2),
        "perdida_total_usd": round(negativos["Margen_Utilidad_USD"].sum(), 2),
        "perdida_por_canal": por_canal.to_dict(orient="index"),
        "top10_skus_mas_perdida": top_skus_negativos.to_dict(orient="index"),
    }

    fig, ax = plt.subplots(figsize=(7, 4))
    por_canal["pct_transacciones_negativas"].sort_values().plot(kind="barh", ax=ax, color="#C0392B")
    ax.set_xlabel("% de transacciones con margen negativo")
    ax.set_title("Pregunta 1 · Fuga de capital por canal de venta")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p1_fuga_capital_canal.png")
    plt.close(fig)

    return resultado


def pregunta_2_crisis_logistica(master: pd.DataFrame) -> dict:
    """Correlación Tiempo de Entrega vs NPS por ciudad/bodega. Zona más crítica."""
    df = master[master["Ciudad_Destino"] != "Sin Ciudad"].copy()
    df = df.dropna(subset=["Satisfaccion_NPS_Prom"])

    corr_general = df["Tiempo_Entrega_Real"].corr(df["Satisfaccion_NPS_Prom"])

    filas = []
    for (ciudad, bodega), g in df.groupby(["Ciudad_Destino", "Bodega_Origen"]):
        if len(g) >= 30:
            c = g["Tiempo_Entrega_Real"].corr(g["Satisfaccion_NPS_Prom"])
            filas.append({"Ciudad": ciudad, "Bodega": bodega, "n": len(g), "correlacion": round(c, 3)})
    tabla = pd.DataFrame(filas).sort_values("correlacion")

    peor_zona = tabla.iloc[0].to_dict() if len(tabla) else None

    resultado = {
        "correlacion_general_tiempo_vs_nps": round(corr_general, 3),
        "zona_mas_critica": peor_zona,
        "tabla_correlaciones_por_zona": tabla.round(3).to_dict(orient="records"),
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    pivot = tabla.pivot(index="Ciudad", columns="Bodega", values="correlacion")
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index))); ax.set_yticklabels(pivot.index)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Pregunta 2 · Correlación Tiempo de Entrega vs NPS (Ciudad x Bodega)")
    plt.colorbar(im, ax=ax, label="Correlación")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p2_correlacion_ciudad_bodega.png")
    plt.close(fig)

    return resultado


def pregunta_3_venta_invisible(master: pd.DataFrame) -> dict:
    """Impacto financiero de las ventas fantasma (SKU no catalogado)."""
    ingreso_total = master["Ingreso_Bruto"].sum()
    fantasma = master[master["Es_Venta_Fantasma"]]
    ingreso_fantasma = fantasma["Ingreso_Bruto"].sum()

    resultado = {
        "ingreso_total_usd": round(ingreso_total, 2),
        "ingreso_en_riesgo_usd": round(ingreso_fantasma, 2),
        "pct_ingreso_en_riesgo": round(ingreso_fantasma / ingreso_total * 100, 2),
        "transacciones_fantasma": int(len(fantasma)),
        "pct_transacciones_fantasma": round(len(fantasma) / len(master) * 100, 2),
        "skus_fantasma_distintos": int(fantasma["SKU_ID"].nunique()),
    }

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        [ingreso_total - ingreso_fantasma, ingreso_fantasma],
        labels=["Catalogado", "Venta Fantasma (en riesgo)"],
        autopct="%1.1f%%", colors=["#2E86C1", "#C0392B"],
    )
    ax.set_title("Pregunta 3 · % del ingreso total en riesgo por falta de catálogo")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p3_venta_fantasma.png")
    plt.close(fig)

    return resultado


def pregunta_4_diagnostico_fidelidad(master: pd.DataFrame) -> dict:
    """Categorías con alto stock pero sentimiento negativo (paradoja)."""
    df = master[master["Categoria"] != "Sin Catálogo"].copy()
    resumen = df.groupby("Categoria").agg(
        Stock_Promedio=("Stock_Actual", "mean"),
        NPS_Promedio=("Satisfaccion_NPS_Prom", "mean"),
        Rating_Producto_Promedio=("Rating_Producto_Prom", "mean"),
        Margen_Promedio_USD=("Margen_Utilidad_USD", "mean"),
    ).round(2)

    stock_mediana = resumen["Stock_Promedio"].median()
    nps_mediana = resumen["NPS_Promedio"].median()
    paradoja = resumen[(resumen["Stock_Promedio"] >= stock_mediana) & (resumen["NPS_Promedio"] < nps_mediana)]

    resultado = {
        "resumen_por_categoria": resumen.to_dict(orient="index"),
        "categorias_paradoja_stock_alto_nps_bajo": paradoja.to_dict(orient="index"),
    }

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(resumen["Stock_Promedio"], resumen["NPS_Promedio"], s=120, color="#8E44AD")
    for cat, row in resumen.iterrows():
        ax.annotate(cat, (row["Stock_Promedio"], row["NPS_Promedio"]), fontsize=9, xytext=(5, 5), textcoords="offset points")
    ax.axvline(stock_mediana, linestyle="--", color="gray", linewidth=0.8)
    ax.axhline(nps_mediana, linestyle="--", color="gray", linewidth=0.8)
    ax.set_xlabel("Stock promedio (unidades)")
    ax.set_ylabel("NPS promedio")
    ax.set_title("Pregunta 4 · Disponibilidad vs. Sentimiento por categoría")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p4_paradoja_categoria.png")
    plt.close(fig)

    return resultado


def pregunta_5_riesgo_operativo(master: pd.DataFrame) -> dict:
    """Antigüedad de revisión de stock vs. tasa de tickets de soporte, por bodega."""
    df = master[master["Bodega_Origen"] != "Sin Bodega"].copy()
    resumen = df.groupby("Bodega_Origen").agg(
        Dias_Desde_Revision_Promedio=("Dias_Desde_Ultima_Revision", "mean"),
        Tasa_Ticket_Soporte=("Ticket_Soporte_Abierto", "mean"),
        N_Transacciones=("Transaccion_ID", "count"),
    ).round(3)
    resumen["Tasa_Ticket_Soporte"] = (resumen["Tasa_Ticket_Soporte"] * 100).round(2)

    corr = resumen["Dias_Desde_Revision_Promedio"].corr(resumen["Tasa_Ticket_Soporte"])
    bodega_riesgo = resumen.sort_values("Dias_Desde_Revision_Promedio", ascending=False).index[0]

    resultado = {
        "resumen_por_bodega": resumen.to_dict(orient="index"),
        "correlacion_antiguedad_vs_tickets": round(corr, 3),
        "bodega_mas_desactualizada": bodega_riesgo,
    }

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(resumen["Dias_Desde_Revision_Promedio"], resumen["Tasa_Ticket_Soporte"], s=140, color="#D35400")
    for bod, row in resumen.iterrows():
        ax.annotate(bod, (row["Dias_Desde_Revision_Promedio"], row["Tasa_Ticket_Soporte"]), fontsize=9, xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("Días promedio desde última revisión de stock")
    ax.set_ylabel("% de transacciones con ticket de soporte")
    ax.set_title("Pregunta 5 · Bodegas operando 'a ciegas' vs. tickets de soporte")
    plt.tight_layout()
    fig.savefig(f"{CHART_DIR}/p5_riesgo_operativo_bodega.png")
    plt.close(fig)

    return resultado
