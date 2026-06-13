import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

def generate_nova_sticker(qr_data, asset_code, asset_name):
    """
    Generates a professional PNG sticker with NovaSuite branding.
    Includes a header, the QR code, and the asset details.
    """
    # 1. Create a base canvas (Sticker size: 400x500)
    width, height = 400, 500
    sticker = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(sticker)
    
    # 2. Add Branding Header (Blue bar at top)
    header_height = 80
    draw.rectangle([0, 0, width, header_height], fill='#1e293b') # Slate-900 style
    
    # Try to load a font, fallback to default
    try:
        # Assuming a common font path on Windows/Linux
        font_path = "arial.ttf" 
        font_large = ImageFont.truetype(font_path, 32)
        font_small = ImageFont.truetype(font_path, 18)
        font_bold = ImageFont.truetype(font_path, 22)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold = ImageFont.load_default()

    # Draw "Nova Lite" Text
    draw.text((width/2, header_height/2 - 10), "NOVA LITE", fill='white', anchor="mm", font=font_large)
    draw.text((width/2, header_height/2 + 20), "LIMITED", fill='white', anchor="mm", font=font_small)
    
    # 3. Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize QR and paste it
    qr_img = qr_img.resize((300, 300))
    sticker.paste(qr_img, (50, 100))
    
    # 4. Add Asset Details Footer
    footer_start = 400
    draw.line([20, footer_start, width-20, footer_start], fill='#e2e8f0', width=2)
    
    draw.text((width/2, footer_start + 30), f"CODE: {asset_code}", fill='#475569', anchor="mm", font=font_bold)
    draw.text((width/2, footer_start + 65), asset_name[:30], fill='#94a3b8', anchor="mm", font=font_small)
    
    # 5. Add Border to Sticker
    draw.rectangle([0, 0, width-1, height-1], outline='#cbd5e1', width=1)

    # Save to bytes
    img_byte_arr = io.BytesIO()
    sticker.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr
