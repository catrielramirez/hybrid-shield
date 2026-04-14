import logging
import json
from vertexai.generative_models import GenerativeModel, Part

logger = logging.getLogger("moderation_pipeline")

# Lazy Global Model cache
_models = {}

def get_gemini_model(model_name: str = "gemini-1.5-flash"):
    """Lazily initializes the GenerativeModel to prevent startup failures."""
    if model_name not in _models:
        try:
            _models[model_name] = GenerativeModel(
                model_name,
                generation_config={"response_mime_type": "application/json"}
            )
        except Exception as e:
            logger.error(f"Failed to initialize GenerativeModel ({model_name}): {e}")
            raise
    return _models[model_name]

def _clean_and_parse_json(text: str) -> dict:
    """Handles Markdown code block prefixes and json parsing with error handling."""
    try:
        clean_json = text.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.removeprefix("```json").removesuffix("```").strip()
        elif clean_json.startswith("```"):
            clean_json = clean_json.removeprefix("```").removesuffix("```").strip()
        
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}. Raw text snippet: {text[:100]}...")
        return {"error": "parsing_failed", "details": str(e)}

def analyze_listing_safety(title: str, description: str) -> dict:
    """
    Analyzes an e-commerce listing for critical safety violations using gemini-1.5-flash.
    Returns a dict with 'is_critical' and 'reason'.
    """
    prompt = f"""
    Analyze this e-commerce listing for critical policy violations: weapons, drugs, or explicit adult content.
    Title: {title}
    Description: {description}

    Return ONLY a JSON object:
    {{
        "is_critical": boolean,
        "reason": "short explanation"
    }}
    """
    try:
        model = get_gemini_model("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return _clean_and_parse_json(response.text)
    except Exception as e:
        logger.error(f"Safety analysis failed: {e}")
        return {"is_critical": False, "error": str(e)}

def extract_multimodal_features(gcs_uri: str, product_data: dict) -> dict:
    """
    Extracts structured features from a product image and metadata using gemini-1.5-pro.
    Handles Part.from_uri and multimodal prompt execution.
    """
    prompt = f"""
    Analyze this e-commerce listing for marketplace moderation.

    Title: {product_data.get('title', 'N/A')}
    Description: {product_data.get('description', 'N/A')}

    Carefully inspect the product image and extract the following structured evidence:

    1. **Primary Object & Category**: Identify the main object and classify it into one of:
       [electronics, clothing, food, furniture, vehicle, animal, person, other].

    2. **Objects Detected**: List all distinct objects found in the image.

    3. **Text Content**: Extract any visible text, brand names, or labels.

    4. **Contact Info Detection**: Detect phone numbers, WhatsApp/social media handles, or external links.

    5. **Visual Dissonance**: Check if the image matches the title and description accurately.

    6. **Product Condition**: Classify as [new, good, used, damaged, rotten, very_poor_quality].

    7. **Usability Assessment (is_sellable)**: 
       Return `false` if the product appears: rotten, broken/unusable, contaminated, biological waste, or contains animal body parts/human remains.

    8. **Image Quality & Type**: 
       - Quality: [high, medium, low].
       - Type: [real_photo, stock_photo, screenshot, ai_generated, unknown].

    9. **Fraud & Risk Signals**: Identify signals like inconsistent backgrounds, watermarks, or screenshots of other apps.

    Return ONLY a valid JSON object with this schema:
    {{
      "primary_object": string,
      "object_category": "electronics" | "clothing" | "food" | "furniture" | "vehicle" | "animal" | "person" | "other",
      "objects_detected": string[],
      "text_in_image": string[],
      "contact_info_detected": boolean,
      "visual_dissonance": boolean,
      "product_condition": "new" | "good" | "used" | "damaged" | "rotten" | "very_poor_quality",
      "condition_issue_detected": boolean,
      "image_quality": "high" | "medium" | "low",
      "image_type": "real_photo" | "stock_photo" | "screenshot" | "ai_generated" | "unknown",
      "fraud_signals": string[],
      "is_sellable": boolean,
      "confidence": number
    }}
    """
    try:
        image_part = Part.from_uri(uri=gcs_uri, mime_type="image/jpeg")
        model = get_gemini_model("gemini-1.5-pro")
        response = model.generate_content([image_part, prompt])
        return _clean_and_parse_json(response.text)
    except Exception as e:
        logger.error(f"Multimodal extraction failed for {gcs_uri}: {e}")
        return {"error": "multimodal_analysis_failed", "details": str(e)}
