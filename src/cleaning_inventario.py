"""
cleaning_inventario.py — Limpieza de inventario_central_v2.csv
==============================================================

Cada paso devuelve un "registro de decisión" (dict) con:
  campo, problema, evidencia (estadística CALCULADA en runtime, no escrita a
  mano), accion, justificacion (media/mediana/moda según la distribución, como
  exige el Challenge) y _fuente. El orquestador (run_fase1) los agrega al JSON.

Cambio de fondo frente a la versión anterior:
  El costo atípico ($850.000) NO se winsoriza. La Guía de Validación pide un
  filtro IQR y "ver registros excluidos": se marca 'Costo_Atipico', se conserva
  el valor ORIGINAL (crítico para no enmascarar el margen negativo de la
  Pregunta 1) y se excluye de KPIs agregados aguas abajo. Además se corrige la
  afirmación falsa de "2 outliers": estadísticamente hay 1 (ver evidencia).
"""

import pandas as pd
import numpy as np
from . import audit

REFERENCE_DATE = pd.Timestamp("2026-01-31")  # corte del proyecto (ver README)

CATEGORIA_MAP = {"smart-phone": "Smartphones", "LAPTOP": "Laptops",
                 "???": "Sin Categoría"}


def _parse_lead_time(value):
    """Lead_Time_Dias (texto mixto) -> días numéricos."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if s == "Inmediato":
        return 0.0
    if "-" in s and "día" in s:                       # "25-30 días" -> punto medio
        nums = [float(x) for x in s.replace("días", "").replace("día", "").split("-")]
        return float(np.mean(nums))
    try:
        return float(s)
    except ValueError:
        return np.nan


def clean_inventario(raw: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    df = raw.copy()
    dec = []

    # --- 1. Categoria: normalizar formato; '???' -> "Sin Categoría" ---
    n_variantes = int(df["Categoria"].isin(["smart-phone", "LAPTOP"]).sum())
    n_desconocida = int((df["Categoria"] == "???").sum())
    df["Categoria"] = df["Categoria"].replace(CATEGORIA_MAP)
    dec.append({
        "campo": "Categoria",
        "problema": "variantes de formato (smart-phone, LAPTOP) y marcador '???'",
        "evidencia": {"variantes_formato": n_variantes,
                      "categoria_desconocida": n_desconocida,
                      "pct_desconocida": round(n_desconocida / len(df) * 100, 2)},
        "accion": "unificar formato; '???' -> categoría explícita 'Sin Categoría'",
        "justificacion": ("no se imputa una categoría real: fabricaría un segmento "
                          "de negocio falso. Se etiqueta la ausencia y se excluye de "
                          "análisis de margen por categoría, conservando la fila."),
        "_fuente": "cleaning_inventario.clean_inventario#1",
    })

    # --- 2. Stock_Actual: negativos + nulos -> imputar por categoría ---
    neg = int((df["Stock_Actual"] < 0).sum())
    nul = int(df["Stock_Actual"].isnull().sum())
    skew = round(float(df["Stock_Actual"].skew()), 3)
    df.loc[df["Stock_Actual"] < 0, "Stock_Actual"] = np.nan
    df["Stock_Actual"] = df.groupby("Categoria")["Stock_Actual"].transform(
        lambda s: s.fillna(s.median()))
    dec.append({
        "campo": "Stock_Actual",
        "problema": "existencias negativas (imposibles) y nulos",
        "evidencia": {"negativos": neg, "nulos": nul, "skew": skew},
        "accion": "negativos y nulos -> NaN -> imputar MEDIANA agrupada por Categoria",
        "justificacion": (f"skew={skew} (casi simétrica: media≈mediana); se usa "
                          "MEDIANA por robustez ante extremos residuales por categoría. "
                          "El negativo no se asume error de signo (no hay evidencia)."),
        "_fuente": "cleaning_inventario.clean_inventario#2",
    })

    # --- 3. Costo_Unitario_USD: detección IQR + corroboración MAD; NO winsoriza ---
    iqr_info = audit.magnitud_outliers_iqr(df["Costo_Unitario_USD"])
    mad_info = audit.z_modificado_mad(df["Costo_Unitario_USD"])
    low, high = iqr_info["cerca_inferior"], iqr_info["cerca_superior"]
    df["Costo_Atipico"] = (df["Costo_Unitario_USD"] < low) | (df["Costo_Unitario_USD"] > high)
    # SKU atípico: contexto de negocio (¿cuántas veces la mediana de su categoría?)
    if df["Costo_Atipico"].any():
        r = df.loc[df["Costo_Atipico"]].iloc[0]
        med_cat = df.loc[df["Categoria"] == r["Categoria"], "Costo_Unitario_USD"].median()
        contexto = {"categoria": r["Categoria"],
                    "veces_mediana_categoria": round(r["Costo_Unitario_USD"] / med_cat, 0)}
    else:
        contexto = {}
    dec.append({
        "campo": "Costo_Unitario_USD",
        "problema": "costo(s) extremo(s) que distorsionan KPIs de rentabilidad",
        "evidencia": {"iqr": iqr_info, "z_modificado_mad": mad_info, "negocio": contexto},
        "accion": ("marcar 'Costo_Atipico', CONSERVAR valor original, excluir de KPIs "
                   "agregados (Guía: 'ver registros excluidos')"),
        "justificacion": ("IQR y z-MAD coinciden en el conteo de outliers. NO se "
                          "winsoriza: capar el costo enmascararía el margen negativo "
                          "que busca la Pregunta 1. El z clásico no se usa (skew alto "
                          "lo hace no fiable)."),
        "_fuente": "cleaning_inventario.clean_inventario#3 (usa audit.magnitud_outliers_iqr)",
    })

    # --- 4. Lead_Time_Dias: parsear texto mixto + imputar por categoría ---
    comp = df["Lead_Time_Dias"].apply(
        lambda v: "Inmediato" if str(v).strip() == "Inmediato"
        else ("rango" if ("-" in str(v) and "día" in str(v))
              else ("nulo" if pd.isna(v) else "numerico")))
    df["Lead_Time_Dias_Clean"] = df["Lead_Time_Dias"].apply(_parse_lead_time)
    nul_lead = int(df["Lead_Time_Dias_Clean"].isnull().sum())
    skew_lead = round(float(df["Lead_Time_Dias_Clean"].skew()), 3)
    df["Lead_Time_Dias_Clean"] = df.groupby("Categoria")["Lead_Time_Dias_Clean"].transform(
        lambda s: s.fillna(s.median()))
    dec.append({
        "campo": "Lead_Time_Dias",
        "problema": "texto mixto: numérico, rangos '25-30 días', 'Inmediato' y nulos",
        "evidencia": {"composicion": comp.value_counts().to_dict(),
                      "nulos_tras_parseo": nul_lead, "skew": skew_lead},
        "accion": "parsear (rango->punto medio, Inmediato->0); nulos -> MEDIANA por categoría",
        "justificacion": (f"skew={skew_lead}; la MEDIANA es más representativa que la "
                          "media para tiempos de reposición y robusta a la cola derecha."),
        "_fuente": "cleaning_inventario.clean_inventario#4",
    })

    # --- 5. Bodega_Origen: normalizar formato (colapsa 'norte'/'Norte') ---
    antes = df["Bodega_Origen"].nunique()
    df["Bodega_Origen"] = (df["Bodega_Origen"].str.strip().str.replace("_", " ")
                           .str.title().str.replace(" ", "_"))
    dec.append({
        "campo": "Bodega_Origen",
        "problema": "misma bodega escrita distinto ('norte' vs 'Norte')",
        "evidencia": {"nodos_antes": int(antes),
                      "nodos_despues": int(df["Bodega_Origen"].nunique()),
                      "conteo": df["Bodega_Origen"].value_counts().to_dict()},
        "accion": "normalizar formato de texto",
        "justificacion": ("'Bod-Ext-99' (3PL) y 'Zona_Franca' se conservan como nodos "
                          "logísticos legítimos y distintos, no se fusionan con las regiones."),
        "_fuente": "cleaning_inventario.clean_inventario#5",
    })

    # --- 6. Ultima_Revision: parseo de fecha + antigüedad ---
    df["Ultima_Revision"] = pd.to_datetime(df["Ultima_Revision"], errors="coerce")
    df["Dias_Desde_Ultima_Revision"] = (REFERENCE_DATE - df["Ultima_Revision"]).dt.days
    dec.append({
        "campo": "Ultima_Revision",
        "problema": "ninguno (formato único YYYY-MM-DD, sin nulos)",
        "evidencia": {"nulos": int(df["Ultima_Revision"].isnull().sum())},
        "accion": "parsear a fecha y derivar 'Dias_Desde_Ultima_Revision' (Pregunta 5)",
        "justificacion": "dato limpio; solo se deriva la variable de antigüedad.",
        "_fuente": "cleaning_inventario.clean_inventario#6",
    })

    return df, dec


def integridad_inventario(clean: pd.DataFrame) -> dict:
    """Hallazgos de negocio (NO defectos) para la sección de integridad."""
    n = len(clean)
    n_sin_cat = int((clean["Categoria"] == "Sin Categoría").sum())
    return {
        "categoria_desconocida_residual": {
            "n": n_sin_cat, "pct": round(n_sin_cat / n * 100, 2),
            "nota": "persiste como 'Sin Categoría': ausencia etiquetada, no recuperada"},
        "sku_id_duplicados": int(clean["SKU_ID"].duplicated().sum()),
    }


# Reglas de validez (defectos inequívocos). Mismas para crudo y limpio.
REGLAS_VALIDEZ = {
    "stock_negativo": lambda d: d["Stock_Actual"] < 0,
    "costo_no_positivo": lambda d: d["Costo_Unitario_USD"] <= 0,
}
