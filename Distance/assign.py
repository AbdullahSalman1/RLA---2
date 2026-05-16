"""
assign.py — Delivery assignment to vehicles and drivers
Built on top of distance.py

Logic:
    Delivery → Vehicle  (based on delivery constraints)
    Vehicle  → Driver   (based on refrigeration certification only)

Run:
    python assign.py
"""

import requests

# ── API Key ───────────────────────────────────────────────────────────────────
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc4MzMyNTBkYTBhMDRiYTg5MDQyYzkxNTQ4MDY0MzQ4IiwiaCI6Im11cm11cjY0In0="

# ── Warehouse ─────────────────────────────────────────────────────────────────
WAREHOUSE_ADDRESS = "14 Rue du Chemin Vert, Paris"

# ── Fleet ─────────────────────────────────────────────────────────────────────
VEHICLES = [
    {"id": "V1", "type": "small",        "label": "Small Van 1",      "max_stops": 30},
    {"id": "V2", "type": "small",        "label": "Small Van 2",      "max_stops": 30},
    {"id": "V3", "type": "small",        "label": "Small Van 3",      "max_stops": 30},
    {"id": "V4", "type": "large",        "label": "Large Van 1",      "max_stops": 20},
    {"id": "V5", "type": "large",        "label": "Large Van 2",      "max_stops": 20},
    {"id": "V6", "type": "refrigerated", "label": "Refrigerated Van", "max_stops": 15},
]

# ── Drivers ───────────────────────────────────────────────────────────────────
DRIVERS = [
    {"id": "D1", "name": "Alexandre M.", "certified_refrigerated": True,  "shift_start": "06:30", "max_hours": 8},
    {"id": "D2", "name": "Fatima B.",    "certified_refrigerated": True,  "shift_start": "06:30", "max_hours": 8},
    {"id": "D3", "name": "Thomas L.",    "certified_refrigerated": False, "shift_start": "07:00", "max_hours": 8},
    {"id": "D4", "name": "Yasmine K.",   "certified_refrigerated": False, "shift_start": "07:00", "max_hours": 8},
    {"id": "D5", "name": "Romain D.",    "certified_refrigerated": False, "shift_start": "07:00", "max_hours": 8},
]

# ── Sample orders for today ───────────────────────────────────────────────────
# Each order has:
#   name        : client name
#   address     : plain street address
#   priority    : critical / high / normal
#   is_cold     : True if temperature-sensitive (vaccines, insulin)
#   is_suburban : True if outside Paris (petite couronne)
#   boxes       : number of boxes (volume indicator)

ORDERS = [
    {"id": "ORD-001", "name": "Hospital Saint-Antoine",  "address": "184 Rue du Faubourg Saint-Antoine, Paris", "priority": "critical", "is_cold": False, "is_suburban": False, "boxes": 5},
    {"id": "ORD-002", "name": "Pharmacie du Marais",     "address": "10 Rue de Bretagne, Paris",                "priority": "high",     "is_cold": False, "is_suburban": False, "boxes": 2},
    {"id": "ORD-003", "name": "Pharmacie Bastille",      "address": "6 Place de la Bastille, Paris",            "priority": "high",     "is_cold": True,  "is_suburban": False, "boxes": 3},
    {"id": "ORD-004", "name": "Pharmacie Montparnasse",  "address": "3 Rue de Rennes, Paris",                   "priority": "normal",   "is_cold": False, "is_suburban": False, "boxes": 2},
    {"id": "ORD-005", "name": "Pharmacie Neuilly",       "address": "2 Rue de Chartres, Neuilly-sur-Seine",     "priority": "high",     "is_cold": False, "is_suburban": True,  "boxes": 4},
    {"id": "ORD-006", "name": "Pharmacie Créteil",       "address": "1 Rue Juliette Savar, Créteil",            "priority": "normal",   "is_cold": False, "is_suburban": True,  "boxes": 6},
    {"id": "ORD-007", "name": "Pharmacie Saint-Denis",   "address": "2 Rue de la République, Saint-Denis",      "priority": "normal",   "is_cold": True,  "is_suburban": True,  "boxes": 3},
    {"id": "ORD-008", "name": "Clinique du Parc",        "address": "21 Rue Leblanc, Paris",                    "priority": "high",     "is_cold": False, "is_suburban": False, "boxes": 8},
    {"id": "ORD-009", "name": "Clinique Levallois",      "address": "22 Rue Voltaire, Levallois-Perret",         "priority": "normal",   "is_cold": False, "is_suburban": True,  "boxes": 10},
    {"id": "ORD-010", "name": "Clinique Aubervilliers",  "address": "83 Rue Édouard Vaillant, Aubervilliers",   "priority": "normal",   "is_cold": False, "is_suburban": True,  "boxes": 7},
]


