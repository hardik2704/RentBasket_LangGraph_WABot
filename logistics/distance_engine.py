import math
import csv
import os
from typing import Dict, Optional, Tuple

class DistanceEngine:
    """
    Estimates road distance between Indian pincodes using haversine and a detour model.
    """
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            csv_path = os.path.join(os.path.dirname(__file__), "data/pincodes.csv")
        self.csv_path = csv_path
        self.pincode_db: Dict[str, Dict] = {}
        self._load_data()
        
        # Default detour model factors
        self.factors = {
            "under_5km": 1.35,
            "5_20km": 1.25,
            "20_80km": 1.18,
            "80_250km": 1.12,
            "over_250km": 1.08,
            "same_city_adj": -0.05,
            "diff_state_adj": 0.03,
            "min_clamp": 1.05,
            "max_clamp": 1.45
        }

    def _load_data(self):
        if not os.path.exists(self.csv_path):
            return
        with open(self.csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.pincode_db[row['pincode']] = {
                    "lat": float(row['lat']),
                    "lng": float(row['lng']),
                    "city": row['city'],
                    "state": row['state']
                }

    def haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate straight-line distance in km."""
        R = 6371  # Earth radius in km
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(d_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def estimate_road_km(self, origin_pincode: str, dest_pincode: str) -> Optional[float]:
        """Estimate road distance between two pincodes."""
        origin = self.pincode_db.get(origin_pincode)
        dest = self.pincode_db.get(dest_pincode)
        
        if not origin or not dest:
            return None
            
        haversine_km = self.haversine(origin['lat'], origin['lng'], dest['lat'], dest['lng'])
        
        # Base factor based on distance band
        if haversine_km < 5:
            factor = self.factors["under_5km"]
        elif haversine_km < 20:
            factor = self.factors["5_20km"]
        elif haversine_km < 80:
            factor = self.factors["20_80km"]
        elif haversine_km < 250:
            factor = self.factors["80_250km"]
        else:
            factor = self.factors["over_250km"]
            
        # Adjustments
        if origin['city'] == dest['city']:
            factor += self.factors["same_city_adj"]
        if origin['state'] != dest['state']:
            factor += self.factors["diff_state_adj"]
            
        # Clamp
        factor = max(self.factors["min_clamp"], min(self.factors["max_clamp"], factor))
        
        return haversine_km * factor

    def calibrate(self, actual_data: list):
        """
        Simple calibration (WIP: would normally use regression).
        Expects list of (origin, dest, actual_km).
        For now, just adjusts the global scale if bias is detected.
        """
        errors = []
        for o, d, actual in actual_data:
            est = self.estimate_road_km(o, d)
            if est:
                errors.append(actual / est)
        
        if errors:
            avg_bias = sum(errors) / len(errors)
            # Apply bias correction to all factors
            for key in ["under_5km", "5_20km", "20_80km", "80_250km", "over_250km"]:
                self.factors[key] *= avg_bias
            print(f"Calibrated factors by multiplier: {avg_bias:.4f}")
