import io
from PIL import Image

def optimize_image(image_bytes: bytes) -> bytes:
    """
    Optimizes an image by resizing its maximum dimension to 768px (preserving aspect ratio)
    and converting it to WebP format with quality 75.

    Args:
        image_bytes (bytes): Original image bytes.

    Returns:
        bytes: Optimized image bytes in WebP format.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Convert to RGB to ensure compatibility with WebP format
        # WebP supports alpha, so we convert to RGBA if alpha channel is present, else RGB
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA") if "A" in img.mode else img.convert("RGB")

        # Resize maintaining aspect ratio
        max_size = (768, 768)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        output_buffer = io.BytesIO()
        # Save as WebP
        img.save(output_buffer, format="webp", quality=75)
        
        return output_buffer.getvalue()
