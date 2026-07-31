"""
generar_informe.py — Documento de Hallazgos (PDF) versionado en el repo
=======================================================================
Ejecutar:  python3 generar_informe.py

El reto exige un PDF **dentro del repo** que actúe como informe de consultoría.
El dashboard ya permite exportar ese PDF desde la pestaña "Insights de IA",
pero esa ruta requiere una GROQ_API_KEY; este script genera el mismo documento
de forma reproducible y sin depender de la IA, para que quede versionado y
cualquiera pueda abrirlo tras clonar el repositorio.

Usa exactamente el mismo generador que el dashboard
(services.pdf_generator.generar_pdf_dinamico), así que el informe versionado y
el que descarga el usuario no pueden divergir.

Requisito previo: haber corrido `python3 run_pipeline.py` (necesita
outputs/master_table.csv).
"""

import sys
from pathlib import Path

import pandas as pd

from services.pdf_generator import generar_pdf_dinamico

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MASTER = Path("outputs/master_table.csv")
SALIDA = Path("Informe_Hallazgos_TechLogistics.pdf")


def main() -> None:
    if not MASTER.exists():
        raise SystemExit(
            f"No se encontró {MASTER}. Corre primero: python3 run_pipeline.py"
        )

    df = pd.read_csv(MASTER)
    df["Fecha_Venta"] = pd.to_datetime(df["Fecha_Venta"])

    # ai_insights vacío -> el informe se arma solo con evidencia calculada.
    pdf_bytes = generar_pdf_dinamico(df, "")
    SALIDA.write_bytes(pdf_bytes)

    print(f"Informe generado: {SALIDA}  ({len(pdf_bytes):,} bytes)")
    print(f"Transacciones analizadas: {len(df):,}")


if __name__ == "__main__":
    main()
