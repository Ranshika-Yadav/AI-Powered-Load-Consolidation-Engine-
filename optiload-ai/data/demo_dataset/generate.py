"""
Demo Dataset Generator — OptiLoad AI
Generates 200 synthetic shipments and 20 vehicles across major Indian cities
"""
import csv
import uuid
import random
import math
from datetime import datetime, timedelta

random.seed(2024)

# Major Indian cities with coordinates
CITIES = [
    ("Mumbai", 19.0760, 72.8777),
    ("Delhi", 28.7041, 77.1025),
    ("Bangalore", 12.9716, 77.5946),
    ("Chennai", 13.0827, 80.2707),
    ("Hyderabad", 17.3850, 78.4867),
    ("Pune", 18.5204, 73.8567),
    ("Ahmedabad", 23.0225, 72.5714),
    ("Kolkata", 22.5726, 88.3639),
    ("Jaipur", 26.9124, 75.7873),
    ("Surat", 21.1702, 72.8311),
    ("Lucknow", 26.8467, 80.9462),
    ("Nagpur", 21.1458, 79.0882),
    ("Indore", 22.7196, 75.8577),
    ("Bhopal", 23.2599, 77.4126),
    ("Visakhapatnam", 17.6868, 83.2185),
    ("Coimbatore", 11.0168, 76.9558),
    ("Kochi", 9.9312, 76.2673),
    ("Chandigarh", 30.7333, 76.7794),
    ("Guwahati", 26.1445, 91.7362),
    ("Bhubaneswar", 20.2961, 85.8245),
]

CARGO_TYPES = ["electronics", "textiles", "pharmaceuticals", "automotive_parts", 
                "food_perishable", "furniture", "chemicals", "machinery", "general", "fragile"]

VEHICLE_TYPES = {
    "mini_truck": {"capacity_weight": 2000, "capacity_volume": 10, "cost_per_km": 8, "fuel_efficiency": 14, "co2_per_km": 0.55},
    "medium_truck": {"capacity_weight": 7500, "capacity_volume": 30, "cost_per_km": 12, "fuel_efficiency": 10, "co2_per_km": 0.78},
    "large_truck": {"capacity_weight": 15000, "capacity_volume": 60, "cost_per_km": 15, "fuel_efficiency": 8, "co2_per_km": 0.92},
    "heavy_truck": {"capacity_weight": 25000, "capacity_volume": 100, "cost_per_km": 18, "fuel_efficiency": 6, "co2_per_km": 1.15},
    "refrigerated_truck": {"capacity_weight": 10000, "capacity_volume": 40, "cost_per_km": 20, "fuel_efficiency": 7, "co2_per_km": 1.05},
}

DRIVERS = [
    "Ramesh Kumar", "Suresh Patel", "Anil Sharma", "Vijay Singh", "Manoj Verma",
    "Rajesh Gupta", "Dinesh Yadav", "Sunil Mehta", "Prakash Nair", "Ganesh Rao",
    "Sanjay Dubey", "Ravi Tiwari", "Ajay Joshi", "Mukesh Shah", "Deepak Mishra",
    "Harish Iyer", "Naresh Pillai", "Umesh Bhat", "Devendra Jain", "Ashok More",
]


def add_noise(lat: float, lng: float, noise_km: float = 20.0) -> tuple:
    """Add slight random noise to coordinates (simulates different locations within city area)."""
    lat_noise = (random.random() - 0.5) * 2 * noise_km / 111.0
    lng_noise = (random.random() - 0.5) * 2 * noise_km / (111.0 * math.cos(math.radians(lat)))
    return round(lat + lat_noise, 6), round(lng + lng_noise, 6)


