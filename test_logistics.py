from logistics import DistanceEngine, calculate_delivery_price

def test_distance():
    engine = DistanceEngine()
    
    # Test 1: Gurgaon to Noida
    # 122003 (Gurgaon) to 201301 (Noida)
    origin = "122003"
    dest = "201301"
    
    road_km = engine.estimate_road_km(origin, dest)
    price = calculate_delivery_price(road_km)
    
    print(f"Test 1: {origin} to {dest}")
    print(f"Road KM: {road_km:.2f}")
    print(f"Price: {price:.2f}")
    
    # Test 2: Gurgaon to Gurgaon
    # 122003 to 122018
    origin2 = "122003"
    dest2 = "122018"
    
    road_km2 = engine.estimate_road_km(origin2, dest2)
    price2 = calculate_delivery_price(road_km2)
    
    print(f"\nTest 2: {origin2} to {dest2}")
    print(f"Road KM: {road_km2:.2f}")
    print(f"Price: {price2:.2f}")

if __name__ == "__main__":
    test_distance()
