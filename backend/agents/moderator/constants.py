RISK_WEIGHTS = {
    # Críticos absolutos
    "banned_object": 1.0,
    "external_contact": 1.0,

    # Graves
    "product_unusable": 0.75,

    # Imagen no verificable — sola ya garantiza HITL
    "unverifiable_image": 0.40,

    # Sospechosos pero no definitivos
    "visual_dissonance": 0.25,
    "price_anomaly": 0.25,

    # Señales débiles
    "low_quality_image": 0.10,

    # Evidencia contextual
    "policy_match": 0.15,
}