# TechLogistics S.A.S. — Consultoría de Datos (Challenge 02, EAFIT)

Pipeline de auditoría de calidad, integración y análisis gerencial para los tres
sistemas de TechLogistics (Inventario, Logística, Feedback de Clientes).

> **Alcance de esta entrega**: Fase 1 (Auditoría de Calidad y Limpieza),
> Fase 2 (Integración + Feature Engineering) y **Fase 3 (Dashboard Streamlit
> + módulo de IA con Groq/Llama-3)**, con las 5 preguntas de alta gerencia
> respondidas con evidencia numérica y gráfica real. **Pendiente**: el
> documento de hallazgos en PDF con capturas del dashboard (ver checklist al
> final de este README).

## Cómo correr el dashboard (Fase 3)

```bash
pip install -r requirements.txt

# 1. Generar los datos (si no lo has hecho / si cambiaste los CSV crudos)
python3 run_pipeline.py

# 2. Configurar tu clave de Groq (nunca se hardcodea en el código)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edita .streamlit/secrets.toml y pega tu GROQ_API_KEY real

# 3. Levantar el dashboard
streamlit run app.py
```

Se abrirá en `http://localhost:8501`. La barra lateral filtra fecha,
categoría, bodega y canal; los 3 primeros tabs se recalculan en vivo sobre
ese filtro. El tab de IA envía únicamente un resumen estadístico agregado
del filtro activo a Groq (nunca datos crudos de clientes).

### ⚠️ Nota de vigencia del modelo de IA

El modelo por defecto es `llama-3.3-70b-versatile` (el "Llama-3" que pide el
reto). Groq anunció su depreciación el 17/jun/2026 con **fecha de apagado
16/ago/2026** para planes free/developer. Si corres esto después de esa
fecha y el modelo ya no responde, cambia `DEFAULT_MODEL` en
`services/groq_client.py` por el reemplazo vigente (verifica en
https://console.groq.com/docs/models) — es la única línea que hay que tocar.

## Cómo reproducir el análisis (Fase 1-2)

```bash
pip install pandas numpy matplotlib seaborn
python3 run_pipeline.py
```

Esto genera en `outputs/`:

| Archivo | Contenido |
|---|---|
| `inventario_limpio.csv`, `transacciones_limpias.csv`, `feedback_limpio.csv` | Datasets limpios, con columnas de auditoría (flags) añadidas |
| `master_table.csv` | Sola Fuente de Verdad (Fase 2): las 10,000 transacciones enriquecidas con inventario y feedback |
| `health_score_report.json` | Health Score (completitud, validez, unicidad) **antes** y **después** de la limpieza, por dataset |
| `decisiones_limpieza.json` | Log cuantitativo de cada decisión de limpieza tomada (cuántos registros se imputaron, con qué criterio, etc.) |
| `respuestas_5_preguntas.json` | Evidencia numérica completa detrás de las 5 preguntas gerenciales |
| `charts/*.png` | Gráfico de soporte para cada una de las 5 preguntas |

## Estructura del repositorio

```
techlogistics/
├── data/                          # CSVs crudos (input)
├── src/                            # Pipeline de limpieza/análisis (Fase 1-2)
│   ├── cleaning_inventario.py
│   ├── cleaning_transacciones.py
│   ├── cleaning_feedback.py
│   ├── health_score.py
│   ├── integration.py
│   └── analysis.py
├── ui/                             # Pestañas del dashboard (Fase 3)
│   ├── components.py               # CSS, tarjetas ledger, tema Plotly
│   ├── tab_auditoria.py
│   ├── tab_operaciones.py
│   ├── tab_cliente.py
│   └── tab_ia.py
├── services/
│   ├── data_loader.py              # Carga/cacheo de outputs/ + filtros
│   └── groq_client.py              # Integración con Groq (Llama-3)
├── assets/styles.css               # Identidad visual "Sala de Control de Datos"
├── .streamlit/
│   ├── config.toml                 # Tema base de Streamlit
│   └── secrets.toml.example        # Plantilla de la API key (NO subir la real)
├── app.py                          # Punto de entrada del dashboard
├── run_pipeline.py                 # Orquestador de Fase 1-2 (CLI)
├── requirements.txt
├── .gitignore
├── outputs/                        # Resultados generados (no versionar en Git si pesan mucho)
└── README.md
```

Cada módulo de limpieza tiene, en su docstring, la justificación completa
de **por qué** se tomó cada decisión (media/mediana/moda, qué se excluyó,
qué se imputó) — es la "Decisión Ética" que exige el reto. Léelos antes de
usar el pipeline con otros datos.

## Fecha de referencia ("hoy") usada en todo el análisis

Se fijó `REFERENCE_DATE = 2026-01-31` (la fecha límite del proyecto indicada
en el PDF del reto) como el "hoy" para calcular antigüedad de revisión de
stock y para detectar fechas de venta futuras/inválidas. Se usa una fecha
fija en vez de `datetime.now()` para que el análisis sea 100% reproducible
sin importar cuándo se ejecute el pipeline.

## Decisiones clave que debes conocer antes de construir el dashboard (Fase 3)

1. **SKU Fantasma**: se clasificó como *falla de catálogo* (no fraude), con
   evidencia: 480 SKUs distintos, cada uno repitiéndose en promedio 3.6 veces
   (rango 1-10) — patrón disperso, no concentrado. Se mantienen en el
   `master_table` vía LEFT JOIN, con `Categoria='Sin Catálogo'` y margen NaN.
2. **Feedback_ID duplicado ≠ evento duplicado**: 469 IDs colisionan con
   contenido distinto (transacciones distintas). No se borró ninguna fila;
   se generó `Feedback_UID` como llave sustituta. Ver docstring de
   `cleaning_feedback.py` para el detalle completo.
3. **Códigos centinela detectados**: `Cantidad_Vendida=-5` (100 filas),
   `Tiempo_Entrega_Real=999` (50 filas), `Rating_Producto=99` (30 filas) — los
   tres se trataron como nulos e imputaron por mediana, nunca por valor
   absoluto o heurísticas ad-hoc.
4. **"Ventas_Web" en Ciudad_Destino**: se validó estadísticamente que NO está
   correlacionado con un canal de venta específico (proporción ~25% en los
   4 canales) → se marca como dato geográfico no disponible, no se intenta
   "recuperar" la ciudad real.

## Subir a GitHub y desplegar en la nube

Ver el paso a paso detallado en la respuesta del chat. Resumen rápido:

```bash
git init
git add .
git commit -m "TechLogistics: Fase 1-3 completas"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/techlogistics-consultoria.git
git push -u origin main
```

Luego, en https://share.streamlit.io: **New app** → selecciona el repo →
`app.py` como archivo principal → en *Advanced settings → Secrets* pega tu
`GROQ_API_KEY` → **Deploy**.

## Próximos pasos (pendiente)

- Documento de hallazgos en PDF con capturas del dashboard (4+ exigidas) y
  el plan de acción de 3 recomendaciones priorizadas (baja/media/alta
  complejidad) — el contenido narrativo ya está listo en
  `outputs/hallazgos_gerenciales.md`, solo falta maquetarlo con capturas.
- Desplegar el dashboard en Streamlit Community Cloud y agregar el enlace
  al README (ver guía de despliegue que te compartí en el chat).
