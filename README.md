# TechLogistics S.A.S. — Consultoría de Datos (Challenge 02, EAFIT)

**Curso:** Fundamentos en Ciencia de Datos — Maestría en Ciencia de Datos y Analítica, EAFIT  
**Conjunto de datos:** Ecosistema TechLogistics (Inventario, Logística y Feedback de Clientes)  
**Fecha de entrega:** 31 de enero de 2026

**Integrantes del equipo:**

| Nombre completo                 | Cédula     |
|---------------------------------|------------|
| Santiago Alberto Vélez Casallas | 1072714309 |
| Santiago Rueda Mira             | 1152217529 |
| Cristian Miguel Gómez Salazar   | 1003402002 |

---

## 1. Resumen ejecutivo

TechLogistics S.A.S. opera con tres sistemas que no comparten idioma: un ERP de Inventarios, un registro de Logística y un sistema de Feedback de Clientes. Integramos, auditamos y analizamos sus **16 000 registros combinados** (2 500 de inventario · 10 000 transacciones · 4 500 de feedback) bajo la metodología CRISP-DM y los lineamientos ISO 8000 de Calidad de Datos.

La evidencia apunta a cinco focos de pérdida de valor. **La prioridad no es acelerar entregas indiscriminadamente**, sino corregir la estructura de precios por canal, cerrar la brecha del catálogo fantasma y establecer disciplina de auditoría de bodegas:

| Hallazgo | Métrica clave | Prioridad |
|---|---|---|
| Fuga de capital por canal | 41.2 % físico / 41.0 % WhatsApp con margen negativo | Alta |
| Tiempo de entrega no mueve el NPS | Pearson r = 0.0032 (p = 0.858) | Alta |
| Inventario / catálogo fantasma | 17.5 % del ingreso total sin trazabilidad | Alta |
| Paradoja stock–sentimiento | Smartphones: stock alto + NPS negativo | Media-Alta |
| Ceguera operativa de bodegas | Occidente: mayor días sin revisión → más tickets | Alta |

El **Documento de Hallazgos** completo está versionado en el repo: [`Informe_Hallazgos_TechLogistics.pdf`](Informe_Hallazgos_TechLogistics.pdf).

---

## 2. Las 5 preguntas de alta gerencia (resumen)

### P1 — Fuga de capital y rentabilidad
Los canales **Físico (41.2 %)** y **WhatsApp (41.0 %)** lideran en transacciones con margen negativo, seguidos de App (37.4 %) y Online (37.3 %). Dado que el porcentaje es similar en todos los canales, la fuga **no es un problema de precios específico de un canal**: es estructural en el catálogo de precios. Pérdida acumulada del período: **USD −11 692 624** frente a un margen total de USD 14 258 937.

### P2 — Crisis logística y cuellos de botella
La correlación global entre Tiempo de Entrega Real y NPS es **prácticamente nula (Pearson r = 0.0032)**. El análisis por ciudad tampoco revela ningún corredor crítico (rango r: −0.020 a +0.035). Acelerar entregas sin atacar otras causas tendrá bajo impacto en satisfacción; la raíz está en calidad del proceso o del producto.

### P3 — Análisis de la venta invisible
El **17.5 % de todo el ingreso** proviene de productos no registrados en el maestro de inventario. Operar con mercancía no estructurada impide análisis de rentabilidad confiables y compromete la auditabilidad exigida por ISO 8000.

### P4 — Diagnóstico de fidelidad
Se detecta una paradoja de alto impacto: **Smartphones** posee el mayor stock promedio (~1 040 u.) pero el NPS más bajo (−4). En contraste, **Tablets** lidera satisfacción (NPS +4) con menor inmovilización. Señal de problemas sistemáticos de soporte, no de disponibilidad.

### P5 — Storytelling de riesgo operativo
A mayor tiempo sin revisión física del stock, mayor porcentaje de tickets de soporte (Pearson r = 0.634). La bodega **Occidente** encabeza ambas variables: opera "a ciegas" y genera la mayor fricción de soporte al cliente final.

