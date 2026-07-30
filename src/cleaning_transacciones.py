"""
cleaning_transacciones.py — Limpieza de transacciones_logistica_v2.csv
======================================================================
Misma filosofía que inventario: cada decisión trae evidencia CALCULADA y _fuente.

Separación clave (que corrige el enfoque anterior):
  - DEFECTOS de dato (centinelas) -> penalizan validez y se imputan.
  - HALLAZGOS de negocio (SKU fantasma, 'Ventas_Web', estado sin dato, fecha
    futura) -> NO se "corrigen", se AÍSLAN con banderas y se reportan en
    integridad. No penalizan el health score porque no son errores de dato.
"""

import pandas as pd
import numpy as np

REFERENCE_DATE = pd.Timestamp("2026-01-31")
CIUDAD_MAP = {"BOG": "Bogotá", "MED": "Medellín"}


def clean_transacciones(raw: pd.DataFrame, sku_maestro: set) -> tuple[pd.DataFrame, list]:
    df = raw.copy()
    dec = []

    # --- 1. Cantidad_Vendida: centinela -5 ---
    negs = sorted(df.loc[df["Cantidad_Vendida"] < 0, "Cantidad_Vendida"].unique().tolist())
    n_cent = int((df["Cantidad_Vendida"] == -5).sum())
    med = float(df.loc[df["Cantidad_Vendida"] != -5, "Cantidad_Vendida"].median())
    df.loc[df["Cantidad_Vendida"] == -5, "Cantidad_Vendida"] = np.nan
    df["Cantidad_Vendida"] = df["Cantidad_Vendida"].fillna(med)
    dec.append({
        "campo": "Cantidad_Vendida",
        "problema": "valor negativo imposible",
        "evidencia": {"valores_negativos_unicos": negs, "n_afectados": n_cent,
                      "mediana_imputada": med},
        "accion": "tratar -5 como nulo e imputar MEDIANA",
        "justificacion": (f"el ÚNICO negativo es exactamente -5 ({n_cent} filas): patrón "
                          "de código centinela, no error aleatorio. No se usa abs(-5)=5 "
                          "porque fabricaría un valor sin respaldo. MEDIANA por robustez."),
        "_fuente": "cleaning_transacciones.clean_transacciones#1",
    })

    # --- 2. Tiempo_Entrega_Real: centinela 999 ---
    n_999 = int((df["Tiempo_Entrega_Real"] == 999).sum())
    otros_altos = int(((df["Tiempo_Entrega_Real"] > 100) & (df["Tiempo_Entrega_Real"] != 999)).sum())
    med_t = float(df.loc[df["Tiempo_Entrega_Real"] != 999, "Tiempo_Entrega_Real"].median())
    df["Entrega_Atipica"] = df["Tiempo_Entrega_Real"] == 999
    df.loc[df["Tiempo_Entrega_Real"] == 999, "Tiempo_Entrega_Real"] = np.nan
    df["Tiempo_Entrega_Real"] = df["Tiempo_Entrega_Real"].fillna(med_t)
    dec.append({
        "campo": "Tiempo_Entrega_Real",
        "problema": "valor 999 (código centinela de error)",
        "evidencia": {"n_999": n_999, "otros_valores_>100": otros_altos,
                      "mediana_imputada": med_t},
        "accion": "999 -> nulo -> imputar MEDIANA; conservar bandera 'Entrega_Atipica'",
        "justificacion": ("no hay otros valores >100: el 999 es centinela aislado. La "
                          "bandera permite excluirlos de la correlación tiempo-NPS (Pregunta 2)."),
        "_fuente": "cleaning_transacciones.clean_transacciones#2",
    })

    # --- 3. Costo_Envio: nulos, distribución simétrica ---
    nul_env = int(df["Costo_Envio"].isnull().sum())
    media_e, med_e = float(df["Costo_Envio"].mean()), float(df["Costo_Envio"].median())
    skew_e = round(float(df["Costo_Envio"].skew()), 3)
    df["Costo_Envio"] = df["Costo_Envio"].fillna(df["Costo_Envio"].median())
    dec.append({
        "campo": "Costo_Envio",
        "problema": "nulos",
        "evidencia": {"nulos": nul_env, "pct": round(nul_env / len(df) * 100, 2),
                      "media": round(media_e, 2), "mediana": round(med_e, 2), "skew": skew_e},
        "accion": "imputar MEDIANA",
        "justificacion": (f"skew={skew_e} (simétrica): media≈mediana. Se elige MEDIANA por "
                          "consistencia con el resto del pipeline; el resultado es equivalente."),
        "_fuente": "cleaning_transacciones.clean_transacciones#3",
    })

    # --- 4. Estado_Envio: nulo -> categoría explícita (NO moda) ---
    nul_est = int(df["Estado_Envio"].isnull().sum())
    df["Estado_Envio"] = df["Estado_Envio"].fillna("Sin Información")
    dec.append({
        "campo": "Estado_Envio",
        "problema": "nulos",
        "evidencia": {"nulos": nul_est, "pct": round(nul_est / len(df) * 100, 2)},
        "accion": "marcar como categoría explícita 'Sin Información' (NO imputar moda)",
        "justificacion": ("imputar la moda fabricaría una confirmación de entrega que no "
                          "ocurrió. La ausencia se etiqueta, no se inventa."),
        "_fuente": "cleaning_transacciones.clean_transacciones#4",
    })

    # --- 5. Ciudad_Destino: normalizar + aislar 'Ventas_Web' con evidencia ---
    df["Ciudad_Destino"] = df["Ciudad_Destino"].replace(CIUDAD_MAP)
    web = df["Ciudad_Destino"] == "Ventas_Web"
    dist_web = (df.loc[web, "Canal_Venta"].value_counts(normalize=True) * 100).round(1).to_dict()
    dist_glob = (df["Canal_Venta"].value_counts(normalize=True) * 100).round(1).to_dict()
    n_web = int(web.sum())
    df.loc[web, "Ciudad_Destino"] = "Sin Ciudad"
    dec.append({
        "campo": "Ciudad_Destino",
        "problema": "variantes (BOG/Bogotá, MED/Medellín) y valor 'Ventas_Web' que no es ciudad",
        "evidencia": {"n_ventas_web": n_web, "pct": round(n_web / len(df) * 100, 2),
                      "distribucion_canal_en_web": dist_web, "distribucion_canal_global": dist_glob},
        "accion": "consolidar variantes; 'Ventas_Web' -> 'Sin Ciudad'",
        "justificacion": ("la distribución de canal dentro de 'Ventas_Web' (~25% c/u) es igual "
                          "a la global: NO está correlacionado con un canal, así que no es "
                          "recuperable como ciudad. Se trata como geo no disponible."),
        "_fuente": "cleaning_transacciones.clean_transacciones#5",
    })

    # --- 6. Fecha_Venta: parseo + fechas futuras (hallazgo, se aísla) ---
    df["Fecha_Venta"] = pd.to_datetime(df["Fecha_Venta"], format="mixed", dayfirst=True, errors="coerce")
    no_parse = int(df["Fecha_Venta"].isnull().sum())
    df["Fecha_Futura_Invalida"] = df["Fecha_Venta"] > REFERENCE_DATE
    n_fut = int(df["Fecha_Futura_Invalida"].sum())
    dec.append({
        "campo": "Fecha_Venta",
        "problema": "posibles formatos mixtos y fechas posteriores al corte",
        "evidencia": {"no_parseables": no_parse, "fechas_futuras": n_fut,
                      "corte": str(REFERENCE_DATE.date()),
                      "max_fecha": str(df["Fecha_Venta"].max().date())},
        "accion": "parsear DD/MM/AAAA; marcar 'Fecha_Futura_Invalida', excluir de series de tiempo",
        "justificacion": ("formato en realidad único (0 no parseables). Las futuras se aíslan, "
                          "no se borran, para conservar el resto de la transacción."),
        "_fuente": "cleaning_transacciones.clean_transacciones#6",
    })

    # --- 7. SKU huérfano / Venta Fantasma (hallazgo central, se aísla) ---
    df["Es_Venta_Fantasma"] = ~df["SKU_ID"].isin(sku_maestro)
    orf = df["Es_Venta_Fantasma"]
    rep = df.loc[orf, "SKU_ID"].value_counts()
    dec.append({
        "campo": "SKU_ID",
        "problema": "SKUs vendidos que no existen en el inventario maestro (Venta Fantasma)",
        "evidencia": {"n_huerfanas": int(orf.sum()), "pct": round(orf.mean() * 100, 2),
                      "skus_distintos": int(df.loc[orf, "SKU_ID"].nunique()),
                      "repeticiones_media": round(float(rep.mean()), 2) if len(rep) else 0,
                      "repeticiones_max": int(rep.max()) if len(rep) else 0},
        "accion": "marcar 'Es_Venta_Fantasma'; conservar vía LEFT JOIN (Fase 2) para cuantificar impacto",
        "justificacion": ("muchos SKUs distintos con recurrencia orgánica y baja (media ~3.6, "
                          "máx 10): patrón de FALLA DE CATÁLOGO (productos nuevos sin registrar), "
                          "no de fraude (que se concentraría en pocos códigos)."),
        "_fuente": "cleaning_transacciones.clean_transacciones#7",
    })

    return df, dec


