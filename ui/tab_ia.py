"""Pestaña Insights de IA — Groq (Llama-3) sobre el resumen filtrado."""

import streamlit as st
from ui.components import section_tag, narrative, ledger_row
from services.groq_client import generar_recomendaciones, resumen_desde_filtro, DEFAULT_MODEL
from services.pdf_generator import generar_reporte_gerencial_bytes # <-- Importamos el generador

def render(df):
    section_tag("FASE 3 · INTELIGENCIA ARTIFICIAL (GROQ / LLAMA-3)", "info")
    st.markdown(
        "Genera recomendaciones estratégicas con IA a partir del **resumen estadístico "
        "de los datos filtrados actualmente** en la barra lateral (no se envían datos "
        "crudos de clientes, solo agregados numéricos)."
    )

    if df.empty:
        st.warning("No hay datos para el filtro seleccionado.")
        return

    resumen = resumen_desde_filtro(df)
    with st.expander("Ver resumen estadístico que se enviará al modelo"):
        st.json(resumen)

    st.caption(f"Modelo configurado: `{DEFAULT_MODEL}` · ver nota de vigencia en `services/groq_client.py`")

    if st.button("🧠 Generar recomendaciones estratégicas", type="primary"):
        with st.spinner("Consultando a Llama-3 en Groq..."):
            try:
                texto = generar_recomendaciones(resumen)
                narrative(texto.replace("\n", "<br>"))
            except RuntimeError as e:
                st.error(str(e))
                st.info(
                    "Configura tu clave así:\n\n"
                    "**Local**: crea `.streamlit/secrets.toml` con:\n"
                    "```toml\nGROQ_API_KEY = \"gsk_...\"\n```\n\n"
                    "**Streamlit Community Cloud**: panel de la app → *Settings* → *Secrets* → "
                    "pega la misma línea."
                )

    # =========================================================
    # NUEVA SECCIÓN: GENERACIÓN Y DESCARGA DE PDF BAJO DEMANDA
    # =========================================================
    st.write("---")
    st.markdown("### 📄 Exportar Reporte Ejecutivo")
    st.caption("Genera un documento PDF con los hallazgos gerenciales de las Fases 1 y 2, incluyendo todas las gráficas analíticas.")

    # 1. Botón de generación (solo ejecuta el script si se presiona)
    if st.button("Generar documento PDF"):
        with st.spinner("Compilando el reporte gerencial con gráficas..."):
            try:
                pdf_bytes = generar_reporte_gerencial_bytes()
                st.session_state['reporte_pdf_listo'] = pdf_bytes
            except Exception as e:
                st.error(f"Error al generar el documento: {e}")

    # 2. Botón de descarga (aparece dinámicamente si el PDF ya se procesó en esta sesión)
    if 'reporte_pdf_listo' in st.session_state:
        st.success("¡Documento generado con éxito!")
        
        st.download_button(
            label="📥 Descargar PDF (TechLogistics)",
            data=st.session_state['reporte_pdf_listo'],
            file_name="Reporte_Gerencial_TechLogistics.pdf",
            mime="application/pdf"
        )