# ── Step 1: Geocode address → coordinates ─────────────────────────────────────

def geocode(name, address):
    url     = "https://api.openrouteservice.org/geocode/search"
    headers = {"Authorization": ORS_API_KEY}
    params  = {"text": address, "boundary.country": "FR", "size": 1}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200 or not response.json()["features"]:
        print(f"  Could not geocode: {address}")
        return None

    feature  = response.json()["features"][0]
    lon, lat = feature["geometry"]["coordinates"]
    return {"name": name, "address": address, "lat": lat, "lon": lon}


# ── Step 2: Assign delivery → vehicle ────────────────────────────────────────

def assign_vehicle(order, vehicle_stops):
    """
    Decide which vehicle should handle this order.

    Rules (in priority order):
      1. Cold chain       → refrigerated van only (hard constraint)
      2. Suburban         → large van preferred (range)
      3. City / urgent    → small van preferred (agile)
      4. Overflow         → next available vehicle with capacity
    """

    # Rule 1: cold chain → must go to refrigerated van
    if order["is_cold"]:
        for v in VEHICLES:
            if v["type"] == "refrigerated":
                if vehicle_stops[v["id"]] < v["max_stops"]:
                    return v["id"], "cold chain → refrigerated van"
        return None, "cold chain order but refrigerated van is full"

    # Rule 2: suburban → large van
    if order["is_suburban"]:
        for v in VEHICLES:
            if v["type"] == "large":
                if vehicle_stops[v["id"]] < v["max_stops"]:
                    return v["id"], "suburban → large van"
        # large vans full, fall through to small vans
        reason_prefix = "suburban but large vans full → "
    else:
        reason_prefix = ""

    # Rule 3: city / urgent → small van
    for v in VEHICLES:
        if v["type"] == "small":
            if vehicle_stops[v["id"]] < v["max_stops"]:
                return v["id"], f"{reason_prefix}city/urgent → small van"

    # Rule 4: overflow — any vehicle with capacity
    for v in VEHICLES:
        if vehicle_stops[v["id"]] < v["max_stops"]:
            return v["id"], "overflow → first available vehicle"

    return None, "no vehicle available — all full"


# ── Step 3: Assign vehicle → driver ───────────────────────────────────────────

def assign_drivers(vehicle_assignments):
    """
    Assign a driver to each vehicle that has orders.
    Rule: refrigerated van → certified driver only.
          all other vans   → any available driver.
    """
    used_vehicles = set(v["vehicle"] for v in vehicle_assignments.values() if v["vehicle"] is not None)

    # Split drivers into certified and non-certified
    certified     = [d for d in DRIVERS if d["certified_refrigerated"]]
    non_certified = [d for d in DRIVERS if not d["certified_refrigerated"]]

    driver_assignment = {}   # vehicle_id → driver
    assigned_drivers  = set()

    # First pass: assign certified driver to refrigerated van
    for v in VEHICLES:
        if v["id"] in used_vehicles and v["type"] == "refrigerated":
            for d in certified:
                if d["id"] not in assigned_drivers:
                    driver_assignment[v["id"]] = d
                    assigned_drivers.add(d["id"])
                    break

    # Second pass: assign remaining drivers to other vehicles
    all_remaining_drivers = [d for d in DRIVERS if d["id"] not in assigned_drivers]
    remaining_index = 0

    for v in VEHICLES:
        if v["id"] in used_vehicles and v["id"] not in driver_assignment:
            if remaining_index < len(all_remaining_drivers):
                driver_assignment[v["id"]] = all_remaining_drivers[remaining_index]
                remaining_index += 1
            else:
                driver_assignment[v["id"]] = None  # no driver available

    return driver_assignment


