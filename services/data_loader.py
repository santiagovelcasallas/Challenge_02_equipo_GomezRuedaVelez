"""Carga de datos para el dashboard. Todo se lee de outputs/ (generado por run_pipeline.py)."""

import json
import pandas as pd
import streamlit as st

OUT_DIR = "outputs"


@st.cache_data(show_spinner="Cargando datos...")
def load_master_table() -> pd.DataFrame:
    df = pd.read_csv(f"{OUT_DIR}/master_table.csv")
    df["Fecha_Venta"] = pd.to_datetime(df["Fecha_Venta"])
    return df


@st.cache_data
def load_health_score() -> dict:
    with open(f"{OUT_DIR}/health_score_report.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_decisiones() -> dict:
    with open(f"{OUT_DIR}/decisiones_limpieza.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_respuestas() -> dict:
    with open(f"{OUT_DIR}/respuestas_5_preguntas.json", encoding="utf-8") as f:
        return json.load(f)


def apply_filters(df: pd.DataFrame, fecha_range, categorias, bodegas, canales) -> pd.DataFrame:
    out = df.copy()
    if fecha_range and len(fecha_range) == 2:
        start, end = pd.Timestamp(fecha_range[0]), pd.Timestamp(fecha_range[1])
        out = out[(out["Fecha_Venta"] >= start) & (out["Fecha_Venta"] <= end)]
    if categorias:
        out = out[out["Categoria"].isin(categorias)]
    if bodegas:
        out = out[out["Bodega_Origen"].isin(bodegas)]
    if canales:
        out = out[out["Canal_Venta"].isin(canales)]
    return out


def cleaning_report_csv(health: dict, decisiones: dict) -> bytes:
    """Genera el CSV descargable del 'reporte de limpieza' exigido por el reto."""
    filas = []
    for dataset in ("inventario", "transacciones", "feedback"):
        antes = health["antes"][dataset]
        despues = health["despues"][dataset]
        filas.append({
            "Dataset": dataset,
            "Health_Score_Antes": antes["health_score"],
            "Health_Score_Despues": despues["health_score"],
            "Completitud_Antes": antes["completitud"],
            "Completitud_Despues": despues["completitud"],
            "Validez_Antes": antes["validez"],
            "Validez_Despues": despues["validez"],
            "Unicidad_Antes": antes["unicidad"],
            "Unicidad_Despues": despues["unicidad"],
        })
    df_health = pd.DataFrame(filas)

    filas_dec = []
    for dataset, log in decisiones.items():
        for decision, valor in log.items():
            filas_dec.append({"Dataset": dataset, "Decision": decision, "Valor": valor})
    df_dec = pd.DataFrame(filas_dec)

    buf = []
    buf.append("=== HEALTH SCORE (ANTES / DESPUÉS) ===")
    buf.append(df_health.to_csv(index=False))
    buf.append("\n=== LOG DE DECISIONES DE LIMPIEZA ===")
    buf.append(df_dec.to_csv(index=False))
    return "\n".join(buf).encode("utf-8")