---

## 3. App desplegada

**Dashboard en vivo:** `https://challenge02equipogomezruedavelez-kmzecxnmygaj8juvgyjgsh.streamlit.app`

> Reemplazar por la URL real de Streamlit Community Cloud tras el despliegue.  
> Es requisito explícito de la Guía de Validación (§ 3.3 README Profesional).

---

## 4. Cómo ejecutar el dashboard (Fase 3)

```bash
# 1. Clonar el repositorio
git clone https://github.com/<USUARIO>/techlogistics-consultoria.git
cd techlogistics-consultoria

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el pipeline de limpieza e integración
#    (genera todos los artefactos en outputs/)
python run_pipeline.py

# 4. Configurar la clave de Groq (nunca se hardcodea en el código)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edita .streamlit/secrets.toml y pega tu GROQ_API_KEY real

# 5. Levantar el dashboard
streamlit run app.py
```

Se abre en `http://localhost:8501`. La **barra lateral** filtra por fecha, categoría, bodega y canal de venta; los tabs de Auditoría, Operaciones y Cliente se recalculan en vivo sobre ese filtro. El tab de IA envía únicamente un resumen estadístico agregado del filtro activo a Groq — nunca datos crudos de clientes.

### Navegación del dashboard (4 pestañas)

| Tab | Contenido |
|---|---|
| **Auditoría** | Health Score antes vs. después de la limpieza, por dataset. Filas eliminadas, duplicados y % de salud. Botón de descarga del reporte. |
| **Operaciones** | P1 (margen por canal), P2 (correlación entrega–NPS), P3 (venta invisible). |
| **Cliente** | P4 (paradoja stock–sentimiento), análisis de NPS por categoría. |
| **Insights de IA** | P5 (bodegas a ciegas), recomendaciones Llama-3 sobre el filtro activo, exportación del PDF de hallazgos. |

### Nota de vigencia del modelo de IA

