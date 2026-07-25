"""
Pipeline principal — Fase 1 (Auditoría) y Fase 2 (Integración)
================================================================
Ejecutar: python3 run_pipeline.py
Genera en outputs/:
  - inventario_limpio.csv, transacciones_limpias.csv, feedback_limpio.csv
  - master_table.csv (Sola Fuente de Verdad, Fase 2)
  - health_score_report.json (antes/después por dataset)
  - decisiones_limpieza.json (log de cada decisión tomada)
"""

import json
import pandas as pd
from src.cleaning_inventario import clean_inventario
from src.cleaning_transacciones import clean_transacciones
from src.cleaning_feedback import clean_feedback
from src.health_score import (
    health_inventario_raw, health_inventario_clean,
    health_transacciones_raw, health_transacciones_clean,
    health_feedback_raw, health_feedback_clean,
)
from src.integration import build_master_table
from src.analysis import (
    pregunta_1_fuga_capital, pregunta_2_crisis_logistica, pregunta_3_venta_invisible,
    pregunta_4_diagnostico_fidelidad, pregunta_5_riesgo_operativo,
)

DATA_DIR = "data"
OUT_DIR = "outputs"


def main():
    # --- Carga de datos crudos ---
    inv_raw = pd.read_csv(f"{DATA_DIR}/inventario_central_v2.csv")
    tx_raw = pd.read_csv(f"{DATA_DIR}/transacciones_logistica_v2.csv")
    fb_raw = pd.read_csv(f"{DATA_DIR}/feedback_clientes_v2.csv")

    sku_maestro = set(inv_raw["SKU_ID"])

    # --- Health Score ANTES ---
    health_before = {
        "inventario": health_inventario_raw(inv_raw),
        "transacciones": health_transacciones_raw(tx_raw, sku_maestro),
        "feedback": health_feedback_raw(fb_raw),
    }

    # --- Limpieza (Fase 1) ---
    inv_clean, log_inv = clean_inventario(inv_raw)
    tx_clean, log_tx = clean_transacciones(tx_raw, sku_maestro)
    fb_clean, log_fb = clean_feedback(fb_raw)

    # --- Health Score DESPUÉS ---
    health_after = {
        "inventario": health_inventario_clean(inv_clean),
        "transacciones": health_transacciones_clean(tx_clean),
        "feedback": health_feedback_clean(fb_clean),
    }

    # --- Integración (Fase 2) ---
    master = build_master_table(tx_clean, inv_clean, fb_clean)

    # --- Guardar resultados ---
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(f"{OUT_DIR}/charts", exist_ok=True)

    # --- Fase 2/3: Las 5 preguntas estratégicas ---
    respuestas = {
        "pregunta_1_fuga_capital": pregunta_1_fuga_capital(master),
        "pregunta_2_crisis_logistica": pregunta_2_crisis_logistica(master),
        "pregunta_3_venta_invisible": pregunta_3_venta_invisible(master),
        "pregunta_4_diagnostico_fidelidad": pregunta_4_diagnostico_fidelidad(master),
        "pregunta_5_riesgo_operativo": pregunta_5_riesgo_operativo(master),
    }
    with open(f"{OUT_DIR}/respuestas_5_preguntas.json", "w", encoding="utf-8") as f:
        json.dump(respuestas, f, indent=2, ensure_ascii=False, default=str)
    inv_clean.to_csv(f"{OUT_DIR}/inventario_limpio.csv", index=False)
    tx_clean.to_csv(f"{OUT_DIR}/transacciones_limpias.csv", index=False)
    fb_clean.to_csv(f"{OUT_DIR}/feedback_limpio.csv", index=False)
    master.to_csv(f"{OUT_DIR}/master_table.csv", index=False)

    with open(f"{OUT_DIR}/health_score_report.json", "w", encoding="utf-8") as f:
        json.dump({"antes": health_before, "despues": health_after}, f, indent=2, ensure_ascii=False)

    with open(f"{OUT_DIR}/decisiones_limpieza.json", "w", encoding="utf-8") as f:
        json.dump({"inventario": log_inv, "transacciones": log_tx, "feedback": log_fb}, f, indent=2, ensure_ascii=False, default=str)

    print("=== HEALTH SCORE ANTES ===")
    print(json.dumps(health_before, indent=2, ensure_ascii=False))
    print("\n=== HEALTH SCORE DESPUÉS ===")
    print(json.dumps(health_after, indent=2, ensure_ascii=False))
    print(f"\nMaster table: {master.shape[0]} filas x {master.shape[1]} columnas")
    print("Pipeline ejecutado correctamente. Resultados en /outputs")


if __name__ == "__main__":
    main()
