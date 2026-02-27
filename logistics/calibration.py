from .distance_engine import DistanceEngine

def calibrate_factors(sample_data_path: str):
    """
    Learn factors from sample actual distances.
    sample_data_path: CSV with [origin, dest, actual_km]
    """
    engine = DistanceEngine()
    samples = []
    
    if not os.path.exists(sample_data_path):
        print(f"Sample file {sample_data_path} not found.")
        return
        
    with open(sample_data_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append((row['origin'], row['dest'], float(row['actual_km'])))
            
    engine.calibrate(samples)
    print("New factors (multi-band calibrated):")
    print(engine.factors)

if __name__ == "__main__":
    import os
    import csv
    # Mock sample data for demo if not provided
    sample_file = "calibration_samples.csv"
    if not os.path.exists(sample_file):
        with open(sample_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["origin", "dest", "actual_km"])
            writer.writerow(["122003", "201301", "52.5"]) # Actual road distance Noida-Gurgaon
            writer.writerow(["122003", "122018", "12.0"])
    
    calibrate_factors(sample_file)
