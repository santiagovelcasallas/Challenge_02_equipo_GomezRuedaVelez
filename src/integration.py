"""
Integración (Fase 2) — Una Sola Fuente de Verdad
==================================================

Estrategia de unión:
  1. Base = transacciones_logistica limpio (se preservan las 10,000 filas;
     ninguna venta se descarta, incluidas las "ventas fantasma").
  2. LEFT JOIN con inventario_central por SKU_ID -> aporta Categoria, Costo
     Unitario, Stock, Bodega, Lead Time. Los SKU sin match (ventas fantasma)
     quedan con estos campos en NaN / 'Sin Catálogo'.
  3. LEFT JOIN con feedback_clientes (agregado a nivel de Transaccion_ID,
     porque puede haber 1:N feedbacks por transacción) -> aporta rating
     promedio, NPS promedio y bandera de ticket de soporte.

Variables derivadas (mínimo 3 exigidas por el reto; se entregan 6):
  - Margen_Utilidad_USD: (Precio_Venta_Final - Costo_Unitario_USD) *
    Cantidad_Vendida - Costo_Envio. NaN cuando el SKU es una venta fantasma
    (no hay costo de referencia), lo cual se documenta explícitamente:
    "no se puede calcular margen de lo que no está catalogado".
  - Margen_Porcentual: Margen_Utilidad_USD / Ingreso_Bruto.
  - Brecha_Entrega_Dias: Tiempo_Entrega_Real - Lead_Time_Dias_Clean. Se
    documenta como una APROXIMACIÓN a "entrega vs. prometido": el diccionario
    de datos no define un campo explícito de fecha prometida al cliente, por
    lo que se usa el lead time del proveedor como la mejor referencia
    disponible del tiempo esperado.
  - Ratio_Soporte_Categoria: % de transacciones con ticket de soporte
    abierto, por Categoria.
  - Dias_Desde_Ultima_Revision: fecha de corte del proyecto - Ultima_Revision.
  - Ingreso_Bruto: Precio_Venta_Final * Cantidad_Vendida (variable de apoyo).
"""

import pandas as pd
import numpy as np


def build_master_table(
    tx_clean: pd.DataFrame, inv_clean: pd.DataFrame, fb_clean: pd.DataFrame
) -> pd.DataFrame:
    inv_cols = [
        "SKU_ID",
        "Categoria",
        "Stock_Actual",
        "Costo_Unitario_USD",
        "Costo_Atipico",
        "Bodega_Origen",
        "Lead_Time_Dias_Clean",
        "Ultima_Revision",
        "Dias_Desde_Ultima_Revision",
    ]
    master = tx_clean.merge(inv_clean[inv_cols], on="SKU_ID", how="left")
    master["Categoria"] = master["Categoria"].fillna("Sin Catálogo")
    master["Bodega_Origen"] = master["Bodega_Origen"].fillna("Sin Bodega")

    # Agregado de feedback a nivel de transacción (1:N -> promedio / any)
    fb_agg = (
        fb_clean.groupby("Transaccion_ID")
        .agg(
            Rating_Producto_Prom=("Rating_Producto", "mean"),
            Rating_Logistica_Prom=("Rating_Logistica", "mean"),
            Satisfaccion_NPS_Prom=("Satisfaccion_NPS", "mean"),
            Ticket_Soporte_Abierto=("Ticket_Soporte_Abierto", "any"),
            N_Feedbacks=("Feedback_UID", "count"),
        )
        .reset_index()
    )
    master = master.merge(fb_agg, on="Transaccion_ID", how="left")
    master["Ticket_Soporte_Abierto"] = master["Ticket_Soporte_Abierto"].fillna(False)
    master["N_Feedbacks"] = master["N_Feedbacks"].fillna(0).astype(int)

    # --- Feature engineering ---
    master["Ingreso_Bruto"] = master["Precio_Venta_Final"] * master["Cantidad_Vendida"]
    master["Margen_Utilidad_USD"] = np.where(
        master["Es_Venta_Fantasma"],
        np.nan,
        (master["Precio_Venta_Final"] - master["Costo_Unitario_USD"]) * master["Cantidad_Vendida"]
        - master["Costo_Envio"],
    )
    master["Margen_Porcentual"] = master["Margen_Utilidad_USD"] / master["Ingreso_Bruto"]
    master["Brecha_Entrega_Dias"] = master["Tiempo_Entrega_Real"] - master["Lead_Time_Dias_Clean"]

    ratio_soporte = (
        master.groupby("Categoria")["Ticket_Soporte_Abierto"].mean().rename("Ratio_Soporte_Categoria")
    )
    master = master.merge(ratio_soporte, on="Categoria", how="left")

    return master
