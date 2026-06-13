from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import io
import qrcode
from PIL import Image

def generate_bulk_qr_pdf(assets):
    """
    Generates an A4 PDF with 6 branded stickers per page.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Sticker dimensions (approx 90mm x 120mm)
    s_width = 90 * mm
    s_height = 120 * mm
    
    # Margins
    margin_x = (width - (2 * s_width)) / 3
    margin_y = (height - (3 * s_height)) / 4
    
    x_positions = [margin_x, margin_x * 2 + s_width]
    y_positions = [height - margin_y - s_height, height - 2*margin_y - 2*s_height, height - 3*margin_y - 3*s_height]
    
    asset_idx = 0
    while asset_idx < len(assets):
        for y in y_positions:
            for x in x_positions:
                if asset_idx >= len(assets):
                    break
                
                asset = assets[asset_idx]
                
                # Draw Sticker Border
                p.setStrokeColorRGB(0.8, 0.8, 0.8)
                p.rect(x, y, s_width, s_height)
                
                # Header (Blue bar)
                p.setFillColorRGB(0.12, 0.16, 0.23) # Slate-900
                p.rect(x, y + s_height - 15*mm, s_width, 15*mm, fill=1)
                
                # Header Text
                p.setFillColorRGB(1, 1, 1)
                p.setFont("Helvetica-Bold", 12)
                p.drawCentredString(x + s_width/2, y + s_height - 7*mm, "NOVA LITE")
                p.setFont("Helvetica-Bold", 6)
                p.drawCentredString(x + s_width/2, y + s_height - 11*mm, "LIMITED")
                
                # QR Code
                qr = qrcode.QRCode(version=1, box_size=10, border=2)
                qr.add_data(asset.get('qr_code_data', asset.get('asset_code')))
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert PIL to something ReportLab can use
                qr_buffer = io.BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                
                p.drawImage(io.BytesIO(qr_buffer.read()), x + 10*mm, y + 25*mm, width=70*mm, height=70*mm)
                
                # Footer Info
                p.setFillColorRGB(0.2, 0.2, 0.2)
                p.setFont("Helvetica-Bold", 10)
                p.drawCentredString(x + s_width/2, y + 15*mm, f"CODE: {asset['asset_code']}")
                
                p.setFillColorRGB(0.5, 0.5, 0.5)
                p.setFont("Helvetica", 8)
                p.drawCentredString(x + s_width/2, y + 10*mm, asset['name'][:40])
                
                asset_idx += 1
                
        if asset_idx < len(assets):
            p.showPage()
            
    p.save()
    buffer.seek(0)
    return buffer
