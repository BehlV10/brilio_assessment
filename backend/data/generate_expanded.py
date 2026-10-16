import json
import random
from pathlib import Path

random.seed(42)

# Load base 12 sample listings
DATA_DIR = Path(__file__).resolve().parent
with open(DATA_DIR / "sample_listings.json", "r", encoding="utf-8") as f:
    base_listings = json.load(f)

cities_meta = [
    {"city": "Springfield", "state": "VA", "zip": "22150", "lat": 38.789, "lon": -77.187},
    {"city": "Fairfax", "state": "VA", "zip": "22030", "lat": 38.846, "lon": -77.306},
    {"city": "Reston", "state": "VA", "zip": "20190", "lat": 38.958, "lon": -77.357},
    {"city": "Vienna", "state": "VA", "zip": "22180", "lat": 38.901, "lon": -77.265},
    {"city": "Manassas", "state": "VA", "zip": "20110", "lat": 38.751, "lon": -77.475},
    {"city": "Chantilly", "state": "VA", "zip": "20151", "lat": 38.891, "lon": -77.432},
    {"city": "Arlington", "state": "VA", "zip": "22201", "lat": 38.881, "lon": -77.106},
    {"city": "Alexandria", "state": "VA", "zip": "22314", "lat": 38.805, "lon": -77.047},
    {"city": "McLean", "state": "VA", "zip": "22101", "lat": 38.934, "lon": -77.177},
    {"city": "Falls Church", "state": "VA", "zip": "22046", "lat": 38.882, "lon": -77.171},
    {"city": "Ashburn", "state": "VA", "zip": "20147", "lat": 39.043, "lon": -77.487},
    {"city": "Bethesda", "state": "MD", "zip": "20814", "lat": 38.984, "lon": -77.094},
]

street_names = [
    "Maple Ave", "Oak St", "Pine Rd", "Cedar Blvd", "Elm Ct",
    "Washington St", "Jefferson Way", "Franklin Dr", "Park Ave",
    "Highland Terrace", "Sunset Blvd", "River Rd", "Lakeview Dr",
    "Commonwealth Ave", "Sycamore Ln", "Magnolia Ct", "Colonial Blvd"
]

property_types = [
    ("Condo", 1, 2, 600, 1100, 290000, 520000),
    ("Townhome", 2, 4, 1200, 2200, 480000, 780000),
    ("Single Family", 3, 5, 1800, 3800, 650000, 1450000),
    ("Luxury Estate", 4, 6, 3200, 5500, 1200000, 2100000),
]

features = [
    "Bright open layout with high ceilings.",
    "Updated kitchen with quartz countertops and stainless appliances.",
    "Fenced backyard with custom deck, perfect for entertaining.",
    "Spacious 2-car garage with EV charging.",
    "Steps to Metro station, shops, and restaurants.",
    "Hardwood flooring throughout the main level.",
    "Community pool, clubhouse, and fitness center.",
    "Private cul-de-sac location backing to mature trees.",
    "Pet friendly building with dog run and wash station.",
    "No pets permitted per HOA guidelines.",
    "Recently renovated bathrooms and fresh interior paint.",
    "Corner lot with wrap-around front porch and mature landscaping."
]

all_listings = list(base_listings)
existing_ids = {f"{item['source']}_{item['id']}" for item in all_listings}

# Generate 100 new listings
generated_count = 0
while generated_count < 100:
    city_info = random.choice(cities_meta)
    p_type, min_bed, max_bed, min_sq, max_sq, min_p, max_p = random.choice(property_types)
    
    beds = random.randint(min_bed, max_bed)
    baths = round(beds * 0.5 + random.choice([0.5, 1.0, 1.5]), 1)
    sqft = random.randint(min_sq, max_sq)
    price = round(random.randint(min_p, max_p) / 1000) * 1000
    
    st_num = random.randint(10, 999)
    st_name = random.choice(street_names)
    unit_str = f", Unit {random.randint(1, 12)}{random.choice(['A','B','C'])}" if p_type == "Condo" else ""
    address = f"{st_num} {st_name}{unit_str}"
    
    lat = round(city_info["lat"] + random.uniform(-0.02, 0.02), 4)
    lon = round(city_info["lon"] + random.uniform(-0.02, 0.02), 4)
    
    # Listed date between 2026-07-01 and 2026-10-10
    month = random.choice([7, 8, 9, 10])
    day = random.randint(1, 28)
    listed_date = f"2026-{month:02d}-{day:02d}"
    
    status = random.choices(["active", "pending", "sold"], weights=[78, 18, 4])[0]
    
    desc_snippets = random.sample(features, k=2)
    desc = f"{p_type}. " + " ".join(desc_snippets)
    
    source = random.choice(["MLS_A", "MLS_B", "MLS_C"])
    item_id = f"{source[4:]}{generated_count + 100}"
    
    key = f"{source}_{item_id}"
    if key in existing_ids:
        continue
    existing_ids.add(key)
    
    listing = {
        "id": item_id,
        "source": source,
        "address": address,
        "city": city_info["city"],
        "state": city_info["state"],
        "zip": city_info["zip"],
        "price": price,
        "bedrooms": beds,
        "bathrooms": baths,
        "sqft": sqft,
        "latitude": lat,
        "longitude": lon,
        "listedDate": listed_date,
        "status": status,
        "description": desc,
    }
    all_listings.append(listing)
    generated_count += 1

    # In 10% of cases, generate a cross-syndicated duplicate on another MLS
    if random.random() < 0.12 and generated_count < 100:
        alt_source = "MLS_B" if source == "MLS_A" else "MLS_A"
        alt_id = f"{alt_source[4:]}{generated_count + 100}"
        # Minor address variation: "St" vs "Street", etc.
        alt_address = address.replace(" Ave", " Avenue").replace(" St", " Street").replace(" Ct", " Court").replace("Unit ", "Apt ")
        alt_price = price + random.choice([-2500, 0, 3000, 5000])
        duplicate_listing = dict(listing)
        duplicate_listing.update({
            "id": alt_id,
            "source": alt_source,
            "address": alt_address,
            "price": alt_price,
            "listedDate": f"2026-{month:02d}-{max(1, day - 2):02d}",
        })
        all_listings.append(duplicate_listing)
        generated_count += 1

# Write to expanded_listings.json
with open(DATA_DIR / "expanded_listings.json", "w", encoding="utf-8") as f:
    json.dump(all_listings, f, indent=2)

print(f"Successfully generated expanded dataset with {len(all_listings)} listings.")
