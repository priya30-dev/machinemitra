"""Printable QR stickers. Scanning one opens MachineMitra with that machine
already selected (?machine=M1), so the owner only has to speak the problem."""
import io

import qrcode
from PIL import Image, ImageDraw, ImageFont


def machine_url(base_url: str, machine_id: str) -> str:
    return f"{base_url.rstrip('/')}/?machine={machine_id}"


def sticker_png(url: str, title: str, subtitle: str) -> bytes:
    qr = qrcode.QRCode(border=2, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    code = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    w = code.width
    canvas = Image.new("RGB", (w, w + 120), "white")
    canvas.paste(code, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        big = ImageFont.load_default(size=28)
        small = ImageFont.load_default(size=18)
    except TypeError:  # older Pillow
        big = small = ImageFont.load_default()
    draw.text((w // 2, w + 20), "Scan to report a breakdown", fill="black", font=small, anchor="mt")
    draw.text((w // 2, w + 50), title, fill="black", font=big, anchor="mt")
    draw.text((w // 2, w + 88), subtitle, fill="#555555", font=small, anchor="mt")
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
