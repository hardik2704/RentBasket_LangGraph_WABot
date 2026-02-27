import sys
import os
import argparse
import csv
from .distance_engine import DistanceEngine
from .pricing import calculate_delivery_price

def main():
    parser = argparse.ArgumentParser(description="RentBasket Distance & Pricing CLI")
    parser.add_argument("--origin", required=True, help="Origin pincode")
    parser.add_argument("--dest", required=True, help="Destination pincode")
    parser.add_argument("--batch", help="CSV file for batch processing")
    
    args = parser.parse_args()
    engine = DistanceEngine()
    
    if args.batch:
        process_batch(engine, args.batch)
        return

    road_km = engine.estimate_road_km(args.origin, args.dest)
    if road_km is None:
        print(f"Error: Pincode {args.origin} or {args.dest} not found in database.")
        sys.exit(1)
        
    price = calculate_delivery_price(road_km)
    
    print(f"Origin: {args.origin}")
    print(f"Destination: {args.dest}")
    print(f"Estimated Road Distance: {road_km:.2f} km")
    print(f"Calculated Delivery Price: ₹{price:.2f}")

def process_batch(engine, batch_path):
    output_path = batch_path.replace(".csv", "_estimated.csv")
    with open(batch_path, 'r') as fin, open(output_path, 'w', newline='') as fout:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames + ["haversine_km", "estimated_road_km", "delivery_price"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            origin = row['origin']
            dest = row['dest']
            
            # Internal haversine for logging/output
            o_data = engine.pincode_db.get(origin)
            d_data = engine.pincode_db.get(dest)
            
            if o_data and d_data:
                hav = engine.haversine(o_data['lat'], o_data['lng'], d_data['lat'], d_data['lng'])
                road = engine.estimate_road_km(origin, dest)
                price = calculate_delivery_price(road)
                
                row["haversine_km"] = f"{hav:.2f}"
                row["estimated_road_km"] = f"{road:.2f}"
                row["delivery_price"] = f"{price:.2f}"
            else:
                row["haversine_km"] = "N/A"
                row["estimated_road_km"] = "N/A"
                row["delivery_price"] = "N/A"
            
            writer.writerow(row)
    print(f"Batch processing complete. Results saved to {output_path}")

if __name__ == "__main__":
    main()
