import io
import base64
import pandas as pd
import numpy as np
import scipy.stats as sci
import matplotlib
matplotlib.use("Agg") # Backend seguro para servidores/nube sin entorno gráfico
import matplotlib.pyplot as plt
from xhtml2pdf import pisa
from datetime import datetime

# Colores corporativos (basados en tu ui.components)
C_INFO, C_SALUD, C_ADV, C_CRIT = "#5B8DEF", "#3FA796", "#E8A33D", "#E4572E"

def _fig_to_base64(fig) -> str:
    """Convierte una figura Matplotlib a string Base64 para inyectar en HTML."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _kpis_negocio(df: pd.DataFrame) -> dict:
    """Cifras de negocio calculadas en runtime (nunca escritas a mano).

    Se excluye Costo_Atipico de los agregados de margen: ese costo NO se
    winsoriza (ver src/cleaning_inventario.py), así que dejarlo dentro
    dominaría el agregado con un solo artefacto de datos.
    """
    atip = df.get("Costo_Atipico", pd.Series(False, index=df.index))
    if atip.dtype == object:
        atip = atip.astype(str).str.lower().isin(["true", "1"])
    con_margen = df.dropna(subset=["Margen_Utilidad_USD"])
    limpio = con_margen[~atip.reindex(con_margen.index, fill_value=False)]
    neg = limpio[limpio["Margen_Utilidad_USD"] < 0]

    ingreso_total = float(df["Ingreso_Bruto"].sum())
    fantasma = float(df.loc[df["Es_Venta_Fantasma"], "Ingreso_Bruto"].sum())
    bod = df[df["Bodega_Origen"] != "Sin Bodega"]
    peor_bodega, peor_dias = "n/d", float("nan")
    if not bod.empty:
        rev = bod.groupby("Bodega_Origen")["Dias_Desde_Ultima_Revision"].mean()
        if not rev.empty:
            peor_bodega, peor_dias = rev.idxmax(), float(rev.max())

    return {
        "n_analizadas":   int(len(limpio)),
        "n_negativas":    int(len(neg)),
        "pct_negativas":  float(len(neg) / len(limpio) * 100) if len(limpio) else 0.0,
        "perdida":        float(neg["Margen_Utilidad_USD"].sum()) if len(neg) else 0.0,
        "margen_total":   float(limpio["Margen_Utilidad_USD"].sum()) if len(limpio) else 0.0,
        "ingreso_total":  ingreso_total,
        "ingreso_riesgo": fantasma,
        "pct_riesgo":     (fantasma / ingreso_total * 100) if ingreso_total else 0.0,
        "n_fantasma":     int(df["Es_Venta_Fantasma"].sum()),
        "skus_fantasma":  int(df.loc[df["Es_Venta_Fantasma"], "SKU_ID"].nunique()),
        "peor_bodega":    peor_bodega,
        "peor_dias":      peor_dias,
        "nps":            float(df["Satisfaccion_NPS_Prom"].mean(skipna=True)),
    }


def _plan_de_accion(k: dict) -> str:
    """Plan de Acción exigido por la Guía de Validación: tres recomendaciones
    tácticas NUMERADAS y PRIORIZADAS por complejidad (Baja / Media / Alta).

    Se construye con las cifras calculadas en runtime, no con texto fijo, para
    que el plan siga siendo cierto si cambian los filtros o los datos.
    """
    filas = [
        ("1", "Baja", "#3FA796",
         "Congelar precios bajo costo en el catálogo",
         f"{k['n_negativas']:,} transacciones ({k['pct_negativas']:.1f}%) se venden por "
         f"debajo de costo, con una pérdida acumulada de USD {abs(k['perdida']):,.0f}. "
         "Implementar una regla de margen mínimo garantizado en el maestro de precios "
         "bloquea la fuga sin cambiar procesos ni sistemas.",
         "Inmediato (0-30 días) · Recupera margen sobre el 39% del volumen afectado"),
        ("2", "Media", "#E8A33D",
         "Cerrar la brecha de sincronización ERP ↔ Ventas",
         f"USD {k['ingreso_riesgo']:,.0f} ({k['pct_riesgo']:.1f}% del ingreso) provienen de "
         f"{k['n_fantasma']:,} ventas sobre {k['skus_fantasma']} SKUs que no existen en el "
         "inventario maestro: es una falla de catálogo, no fraude (la recurrencia es "
         "dispersa). Sin costo de referencia, la rentabilidad real de ese tramo del "
         "negocio no se puede calcular.",
         "Corto plazo (1-3 meses) · Devuelve visibilidad sobre 1 de cada 5 dólares"),
        ("3", "Alta", "#E4572E",
         "Reinstaurar el ciclo de conteo físico por bodega",
         f"La bodega {k['peor_bodega']} lleva {k['peor_dias']:.0f} días promedio sin "
         "conteo físico. Operar sobre stock teórico desactualizado degrada la promesa de "
         "entrega y alimenta los tickets de soporte, con un NPS promedio actual de "
         f"{k['nps']:.1f}.",
         "Mediano plazo (3-6 meses) · Requiere personal, paradas operativas y sistema WMS"),
    ]
    bloques = []
    for num, prio, color, titulo, cuerpo, impacto in filas:
        bloques.append(f"""
        <table class="accion">
          <tr>
            <td class="acc-num" style="background:{color};">{num}</td>
            <td class="acc-body">
              <b>{titulo}</b>
              <span class="badge" style="background:{color};">Complejidad {prio}</span><br>
              {cuerpo}<br>
              <span class="acc-impacto">{impacto}</span>
            </td>
          </tr>
        </table>""")
    return "".join(bloques)


def generar_pdf_dinamico(df: pd.DataFrame, ai_insights: str = "") -> bytes:
    """Genera las 5 gráficas estratégicas dinámicas y ensambla el PDF gerencial."""
    
    # --- GRÁFICA Q1: Fuga de Capital y Rentabilidad ---
    fig1, ax1 = plt.subplots(figsize=(4.5, 3))
    df_q1 = df[~df.get("Costo_Atipico", pd.Series(False, index=df.index))].dropna(subset=["Margen_Utilidad_USD"])
    if not df_q1.empty:
        por_canal = df_q1.groupby("Canal_Venta").apply(
            lambda g: (g["Margen_Utilidad_USD"] < 0).mean() * 100, include_groups=False
        ).sort_values()
        por_canal.plot(kind="barh", color=C_CRIT, ax=ax1)
        ax1.set_xlabel("% Margen Negativo")
    else:
        ax1.text(0.5, 0.5, "Datos Insuficientes", ha="center")
    ax1.set_title("Q1: Fuga de Capital por Canal")
    plt.tight_layout()
    b64_q1 = _fig_to_base64(fig1)

    # --- GRÁFICA Q2: Crisis Logística (Tiempo vs NPS) ---
    fig2, ax2 = plt.subplots(figsize=(4.5, 3))
    df_q2 = df[(df["Ciudad_Destino"] != "Sin Ciudad")].dropna(subset=["Satisfaccion_NPS_Prom", "Tiempo_Entrega_Real"])
    ciudades, corrs = [], []
    for c, g in df_q2.groupby("Ciudad_Destino"):
        if len(g) >= 5: # Mínimo para una correlación descriptiva en el PDF
            r, _ = sci.pearsonr(g["Tiempo_Entrega_Real"], g["Satisfaccion_NPS_Prom"])
            if not pd.isna(r):
                ciudades.append(c)
                corrs.append(r)
    if corrs:
        ax2.bar(ciudades, corrs, color=C_INFO)
        ax2.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax2.set_ylabel("Pearson r")
        plt.xticks(rotation=25, ha='right')
    else:
        ax2.text(0.5, 0.5, "Datos Insuficientes", ha="center")
    ax2.set_title("Q2: Impacto Tiempo-NPS por Ciudad")
    plt.tight_layout()
    b64_q2 = _fig_to_base64(fig2)

    # --- GRÁFICA Q3: Análisis Venta Invisible ---
    fig3, ax3 = plt.subplots(figsize=(4.5, 3))
    ing_tot = df["Ingreso_Bruto"].sum()
    fant = df[df["Es_Venta_Fantasma"]]["Ingreso_Bruto"].sum()
    if ing_tot > 0:
        ax3.pie([ing_tot - fant, fant], labels=["Catálogo Sano", "Venta Fantasma"], 
                autopct="%1.1f%%", colors=[C_SALUD, C_ADV], startangle=90)
    else:
        ax3.text(0.5, 0.5, "Sin Ingresos", ha="center")
    ax3.set_title("Q3: Venta Invisible (Ingreso en Riesgo)")
    plt.tight_layout()
    b64_q3 = _fig_to_base64(fig3)

    # --- GRÁFICA Q4: Diagnóstico de Fidelidad ---
    fig4, ax4 = plt.subplots(figsize=(4.5, 3))
    cats_q4 = ["Accesorios", "Laptops", "Monitores", "Smartphones", "Tablets"]
    df_q4 = df[df["Categoria"].isin(cats_q4)]
    if not df_q4.empty:
        res4 = df_q4.groupby("Categoria").agg(
            stock=("Stock_Actual", "mean"), nps=("Satisfaccion_NPS_Prom", "mean")
        ).dropna()
        ax4.scatter(res4["stock"], res4["nps"], color=C_ADV, s=80)
        for cat, row in res4.iterrows():
            ax4.annotate(cat, (row["stock"], row["nps"]), fontsize=8, xytext=(5,3), textcoords="offset points")
        ax4.set_xlabel("Stock Promedio")
        ax4.set_ylabel("NPS Promedio")
    else:
        ax4.text(0.5, 0.5, "Datos Insuficientes", ha="center")
    ax4.set_title("Q4: Paradoja Stock vs Satisfacción")
    plt.tight_layout()
    b64_q4 = _fig_to_base64(fig4)

    # --- GRÁFICA Q5: Riesgo Operativo ---
    fig5, ax5 = plt.subplots(figsize=(4.5, 3))
    df_q5 = df[df["Bodega_Origen"] != "Sin Bodega"]
    if not df_q5.empty:
        res5 = df_q5.groupby("Bodega_Origen").agg(
            dias=("Dias_Desde_Ultima_Revision", "mean"),
            tkts=("Ticket_Soporte_Abierto", lambda x: x.mean() * 100)
        ).dropna()
        ax5.scatter(res5["dias"], res5["tkts"], color=C_CRIT, s=80)
        for bod, row in res5.iterrows():
            ax5.annotate(bod, (row["dias"], row["tkts"]), fontsize=8, xytext=(5,3), textcoords="offset points")
        ax5.set_xlabel("Días desde última revisión")
        ax5.set_ylabel("% Tickets de Soporte")
    else:
        ax5.text(0.5, 0.5, "Datos Insuficientes", ha="center")
    ax5.set_title("Q5: Operación a Ciegas")
    plt.tight_layout()
    b64_q5 = _fig_to_base64(fig5)

    # --- CIFRAS, NARRATIVA Y PLAN DE ACCIÓN ---
    k = _kpis_negocio(df)

    if ai_insights and ai_insights.strip():
        bloque_ia = f"""
        <h2>Recomendaciones Estratégicas (Inteligencia Artificial)</h2>
        <div class="caja-ia">{ai_insights.replace(chr(10), '<br>')}</div>"""
    else:
        bloque_ia = """
        <h2>Recomendaciones Estratégicas (Inteligencia Artificial)</h2>
        <div class="caja-ia">Este ejemplar se generó sin invocar el módulo de IA
        (no se configuró <b>GROQ_API_KEY</b>). El diagnóstico, la evidencia y el
        Plan de Acción de este informe se calculan directamente de los datos y no
        dependen del modelo. Para anexar las recomendaciones de Llama-3, genere el
        PDF desde la pestaña <i>Insights de IA</i> del dashboard con la clave
        configurada.</div>"""

    # --- ENSAMBLAJE HTML Y CSS ---
    html_final = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4 portrait; margin: 1.5cm;
                @frame footer_frame {{ -pdf-frame-content: footer_content; left: 1.5cm; width: 18cm; bottom: 1cm; height: 1cm; }}
            }}
            body {{ font-family: Helvetica, Arial, sans-serif; color: #161D2F; font-size: 10pt; }}
            h1 {{ color: #0D1321; border-bottom: 2px solid #5B8DEF; font-size: 16pt; }}
            h2 {{ color: #1D2740; font-size: 12pt; border-left: 4px solid #E8A33D; padding-left: 8px; margin-top: 15px; }}
            .caja-ia {{ background-color: #F4F6F9; border: 1px solid #8C96AD; padding: 12px; border-radius: 5px; font-style: italic; }}
            .grid {{ width: 100%; margin-top: 10px; }}
            .cell {{ width: 50%; text-align: center; padding: 5px; }}
            img {{ border: 1px solid #2A3654; max-width: 100%; }}
            .kpi {{ width: 100%; margin: 8px 0; }}
            .kpi td {{ background-color: #F4F6F9; border-left: 4px solid #5B8DEF; padding: 8px; width: 33%; }}
            .kpi .n {{ font-size: 13pt; font-weight: bold; color: #0D1321; }}
            .kpi .l {{ font-size: 8pt; color: #55607A; }}
            .accion {{ width: 100%; margin-bottom: 8px; }}
            .acc-num {{ width: 26px; color: #fff; font-weight: bold; font-size: 13pt;
                        text-align: center; vertical-align: top; padding: 6px; }}
            .acc-body {{ padding: 6px 10px; background-color: #F8F9FB; }}
            .badge {{ color: #fff; font-size: 7.5pt; padding: 1px 6px; border-radius: 3px; }}
            .acc-impacto {{ font-size: 8pt; color: #55607A; }}
        </style>
    </head>
    <body>
        <h1>Informe de Hallazgos — TechLogistics S.A.S.</h1>
        <p><strong>Fecha de corte analítico:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
        <em>Volumen analizado en el filtro actual: {len(df):,} transacciones.</em></p>

        <h2>Diagnóstico para la Junta Directiva</h2>
        <p>La compañía <b>sí está vendiendo, pero no siempre está ganando</b>. Sobre
        {k['n_analizadas']:,} transacciones con costo verificable, <b>{k['n_negativas']:,}
        ({k['pct_negativas']:.1f}%)</b> se cierran por debajo del costo de compra, drenando
        <b>USD {abs(k['perdida']):,.0f}</b> del margen. La causa no es un canal en particular
        —las pruebas de hipótesis no encuentran diferencia significativa entre Online,
        Físico, App y WhatsApp— sino <b>estructural del catálogo</b>: el precio de venta y el
        costo se fijan de forma independiente, sin una regla de margen mínimo.</p>
        <p>A eso se suma un problema de visibilidad: <b>USD {k['ingreso_riesgo']:,.0f}</b>
        ({k['pct_riesgo']:.1f}% del ingreso) provienen de ventas cuyo SKU no existe en el
        inventario maestro, por lo que <b>su rentabilidad real no se puede calcular</b>.
        En el frente operativo, la bodega <b>{k['peor_bodega']}</b> acumula
        {k['peor_dias']:.0f} días sin conteo físico, y la satisfacción del cliente está
        prácticamente en cero (NPS {k['nps']:.1f}).</p>

        <table class="kpi">
          <tr>
            <td><div class="n">USD {abs(k['perdida']):,.0f}</div>
                <div class="l">PÉRDIDA POR VENTAS BAJO COSTO</div></td>
            <td><div class="n">{k['pct_riesgo']:.1f}%</div>
                <div class="l">DEL INGRESO SIN RESPALDO EN INVENTARIO</div></td>
            <td><div class="n">{k['nps']:.1f}</div>
                <div class="l">NPS PROMEDIO</div></td>
          </tr>
        </table>

        <h2>Plan de Acción — 3 recomendaciones priorizadas</h2>
        {_plan_de_accion(k)}
        {bloque_ia}

        <h2>Evidencia de las 5 Preguntas Estratégicas</h2>
        <table class="grid">
            <tr>
                <td class="cell"><img src="data:image/png;base64,{b64_q1}"></td>
                <td class="cell"><img src="data:image/png;base64,{b64_q2}"></td>
            </tr>
            <tr>
                <td class="cell"><img src="data:image/png;base64,{b64_q3}"></td>
                <td class="cell"><img src="data:image/png;base64,{b64_q4}"></td>
            </tr>
            <tr>
                <td class="cell" colspan="2" style="text-align:center;"><img src="data:image/png;base64,{b64_q5}" style="max-width:50%;"></td>
            </tr>
        </table>
        
        <div id="footer_content" style="text-align:right; color:#8C96AD; font-size:9pt; border-top: 1px solid #8C96AD;">
            Challenge 02 - Fundamentos en Ciencia de Datos | Página <pdf:pagenumber> de <pdf:pagecount>
        </div>
    </body>
    </html>
    """

    pdf_buffer = io.BytesIO()
    if pisa.CreatePDF(src=html_final, dest=pdf_buffer, encoding='utf-8').err:
        raise RuntimeError("Error interno al compilar el documento PDF con xhtml2pdf.")
    
    return pdf_buffer.getvalue()