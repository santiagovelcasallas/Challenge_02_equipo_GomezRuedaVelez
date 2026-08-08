"""Pestaña Insights de IA — Groq (Llama-3) y Descarga de Informe Ejecutivo Estático (PDF)."""

import streamlit as st
from pathlib import Path
from ui.components import section_tag, narrative
from services.groq_client import generar_recomendaciones, resumen_desde_filtro, DEFAULT_MODEL

def render(df):
    section_tag("FASE 3 · INTELIGENCIA ARTIFICIAL E INFORMES", "info")
    st.markdown(
        "Genera recomendaciones estratégicas con IA a partir del **resumen estadístico "
        "de los datos filtrados actualmente**. También puedes descargar el informe ejecutivo oficial en formato PDF."
    )

    if df.empty:
        st.warning("No hay datos para el filtro seleccionado.")
        return

    resumen = resumen_desde_filtro(df)
    with st.expander("Ver resumen estadístico que se enviará al modelo"):
        st.json(resumen)

    st.caption(f"Modelo configurado en ambiente: `{DEFAULT_MODEL}`")

    # Recuperar texto generado si ya existe en la memoria de la sesión
    ai_text_actual = st.session_state.get('ai_insights_text', None)

    if st.button("🧠 Generar recomendaciones estratégicas", type="primary"):
        with st.spinner("Consultando a Llama-3 en Groq..."):
            try:
                ai_text_actual = generar_recomendaciones(resumen)
                st.session_state['ai_insights_text'] = ai_text_actual
            except RuntimeError as e:
                st.error(str(e))

    # Mostrar la narrativa de la IA en la interfaz gráfica si existe
    if ai_text_actual:
        narrative(ai_text_actual.replace("\n", "<br>"))

    st.write("---")
    st.markdown("### 📄 Descarga de Informe Ejecutivo para la Junta Directiva (PDF)")
    st.caption("Obtén el documento gerencial oficial estático almacenado en el sistema.")

    # Ruta del archivo PDF estático (puedes ajustar el nombre si incluye extensión .pdf)
    pdf_path = Path("outputs/Technologistics_Informe.pdf")
    
    # Si la ruta que pasas no tiene la extensión explícita en tu disco, asegúrate de que coincida:
    if not pdf_path.exists():
        # Intentar buscar alternativa sin extensión si fuera el caso
        pdf_path_alt = Path("outputs/Technologistics_Informe")
        if pdf_path_alt.exists():
            pdf_path = pdf_path_alt

    if pdf_path.exists():
        try:
            pdf_bytes = pdf_path.read_bytes()
            st.success("¡Informe ejecutivo disponible para descarga!")
            st.download_button(
                label="📥 Descargar Informe Ejecutivo (PDF)",
                data=pdf_bytes,
                file_name="Informe_Ejecutivo_Technologistics.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error al leer el archivo PDF estático: {e}")
    else:
        st.error(f"⚠️ El archivo PDF estático no se encuentra en la ruta esperada: `{pdf_path}`. Asegúrate de ubicarlo en la carpeta outputs/.")