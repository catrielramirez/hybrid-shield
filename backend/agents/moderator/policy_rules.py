def check_object_safety_signals(primary_object_lower: str, object_category_lower: str, listing_text_lower: str) -> dict:
    """Evaluates banned objects and animal products in listings. Expects pre-lowercased arguments."""
    signals = {}
    banned_product_keywords = ["person", "human", "baby", "child", "blood", "corpse", "body"]
    animal_keywords = ["dog", "puppy", "cat", "kitten", "animal", "bird", "fish", "reptile"]
    combined_text = f"{primary_object_lower} {object_category_lower}"
    
    if any(keyword in combined_text for keyword in banned_product_keywords):
        signals["banned_object"] = True
    elif any(keyword in combined_text for keyword in animal_keywords):
        animal_as_product_indicators = [
            "vendo", "venta", "cachorro", "cría", "camada",
            "mascota en venta", "adopción", "permuto"
        ]
        accessory_indicators = [
            "para perro", "para gato", "para mascota", "accesorio",
            "ropa para", "cama para", "colchón para", "piloto para",
            "juguete para", "collar", "correa", "bowl", "comedero"
        ]
        is_accessory = any(ind in listing_text_lower for ind in accessory_indicators)
        is_animal_product = any(ind in listing_text_lower for ind in animal_as_product_indicators)
        if is_animal_product and not is_accessory:
            signals["banned_object"] = True
        elif not is_accessory:
            signals["animal_in_image_ambiguous"] = True
            
    return signals


def check_product_unusable(is_sellable: bool, product_condition: str) -> bool:
    """Checks whether the product is unsellable or in extremely poor condition."""
    return not is_sellable or product_condition in ["rotten", "damaged", "very_poor_quality"]


def check_image_quality_signals(image_quality: str) -> dict:
    """Sets low quality and unverifiable image flags if image quality is low."""
    if image_quality == "low":
        return {"low_quality_image": True, "unverifiable_image": True}
    return {}


def check_stock_photo_detected(image_type: str) -> bool:
    """Checks if the image type is a screenshot or stock photo."""
    return image_type in ["screenshot", "stock_photo"]


def check_contact_signals(contact_info_detected: bool) -> dict:
    """Sets external contact and contact info detected flags if true."""
    if contact_info_detected:
        return {"external_contact": True, "contact_info_detected": True}
    return {}


def check_price_anomaly(price: float, min_market_price: float, max_market_price: float, title_lower: str) -> bool:
    """Checks for price anomalies against dynamic limits or a default high-value catalog heuristic."""
    if min_market_price > 0.0 or max_market_price < float('inf'):
        return bool(price < min_market_price or price > max_market_price)
    else:
        high_value_keywords = ["macbook", "iphone", "ipad", "samsung", "tv", "playstation", "xbox", "nvidia"]
        is_high_value = any(kw in title_lower for kw in high_value_keywords)
        return bool(is_high_value and 0 < price < 50)


def evaluate_policy_rules(
    features: dict,
    input_data: dict,
    min_market_price: float,
    max_market_price: float
) -> dict:
    """Aggregates all policy validation checks using pre-normalized lowercase representations."""
    title_lower = input_data.get("title", "").lower()
    description_lower = input_data.get("description", "").lower()
    listing_text_lower = f"{title_lower} {description_lower}"
    primary_object_lower = features.get("primary_object", "").lower()
    object_category_lower = features.get("object_category", "").lower()
    
    product_condition = features.get("product_condition", "")
    image_quality = features.get("image_quality", "")
    image_type = features.get("image_type", "")
    contact_info_detected = features.get("contact_info_detected", False)
    is_sellable = features.get("is_sellable", True)
    
    price = float(input_data.get("price", 0))
    
    signals = {}
    
    # 1. Banned objects & animal checks
    signals.update(check_object_safety_signals(primary_object_lower, object_category_lower, listing_text_lower))
    
    # 2. Product usability
    if check_product_unusable(is_sellable, product_condition):
        signals["product_unusable"] = True
        
    # 3. Image quality
    signals.update(check_image_quality_signals(image_quality))
    
    # 4. Stock photo
    if check_stock_photo_detected(image_type):
        signals["stock_photo_detected"] = True
        
    # 5. External contact
    signals.update(check_contact_signals(contact_info_detected))
    
    # 6. Visual dissonance and condition issue (directly mapped from features)
    signals["visual_dissonance"] = bool(features.get("visual_dissonance", False))
    signals["condition_issue"] = bool(features.get("condition_issue_detected", False))
    
    # 7. Price anomaly
    signals["price_anomaly"] = check_price_anomaly(price, min_market_price, max_market_price, title_lower)
    
    return signals
