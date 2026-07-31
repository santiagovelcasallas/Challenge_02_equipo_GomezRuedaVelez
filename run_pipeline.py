"""
run_pipeline.py — Orquestador Fase 1 + Fase 2
==============================================
Ejecutar:  python3 run_pipeline.py
Genera en outputs/:
  - inventario_limpio.csv, transacciones_limpias.csv, feedback_limpio.csv
  - master_table.csv  (Sola Fuente de Verdad, Fase 2)
  - health_score_report.json  (formato que consume el dashboard)
  - health_score_trazable.json  (versión enriquecida con _fuente por métrica)
  - decisiones_limpieza.json   (formato que consume el dashboard)
  - decisiones_limpieza_trazable.json (versión con evidencia calculada + _fuente)
  - respuestas_5_preguntas.json
"""

import json, os, sys
import pandas as pd
from pathlib import Path

# En Windows la consola usa cp1252 por defecto y no puede imprimir "→", "≈" ni
# tildes: sin esto el resumen final revienta con UnicodeEncodeError aunque los
# artefactos ya se hayan escrito bien. En Linux/Streamlit Cloud no cambia nada.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src import audit
from src.cleaning_inventario  import clean_inventario,  integridad_inventario,  REGLAS_VALIDEZ as RV_INV
from src.cleaning_transacciones import clean_transacciones, integridad_transacciones, REGLAS_VALIDEZ as RV_TX
from src.cleaning_feedback    import clean_feedback,    integridad_feedback,    REGLAS_VALIDEZ as RV_FB
from src.integration import build_master_table
from src.analysis import (
    pregunta_1_fuga_capital, pregunta_2_crisis_logistica, pregunta_3_venta_invisible,
    pregunta_4_diagnostico_fidelidad, pregunta_5_riesgo_operativo,
)

DATA_DIR = "data"
OUT_DIR  = "outputs"


# ---------------------------------------------------------------------------
# Helpers: convertir la salida trazable al formato plano que espera el dash
# ---------------------------------------------------------------------------
def _health_para_dashboard(bloque: dict) -> dict:
    """Extrae las 5 claves que consume data_loader.load_health_score()."""
    dim = bloque["dimensiones"]
    return {
        "n_registros":  bloque["n_registros"],
        "completitud":  dim["completitud"],
        "validez":      dim["validez"],
        "unicidad":     dim["unicidad"],
        "health_score": bloque["health_score"],
    }


