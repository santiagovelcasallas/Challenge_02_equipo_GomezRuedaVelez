"""
cleaning_feedback.py — Limpieza de feedback_clientes_v2.csv
===========================================================
Misma filosofía: evidencia calculada + _fuente por decisión.

Hallazgo auditado y corregido frente a la versión anterior: el reto habla de
"duplicados intencionales", pero la evidencia muestra 0 filas idénticas. Lo real
es una COLISIÓN de Feedback_ID (mismo ID, contenido distinto). No se borra nada;
se genera una llave sustituta. Esto se reporta en integridad, NO como unicidad.
"""

import pandas as pd
import numpy as np


def clean_feedback(raw: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    df = raw.copy().reset_index(drop=True)
    dec = []

    # --- 1. Colisión de Feedback_ID (no son duplicados) -> llave sustituta ---
    dup_full = int(df.duplicated().sum())
    ids_colision = int((df["Feedback_ID"].value_counts() > 1).sum())
    filas_colision = int(df["Feedback_ID"].duplicated(keep=False).sum())
    # ¿cuántos grupos colisionados tienen contenido IDÉNTICO? (=duplicado real)
    dupids = df["Feedback_ID"].value_counts()
    dupids = dupids[dupids > 1].index
    sub = df[df["Feedback_ID"].isin(dupids)]
    grupos_identicos = int(sub.groupby("Feedback_ID").apply(
        lambda g: g.drop_duplicates().shape[0] == 1, include_groups=False).sum())
    df["Feedback_UID"] = ["FBK-" + str(i).zfill(6) for i in range(len(df))]
    dec.append({
        "campo": "Feedback_ID",
        "problema": "IDs repetidos (el reto los llama 'duplicados intencionales')",
        "evidencia": {"duplicados_fila_completa": dup_full,
                      "ids_que_colisionan": ids_colision, "filas_involucradas": filas_colision,
                      "grupos_con_contenido_identico": grupos_identicos},
        "accion": "generar llave sustituta 'Feedback_UID'; NO borrar filas",
        "justificacion": (f"0 filas idénticas y {grupos_identicos} grupos con contenido "
                          "igual: NO son eventos duplicados sino colisión de llave. Borrarlos "
                          "destruiría observaciones reales y distintas de clientes."),
        "_fuente": "cleaning_feedback.clean_feedback#1",
    })

    # --- 2. Rating_Producto: centinela 99 sobre escala 1-5 ---
    n99 = int((df["Rating_Producto"] == 99).sum())
    med_r = float(df.loc[df["Rating_Producto"] != 99, "Rating_Producto"].median())
    df.loc[df["Rating_Producto"] == 99, "Rating_Producto"] = np.nan
    df["Rating_Producto"] = df["Rating_Producto"].fillna(med_r)
    dec.append({
        "campo": "Rating_Producto",
        "problema": "valor 99 en escala 1-5 (centinela)",
        "evidencia": {"n_99": n99, "pct": round(n99 / len(df) * 100, 2), "mediana": med_r},
        "accion": "99 -> nulo -> imputar MEDIANA",
        "justificacion": "variable ORDINAL: la MEDIANA es el estadístico apropiado (no la media).",
        "_fuente": "cleaning_feedback.clean_feedback#2",
    })

    # --- 3. Edad_Cliente: edades imposibles ---
    n_edad = int((df["Edad_Cliente"] > 100).sum())
    mx_edad = int(df["Edad_Cliente"].max())
    skew_ed = round(float(df.loc[df["Edad_Cliente"] <= 100, "Edad_Cliente"].skew()), 3)
    med_ed = float(df.loc[df["Edad_Cliente"] <= 100, "Edad_Cliente"].median())
    df.loc[df["Edad_Cliente"] > 100, "Edad_Cliente"] = np.nan
    df["Edad_Cliente"] = df["Edad_Cliente"].fillna(med_ed)
    dec.append({
        "campo": "Edad_Cliente",
        "problema": "edades imposibles (>100, hasta 195)",
        "evidencia": {"n_invalidas": n_edad, "edad_max_original": mx_edad,
                      "skew_validas": skew_ed, "mediana": med_ed},
        "accion": ">100 -> nulo -> imputar MEDIANA",
        "justificacion": f"skew={skew_ed}; MEDIANA robusta a extremos residuales y a asimetría.",
        "_fuente": "cleaning_feedback.clean_feedback#3",
    })

    # --- 4. Comentario_Texto: unificar marcadores de ausencia ---
    n_guion = int((df["Comentario_Texto"] == "---").sum())
    n_nulo = int(df["Comentario_Texto"].isnull().sum())
    df["Comentario_Texto"] = df["Comentario_Texto"].replace("---", np.nan).fillna("Sin Comentario")
    dec.append({
        "campo": "Comentario_Texto",
        "problema": "dos marcadores de ausencia distintos ('---' y nulo real)",
        "evidencia": {"marcador_guion": n_guion, "nulo_real": n_nulo},
        "accion": "unificar en 'Sin Comentario'",
        "justificacion": "campo cualitativo: no hay forma válida de inferir texto faltante.",
        "_fuente": "cleaning_feedback.clean_feedback#4",
    })

    # --- 5. Recomienda_Marca: normalizar + nulo explícito ---
    n_nul_rec = int(df["Recomienda_Marca"].isnull().sum())
    df["Recomienda_Marca"] = df["Recomienda_Marca"].replace(
        {"SI": "Sí", "NO": "No", "Maybe": "Tal vez"}).fillna("Sin Respuesta")
    dec.append({
        "campo": "Recomienda_Marca",
        "problema": "codificación mixta (SI/NO/Maybe) y no respuesta",
        "evidencia": {"sin_respuesta": n_nul_rec, "pct": round(n_nul_rec / len(df) * 100, 2)},
        "accion": "normalizar a Sí/No/Tal vez; nulo -> 'Sin Respuesta'",
        "justificacion": ("no se colapsa 'Tal vez' en Sí/No (sesgaría la lealtad) ni se imputa "
                          "el nulo (fabricaría una postura del cliente)."),
        "_fuente": "cleaning_feedback.clean_feedback#5",
    })

    # --- 6. Ticket_Soporte_Abierto: normalizar a booleano ---
    df["Ticket_Soporte_Abierto"] = df["Ticket_Soporte_Abierto"].replace(
        {"Sí": True, "1": True, 1: True, "No": False, "0": False, 0: False}).astype(bool)
    dec.append({
        "campo": "Ticket_Soporte_Abierto",
        "problema": "codificación mixta (Sí/No/1/0)",
        "evidencia": {"n_true": int(df["Ticket_Soporte_Abierto"].sum())},
        "accion": "normalizar a booleano True/False",
        "justificacion": "unifica la representación de una variable binaria.",
        "_fuente": "cleaning_feedback.clean_feedback#6",
    })

    # --- 7. Satisfaccion_NPS: categorización estándar (no reescalado) ---
    rango = (round(float(df["Satisfaccion_NPS"].min()), 1),
             round(float(df["Satisfaccion_NPS"].max()), 1))
    df["NPS_Categoria"] = pd.cut(df["Satisfaccion_NPS"], bins=[-101, 0, 50, 101],
                                 labels=["Detractor", "Pasivo", "Promotor"], right=False)
    dec.append({
        "campo": "Satisfaccion_NPS",
        "problema": "requiere interpretación (categorización), no reescalado",
        "evidencia": {"rango_observado": rango},
        "accion": "derivar 'NPS_Categoria' (Detractor<0, Pasivo 0-49, Promotor>=50)",
        "justificacion": (f"el valor ya está en escala estándar {rango} (-100..100): no se "
                          "reescala. La 'normalización' del diccionario se interpreta como la "
                          "categorización de negocio, sin alterar el número original."),
        "_fuente": "cleaning_feedback.clean_feedback#7",
    })

    return df, dec


def integridad_feedback(raw: pd.DataFrame, clean: pd.DataFrame) -> dict:
    n = len(clean)
    ids_col = int((raw["Feedback_ID"].value_counts() > 1).sum())
    sin_com = int((clean["Comentario_Texto"] == "Sin Comentario").sum())
    sin_resp = int((clean["Recomienda_Marca"] == "Sin Respuesta").sum())
    return {
        "colision_feedback_id": {"ids": ids_col,
                                 "filas": int(raw["Feedback_ID"].duplicated(keep=False).sum())},
        "comentario_ausente": {"n": sin_com, "pct": round(sin_com / n * 100, 2)},
        "recomendacion_sin_respuesta": {"n": sin_resp, "pct": round(sin_resp / n * 100, 2)},
    }


# Reglas de validez: valores imposibles / fuera de rango (defectos de dato).
REGLAS_VALIDEZ = {
    "rating_producto_fuera_1_5": lambda d: ~d["Rating_Producto"].between(1, 5),
    "rating_logistica_fuera_1_5": lambda d: ~d["Rating_Logistica"].between(1, 5),
    "edad_imposible": lambda d: ~d["Edad_Cliente"].between(18, 100),
    "nps_fuera_rango": lambda d: ~d["Satisfaccion_NPS"].between(-100, 100),
}
