"""
TechLogistics S.A.S. — Sala de Control de Datos
=================================================
Dashboard Streamlit (Fase 3).
El pipeline de limpieza (run_pipeline.py) se ejecuta automáticamente al
arrancar si los outputs no existen o si los datos crudos son más recientes
que el master_table.csv generado. Así funciona tanto en local como en
Streamlit Cloud sin pasos manuales.
"""

import streamlit as st
from pathlib import Path
from services.pdf_report import generate_board_report

# ── Auto-pipeline: corre si faltan outputs o los datos son más nuevos ──────
def _necesita_pipeline() -> bool:
    master = Path("outputs/master_table.csv")
    if not master.exists():
        return True
    # Si cualquier CSV crudo es más nuevo que el master, regenerar
    for csv in Path("data").glob("*.csv"):
        if csv.stat().st_mtime > master.stat().st_mtime:
            return True
    return False

if _necesita_pipeline():
    with st.spinner("⚙️ Ejecutando pipeline de limpieza e integración..."):
        import run_pipeline
        run_pipeline.main()
    st.cache_data.clear()

from ui.components import inject_css, register_plotly_theme, hero, ledger_row
from services.data_loader import load_master_table, load_health_score, load_decisiones, apply_filters
from ui import tab_auditoria, tab_tiempo, tab_operaciones, tab_cliente, tab_ia

st.set_page_config(
    page_title="TechLogistics · Sala de Control de Datos",
    page_icon="🛰️",
    layout="wide",
)

inject_css("assets/styles.css")
register_plotly_theme()

# --- Carga de datos (cacheada) ---
try:
    master = load_master_table()
    health = load_health_score()
    decisiones = load_decisiones()
except FileNotFoundError:
    st.error(
        "No se encontraron los archivos de `outputs/`. Corre primero "
        "`python3 run_pipeline.py` desde la raíz del repositorio."
    )
    st.stop()

# --- Sidebar: filtros ---
with st.sidebar:
    st.markdown("## 🎛️ Filtros")
    fecha_min, fecha_max = master["Fecha_Venta"].min(), master["Fecha_Venta"].max()
    fecha_range = st.date_input("Rango de fechas", value=(fecha_min, fecha_max),
                                 min_value=fecha_min, max_value=fecha_max)
    categorias = st.multiselect("Categoría", sorted(master["Categoria"].unique()))
    bodegas = st.multiselect("Bodega de origen", sorted(master["Bodega_Origen"].unique()))
    canales = st.multiselect("Canal de venta", sorted(master["Canal_Venta"].unique()))

    st.write("")
    if st.button("🔄 Refrescar análisis"):
        st.cache_data.clear()
        st.rerun()

    st.write("---")
    st.caption(
        "TechLogistics S.A.S. (ficticio) · Challenge 02 · Fundamentos en "
        "Ciencia de Datos · Universidad EAFIT"
    )

df_filtrado = apply_filters(master, fecha_range, categorias, bodegas, canales)


# ... Tu código existente del sidebar ...

st.write("---")
st.markdown("## 📄 Exportar")

# Caché para que no recalcule el PDF en cada mínimo cambio de UI, solo si cambia el filtro
@st.cache_data(show_spinner=False)
def get_pdf(dataframe):
    return generate_board_report(dataframe)

# Genera el documento usando la tabla maestra filtrada que ya posees
with st.spinner("Generando documento para junta..."):
    pdf_bytes = get_pdf(df_filtrado)
    
st.download_button(
    label="📥 Descargar Informe PDF",
    data=pdf_bytes,
    file_name="TechLogistics_Informe_Junta.pdf",
    mime="application/pdf",
    type="primary"
)


# --- Hero ---
hero(
    eyebrow="CONSULTORÍA SENIOR · DECISION SUPPORT SYSTEM",
    title="TechLogistics — Sala de Control de Datos",
    subtitle=(
        "De tres sistemas que no se hablan entre sí, a una sola fuente de verdad: "
        "auditoría, operaciones, cliente e inteligencia artificial en un solo lugar."
    ),
)

ledger_row([
    {"label": "Transacciones en el filtro", "value": f"{len(df_filtrado):,}",
     "context": f"de {len(master):,} totales", "severity": "info"},
    {"label": "Ingreso bruto filtrado", "value": f"USD {df_filtrado['Ingreso_Bruto'].sum():,.0f}", "severity": "info"},
    {"label": "% Venta fantasma", "value": f"{df_filtrado['Es_Venta_Fantasma'].mean()*100:.1f}%",
     "severity": "advertencia"},
    {"label": "Health Score promedio", "value": f"{sum(health['despues'][d]['health_score'] for d in health['despues'])/3:.1f}",
     "context": "post-limpieza, los 3 datasets", "severity": "saludable"},
])

st.write("")
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Auditoría", "📈 Serie de Tiempo", "🚚 Operaciones", "👥 Cliente", "🧠 Insights de IA"
])

with tab1:
    tab_auditoria.render(health, decisiones)
with tab2:
    tab_tiempo.render(df_filtrado, master)
with tab3:
    tab_operaciones.render(df_filtrado)
with tab4:
    tab_cliente.render(df_filtrado)
with tab5:
    tab_ia.render(df_filtrado)
