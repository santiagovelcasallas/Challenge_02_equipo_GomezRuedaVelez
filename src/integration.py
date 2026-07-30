"""
integration.py — Fase 2: Una Sola Fuente de Verdad
====================================================

ESTRATEGIA DE UNIÓN (documentada, no implícita)
------------------------------------------------
1. Base = transacciones limpias (10.000 filas). Ninguna venta se descarta.
2. LEFT JOIN con inventario por SKU_ID: aporta Categoria, Costo, Stock,
   Bodega, Lead Time. SKUs fantasma quedan con NaN / 'Sin Catálogo'.
3. LEFT JOIN con feedback AGREGADO a nivel Transaccion_ID (1:N → promedio):
   aporta Rating, NPS y bandera de ticket.

VARIABLES DERIVADAS (mínimo 3 exigidas; se entregan 6)
------------------------------------------------------
Todas incluyen _fuente citable.

1. Ingreso_Bruto = Precio_Venta_Final × Cantidad_Vendida
   _fuente: integration.build_master_table#FE1

2. Margen_Utilidad_USD = (Precio - Costo) × Cantidad - Costo_Envio
   NaN en ventas fantasma (no hay costo de referencia → no se inventa margen).
   ADVERTENCIA: el SKU PROD-1500 (Costo=$850.000, marcado Costo_Atipico=True)
   produce márgenes extremos que distorsionan el agregado global. Las funciones
   de análisis deben reportar dos cifras: con y sin el outlier.
   _fuente: integration.build_master_table#FE2

3. Margen_Porcentual = Margen_Utilidad_USD / Ingreso_Bruto
   _fuente: integration.build_master_table#FE3

4. Brecha_Entrega_Dias = Tiempo_Entrega_Real - Lead_Time_Dias_Clean
   APROXIMACIÓN documentada: el diccionario de datos no define una fecha
   prometida al cliente; se usa el lead time del proveedor como proxy del
   tiempo esperado. Positivo = más lento de lo esperado.
   _fuente: integration.build_master_table#FE4

5. Ratio_Soporte_Categoria = % de transacciones con ticket por Categoria
   _fuente: integration.build_master_table#FE5

6. Dias_Desde_Ultima_Revision: ya viene de cleaning_inventario (derivada
   en Fase 1, se propaga vía JOIN).
   _fuente: cleaning_inventario.clean_inventario#6
"""

import pandas as pd
import numpy as np


def build_master_table(
    tx_clean: pd.DataFrame,
    inv_clean: pd.DataFrame,
    fb_clean: pd.DataFrame,
) -> pd.DataFrame:

    # ── JOIN 1: transacciones ← inventario ────────────────────────────────
    inv_cols = [
        "SKU_ID", "Categoria", "Stock_Actual", "Costo_Unitario_USD",
        "Costo_Atipico", "Bodega_Origen", "Lead_Time_Dias_Clean",
        "Ultima_Revision", "Dias_Desde_Ultima_Revision",
    ]
    master = tx_clean.merge(inv_clean[inv_cols], on="SKU_ID", how="left")
    master["Categoria"]    = master["Categoria"].fillna("Sin Catálogo")
    master["Bodega_Origen"] = master["Bodega_Origen"].fillna("Sin Bodega")
    master["Costo_Atipico"] = master["Costo_Atipico"].fillna(False)

    # ── JOIN 2: transacciones ← feedback (agregado 1:N) ───────────────────
    fb_agg = (
        fb_clean.groupby("Transaccion_ID")
        .agg(
            Rating_Producto_Prom  = ("Rating_Producto",      "mean"),
            Rating_Logistica_Prom = ("Rating_Logistica",     "mean"),
            Satisfaccion_NPS_Prom = ("Satisfaccion_NPS",     "mean"),
            Ticket_Soporte_Abierto= ("Ticket_Soporte_Abierto","any"),
            N_Feedbacks           = ("Feedback_UID",          "count"),
        )
        .reset_index()
    )
    master = master.merge(fb_agg, on="Transaccion_ID", how="left")
    master["Ticket_Soporte_Abierto"] = master["Ticket_Soporte_Abierto"].fillna(False)
    master["N_Feedbacks"]            = master["N_Feedbacks"].fillna(0).astype(int)

    # ── Feature Engineering ───────────────────────────────────────────────
    # FE1: Ingreso Bruto
    master["Ingreso_Bruto"] = (
        master["Precio_Venta_Final"] * master["Cantidad_Vendida"]
    )  # _fuente: integration.build_master_table#FE1

    # FE2: Margen de Utilidad (NaN en fantasmas; outlier preservado con flag)
    master["Margen_Utilidad_USD"] = np.where(
        master["Es_Venta_Fantasma"],
        np.nan,
        (master["Precio_Venta_Final"] - master["Costo_Unitario_USD"])
        * master["Cantidad_Vendida"]
        - master["Costo_Envio"],
    )  # _fuente: integration.build_master_table#FE2

    # FE3: Margen Porcentual
    master["Margen_Porcentual"] = (
        master["Margen_Utilidad_USD"] / master["Ingreso_Bruto"]
    )  # _fuente: integration.build_master_table#FE3

    # FE4: Brecha de entrega (proxy documentado)
    master["Brecha_Entrega_Dias"] = (
        master["Tiempo_Entrega_Real"] - master["Lead_Time_Dias_Clean"]
    )  # _fuente: integration.build_master_table#FE4

    # FE5: Ratio de soporte por categoría
    ratio = (
        master.groupby("Categoria")["Ticket_Soporte_Abierto"]
        .mean()
        .rename("Ratio_Soporte_Categoria")
    )
    master = master.merge(ratio, on="Categoria", how="left")
    # _fuente: integration.build_master_table#FE5

    return master
