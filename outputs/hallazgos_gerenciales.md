# Hallazgos Gerenciales — TechLogistics S.A.S.
### Basado en `master_table.csv` (10,000 transacciones, Fase 1-2 completadas)

---

## 1. Fuga de Capital y Rentabilidad

**Hallazgo**: el **39.27%** de las transacciones (3,239 de las 8,249 con costo
conocido) tienen margen negativo, con una pérdida acumulada de **-USD
11,692,624**.

**¿Es un problema del canal Online?** Los datos **no respaldan esa
hipótesis**. La tasa de transacciones con margen negativo es prácticamente
la misma en los cuatro canales:

| Canal | % transacciones con margen negativo | Pérdida acumulada |
|---|---|---|
| Físico | 41.21% | -USD 3,122,093 |
| WhatsApp | 40.98% | -USD 3,052,912 |
| App | 37.44% | -USD 2,689,710 |
| **Online** | **37.34%** (el más bajo) | -USD 2,827,909 |

**Conclusión para la junta**: esto no es una falla de precios de un canal
específico; es un **problema estructural del catálogo**: el precio de venta
y el costo unitario parecen fijarse de forma independiente, sin una regla de
margen mínimo garantizado. Se identificaron 10 SKUs individuales responsables
de las mayores pérdidas acumuladas (ej. PROD-2858 con -USD 58,143 en 7
ventas), buenos candidatos para una revisión de precios inmediata.

*Gráfico de soporte:* `charts/p1_fuga_capital_canal.png`

---

## 2. Crisis Logística y Cuellos de Botella

**Hallazgo**: la correlación general entre Tiempo de Entrega y NPS es
prácticamente nula (**r = 0.003**). Al desagregar por ciudad y bodega, la
combinación con la relación más negativa es **Bucaramanga / Bodega
Occidente** (r = -0.121, n=55), una correlación débil.

**Conclusión honesta para la junta**: con la evidencia disponible, el tiempo
de entrega **no es**, hoy, el principal motor de la insatisfacción del
cliente en ninguna zona geográfica particular — ninguna combinación
ciudad-bodega supera una correlación de 0.15 en magnitud. Recomendamos no
priorizar un cambio de operador logístico basado solo en esta métrica, y en
cambio investigar otros factores (precio, calidad de producto — ver hallazgo
4) que muestran señales más fuertes. Esto no significa que la logística esté
bien: la tasa general de "Retrasado"/"Perdido" sigue siendo alta (~33% de los
envíos combinados), pero su vínculo directo con el NPS no se sostiene
estadísticamente con estos datos.

*Gráfico de soporte:* `charts/p2_correlacion_ciudad_bodega.png`

---

## 3. Análisis de la Venta Invisible

**Hallazgo**: **17.45%** del ingreso total (**USD 13,131,809** de USD
75,251,242) proviene de 1,751 transacciones (17.51% del volumen) cuyo SKU no
existe en el inventario maestro.

**Diagnóstico**: se identificaron 480 SKUs huérfanos distintos, cada uno
vendido en promedio 3.6 veces (rango 1-10 transacciones). Este patrón
disperso y sin concentración en pocos códigos es más compatible con una
**falla de sincronización del catálogo** (productos nuevos vendidos antes de
registrarse en el ERP) que con fraude, que típicamente concentraría el
volumen en unos pocos SKUs explotados repetidamente.

**Conclusión para la junta**: casi 1 de cada 5 dólares de ingreso hoy no
tiene un costo de referencia verificable, lo que significa que la
rentabilidad real de la compañía **no se puede calcular con certeza** sobre
ese 17.45% del negocio. Cerrar la brecha de sincronización ERP-Ventas es
prioridad alta.

*Gráfico de soporte:* `charts/p3_venta_fantasma.png`

---

## 4. Diagnóstico de Fidelidad

**Hallazgo**: dos categorías muestran la paradoja de "alta disponibilidad,
sentimiento negativo": **Smartphones** (stock promedio 1,045 unidades, NPS
promedio **-4.22**, el más bajo) y los productos **Sin Categoría** (stock
1,009, NPS -2.09). En contraste, Tablets (NPS +3.96) y Laptops (NPS +2.35)
tienen sentimiento positivo con niveles de stock similares.

**¿Es mala calidad de producto o sobrecosto?** El Rating_Producto promedio es
prácticamente idéntico entre categorías (2.97 a 3.06 sobre 5) — es decir, la
percepción de calidad del producto en sí **no varía** entre categorías. Esto
apunta a que la caída de NPS en Smartphones **no es un problema de calidad
del producto**, sino de otro factor no capturado directamente en este rating
(candidatos: precio percibido, expectativas de marca, o experiencia de
compra) — se recomienda una encuesta de seguimiento específica a
compradores de Smartphones para confirmar la causa raíz antes de invertir en
cambios de producto.

*Gráfico de soporte:* `charts/p4_paradoja_categoria.png`

---

## 5. Storytelling de Riesgo Operativo

**Hallazgo**: existe una correlación **moderada-alta (r = 0.634)** entre los
días transcurridos desde la última revisión física de stock por bodega y su
tasa de tickets de soporte (nota: con solo 5 bodegas, esta correlación es
indicativa, no estadísticamente concluyente).

| Bodega | Días desde última revisión (prom.) | Tasa de tickets de soporte |
|---|---|---|
| **Occidente** | **356** (la más desactualizada) | **22.02%** (la más alta) |
| Bod-Ext-99 | 356 | 20.10% |
| Zona_Franca | 347 | 20.70% |
| Norte | 345 | 20.61% |
| **Sur** | **330** (la más actualizada) | **19.72%** (la más baja) |

**Conclusión para la junta**: la bodega **Occidente** es la que más está
"operando a ciegas" y, consistente con esa hipótesis, tiene la mayor tasa de
tickets de soporte. Se recomienda priorizar ahí el próximo ciclo de conteo
físico.

*Gráfico de soporte:* `charts/p5_riesgo_operativo_bodega.png`

---

## Resumen ejecutivo (para la portada del PDF de hallazgos)

| # | Pregunta | Severidad | Cifra clave |
|---|---|---|---|
| 1 | Fuga de capital | 🔴 Alta | -USD 11.69M en margen negativo (39.3% de las ventas) |
| 2 | Crisis logística vs NPS | 🟡 Baja evidencia | Correlación máxima -0.12 (débil) |
| 3 | Venta invisible | 🔴 Alta | 17.45% del ingreso sin costo verificable |
| 4 | Paradoja de fidelidad | 🟠 Media | Smartphones: NPS -4.22 pese a stock alto |
| 5 | Riesgo operativo | 🟠 Media | r=0.634 antigüedad de revisión vs tickets (Occidente en riesgo) |
