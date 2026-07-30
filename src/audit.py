"""
audit.py — Motor de Auditoría de Calidad (Fase 1)
=================================================

PRINCIPIO DE TRAZABILIDAD
-------------------------
Ninguna cifra de este proyecto vive en un docstring ni se escribe "a mano".
Toda métrica la produce una función pura y nombrada de este módulo. El reporte
JSON que se genera guarda, junto a cada bloque de números, el campo "_fuente"
con el nombre exacto de la función que lo calculó. Así el dashboard y el PDF de
hallazgos pueden CITAR el origen de cada número (p. ej. "audit.nulidad_por_columna")
en lugar de pedir que se confíe en él.

DEFINICIÓN DEL HEALTH SCORE (y por qué es así)
----------------------------------------------
El Challenge (Fase 1, "Métricas de Calidad") ordena reportar exactamente tres
cosas: (1) porcentaje de nulidad POR COLUMNA, (2) número de duplicados y
(3) magnitud de los outliers. Esas tres se mapean a tres dimensiones 0-100:

    Completitud  <- nulidad         (100 - % de celdas nulas sobre TODAS las columnas)
    Validez      <- outliers/defectos (100 - % de filas con >=1 defecto inequívoco)
    Unicidad     <- duplicados        (100 - % de filas duplicadas exactas)

Health Score = promedio SIMPLE de las tres.

Peso igual (1/3 c/u) porque ni el Challenge ni la Guía de Validación establecen
jerarquía entre las dimensiones; ponderar "por criticidad" sería un criterio
inventado sin respaldo documental. La ponderación se deja explícita y las tres
dimensiones se exponen por separado para que el evaluador vea el desglose.

REGLAS DE COMPARABILIDAD (lo que se corrigió del enfoque anterior)
------------------------------------------------------------------
1. Completitud se calcula sobre TODAS las columnas del esquema original, no
   sobre 2 columnas elegidas a dedo. Y se reporta la nulidad por columna, tal
   como exige el Challenge.
2. Validez cuenta SOLO defectos inequívocos y corregibles (centinelas, valores
   imposibles). Los hallazgos de negocio (SKU fantasma, "Ventas_Web", estado
   sin dato, categoría desconocida, colisión de Feedback_ID) NO penalizan la
   validez: no son errores de dato sino integridad de negocio, y se reportan
   aparte en la sección "integridad". Así no se mide una cosa y se limpia otra.
3. Unicidad usa SIEMPRE duplicados de fila completa, igual en los tres datasets,
   para que el score sea comparable. Una colisión de llave con contenido
   distinto NO es un duplicado y va a "integridad", no a unicidad.
"""

import pandas as pd
import numpy as np


# --------------------------------------------------------------------------- #
#  MÉTRICAS ATÓMICAS (cada una es una fuente citable)                         #
# --------------------------------------------------------------------------- #
def nulidad_por_columna(df: pd.DataFrame) -> dict:
    """% de nulos por cada columna. Exigido literalmente por el Challenge."""
    return {c: round(df[c].isnull().mean() * 100, 2) for c in df.columns}


def reporte_duplicados(df: pd.DataFrame) -> dict:
    """Duplicados de FILA COMPLETA (criterio uniforme para los 3 datasets)."""
    n = len(df)
    dups = int(df.duplicated().sum())
    return {"n_filas": n, "duplicados_fila_completa": dups,
            "pct": round(dups / n * 100, 4) if n else 0.0}


def magnitud_outliers_iqr(serie: pd.Series, k: float = 1.5) -> dict:
    """
    Magnitud de outliers por IQR (método que exige la Guía de Validación).
    Devuelve las cercas, el conteo y CUÁNTOS IQR se aleja el valor extremo,
    que es el "finding" de magnitud que pide el Challenge.
    """
    s = serie.dropna()
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    low = max(q1 - k * iqr, s.min())   # piso realista, no negativo artificial
    high = q3 + k * iqr
    mask = (serie < low) | (serie > high)
    n_out = int(mask.sum())
    extremo = float(s.max())
    return {
        "q1": round(float(q1), 2), "q3": round(float(q3), 2),
        "iqr": round(float(iqr), 2),
        "cerca_inferior": round(float(low), 2),
        "cerca_superior": round(float(high), 2),
        "n_outliers": n_out,
        "pct_outliers": round(n_out / len(serie) * 100, 3),
        "valor_maximo": round(extremo, 2),
        "iqr_por_encima_de_cerca": round((extremo - high) / iqr, 1) if iqr else None,
    }


