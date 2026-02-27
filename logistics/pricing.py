def calculate_delivery_price(road_km: float, base: float = 300, per_km: float = 15, min_km: float = 15) -> float:
    """
    Calculate delivery price based on estimated road distance.
    Formula: base + per_km * max(km, min_km)
    """
    applicable_km = max(road_km, min_km)
    return base + (per_km * applicable_km)
