import os
import re
import io
import markdown
from xhtml2pdf import pisa

def generar_reporte_gerencial_bytes() -> bytes:
    """Lee el Markdown, inyecta las gráficas y retorna los bytes del PDF."""
    # Como el archivo estará en services/, subimos un nivel para llegar a la raíz
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ruta_md = os.path.join(base_dir, "hallazgos_gerenciales.md")

    if not os.path.exists(ruta_md):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_md}")

    # 1. Leer el archivo Markdown
    with open(ruta_md, "r", encoding="utf-8") as f:
        md_texto = f.read()

    # 2. Reemplazar rutas de imágenes (charts/...) por rutas absolutas para xhtml2pdf
    md_texto = re.sub(
        r"`(charts/[\w_]+\.png)`",
        f'<br><img src="{base_dir}/outputs/\\1" width="550"><br>',
        md_texto
    )

    # 3. Convertir Markdown a HTML
    html_body = markdown.markdown(md_texto, extensions=['tables'])

    # 4. Envolver en estructura HTML con CSS de tu PALETTE corporativa
    html_final = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4 portrait;
                margin: 2cm;
                @frame header_frame {{
                    -pdf-frame-content: header_content;
                    left: 2cm; width: 17cm; top: 1cm; height: 1cm;
                }}
                @frame footer_frame {{
                    -pdf-frame-content: footer_content;
                    left: 2cm; width: 17cm; bottom: 1cm; height: 1cm;
                }}
            }}
            body {{ font-family: Helvetica, Arial, sans-serif; color: #161D2F; font-size: 11pt; line-height: 1.5; }}
            h1 {{ color: #0D1321; border-bottom: 2px solid #5B8DEF; padding-bottom: 5px; font-size: 18pt; }}
            h2 {{ color: #E4572E; margin-top: 25px; font-size: 14pt; }}
            h3 {{ color: #1D2740; font-size: 12pt; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px; }}
            th {{ background-color: #1D2740; color: #EDF1F7; padding: 8px; border: 1px solid #2A3654; text-align: left; }}
            td {{ padding: 8px; border: 1px solid #8C96AD; }}
            img {{ margin-top: 15px; margin-bottom: 15px; border: 1.5px solid #2A3654; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div id="header_content" style="text-align: left; border-bottom: 1px solid #8C96AD; padding-bottom: 3px; color:#5B8DEF;">
            <strong>TechLogistics S.A.S.</strong> | Consultoría Senior
        </div>
        
        {html_body}
        
        <div id="footer_content" style="text-align:right; color:#8C96AD; font-size:9pt; border-top: 1px solid #8C96AD; padding-top: 3px;">
            Challenge 02 - Fundamentos en Ciencia de Datos | Página <pdf:pagenumber> de <pdf:pagecount>
        </div>
    </body>
    </html>
    """

    # 5. Generar PDF en memoria (buffer)
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(src=html_final, dest=pdf_buffer, encoding='utf-8')

    if pisa_status.err:
        raise RuntimeError("Error interno al compilar el documento PDF.")

    return pdf_buffer.getvalue()