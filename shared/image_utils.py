import io
from PIL import Image

def optimize_image(image_bytes: bytes, max_size: int = 768, quality: int = 88) -> bytes:
    """
    Optimiza una imagen para análisis multimodal de Trust & Safety.
    Mantiene el aspect ratio, redimensiona el lado mayor a max_size y convierte a WebP.
    """
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convertir a RGB si viene en RGBA (transparencias de PNG) para evitar fallos en WebP/JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    # Redimensionar manteniendo relación de aspecto
    img.thumbnail((max_size, max_size), Image.Resampling.LANCEZOL)
    
    output = io.BytesIO()
    # Guardar en formato WebP de alta fidelidad
    img.save(output, format="WEBP", quality=quality, method=6) # method 6 es la compresión más lenta pero de mejor calidad
    return output.getvalue()