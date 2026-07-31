import base64
import plotly.graph_objects as go
from weasyprint import HTML
import pandas as pd

def generate_board_report(df: pd.DataFrame) -> bytes:
    """
    Genera un reporte PDF gerencial extrayendo gráficas exactas del dashboard.
    """
    # ==========================================
    # 1. EXTRACCIÓN ESTRICTA DE GRÁFICAS (Plotly)
    # ==========================================
    
    # Gráfica P1: Fuga de capital por canal
    df_c = df.dropna(subset=["Margen_Utilidad_USD"])
    df_c = df_c[~df_c["Costo_Atipico"].astype(str).str.lower().isin(["true","1"])]
    
    por_canal = df_c.groupby("Canal_Venta").apply(lambda g: pd.Series({
        "pct_neg": (g["Margen_Utilidad_USD"]<0).mean()*100
    }), include_groups=False).sort_values("pct_neg")
    
    fig1 = go.Figure(go.Bar(
        x=por_canal["pct_neg"], y=por_canal.index, orientation="h",
        marker_color="#E4572E", text=[f"{v:.1f}%" for v in por_canal["pct_neg"]], textposition="outside"
    ))
    fig1.update_layout(title="% Transacciones con Margen Negativo", height=320, template="plotly_white")
    # Requiere la librería 'kaleido' para exportar a PNG en memoria
    img1_b64 = base64.b64encode(fig1.to_image(format="png", engine="kaleido")).decode()

    # Gráfica P3: Venta Invisible (Ingreso en Riesgo)
    ing_total = df["Ingreso_Bruto"].sum()
    fant = df[df["Es_Venta_Fantasma"]]
    ing_fant = fant["Ingreso_Bruto"].sum()
    
    fig3 = go.Figure(go.Pie(
        labels=["Catalogado", "Sin catálogo (en riesgo)"],
        values=[ing_total - ing_fant, ing_fant],
        marker_colors=["#5B8DEF", "#E4572E"], hole=0.5
    ))
    fig3.update_layout(title="Proporción de Ingreso en Riesgo (USD)", height=320, template="plotly_white")
    img3_b64 = base64.b64encode(fig3.to_image(format="png", engine="kaleido")).decode()

    # ==========================================
    # 2. NARRATIVA Y ESTRUCTURA HTML (WeasyPrint)
    # ==========================================
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ 
                size: A4; 
                margin: 20mm 15mm; 
                background-color: #F8F9FA; 
            }}
            body {{ font-family: 'Helvetica Neue', Helvetica, sans-serif; color: #1D2740; margin: 0; padding: 0; }}
            * {{ box-sizing: border-box; }}
            .header {{ 
                background: #161D2F; color: white; padding: 30px; 
                text-align: center; margin: -20mm -15mm 20px -15mm; 
            }}
            .header h1 {{ margin: 0; font-size: 22pt; letter-spacing: 1px; color: #5B8DEF; }}
            .header p {{ margin: 10px 0 0 0; font-size: 11pt; opacity: 0.9; }}
            .consultant {{ text-align: right; font-style: italic; color: #8C96AD; margin-bottom: 25px; font-size: 10pt; }}
            .section {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #E4572E; page-break-inside: avoid; }}
            h2 {{ color: #161D2F; font-size: 14pt; margin-top: 0; border-bottom: 1px solid #E2E6EA; padding-bottom: 8px; }}
            .chart-container {{ text-align: center; margin: 15px 0; }}
            .chart-container img {{ max-width: 85%; border: 1px solid #E2E6EA; border-radius: 4px; }}
            p {{ text-align: justify; line-height: 1.6; font-size: 10.5pt; }}
            .action-box {{ background: #0D1321; color: white; padding: 12px; border-radius: 4px; font-size: 10pt; margin-top: 10px; border-left: 3px solid #3FA796; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>TECHLOGISTICS S.A.S.</h1>
            <p>Informe Ejecutivo para Junta Directiva · Data Support System</p>
        </div>
        
        <div class="consultant">
            Consultor Principal: Cristian Gómez<br>
            Área: Operaciones & Analytics
        </div>

        <div class="section">
            <h2>1. Fuga de Capital y Estructura de Precios</h2>
            <p>Tras la integración de las fuentes de datos operativos, el análisis de rentabilidad evidencia una vulnerabilidad crítica que trasciende a los canales de distribución individuales. Como se observa en la gráfica derivada directamente de la facturación consolidada, un volumen insostenible de transacciones se está operando a pérdida, desmintiendo la hipótesis inicial que atribuía la falla exclusivamente al canal Online.</p>
            <div class="chart-container"><img src="data:image/png;base64,{img1_b64}"></div>
            <div class="action-box">
                <strong>Decisión Estratégica Recomendada:</strong> La matriz de fuga es estructural. Se sugiere congelar la política de descuentos parametrizados y ejecutar una auditoría de costos a nivel SKU para reestructurar el pricing dinámico corporativo.
            </div>
        </div>

        <div class="section">
            <h2>2. Exposición por "Venta Invisible" (Control de Inventario)</h2>
            <p>Un segundo vector de riesgo operativo se ha detectado en la sincronización entre el catálogo de inventario y la facturación. Una porción altamente material del ingreso bruto ingresa por productos sin trazabilidad (Venta Fantasma).</p>
            <div class="chart-container"><img src="data:image/png;base64,{img3_b64}"></div>
            <div class="action-box">
                <strong>Decisión Estratégica Recomendada:</strong> Actualmente existen USD {ing_fant:,.0f} en riesgo contable directo. Es imperativo forzar un <em>hard-stop</em> en el CRM/POS que impida facturar SKUs que no existan previamente en el Warehouse Management System (WMS).
            </div>
        </div>
    </body>
    </html>
    """
    
    # 3. CONVERSIÓN A PDF
    return HTML(string=html_content).write_pdf()