def _decisiones_para_dashboard(dec_list: list) -> dict:
    """
    Convierte la lista de decisiones (nueva estructura) a dict plano
    que consume el expander de decisiones en tab_auditoria.
    Incluye campo _fuente para trazabilidad directa desde el dashboard.
    """
    out = {}
    for d in dec_list:
        clave = d["campo"]
        out[clave + "__problema"]      = d["problema"]
        out[clave + "__accion"]        = d["accion"]
        out[clave + "__justificacion"] = d["justificacion"]
        out[clave + "__fuente"]        = d["_fuente"]
        # evidencia numérica clave (para que se vea en el expander)
        ev = d.get("evidencia", {})
        for k, v in ev.items():
            if not isinstance(v, dict):   # sólo escalares (legibles en tabla)
                out[f"{clave}__ev__{k}"] = v
    return out


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(f"{OUT_DIR}/charts", exist_ok=True)

    # ── Carga ──────────────────────────────────────────────────────────────
    inv_raw = pd.read_csv(f"{DATA_DIR}/inventario_central_v2.csv")
    tx_raw  = pd.read_csv(f"{DATA_DIR}/transacciones_logistica_v2.csv")
    fb_raw  = pd.read_csv(f"{DATA_DIR}/feedback_clientes_v2.csv")
    sku_maestro = set(inv_raw["SKU_ID"])

    cols_inv = list(inv_raw.columns)
    cols_tx  = list(tx_raw.columns)
    cols_fb  = list(fb_raw.columns)

    # ── Health Score ANTES (sobre datos crudos) ────────────────────────────
    antes_traz = {
        "inventario":    audit.auditar("inventario",    inv_raw, RV_INV, cols_inv),
        "transacciones": audit.auditar("transacciones", tx_raw,  RV_TX,  cols_tx),
        "feedback":      audit.auditar("feedback",      fb_raw,  RV_FB,  cols_fb),
    }

    # ── Limpieza (Fase 1) ──────────────────────────────────────────────────
    inv_clean, dec_inv = clean_inventario(inv_raw)
    tx_clean,  dec_tx  = clean_transacciones(tx_raw, sku_maestro)
    fb_clean,  dec_fb  = clean_feedback(fb_raw)

    # ── Health Score DESPUÉS (mismas reglas → delta honesto) ───────────────
    despues_traz = {
        "inventario":    audit.auditar("inventario",    inv_clean, RV_INV, cols_inv,
                                       integridad=integridad_inventario(inv_clean)),
        "transacciones": audit.auditar("transacciones", tx_clean,  RV_TX,  cols_tx,
                                       integridad=integridad_transacciones(tx_clean)),
        "feedback":      audit.auditar("feedback",      fb_clean,  RV_FB,  cols_fb,
                                       integridad=integridad_feedback(fb_raw, fb_clean)),
    }

    # ── Integración (Fase 2) ───────────────────────────────────────────────
    master = build_master_table(tx_clean, inv_clean, fb_clean)

    # ── Las 5 preguntas estratégicas ───────────────────────────────────────
    respuestas = {
        "pregunta_1_fuga_capital":        pregunta_1_fuga_capital(master),
        "pregunta_2_crisis_logistica":    pregunta_2_crisis_logistica(master),
        "pregunta_3_venta_invisible":     pregunta_3_venta_invisible(master),
        "pregunta_4_diagnostico_fidelidad": pregunta_4_diagnostico_fidelidad(master),
        "pregunta_5_riesgo_operativo":    pregunta_5_riesgo_operativo(master),
    }

    # ── Escritura de artefactos ────────────────────────────────────────────
    # 1. Formato que consume el dashboard (sin cambiar data_loader)
    health_dash = {
        "antes":   {ds: _health_para_dashboard(antes_traz[ds])   for ds in antes_traz},
        "despues": {ds: _health_para_dashboard(despues_traz[ds]) for ds in despues_traz},
    }
    Path(f"{OUT_DIR}/health_score_report.json").write_text(
        json.dumps(health_dash, ensure_ascii=False, indent=2), encoding="utf-8")

    dec_dash = {
        "inventario":    _decisiones_para_dashboard(dec_inv),
        "transacciones": _decisiones_para_dashboard(dec_tx),
        "feedback":      _decisiones_para_dashboard(dec_fb),
    }
    Path(f"{OUT_DIR}/decisiones_limpieza.json").write_text(
        json.dumps(dec_dash, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # 2. Versión enriquecida con trazabilidad completa (para PDF/auditoría)
    health_traz = {
        ds: {"antes": antes_traz[ds], "despues": despues_traz[ds],
             "delta": round(despues_traz[ds]["health_score"] - antes_traz[ds]["health_score"], 2)}
        for ds in ("inventario", "transacciones", "feedback")
    }
    Path(f"{OUT_DIR}/health_score_trazable.json").write_text(
        json.dumps(health_traz, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    dec_traz = {"_principio": "evidencia calculada en runtime; _fuente = función exacta.",
                "inventario": dec_inv, "transacciones": dec_tx, "feedback": dec_fb}
    Path(f"{OUT_DIR}/decisiones_limpieza_trazable.json").write_text(
        json.dumps(dec_traz, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # 3. Resto de artefactos
    inv_clean.to_csv(f"{OUT_DIR}/inventario_limpio.csv",       index=False)
    tx_clean.to_csv( f"{OUT_DIR}/transacciones_limpias.csv",   index=False)
    fb_clean.to_csv( f"{OUT_DIR}/feedback_limpio.csv",          index=False)
    master.to_csv(   f"{OUT_DIR}/master_table.csv",             index=False)
    Path(f"{OUT_DIR}/respuestas_5_preguntas.json").write_text(
        json.dumps(respuestas, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # ── Resumen consola ────────────────────────────────────────────────────
    print("=== HEALTH SCORE (antes → después) ===")
    for ds in ("inventario", "transacciones", "feedback"):
        a = health_traz[ds]["antes"]["health_score"]
        d = health_traz[ds]["despues"]["health_score"]
        print(f"  {ds:14s}: {a:.2f} → {d:.2f}  (Δ {health_traz[ds]['delta']:+.2f})")
    print(f"\nMaster table: {master.shape[0]} filas × {master.shape[1]} columnas")
    print(f"Artefactos en: {OUT_DIR}/")
    print("\nPipeline ejecutado correctamente.")


if __name__ == "__main__":
    main()
