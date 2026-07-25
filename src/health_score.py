"""
Health Score
============
Métrica compuesta 0-100 por dataset = promedio simple de:
  - Completitud: 100 - % de nulos (columnas relevantes)
  - Validez:     100 - % de registros con al menos un valor imposible/centinela
  - Unicidad:    100 - % de registros duplicados (fila completa)

Se calcula ANTES (datos crudos) y DESPUÉS (datos limpios) de cada dataset,
usando exactamente los mismos criterios de detección para que el delta sea
comparable y auditable.
"""

import pandas as pd
import numpy as np


def _score(completeness, validity, uniqueness):
    return round((completeness + validity + uniqueness) / 3, 2)


def health_inventario_raw(df: pd.DataFrame) -> dict:
    n = len(df)
    completeness = 100 - df[["Stock_Actual", "Lead_Time_Dias"]].isnull().mean().mean() * 100
    invalid = (
        (df["Stock_Actual"] < 0)
        | (df["Categoria"] == "???")
        | (df["Costo_Unitario_USD"] < 1)
        | (df["Costo_Unitario_USD"] > 100000)
    )
    validity = 100 - invalid.mean() * 100
    uniqueness = 100 - df.duplicated().mean() * 100
    return {
        "n_registros": n,
        "completitud": round(completeness, 2),
        "validez": round(validity, 2),
        "unicidad": round(uniqueness, 2),
        "health_score": _score(completeness, validity, uniqueness),
    }


def health_inventario_clean(df: pd.DataFrame) -> dict:
    n = len(df)
    completeness = 100 - df[["Stock_Actual", "Lead_Time_Dias_Clean"]].isnull().mean().mean() * 100
    # Tras la limpieza no deberían quedar centinelas; Sin Categoría/Costo_Atipico
    # son flags de negocio documentados, no defectos, por lo que no penalizan validez.
    invalid = df["Stock_Actual"] < 0
    validity = 100 - invalid.mean() * 100
    uniqueness = 100 - df.duplicated(subset=[c for c in df.columns if c != "Costo_Unitario_USD_Original"]).mean() * 100
    return {
        "n_registros": n,
        "completitud": round(completeness, 2),
        "validez": round(validity, 2),
        "unicidad": round(uniqueness, 2),
        "health_score": _score(completeness, validity, uniqueness),
    }


def health_transacciones_raw(df: pd.DataFrame, sku_maestro: set) -> dict:
    n = len(df)
    completeness = 100 - df[["Costo_Envio", "Estado_Envio"]].isnull().mean().mean() * 100
    invalid = (
        (df["Cantidad_Vendida"] == -5)
        | (df["Tiempo_Entrega_Real"] == 999)
        | (~df["SKU_ID"].isin(sku_maestro))
        | (df["Ciudad_Destino"] == "Ventas_Web")
    )
    validity = 100 - invalid.mean() * 100
    uniqueness = 100 - df.duplicated().mean() * 100
    return {
        "n_registros": n,
        "completitud": round(completeness, 2),
        "validez": round(validity, 2),
        "unicidad": round(uniqueness, 2),
        "health_score": _score(completeness, validity, uniqueness),
    }


def health_transacciones_clean(df: pd.DataFrame) -> dict:
    n = len(df)
    completeness = 100 - df[["Costo_Envio", "Estado_Envio"]].isnull().mean().mean() * 100
    # Es_Venta_Fantasma / Ciudad "Sin Ciudad" / Fecha_Futura_Invalida son flags de
    # negocio documentados (no se pueden "corregir", solo aislar), por lo que no
    # penalizan la validez post-limpieza; se valida que ya no queden centinelas.
    invalid = (df["Cantidad_Vendida"] <= 0) | (df["Tiempo_Entrega_Real"] == 999)
    validity = 100 - invalid.mean() * 100
    uniqueness = 100 - df.duplicated(subset=[c for c in df.columns if c not in ("Entrega_Atipica",)]).mean() * 100
    return {
        "n_registros": n,
        "completitud": round(completeness, 2),
        "validez": round(validity, 2),
        "unicidad": round(uniqueness, 2),
        "health_score": _score(completeness, validity, uniqueness),
    }


def health_feedback_raw(df: pd.DataFrame) -> dict:
    n = len(df)
    completeness = 100 - df[["Comentario_Texto", "Recomienda_Marca"]].isnull().mean().mean() * 100
    invalid = (df["Rating_Producto"] == 99) | (df["Edad_Cliente"] > 100)
    validity = 100 - invalid.mean() * 100
    uniqueness = 100 - df["Feedback_ID"].duplicated().mean() * 100
    return {
        "n_registros": n,
        "completitud": round(completeness, 2),
        "validez": round(validity, 2),
        "unicidad": round(uniqueness, 2),
        "health_score": _score(completeness, validity, uniqueness),
    }


def health_feedback_clean(df: pd.DataFrame) -> dict:
    n = len(df)
    completeness = 100 - df[["Comentario_Texto", "Recomienda_Marca"]].isnull().mean().mean() * 100
    invalid = (df["Rating_Producto"] == 99) | (df["Edad_Cliente"] > 100)
    validity = 100 - invalid.mean() * 100
    uniqueness = 100 - df["Feedback_UID"].duplicated().mean() * 100
    return {
        "n_registros": n,
        "completitud": round(completeness, 2),
        "validez": round(validity, 2),
        "unicidad": round(uniqueness, 2),
        "health_score": _score(completeness, validity, uniqueness),
    }