def generate_shipments(n: int = 200) -> list:
    shipments = []
    base_date = datetime(2026, 3, 10, 8, 0, 0)

    for i in range(n):
        origin_city = random.choice(CITIES)
        dest_city = random.choice([c for c in CITIES if c != origin_city])

        o_lat, o_lng = add_noise(origin_city[1], origin_city[2])
        d_lat, d_lng = add_noise(dest_city[1], dest_city[2])

        pickup_offset = timedelta(hours=random.randint(0, 48))
        pickup_time = base_date + pickup_offset
        transit_days = random.randint(1, 5)
        delivery_deadline = pickup_time + timedelta(hours=random.randint(24, transit_days * 24 + 12))

        cargo = random.choice(CARGO_TYPES)
        weight = round(random.uniform(100, 12000), 0)
        volume = round(random.uniform(0.5, 45.0), 1)
        priority = random.choices([1, 2, 3, 4, 5], weights=[20, 25, 30, 15, 10])[0]

        requirements = None
        if cargo == "food_perishable":
            requirements = "refrigeration_required"
        elif cargo == "fragile":
            requirements = "handle_with_care"
        elif cargo == "chemicals":
            requirements = "hazmat_certified_driver"

        shipments.append({
            "shipment_id": str(uuid.uuid4()),
            "origin_lat": o_lat,
            "origin_lng": o_lng,
            "destination_lat": d_lat,
            "destination_lng": d_lng,
            "origin_city": origin_city[0],
            "destination_city": dest_city[0],
            "weight": weight,
            "volume": volume,
            "pickup_time": pickup_time.strftime("%Y-%m-%d %H:%M:%S"),
            "delivery_deadline": delivery_deadline.strftime("%Y-%m-%d %H:%M:%S"),
            "priority": priority,
            "cargo_type": cargo,
            "special_requirements": requirements or "",
        })

    return shipments


def generate_vehicles(n: int = 20) -> list:
    vehicles = []
    veh_type_names = list(VEHICLE_TYPES.keys())
    used_drivers = random.sample(DRIVERS, min(n, len(DRIVERS)))

    for i in range(n):
        vtype_name = random.choice(veh_type_names)
        vtype = VEHICLE_TYPES[vtype_name]
        city = random.choice(CITIES)
        c_lat, c_lng = add_noise(city[1], city[2], noise_km=5)

        # Registration number
        states = ["MH", "DL", "KA", "TN", "TS", "GJ", "UP", "WB", "RJ"]
        reg = f"{random.choice(states)}{random.randint(10,99)}{random.choice('ABCDEFGHJKLMNPQRST')}{random.choice('ABCDEFGHJKLMNPQRST')}{random.randint(1000,9999)}"

        vehicles.append({
            "vehicle_id": str(uuid.uuid4()),
            "vehicle_type": vtype_name,
            "registration_number": reg,
            "capacity_weight": vtype["capacity_weight"],
            "capacity_volume": vtype["capacity_volume"],
            "cost_per_km": vtype["cost_per_km"],
            "fuel_efficiency": vtype["fuel_efficiency"],
            "co2_per_km": vtype["co2_per_km"],
            "availability_status": True,
            "current_lat": c_lat,
            "current_lng": c_lng,
            "current_city": city[0],
            "driver_name": used_drivers[i] if i < len(used_drivers) else f"Driver_{i}",
        })

    return vehicles


def save_csv(data: list, filepath: str, fieldnames: list = None):
    if not data:
        return
    if not fieldnames:
        fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"Saved {len(data)} records to {filepath}")


if __name__ == "__main__":
    import os
    output_dir = os.path.dirname(os.path.abspath(__file__))

    print("Generating OptiLoad AI Demo Dataset...")
    shipments = generate_shipments(200)
    vehicles = generate_vehicles(20)
    save_csv(shipments, os.path.join(output_dir, "shipments.csv"))
    save_csv(vehicles, os.path.join(output_dir, "vehicles.csv"))

    # Print stats
    cities_used = set(s["origin_city"] for s in shipments) | set(s["destination_city"] for s in shipments)
    print(f"\n📦 Generated {len(shipments)} shipments across {len(cities_used)} cities")
    print(f"🚛 Generated {len(vehicles)} vehicles")
    print(f"🏙️  Cities: {', '.join(sorted(cities_used))}")
    
    total_weight = sum(s["weight"] for s in shipments)
    total_volume = sum(s["volume"] for s in shipments)
    total_veh_weight_cap = sum(v["capacity_weight"] for v in vehicles)
    total_veh_vol_cap = sum(v["capacity_volume"] for v in vehicles)
    print(f"\n📊 Total shipment weight: {total_weight:,.0f} kg | Total volume: {total_volume:,.1f} m³")
    print(f"🚛 Total vehicle weight capacity: {total_veh_weight_cap:,} kg | Volume: {total_veh_vol_cap} m³")
    print(f"📈 Load factor (vol): {total_volume/total_veh_vol_cap:.1%}")
    print("\n✅ Demo dataset ready! Run docker-compose up to load it automatically.")
