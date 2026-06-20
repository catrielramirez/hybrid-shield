from typing import List, Literal
from pydantic import BaseModel, Field

# ================================================================
# Tipos y Literales compartidos
# ================================================================
ViolationCategory = Literal["contact_info", "illegal_product", "none", "violence", "sexual"]
ProductCondition = Literal["new", "like_new", "good", "fair", "poor", "damaged", "rotten"]
ImageQuality = Literal["high", "medium", "low", "ambiguous"]
ImageType = Literal["original_photo", "stock_photo", "screenshot", "edited_composite", "unknown"]

# Literal para forzar las categorías de Firestore
ProductCategory = Literal[
    "calzado",
    "alimentos_y_bebidas",
    "autos_y_camionetas", 
    "accesorios_celulares",
    "accesorios_para_mascotas",
    "audio_y_auriculares",
    "motos", 
    "grandes_electrodomesticos", 
    "pequeños_electrodomesticos",
    "ropa",
    "relojes",
    "piletas",
    "perfumes",
    "papeleria",
    "notebooks_y_computadoras",
    "neumaticos",
    "muebles_interior",
    "muebles_exterior",
    "monitores_y_televisores",
    "microfonos",
    "maquinas",
    "lamparas",
    "instrumentos_musicales",
    "herramientas_y_construccion",
    "consolas_y_videojuegos",
    "componentes_pc",
    "camaras_y_fotografia",
    "bazar_y_cocina", 
    "unknown"
]

# ================================================================
# Modelos de Datos para el Grafo de Moderación
# ================================================================

class MultimodalProductFeatures(BaseModel):
    """
    Modelo estricto para la extracción de características multimedia.
    Garantiza que la salida sea un JSON válido y tipado por el LLM Multimodal.
    """
    primary_object: str = Field(
        description="The main commercial item identified in the image."
    )
    object_category: ProductCategory = Field(
        description="General marketplace category of the object. MUST be an exact match to the allowed enumerations."
    )
    objects_detected: List[str] = Field(
        description="List of all relevant secondary objects or elements visible in the background."
    )
    text_in_image: List[str] = Field(
        description="Array of all text strings, labels, or watermarks extracted from the image."
    )
    contact_info_detected: bool = Field(
        description="True if phone numbers, WhatsApp links, emails, social media handles, or QR codes are visible."
    )
    visual_dissonance: bool = Field(
        description="True if there is an explicit mismatch or contradiction between the image and the text metadata."
    )
    product_condition: ProductCondition = Field(
        description="The physical state of the item based strictly on visual evidence."
    )
    condition_issue_detected: bool = Field(
        description="True if the visual physical state directly contradicts a claim of being completely new."
    )
    image_quality: ImageQuality = Field(
        description="Overall visual clarity and resolution of the provided image file. Use 'ambiguous' if it is too dark or blurry to identify the object."
    )
    image_quality_score: float = Field(
        description="A score from 0.0 to 1.0 evaluating the overall quality, brightness, and sharpness of the image."
    )
    image_type: ImageType = Field(
        description="Classification of the image origin (e.g., user's own original photo, generic stock photo, or screenshot)."
    )
    fraud_signals: List[str] = Field(
        description="List of specific observations indicating risk (e.g., cropped watermarks, competitor logos)."
    )
    is_sellable: bool = Field(
        description="High-level evaluation of whether this item complies with marketplace safety and quality standards."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0 reflecting the certainty of the visual extraction."
    )


class SafetyAnalysis(BaseModel):
    """Esquema para el análisis de seguridad inicial (Pre-Filter)."""
    thought_process: str = Field(
        description="Step-by-step reasoning explaining if the text contains explicit violations."
    )
    is_critical: bool = Field(
        description="True if the text violates platform rules and must be blocked immediately."
    )
    reason: str = Field(
        description="Brief explanation in Spanish detailing the specific rule broken, or empty string if safe."
    )
    violation_type: Literal["contact_info", "illegal_product", "none"] = Field(
        description="The specific policy group matched during text analysis."
    )


class PolicyViolation(BaseModel):
    """Detalle individual de una infracción de política detectada por el RAG."""
    policy_id: str = Field(description="The unique identifier or code of the internal policy rule.")
    factor: str = Field(description="The specific element or feature that triggered the violation.")
    explanation: str = Field(description="Detailed explanation in Spanish of how the product breaks this specific policy.")


class ExplanationResponse(BaseModel):
    """Esquema para la justificación final consolidada del producto."""
    reasoning: str = Field(
        description="Concise automated explanation (2-3 sentences max) in Spanish why the product was flagged or approved."
    )
    policy_violations: List[PolicyViolation] = Field(
        description="List of structural policy objects matched against the product features. Empty if approved."
    )