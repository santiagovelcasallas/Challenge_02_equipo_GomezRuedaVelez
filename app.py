"""
TechLogistics S.A.S. — Sala de Control de Datos
=================================================
Dashboard Streamlit (Fase 3). Requiere haber corrido antes `run_pipeline.py`
para generar los archivos en outputs/.

Ejecutar: streamlit run app.py
"""

import streamlit as st
from ui.components import inject_css, register_plotly_theme, hero, ledger_row
from services.data_loader import load_master_table, load_health_score, load_decisiones, apply_filters
from ui import tab_auditoria, tab_operaciones, tab_cliente, tab_ia

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
tab1, tab2, tab3, tab4 = st.tabs(["📋 Auditoría", "🚚 Operaciones", "👥 Cliente", "🧠 Insights de IA"])

with tab1:
    tab_auditoria.render(health, decisiones)
with tab2:
    tab_operaciones.render(df_filtrado)
with tab3:
    tab_cliente.render(df_filtrado)
with tab4:
    tab_ia.render(df_filtrado)
