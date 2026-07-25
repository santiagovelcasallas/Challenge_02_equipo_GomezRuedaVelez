"""
Limpieza de transacciones_logistica_v2.csv
============================================

Decisiones de limpieza documentadas (Fase 1 - Auditoría de Calidad):

1. Cantidad_Vendida: 100 registros (1%) tienen el valor EXACTO -5 (nunca otro
   negativo). Que sea siempre el mismo número descarta un error de digitación
   aleatorio y apunta a un código centinela/de error del sistema de origen
   (mismo patrón que Rating_Producto=99 y Tiempo_Entrega_Real=999). Se trata
   como dato faltante y se imputa con la MEDIANA (7 unidades), no con el valor
   absoluto, porque tomar abs(-5)=5 fabricaría un valor puntual sin respaldo
   estadístico.

2. Tiempo_Entrega_Real = 999 (50 registros): mismo patrón de código centinela,
   confirmado también por rango intercuartílico (IQR). Se trata como dato
   faltante y se imputa con la mediana (15 días). Se conserva la bandera
   'Entrega_Atipica' para poder excluir estos registros de análisis de
   correlación tiempo-satisfacción si se requiere mayor rigor (Pregunta 2).

3. Costo_Envio: 8.34% de nulos, distribución simétrica (media≈52.4,
   mediana≈52.4) -> imputación por media/mediana (equivalentes aquí).

4. Estado_Envio: 16.83% de nulos. NO se imputa con la moda porque eso
   fabricaría una confirmación de entrega que no ocurrió; se deja como
   categoría explícita "Sin Información".

5. Ciudad_Destino: se detectan variantes de la misma ciudad (BOG/Bogotá,
   MED/Medellín) que se consolidan. Además, el valor "Ventas_Web" (12.9% de
   los registros) NO es una ciudad sino que parece un residuo del campo
   Canal_Venta. Se validó cruzando Ciudad_Destino=='Ventas_Web' contra
   Canal_Venta real: la distribución resultante es proporcional a la
   distribución general de canales (~25% cada uno), es decir, NO está
   correlacionada con un canal específico. Esto descarta que sea un error de
   mapeo recuperable; se trata como dato geográfico no disponible
   ("Sin Ciudad") y se excluye del análisis geográfico (Pregunta 2), pero se
   mantiene la fila para no perder el resto de la información transaccional.

6. Fecha_Venta: formato único y consistente (DD/MM/AAAA), sin necesidad de
   parseo múltiple. Se validan fechas futuras respecto a la fecha de corte
   del proyecto (2026-01-31, ver README): 75 registros (0.75%) caen entre el
   1 y el 4 de febrero de 2026. Se marcan como 'Fecha_Futura_Invalida' y se
   excluyen de gráficas de series de tiempo, conservando la fila.

7. SKU_ID huérfano ("Venta Fantasma", Dilema central del reto): 1,751
   transacciones (17.51%) referencian 480 SKUs distintos que NO existen en el
   inventario maestro, cada uno repitiéndose en promedio ~3.6 veces (rango
   1-10). Este patrón —muchos SKUs distintos con recurrencia orgánica y
   moderada, sin concentración en unos pocos códigos— es más consistente con
   una FALLA DE CATÁLOGO (productos nuevos vendidos antes de ser registrados
   en el ERP) que con fraude (que típicamente se concentraría en pocos
   códigos explotados repetidamente). Decisión: se clasifican como
   "Producto No Catalogado" y se conservan en el LEFT JOIN con inventario
   (ver integration.py) para cuantificar el impacto financiero real
   (Pregunta 3), en vez de descartarlas.
"""

import pandas as pd
import numpy as np

REFERENCE_DATE = pd.Timestamp("2026-01-31")

CIUDAD_MAP = {
    "BOG": "Bogotá",
    "MED": "Medellín",
}


def clean_transacciones(raw: pd.DataFrame, sku_maestro: set) -> tuple[pd.DataFrame, dict]:
    """Limpia transacciones_logistica_v2 y devuelve (df_limpio, log_de_decisiones)."""
    df = raw.copy()
    log = {}

    # --- 1. Cantidad_Vendida: -5 centinela -> nulo -> imputar mediana ---
    centinela_qty = (df["Cantidad_Vendida"] == -5).sum()
    df.loc[df["Cantidad_Vendida"] == -5, "Cantidad_Vendida"] = np.nan
    df["Cantidad_Vendida"] = df["Cantidad_Vendida"].fillna(df["Cantidad_Vendida"].median())
    log["cantidad_vendida_centinela_-5_tratados"] = int(centinela_qty)

    # --- 2. Tiempo_Entrega_Real: 999 centinela -> nulo -> imputar mediana ---
    centinela_tiempo = (df["Tiempo_Entrega_Real"] == 999).sum()
    df["Entrega_Atipica"] = df["Tiempo_Entrega_Real"] == 999
    df.loc[df["Tiempo_Entrega_Real"] == 999, "Tiempo_Entrega_Real"] = np.nan
    df["Tiempo_Entrega_Real"] = df["Tiempo_Entrega_Real"].fillna(df["Tiempo_Entrega_Real"].median())
    log["tiempo_entrega_centinela_999_tratados"] = int(centinela_tiempo)

    # --- 3. Costo_Envio: imputar mediana ---
    nulos_envio = df["Costo_Envio"].isnull().sum()
    df["Costo_Envio"] = df["Costo_Envio"].fillna(df["Costo_Envio"].median())
    log["costo_envio_nulos_imputados"] = int(nulos_envio)

    # --- 4. Estado_Envio: nulo -> categoría explícita ---
    nulos_estado = df["Estado_Envio"].isnull().sum()
    df["Estado_Envio"] = df["Estado_Envio"].fillna("Sin Información")
    log["estado_envio_nulos_marcados"] = int(nulos_estado)

    # --- 5. Ciudad_Destino: normalizar + aislar "Ventas_Web" ---
    df["Ciudad_Destino"] = df["Ciudad_Destino"].replace(CIUDAD_MAP)
    ventas_web_mask = df["Ciudad_Destino"] == "Ventas_Web"
    log["ciudad_destino_sin_dato_(Ventas_Web)"] = int(ventas_web_mask.sum())
    df.loc[ventas_web_mask, "Ciudad_Destino"] = "Sin Ciudad"
    log["ciudad_destino_normalizada"] = df["Ciudad_Destino"].value_counts().to_dict()

    # --- 6. Fecha_Venta: parseo + fechas futuras ---
    df["Fecha_Venta"] = pd.to_datetime(df["Fecha_Venta"], format="mixed", dayfirst=True)
    df["Fecha_Futura_Invalida"] = df["Fecha_Venta"] > REFERENCE_DATE
    log["fechas_futuras_marcadas"] = int(df["Fecha_Futura_Invalida"].sum())

    # --- 7. SKU huérfano / Venta Fantasma ---
    df["Es_Venta_Fantasma"] = ~df["SKU_ID"].isin(sku_maestro)
    log["ventas_fantasma_detectadas"] = int(df["Es_Venta_Fantasma"].sum())
    log["skus_fantasma_distintos"] = int(df.loc[df["Es_Venta_Fantasma"], "SKU_ID"].nunique())

    # --- Duplicados ---
    log["duplicados_fila_completa"] = int(df.duplicated().sum())
    log["duplicados_transaccion_id"] = int(df["Transaccion_ID"].duplicated().sum())

    return df, log