# ── Print results ─────────────────────────────────────────────────────────────

def print_assignments(order_vehicle, vehicle_stops, driver_assignment):

    print("\n" + "="*70)
    print("  ORDER ASSIGNMENTS")
    print("="*70)
    print(f"  {'Order ID':<10} {'Client':<28} {'Priority':<10} {'Cold':<6} {'Vehicle':<20} {'Reason'}")
    print("-"*70)

    for order in ORDERS:
        vid    = order_vehicle.get(order["id"], {}).get("vehicle")
        reason = order_vehicle.get(order["id"], {}).get("reason", "unassigned")
        vlabel = next((v["label"] for v in VEHICLES if v["id"] == vid), "UNASSIGNED")
        cold   = "❄️" if order["is_cold"] else ""
        print(f"  {order['id']:<10} {order['name']:<28} {order['priority']:<10} {cold:<6} {vlabel:<20} {reason}")

    print("\n" + "="*70)
    print("  VEHICLE SUMMARY")
    print("="*70)
    print(f"  {'Vehicle':<22} {'Stops':>6} {'Max':>5}   {'Driver':<20} {'Shift'}")
    print("-"*70)

    for v in VEHICLES:
        stops  = vehicle_stops[v["id"]]
        if stops == 0:
            continue
        driver = driver_assignment.get(v["id"])
        dname  = driver["name"] if driver else "⚠ No driver available"
        shift  = driver["shift_start"] if driver else ""
        cert   = " ❄️ certified" if (driver and driver["certified_refrigerated"]) else ""
        print(f"  {v['label']:<22} {stops:>6} / {v['max_stops']:<4}  {dname:<20} {shift}{cert}")

    print("="*70)

    # Warnings
    unassigned = [o for o in ORDERS if order_vehicle.get(o["id"], {}).get("vehicle") is None]
    if unassigned:
        print(f"\n  ⚠ UNASSIGNED ORDERS ({len(unassigned)}):")
        for o in unassigned:
            print(f"    - {o['id']} {o['name']}: {order_vehicle.get(o['id'], {}).get('reason')}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Sort orders: critical first, then high, then normal
    priority_rank = {"critical": 0, "high": 1, "normal": 2}
    sorted_orders = sorted(ORDERS, key=lambda o: priority_rank[o["priority"]])

    # Track how many stops each vehicle has
    vehicle_stops = {v["id"]: 0 for v in VEHICLES}

    # Track assignment result per order
    order_vehicle = {}

    print("\n" + "="*70)
    print("  ASSIGNING ORDERS TO VEHICLES")
    print("="*70)

    for order in sorted_orders:
        vid, reason = assign_vehicle(order, vehicle_stops)
        order_vehicle[order["id"]] = {"vehicle": vid, "reason": reason}

        if vid:
            vehicle_stops[vid] += 1
            status = f"→ {next(v['label'] for v in VEHICLES if v['id'] == vid)}"
        else:
            status = "→ UNASSIGNED"

        print(f"  {order['id']} {order['name']:<28} {status} ({reason})")

    # Assign drivers to vehicles
    driver_assignment = assign_drivers(order_vehicle)

    # Print full summary
    print_assignments(order_vehicle, vehicle_stops, driver_assignment)