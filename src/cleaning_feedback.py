"""
Limpieza de feedback_clientes_v2.csv
=====================================

Decisiones de limpieza documentadas (Fase 1 - Auditoría de Calidad):

1. "Registros duplicados intencionales" (mencionados en el reto): se
   auditó exhaustivamente y NO existen duplicados de fila completa (0),
   ni grupos de filas con contenido idéntico agrupando por Transaccion_ID
   (se muestrearon 400 grupos con Transaccion_ID repetido y en el 100% de
   los casos el contenido —rating, comentario, edad, NPS— era distinto).
   Lo que sí se encontró es una COLISIÓN DE LLAVE PRIMARIA: 469 valores de
   Feedback_ID están asignados a 2+ filas con contenido completamente
   distinto (distinta Transaccion_ID, distinto rating, etc.). Es decir, no
   son eventos duplicados sino un defecto de generación/exportación de IDs.
   Decisión ética: NO se eliminan estas filas (blanquear "duplicados" aquí
   destruiría observaciones reales y distintas de clientes), en su lugar se
   genera una llave sustituta única (Feedback_UID) y se documenta el hallazgo
   como hallazgo de auditoría, no como limpieza de duplicados.

2. Rating_Producto: 30 registros (0.67%) con valor 99 sobre una escala 1-5.
   Mismo patrón de código centinela que en otros datasets. Se trata como
   nulo y se imputa con la MEDIANA (3), apropiada para una variable ordinal.

3. Edad_Cliente: 23 registros (0.51%) con edades imposibles (>100, hasta
   195 años). Se tratan como nulo y se imputan con la mediana (50 años),
   preferida sobre la media por tratarse de una variable con posible
   asimetría y por ser más robusta a valores extremos residuales.

4. Comentario_Texto: se unifican los marcadores de ausencia de dato
   ("---" y nulo real) en una sola categoría "Sin Comentario". No se
   imputa un comentario porque el campo es cualitativo y no existe forma
   estadísticamente válida de inferir texto faltante.

5. Recomienda_Marca: variable ternaria (Sí/No/Tal vez) con 24.87% de no
   respuesta. Se conserva "Tal vez" como categoría propia (no se colapsa
   en Sí/No, lo que sesgaría el indicador de lealtad) y el nulo se marca
   como "Sin Respuesta" en vez de imputarse.

6. Ticket_Soporte_Abierto: codificación mixta (Sí/No/1/0) -> se normaliza a
   booleano (True/False).

7. Satisfaccion_NPS: el valor ya está en la escala estándar -100 a +100
   (no requiere reescalado). La "normalización" que pide el diccionario de
   datos se interpreta como la categorización estándar de negocio:
     - Promotor: score >= 50
     - Pasivo:   0 <= score < 50
     - Detractor: score < 0
   Este mapeo se agrega como columna derivada NPS_Categoria sin alterar el
   valor numérico original.
"""

import pandas as pd
import numpy as np


def clean_feedback(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpia feedback_clientes_v2 y devuelve (df_limpio, log_de_decisiones)."""
    df = raw.copy()
    log = {}

    # --- 1. Colisión de Feedback_ID: llave sustituta única ---
    dup_id = df["Feedback_ID"].duplicated(keep=False).sum()
    log["feedback_id_colisiones_detectadas"] = int(dup_id)
    log["duplicados_fila_completa"] = int(df.duplicated().sum())
    df = df.reset_index(drop=True)
    df["Feedback_UID"] = ["FBK-" + str(i).zfill(6) for i in range(len(df))]

    # --- 2. Rating_Producto: 99 centinela -> nulo -> imputar mediana ---
    centinela_rating = (df["Rating_Producto"] == 99).sum()
    df.loc[df["Rating_Producto"] == 99, "Rating_Producto"] = np.nan
    df["Rating_Producto"] = df["Rating_Producto"].fillna(df["Rating_Producto"].median())
    log["rating_producto_centinela_99_tratados"] = int(centinela_rating)

    # --- 3. Edad_Cliente: >100 -> nulo -> imputar mediana ---
    edad_invalida = (df["Edad_Cliente"] > 100).sum()
    df.loc[df["Edad_Cliente"] > 100, "Edad_Cliente"] = np.nan
    df["Edad_Cliente"] = df["Edad_Cliente"].fillna(df["Edad_Cliente"].median())
    log["edad_cliente_invalidas_tratadas"] = int(edad_invalida)

    # --- 4. Comentario_Texto: unificar marcadores de ausencia ---
    df["Comentario_Texto"] = df["Comentario_Texto"].replace("---", np.nan).fillna("Sin Comentario")

    # --- 5. Recomienda_Marca: mapear + marcar nulo explícito ---
    df["Recomienda_Marca"] = df["Recomienda_Marca"].replace(
        {"SI": "Sí", "NO": "No", "Maybe": "Tal vez"}
    ).fillna("Sin Respuesta")

    # --- 6. Ticket_Soporte_Abierto: normalizar a booleano ---
    df["Ticket_Soporte_Abierto"] = df["Ticket_Soporte_Abierto"].replace(
        {"Sí": True, "1": True, 1: True, "No": False, "0": False, 0: False}
    ).astype(bool)

    # --- 7. Satisfaccion_NPS: categorización estándar ---
    def _nps_bucket(score):
        if score >= 50:
            return "Promotor"
        elif score >= 0:
            return "Pasivo"
        return "Detractor"

    df["NPS_Categoria"] = df["Satisfaccion_NPS"].apply(_nps_bucket)

    return df, log
