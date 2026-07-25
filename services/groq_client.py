"""
Integración de IA con Groq (Fase 3)
=====================================

IMPORTANTE — nota de vigencia del modelo (verificar antes de tu entrega):
Groq anunció el 17/jun/2026 la depreciación de 'llama-3.3-70b-versatile' con
fecha de apagado 16/ago/2026 (planes free y developer). Al momento de escribir
este módulo el modelo TODAVÍA funciona, pero si tu entrega es después de esa
fecha, el modelo Llama-3 ya no estará disponible en Groq y deberás usar el
reemplazo que ellos recomienden (revisa https://console.groq.com/docs/models).
Por eso el nombre del modelo es una CONSTANTE fácil de cambiar en un solo
lugar (`DEFAULT_MODEL`), no está repetido en el código.

La API Key NUNCA se hardcodea aquí: se lee de `st.secrets["GROQ_API_KEY"]`
(local: `.streamlit/secrets.toml`; en Streamlit Community Cloud: sección
"Secrets" del panel de la app), tal como exige la guía de validación.
"""

import streamlit as st
from groq import Groq

DEFAULT_MODEL = "llama-3.3-70b-versatile"  # ver nota de vigencia arriba


def _get_client() -> Groq | None:
    try:
        api_key = st.secrets.get("GROQ_API_KEY", None)
    except Exception:
        # st.secrets lanza excepción (no retorna None) cuando no existe
        # ningún archivo secrets.toml en absoluto — lo tratamos como "sin key".
        api_key = None
    if not api_key:
        return None
    return Groq(api_key=api_key)


def build_prompt(resumen: dict) -> str:
    """Convierte el resumen estadístico filtrado por el usuario en un prompt
    estructurado. Solo se envían agregados numéricos, nunca datos crudos de
    clientes (privacidad)."""
    return f"""
Eres un consultor senior de datos presentando hallazgos a la junta directiva
de TechLogistics S.A.S., un retailer de tecnología. Con base ÚNICAMENTE en
el siguiente resumen estadístico (ya filtrado por el usuario del dashboard),
escribe EXACTAMENTE tres párrafos de recomendación estratégica en español:
  1. Diagnóstico: qué muestra el resumen sobre la salud financiera/operativa.
  2. Riesgo priorizado: cuál es el problema más urgente a atender primero y por qué.
  3. Acción concreta: una recomendación táctica específica y accionable.

No inventes cifras que no estén en el resumen. Sé directo, ejecutivo, sin
rodeos técnicos.

RESUMEN ESTADÍSTICO (datos filtrados):
- Transacciones en el filtro actual: {resumen['n_transacciones']}
- Ingreso bruto total: USD {resumen['ingreso_bruto']:,.2f}
- Margen de utilidad total: USD {resumen['margen_total']:,.2f}
- % de transacciones con margen negativo: {resumen['pct_margen_negativo']:.1f}%
- % de ingreso proveniente de ventas fantasma (SKU no catalogado): {resumen['pct_venta_fantasma']:.1f}%
- NPS promedio: {resumen['nps_promedio']:.1f}
- % de transacciones con ticket de soporte abierto: {resumen['pct_ticket_soporte']:.1f}%
- Tiempo de entrega promedio: {resumen['tiempo_entrega_promedio']:.1f} días
"""


def generar_recomendaciones(resumen: dict, model: str = DEFAULT_MODEL) -> str:
    """Llama a Groq (Llama-3) y devuelve el texto de recomendaciones.
    Lanza RuntimeError con un mensaje claro para la UI si algo falla."""
    client = _get_client()
    if client is None:
        raise RuntimeError(
            "No se encontró GROQ_API_KEY en st.secrets. Configúrala en "
            ".streamlit/secrets.toml (local) o en Secrets de Streamlit "
            "Community Cloud (producción)."
        )
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": build_prompt(resumen)}],
            temperature=0.4,
            max_tokens=700,
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Error al llamar a la API de Groq: {e}") from e


def resumen_desde_filtro(df_filtrado) -> dict:
    """Calcula el resumen estadístico agregado que se envía a la IA,
    a partir del master_table ya filtrado por la barra lateral."""
    df = df_filtrado
    con_margen = df.dropna(subset=["Margen_Utilidad_USD"])
    return {
        "n_transacciones": int(len(df)),
        "ingreso_bruto": float(df["Ingreso_Bruto"].sum()),
        "margen_total": float(con_margen["Margen_Utilidad_USD"].sum()) if len(con_margen) else 0.0,
        "pct_margen_negativo": float((con_margen["Margen_Utilidad_USD"] < 0).mean() * 100) if len(con_margen) else 0.0,
        "pct_venta_fantasma": float(df["Es_Venta_Fantasma"].mean() * 100),
        "nps_promedio": float(df["Satisfaccion_NPS_Prom"].mean()) if df["Satisfaccion_NPS_Prom"].notna().any() else 0.0,
        "pct_ticket_soporte": float(df["Ticket_Soporte_Abierto"].mean() * 100),
        "tiempo_entrega_promedio": float(df["Tiempo_Entrega_Real"].mean()),
    }