def integridad_transacciones(clean: pd.DataFrame) -> dict:
    n = len(clean)
    def pct(x): return round(x / n * 100, 2)
    return {
        "ventas_fantasma": {"n": int(clean["Es_Venta_Fantasma"].sum()),
                            "pct": pct(int(clean["Es_Venta_Fantasma"].sum()))},
        "sin_ciudad_ventas_web": {"n": int((clean["Ciudad_Destino"] == "Sin Ciudad").sum()),
                                  "pct": pct(int((clean["Ciudad_Destino"] == "Sin Ciudad").sum()))},
        "estado_sin_informacion": {"n": int((clean["Estado_Envio"] == "Sin Información").sum()),
                                   "pct": pct(int((clean["Estado_Envio"] == "Sin Información").sum()))},
        "fechas_futuras": {"n": int(clean["Fecha_Futura_Invalida"].sum()),
                           "pct": pct(int(clean["Fecha_Futura_Invalida"].sum()))},
    }


# Reglas de validez: SOLO defectos de dato (centinelas). NO incluye hallazgos.
REGLAS_VALIDEZ = {
    "cantidad_no_positiva": lambda d: d["Cantidad_Vendida"] <= 0,
    "tiempo_centinela_999": lambda d: d["Tiempo_Entrega_Real"] == 999,
}
