import pytest
from backend.agents.moderator.policy_rules import (
    check_object_safety_signals,
    check_product_unusable,
    check_image_quality_signals,
    check_stock_photo_detected,
    check_contact_signals,
    check_price_anomaly,
    evaluate_policy_rules
)


def test_check_object_safety_signals_banned():
    # Test banned product keyword
    res = check_object_safety_signals("person", "electronics", "some description")
    assert res.get("banned_object") is True
    assert "animal_in_image_ambiguous" not in res


def test_check_object_safety_signals_animal_product():
    # Test animal keyword indicating product in sale
    res = check_object_safety_signals("dog", "pets", "vendo hermoso cachorro")
    assert res.get("banned_object") is True
    assert "animal_in_image_ambiguous" not in res


def test_check_object_safety_signals_animal_accessory():
    # Test animal keyword that is an accessory (not banned)
    res = check_object_safety_signals("dog", "pets", "collar para perro de cuero")
    assert not res.get("banned_object")
    assert not res.get("animal_in_image_ambiguous")


def test_check_object_safety_signals_animal_ambiguous():
    # Test animal keyword with no indicators (ambiguous)
    res = check_object_safety_signals("dog", "pets", "solo un perro en la foto")
    assert not res.get("banned_object")
    assert res.get("animal_in_image_ambiguous") is True


def test_check_product_unusable():
    assert check_product_unusable(False, "good") is True
    assert check_product_unusable(True, "rotten") is True
    assert check_product_unusable(True, "good") is False


def test_check_image_quality_signals():
    res = check_image_quality_signals("low")
    assert res.get("low_quality_image") is True
    assert res.get("unverifiable_image") is True
    
    assert check_image_quality_signals("good") == {}


def test_check_stock_photo_detected():
    assert check_stock_photo_detected("screenshot") is True
    assert check_stock_photo_detected("live") is False


def test_check_contact_signals():
    res = check_contact_signals(True)
    assert res.get("external_contact") is True
    assert res.get("contact_info_detected") is True
    
    assert check_contact_signals(False) == {}


def test_check_price_anomaly_thresholds():
    # Price within limits
    assert check_price_anomaly(100.0, 50.0, 200.0, "title") is False
    # Price too low
    assert check_price_anomaly(30.0, 50.0, 200.0, "title") is True
    # Price too high
    assert check_price_anomaly(300.0, 50.0, 200.0, "title") is True


def test_check_price_anomaly_fallback():
    # High value product below fallback price
    assert check_price_anomaly(10.0, 0.0, float('inf'), "macbook pro") is True
    # High value product normal price
    assert check_price_anomaly(1500.0, 0.0, float('inf'), "macbook pro") is False
    # Low value product cheap price
    assert check_price_anomaly(10.0, 0.0, float('inf'), "silla de pino") is False


def test_evaluate_policy_rules():
    features = {
        "primary_object": "dog",
        "object_category": "pets",
        "product_condition": "good",
        "image_quality": "good",
        "image_type": "live",
        "contact_info_detected": False,
        "is_sellable": True
    }
    input_data = {
        "title": "Silla con perro de fondo",
        "description": "Una hermosa silla de madera.",
        "price": 100.0
    }
    # No price thresholds, normal title
    signals = evaluate_policy_rules(features, input_data, 0.0, float('inf'))
    assert not signals.get("banned_object")
    assert signals.get("animal_in_image_ambiguous") is True # dog in primary_object, not accessory
