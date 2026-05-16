"""
distance.py — Real-world distance and travel time calculator
Using OpenRouteService Geocoding + Matrix API

Usage:
    python distance.py

The user only needs to provide addresses — no coordinates needed.
The system automatically converts addresses to coordinates using geocoding.
"""

import requests

# ── Paste your API key here ───────────────────────────────────────────────────
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc4MzMyNTBkYTBhMDRiYTg5MDQyYzkxNTQ4MDY0MzQ4IiwiaCI6Im11cm11cjY0In0="

# ── Warehouse address ─────────────────────────────────────────────────────────
WAREHOUSE_ADDRESS = "14 Rue du Chemin Vert, Paris"

# ── Client addresses (just plain addresses, no coordinates needed) ─────────────
CLIENT_ADDRESSES = [
    ("Hospital Saint-Antoine",  "184 Rue du Faubourg Saint-Antoine, Paris"),
    ("Pharmacie du Marais",     "10 Rue de Bretagne, Paris"),
    ("Pharmacie Bastille",      "6 Place de la Bastille, Paris"),
    ("Pharmacie Montparnasse",  "3 Rue de Rennes, Paris"),
    ("Pharmacie Neuilly",       "2 Rue de Chartres, Neuilly-sur-Seine"),
    ("Pharmacie Créteil",       "1 Rue Juliette Savar, Créteil"),
    ("Pharmacie Saint-Denis",   "2 Rue de la République, Saint-Denis"),
    ("Clinique du Parc",        "21 Rue Leblanc, Paris"),
    ("Clinique Levallois",      "22 Rue Voltaire, Levallois-Perret"),
    ("Clinique Aubervilliers",  "83 Rue Édouard Vaillant, Aubervilliers"),
]


# ── Step 1: Convert address to coordinates ────────────────────────────────────

def address_to_coordinates(name: str, address: str) -> dict:
    """
    Takes a plain text address and returns lat/lon using ORS Geocoding.
    """
    url = "https://api.openrouteservice.org/geocode/search"

    headers = {"Authorization": ORS_API_KEY}

    params = {
        "text": address,
        "boundary.country": "FR",  # limit results to France
        "size": 1                   # only top result
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"  Geocoding error for '{address}': {response.status_code} {response.text}")
        return None

    data = response.json()

    if not data["features"]:
        print(f"  No result found for address: '{address}'")
        return None

    feature = data["features"][0]
    lon, lat = feature["geometry"]["coordinates"]
    resolved = feature["properties"]["label"]

    print(f"  ✓ {name}: '{address}' → ({lat:.4f}, {lon:.4f})")

    return {
        "name": name,
        "address": address,
        "resolved": resolved,
        "lat": lat,
        "lon": lon
    }


def geocode_all(warehouse_address: str, client_addresses: list) -> tuple:
    """
    Geocode warehouse and all clients.
    Returns (warehouse_location, list_of_client_locations)
    """
    print("\n" + "="*65)
    print("  GEOCODING ADDRESSES")
    print("="*65)

    # Geocode warehouse
    print(f"\n  Warehouse:")
    warehouse = address_to_coordinates("Warehouse", warehouse_address)
    if warehouse is None:
        print("  ERROR: Could not geocode warehouse address.")
        exit(1)

    # Geocode all clients
    print(f"\n  Clients:")
    clients = []
    for name, address in client_addresses:
        location = address_to_coordinates(name, address)
        if location:
            clients.append(location)

    print(f"\n  Geocoded {len(clients)}/{len(client_addresses)} clients successfully.")
    return warehouse, clients


# ── Step 2: Get distance matrix ───────────────────────────────────────────────

def get_distance_matrix(locations: list) -> dict:
    """
    Send all coordinates to ORS in one API call.
    Returns a full matrix of distances (km) and durations (minutes).
    """
    url = "https://api.openrouteservice.org/v2/matrix/driving-car"

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    # ORS expects [longitude, latitude] — note the order
    coords = [[loc["lon"], loc["lat"]] for loc in locations]

    body = {
        "locations": coords,
        "metrics": ["distance", "duration"],
        "units": "km"
    }

    print(f"\n  Calling ORS Matrix API with {len(locations)} locations...")

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        print(f"  API Error {response.status_code}: {response.text}")
        return None

    data = response.json()

    # Convert durations from seconds to minutes
    distances = data["distances"]
    durations = [[s / 60 for s in row] for row in data["durations"]]

    return {
        "distances": distances,
        "durations": durations,
        "locations": locations
    }


# ── Step 3: Print results ─────────────────────────────────────────────────────

def print_warehouse_to_clients(matrix: dict):
    """
    Print distance and travel time from warehouse to each client.
    """
    locations = matrix["locations"]
    distances = matrix["distances"]
    durations = matrix["durations"]

    print("\n" + "="*65)
    print("  DISTANCES FROM WAREHOUSE TO ALL CLIENTS (by car)")
    print("="*65)
    print(f"  {'Client':<30} {'Distance':>10} {'Travel Time':>12}")
    print("-"*65)

    for i in range(1, len(locations)):
        name    = locations[i]["name"]
        dist_km = distances[0][i]
        dur_min = durations[0][i]
        print(f"  {name:<30} {dist_km:>8.1f} km  {dur_min:>8.0f} min")

    print("="*65)


def print_between_two(matrix: dict, name_a: str, name_b: str):
    """
    Print distance and time between any two locations by name.
    """
    locations = matrix["locations"]
    names     = [loc["name"] for loc in locations]

    if name_a not in names or name_b not in names:
        print(f"  Location not found.")
        return

    i = names.index(name_a)
    j = names.index(name_b)

    dist = matrix["distances"][i][j]
    dur  = matrix["durations"][i][j]

    print(f"\n  {name_a} → {name_b}")
    print(f"  Distance:    {dist:.1f} km")
    print(f"  Travel time: {dur:.0f} min")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Step 1: Geocode all addresses → get coordinates automatically
    warehouse, clients = geocode_all(WAREHOUSE_ADDRESS, CLIENT_ADDRESSES)

    # Step 2: Build location list (warehouse first, then clients)
    all_locations = [warehouse] + clients

    # Step 3: Get real road distances in one API call
    print("\n" + "="*65)
    print("  CALCULATING ROAD DISTANCES")
    print("="*65)
    matrix = get_distance_matrix(all_locations)

    if matrix is None:
        print("  Failed to get distance matrix.")
        exit(1)

    # Step 4: Print results
    print_warehouse_to_clients(matrix)

    # Example: distance between two specific clients
    print_between_two(matrix, "Hospital Saint-Antoine", "Pharmacie Bastille")
    print_between_two(matrix, "Pharmacie Neuilly", "Clinique Levallois")
    print_between_two(matrix, "Hospital Saint-Antoine", "Pharmacie Créteil")

    print("\n  Done. Matrix ready for routing algorithm.")