El modelo por defecto es `llama-3.3-70b-versatile`. Groq anunció su depreciación el 17/jun/2026 con **fecha de apagado 16/ago/2026** para planes free/developer. Si el modelo ya no responde, cambia `DEFAULT_MODEL` en `services/groq_client.py` por el reemplazo vigente (consulta [console.groq.com/docs/models](https://console.groq.com/docs/models)) — es la única línea que hay que tocar.

---

## 5. Cómo reproducir solo el análisis (Fases 1 y 2)

```bash
pip install pandas numpy matplotlib seaborn scipy
python run_pipeline.py
```

Artefactos generados en `outputs/`:

| Archivo | Contenido |
|---|---|
| `inventario_limpio.csv` | Dataset de inventario limpio con flags de auditoría |
| `transacciones_limpias.csv` | Transacciones limpias (outliers marcados, fechas normalizadas) |
| `feedback_limpio.csv` | Feedback sin duplicados, edades y NPS normalizados |
| `master_table.csv` | Sola Fuente de Verdad: 10 000 transacciones + inventario + feedback |
| `health_score_report.json` | Health Score antes y después, por dataset |
| `decisiones_limpieza.json` | Log cuantitativo de cada decisión ética de imputación / exclusión |
| `respuestas_5_preguntas.json` | Evidencia numérica detrás de las 5 preguntas gerenciales |
| `charts/*.png` | Gráfico de soporte por pregunta (para el PDF de hallazgos) |

Para regenerar el PDF de hallazgos sin Groq:

```bash
python generar_informe.py
```

---

## 6. El viaje de los datos: del caos a la fuente de verdad

### 6.1 Lo que encontramos al abrir los tres archivos crudos

| Dataset | Problema | Registros afectados | Riesgo de negocio |
|---|---|---|---|
| Inventario | Costos atípicos ($0.01–$850 k), fechas y lead times mezclados, existencias negativas | ~15 % de filas | KPIs de margen distorsionados |
| Transacciones | SKUs huérfanos no presentes en inventario, formatos de fecha mixtos, tiempos de entrega con centinela 999 días | 1 750 SKUs / 50 filas | 17.5 % del ingreso sin trazabilidad |
| Feedback | Duplicados intencionales, edades imposibles (> 100 años), NPS sin normalizar | 469 Feedback_ID colisionantes | Indicadores de satisfacción sesgados |

### 6.2 Cómo lo arreglamos (y por qué)

- **SKU Fantasma**: clasificado como *falla de catálogo*, no fraude. Evidencia: 480 SKUs distintos, cada uno aparece en promedio 3.6 veces (rango 1–10, distribución dispersa). Se conservan vía LEFT JOIN con `Categoria = 'Sin Catálogo'` y margen NaN.
- **Costos y precios atípicos**: filtro IQR; los outliers extremos se excluyen del cálculo de KPIs globales pero son visibles en la pestaña de Auditoría ("Ver registros excluidos").
- **Centinelas**: `Cantidad_Vendida = −5` (100 filas), `Tiempo_Entrega_Real = 999` (50 filas), `Rating_Producto = 99` (30 filas) — los tres tratados como nulos e imputados por mediana de su grupo, nunca por valor absoluto.
- **Fechas futuras**: transacciones con fecha posterior a `REFERENCE_DATE = 2026-01-31` se marcan como inválidas y se excluyen de las series de tiempo. Se usa fecha fija en vez de `datetime.now()` para que el análisis sea 100 % reproducible.
- **Ciudades inconsistentes**: diccionario de mapeo (`MED → Medellín`, `BOG → Bogotá`, etc.) + `.str.title()`. El filtro de ciudad en la barra lateral muestra una única opción por región.
- **Feedback_ID duplicado ≠ evento duplicado**: 469 IDs colisionan con contenido distinto. No se borró ninguna fila; se generó `Feedback_UID` como llave sustituta.

### 6.3 Variables derivadas creadas (Feature Engineering)

| Variable | Fórmula | Para qué pregunta |
|---|---|---|
| `Margen_Ganancia` | `(Precio_Venta_Final − Costo_Unitario_USD) × Cantidad_Vendida − Costo_Envio` | P1 |
| `Retraso_Logistico_Dias` | `Tiempo_Entrega_Real − Lead_Time_Dias` | P2 |
| `Alerta_Inventario` | `Stock_Actual < Punto_Reorden` | P4 / P5 |

---

## 7. Lo que dicen los datos ya limpios

### 7.1 La fuga de capital es estructural, no de canal

El porcentaje de transacciones con margen negativo oscila entre 37.3 % (Online) y 41.2 % (Físico) — una diferencia de apenas 4 puntos entre el mejor y el peor canal. Si fuera un problema de precios de un canal específico, el canal Online debería sobresalir. No lo hace. La causa está en el catálogo de costos, no en el canal de distribución.

### 7.2 El tiempo de entrega no es la palanca del NPS

Con r = 0.0032 y p = 0.858, no existe evidencia estadística de que reducir el tiempo de entrega mejore la satisfacción. El análisis desagregado por ciudad (Bucaramanga, Bogotá, Cali, Medellín, Barranquilla) tampoco revela ningún corredor crítico. La acción correctiva debe enfocarse en soporte y calidad de producto.

### 7.3 El 17.5 % del ingreso opera sin red de seguridad

USD 13.2 M de los USD 75.3 M de ingreso bruto provienen de SKUs sin registro en el maestro de inventario. Es imposible calcular margen real, proyectar reposición o auditar bajo ISO 8000 para este segmento.

### 7.4 Paradoja de categorías: más stock ≠ más NPS

Smartphones (stock ~1 040 u., NPS = −4) vs. Tablets (stock ~985 u., NPS = +4). La disponibilidad garantiza la venta pero no la experiencia. Los datos apuntan a problemas de soporte posventa en telefonía, no de desabastecimiento.

### 7.5 Las bodegas a ciegas pagan con tickets

La correlación entre días sin revisión física y % de tickets es r = 0.634. **Occidente** encabeza ambas variables. Con solo 5 bodegas el p-value no es concluyente (p = 0.250), pero la tendencia es consistente con la hipótesis operativa y constituye la señal de mayor impacto accionable.

---

## 8. Plan de acción recomendado

| # | Recomendación | Complejidad | Impacto |
|---|---|---|---|
| 1 | Auditoría de costos e intermediación en canales Físico y WhatsApp; revisar márgenes por SKU antes de autorizar nuevas transacciones en estos canales. | Baja | Alto |
| 2 | Catalogar el 100 % de los 480 SKUs fantasma: asignar costo, categoría y punto de reorden. Meta: reducir el ingreso en riesgo del 17.5 % al < 5 % en 60 días. | Media | Alto |
| 3 | Institucionalizar auditoría física en bodega Occidente (y cualquier bodega con > 340 días sin revisión): implementar ciclo de conteo mensual y alerta automática en el dashboard. | Alta | Alto |

---

## 9. Estructura del repositorio

```
techlogistics/
├── data/                          # CSVs crudos (input — no modificar)
│   ├── inventario_central_v2.csv
│   ├── transacciones_logistica_v2.csv
│   └── feedback_clientes_v2.csv
├── src/                           # Pipeline Fases 1 y 2
│   ├── audit.py                   # Motor de Health Score
│   ├── cleaning_inventario.py
│   ├── cleaning_transacciones.py
│   ├── cleaning_feedback.py
│   ├── integration.py             # Merge + Feature Engineering
│   └── analysis.py                # Las 5 preguntas + estadísticas
├── ui/                            # Pestañas del dashboard (Fase 3)
│   ├── components.py              # CSS, tarjetas, tema Plotly
│   ├── tab_auditoria.py
│   ├── tab_operaciones.py
│   ├── tab_cliente.py
│   └── tab_ia.py                  # Groq + exportación PDF
├── services/
│   ├── data_loader.py             # Carga/cacheo de outputs/ + filtros
│   ├── groq_client.py             # Integración Groq (Llama-3)
│   └── pdf_generator.py           # Documento de Hallazgos
├── assets/styles.css              # Identidad visual "Sala de Control de Datos"
├── .streamlit/
│   ├── config.toml                # Tema base de Streamlit
│   └── secrets.toml.example       # Plantilla API key (NO subir la real)
├── app.py                         # Punto de entrada del dashboard
├── run_pipeline.py                # Orquestador Fases 1–2 (CLI)
├── generar_informe.py             # Regenera el PDF versionado sin Groq
├── Informe_Hallazgos_TechLogistics.pdf   # Entregable PDF (junta directiva)
├── requirements.txt
├── .gitignore
├── outputs/                       # Artefactos generados (git-ignorados)
└── README.md
```

Cada módulo de `src/` contiene en su docstring la justificación completa de cada decisión de imputación/exclusión — es la "Decisión Ética" que exige el reto. Léalos antes de usar el pipeline con otros datos.

---

## 10. Subir a GitHub y desplegar en la nube

```bash
git init
git add .
git commit -m "TechLogistics: Fases 1-3 completas — Challenge 02 EAFIT"
git branch -M main
git remote add origin https://github.com/<USUARIO>/techlogistics-consultoria.git
git push -u origin main
```

En [share.streamlit.io](https://share.streamlit.io): **New app** → selecciona el repo → `app.py` como archivo principal → en *Advanced settings → Secrets* pega `GROQ_API_KEY = "tu_clave"` → **Deploy**.

---

## 11. Declaración de uso de Inteligencia Artificial

Se usó IA generativa (Claude Code y Llama-3 vía Groq) para: sintaxis de pandas/plotly, depuración inicial del pipeline de limpieza y un primer borrador del informe ejecutivo. Las decisiones de criterio (estrategia de imputación, tratamiento del SKU fantasma, llave de duplicados, interpretación de resultados y las tres recomendaciones tácticas) fueron discutidas y validadas por el equipo. El módulo de Groq integrado en el dashboard genera recomendaciones basadas exclusivamente en el resumen estadístico del filtro activo del usuario, nunca en datos individuales de clientes.