def z_modificado_mad(serie: pd.Series, umbral: float = 3.5) -> dict:
    """
    z modificado por MAD (Iglewicz-Hoaglin). Robusto ante asimetría alta, donde
    el z clásico (media/desv) no es fiable. Corrobora la detección por IQR.
    """
    s = serie.dropna()
    med = s.median()
    mad = (s - med).abs().median()
    if mad == 0:
        return {"n_outliers": 0, "umbral": umbral, "mad": 0.0, "nota": "MAD=0"}
    mz = 0.6745 * (s - med) / mad
    return {"mediana": round(float(med), 2), "mad": round(float(mad), 2),
            "umbral": umbral, "n_outliers": int((mz.abs() > umbral).sum()),
            "mz_maximo": round(float(mz.abs().max()), 1)}


# --------------------------------------------------------------------------- #
#  DIMENSIONES DEL HEALTH SCORE                                               #
# --------------------------------------------------------------------------- #
def completitud(df: pd.DataFrame, columnas: list[str]) -> float:
    sub = df[columnas]
    return round(100 - sub.isnull().to_numpy().mean() * 100, 2)


def validez(df: pd.DataFrame, reglas: dict) -> tuple[float, dict]:
    """
    reglas: dict {nombre_defecto: callable(df)->Series[bool]}. Una fila es
    inválida si dispara >=1 regla. Devuelve (score, conteo_por_regla).
    """
    n = len(df)
    if not reglas:
        return 100.0, {}
    detalle, union = {}, pd.Series(False, index=df.index)
    for nombre, fn in reglas.items():
        m = fn(df).fillna(False)
        detalle[nombre] = int(m.sum())
        union |= m
    return round(100 - union.mean() * 100, 2), detalle


def unicidad(df: pd.DataFrame) -> float:
    return round(100 - df.duplicated().mean() * 100, 2)


def health_score(comp: float, val: float, uniq: float) -> float:
    """Promedio simple (peso 1/3 c/u). Ver docstring del módulo para la razón."""
    return round((comp + val + uniq) / 3, 2)


# --------------------------------------------------------------------------- #
#  ENSAMBLADOR: audita un dataset y devuelve el bloque con _fuente            #
# --------------------------------------------------------------------------- #
def auditar(nombre: str, df: pd.DataFrame, reglas_validez: dict,
            columnas_completitud: list[str] | None = None,
            integridad: dict | None = None) -> dict:
    cols = columnas_completitud or list(df.columns)
    comp = completitud(df, cols)
    val, val_detalle = validez(df, reglas_validez)
    uniq = unicidad(df)
    return {
        "dataset": nombre,
        "n_registros": len(df),
        "nulidad_por_columna_pct": nulidad_por_columna(df),
        "_fuente_nulidad": "audit.nulidad_por_columna",
        "duplicados": reporte_duplicados(df),
        "_fuente_duplicados": "audit.reporte_duplicados",
        "dimensiones": {
            "completitud": comp,
            "validez": val,
            "unicidad": uniq,
            "validez_defectos_por_regla": val_detalle,
        },
        "_fuente_dimensiones": "audit.completitud / audit.validez / audit.unicidad",
        "health_score": health_score(comp, val, uniq),
        "_fuente_health_score": "audit.health_score (promedio simple 1/3)",
        "integridad_negocio": integridad or {},
        "_nota_integridad": ("Hallazgos de negocio: NO penalizan el health score "
                             "(no son defectos de dato). Se reportan para justificar "
                             "las decisiones de limpieza."),
    }
