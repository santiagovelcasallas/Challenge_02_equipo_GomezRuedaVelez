'''"""Pestaña Insights de IA — Groq (Llama-3) sobre el resumen filtrado."""

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
        )'''
        
        
"""Pestaña Insights de IA — Groq (Llama-3) y Generador Dinámico de PDF."""

import streamlit as st
from ui.components import section_tag, narrative
from services.groq_client import generar_recomendaciones, resumen_desde_filtro, DEFAULT_MODEL
from services.pdf_generator import generar_pdf_dinamico

def render(df):
    section_tag("FASE 3 · INTELIGENCIA ARTIFICIAL E INFORMES", "info")
    st.markdown(
        "Genera recomendaciones estratégicas con IA a partir del **resumen estadístico "
        "de los datos filtrados actualmente**. También puedes exportar el informe completo a PDF."
    )

    if df.empty:
        st.warning("No hay datos para el filtro seleccionado.")
        return

    resumen = resumen_desde_filtro(df)
    with st.expander("Ver resumen estadístico que se enviará al modelo"):
        st.json(resumen)

    st.caption(f"Modelo configurado: `{DEFAULT_MODEL}`")

    # Recuperar texto generado si ya existe en la sesión
    ai_text_actual = st.session_state.get('ai_insights_text', None)

    if st.button("🧠 Generar recomendaciones estratégicas", type="primary"):
        with st.spinner("Consultando a Llama-3 en Groq..."):
            try:
                ai_text_actual = generar_recomendaciones(resumen)
                st.session_state['ai_insights_text'] = ai_text_actual
            except RuntimeError as e:
                st.error(str(e))

    # Mostrar la narrativa de la IA en la UI si existe
    if ai_text_actual:
        narrative(ai_text_actual.replace("\n", "<br>"))

    st.write("---")
    st.markdown("### 📄 Exportar Reporte para la Junta Directiva (PDF)")
    st.caption("Consolida las 5 gráficas de respuestas estratégicas y las recomendaciones de la IA en un solo documento.")

    if st.button("Generar documento PDF"):
        with st.spinner("Construyendo documento..."):
            try:
                texto_para_pdf = ai_text_actual
                
                # --- AUTO-TRIGGER Llama 3 si no se había generado antes ---
                if not texto_para_pdf:
                    st.info("Obteniendo recomendaciones estratégicas de la IA para anexar al reporte...")
                    texto_para_pdf = generar_recomendaciones(resumen)
                    st.session_state['ai_insights_text'] = texto_para_pdf # Lo guardamos para la UI
                
                st.info("Renderizando gráficas dinámicas y ensamblando PDF...")
                pdf_bytes = generar_pdf_dinamico(df, texto_para_pdf)
                st.session_state['reporte_pdf_listo'] = pdf_bytes
                
            except RuntimeError as api_error:
                # Manejo de error específico de la API de Groq
                st.error(f"Fallo en la comunicación con IA: {api_error}")
                st.stop()
            except Exception as e:
                # Manejo de error general (Matplotlib, xhtml2pdf, Pandas)
                st.error(f"Error inesperado al generar el documento: {e}")
                st.stop()

    # Botón de descarga
    if 'reporte_pdf_listo' in st.session_state:
        st.success("¡Documento ensamblado con éxito!")
        st.download_button(
            label="📥 Descargar Reporte Ejecutivo (PDF)",
            data=st.session_state['reporte_pdf_listo'],
            file_name="Reporte_Estrategico_TechLogistics.pdf",
            mime="application/pdf"
        )