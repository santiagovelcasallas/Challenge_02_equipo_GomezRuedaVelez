"""
Limpieza de inventario_central_v2.csv
======================================

Decisiones de limpieza documentadas (Fase 1 - Auditoría de Calidad):

1. Categoria: existen 8 valores únicos que en realidad representan 5 categorías
   de negocio + variantes de formato + un marcador de dato desconocido:
     - 'smart-phone'  -> 'Smartphones' (variante de formato)
     - 'LAPTOP'       -> 'Laptops'     (variante de formato)
     - '???'          -> 'Sin Categoría' (dato no capturado, NO se imputa con
       una categoría real porque fabricaríamos un segmento de negocio falso;
       se mantiene como categoría explícita "Sin Categoría" y se excluye de
       los análisis de rentabilidad por categoría, pero se conserva la fila
       para no romper la integridad referencial con ventas).

2. Stock_Actual: 4% de nulos y 60 registros con existencias negativas
   (imposible contablemente). Ambos casos se tratan como dato faltante
   (no se asume que el negativo sea un error de signo, ya que no hay evidencia
   que lo sustente) y se imputan con la MEDIANA de Stock_Actual agrupada por
   Categoria. Se usa mediana y no media porque, aunque la distribución global
   es razonablemente simétrica, la mediana es robusta a los pocos valores
   extremos que puedan quedar por categoría.

3. Costo_Unitario_USD: se detectan 2 valores extremos vía rango intercuartílico
   (IQR): $0.05 (implausible para cualquier categoría) y $850,000 (100-1000x
   el costo típico). Ambos se marcan como "excluido_costo_atipico" = True y se
   capan (winsorizan) al límite superior/inferior del IQR para no distorsionar
   KPIs de rentabilidad agregados, pero se conservan visibles en el reporte de
   auditoría ("ver registros excluidos"), tal como exige la guía de validación.

4. Lead_Time_Dias ("dato ruidoso" según el diccionario): mezcla de:
     - valores numéricos puros (1,210 registros, 3-10 días)
     - rangos en texto "25-30 días" (454 registros) -> se toma el punto medio
     - "Inmediato" (433 registros) -> se traduce a 0 días
     - nulos (403 registros, 16.12%) -> se imputan con la MEDIANA de la
       columna ya parseada, agrupada por Categoria (distribución de días de
       entrega del proveedor sesgada a la derecha, por lo que la mediana es
       más representativa que la media).

5. Bodega_Origen: se normaliza únicamente el formato de texto (mayúsculas
   iniciales). 'BOD-EXT-99' y 'ZONA_FRANCA' se conservan como nodos de bodega
   legítimos y distintos (bodega externa/3PL y zona franca son conceptos
   logísticos reales en Colombia), no se fusionan con Norte/Sur/Occidente.

6. Ultima_Revision: se parsea a fecha; no presenta nulos ni inconsistencias
   de formato. Se usa para derivar "Dias_Desde_Ultima_Revision" en la fase de
   feature engineering (Pregunta 5).
"""

import pandas as pd
import numpy as np

REFERENCE_DATE = pd.Timestamp("2026-01-31")  # fecha de corte del proyecto (ver README)

CATEGORIA_MAP = {
    "smart-phone": "Smartphones",
    "LAPTOP": "Laptops",
    "???": "Sin Categoría",
}


def _parse_lead_time(value):
    """Convierte Lead_Time_Dias (texto mixto) a número de días."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if s == "Inmediato":
        return 0.0
    if "-" in s and "día" in s:
        # ej. "25-30 días" -> punto medio
        nums = [float(x) for x in s.replace("días", "").replace("día", "").split("-")]
        return float(np.mean(nums))
    try:
        return float(s)
    except ValueError:
        return np.nan


def clean_inventario(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpia inventario_central_v2 y devuelve (df_limpio, log_de_decisiones)."""
    df = raw.copy()
    log = {}

    # --- 1. Categoria ---
    df["Categoria"] = df["Categoria"].replace(CATEGORIA_MAP)
    log["categoria_normalizada"] = df["Categoria"].value_counts().to_dict()

    # --- 2. Stock_Actual: negativos -> nulo, luego imputar por mediana de categoría ---
    negativos = (df["Stock_Actual"] < 0).sum()
    nulos_originales = df["Stock_Actual"].isnull().sum()
    df.loc[df["Stock_Actual"] < 0, "Stock_Actual"] = np.nan
    df["Stock_Actual"] = df.groupby("Categoria")["Stock_Actual"].transform(
        lambda s: s.fillna(s.median())
    )
    log["stock_actual_negativos_tratados"] = int(negativos)
    log["stock_actual_nulos_originales"] = int(nulos_originales)
    log["stock_actual_imputados_total"] = int(negativos + nulos_originales)

    # --- 3. Costo_Unitario_USD: winsorización por IQR ---
    q1, q3 = df["Costo_Unitario_USD"].quantile([0.25, 0.75])
    iqr = q3 - q1
    low, high = max(q1 - 1.5 * iqr, 0), q3 + 1.5 * iqr
    df["Costo_Atipico"] = (df["Costo_Unitario_USD"] < low) | (df["Costo_Unitario_USD"] > high)
    log["costo_unitario_outliers_detectados"] = int(df["Costo_Atipico"].sum())
    log["costo_unitario_limites_iqr"] = (round(low, 2), round(high, 2))
    df["Costo_Unitario_USD_Original"] = df["Costo_Unitario_USD"]
    df["Costo_Unitario_USD"] = df["Costo_Unitario_USD"].clip(lower=low, upper=high)

    # --- 4. Lead_Time_Dias: parseo + imputación por mediana de categoría ---
    df["Lead_Time_Dias_Clean"] = df["Lead_Time_Dias"].apply(_parse_lead_time)
    nulos_lead = df["Lead_Time_Dias_Clean"].isnull().sum()
    df["Lead_Time_Dias_Clean"] = df.groupby("Categoria")["Lead_Time_Dias_Clean"].transform(
        lambda s: s.fillna(s.median())
    )
    log["lead_time_nulos_imputados"] = int(nulos_lead)

    # --- 5. Bodega_Origen: normalizar formato ---
    df["Bodega_Origen"] = (
        df["Bodega_Origen"].str.strip().str.replace("_", " ").str.title().str.replace(" ", "_")
    )
    log["bodegas_normalizadas"] = df["Bodega_Origen"].value_counts().to_dict()

    # --- 6. Ultima_Revision: parseo de fecha ---
    df["Ultima_Revision"] = pd.to_datetime(df["Ultima_Revision"], errors="coerce")
    df["Dias_Desde_Ultima_Revision"] = (REFERENCE_DATE - df["Ultima_Revision"]).dt.days

    # --- Duplicados ---
    dup_full = df.duplicated().sum()
    dup_sku = df["SKU_ID"].duplicated().sum()
    log["duplicados_fila_completa"] = int(dup_full)
    log["duplicados_sku_id"] = int(dup_sku)

    return df, log
