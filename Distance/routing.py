"""
routing.py — Route sequencing using Clarke-Wright Savings + 2-opt improvement
Built on top of assign.py

Pipeline:
    1. Take assigned orders per vehicle (from assign.py)
    2. Clarke-Wright: compute savings, merge stops into efficient routes
    3. 2-opt: improve each route by fixing crossing paths
    4. Time simulation: compute arrival times, flag late deliveries

Run:
    python routing.py
"""

import requests

# ── API Key ───────────────────────────────────────────────────────────────────
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc4MzMyNTBkYTBhMDRiYTg5MDQyYzkxNTQ4MDY0MzQ4IiwiaCI6Im11cm11cjY0In0="

# ── Warehouse ─────────────────────────────────────────────────────────────────
WAREHOUSE = {"id": "W0", "name": "Warehouse", "address": "14 Rue du Chemin Vert, Paris"}

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

# ── Orders for today ──────────────────────────────────────────────────────────
ORDERS = [
    {"id": "ORD-001", "name": "Hospital Saint-Antoine",  "address": "184 Rue du Faubourg Saint-Antoine, Paris", "priority": "critical", "is_cold": False, "is_suburban": False, "boxes": 5,  "time_window": ("06:30", "09:00")},
    {"id": "ORD-002", "name": "Pharmacie du Marais",     "address": "10 Rue de Bretagne, Paris",                "priority": "high",     "is_cold": False, "is_suburban": False, "boxes": 2,  "time_window": ("08:00", "10:00")},
    {"id": "ORD-003", "name": "Pharmacie Bastille",      "address": "6 Place de la Bastille, Paris",            "priority": "high",     "is_cold": True,  "is_suburban": False, "boxes": 3,  "time_window": ("08:00", "11:00")},
    {"id": "ORD-004", "name": "Pharmacie Montparnasse",  "address": "3 Rue de Rennes, Paris",                   "priority": "normal",   "is_cold": False, "is_suburban": False, "boxes": 2,  "time_window": ("09:00", "17:00")},
    {"id": "ORD-005", "name": "Pharmacie Neuilly",       "address": "2 Rue de Chartres, Neuilly-sur-Seine",     "priority": "high",     "is_cold": False, "is_suburban": True,  "boxes": 4,  "time_window": ("08:00", "10:00")},
    {"id": "ORD-006", "name": "Pharmacie Créteil",       "address": "1 Rue Juliette Savar, Créteil",            "priority": "normal",   "is_cold": False, "is_suburban": True,  "boxes": 6,  "time_window": ("09:00", "17:00")},
    {"id": "ORD-007", "name": "Pharmacie Saint-Denis",   "address": "2 Rue de la République, Saint-Denis",      "priority": "normal",   "is_cold": True,  "is_suburban": True,  "boxes": 3,  "time_window": ("09:00", "17:00")},
    {"id": "ORD-008", "name": "Clinique du Parc",        "address": "21 Rue Leblanc, Paris",                    "priority": "high",     "is_cold": False, "is_suburban": False, "boxes": 8,  "time_window": ("08:00", "12:00")},
    {"id": "ORD-009", "name": "Clinique Levallois",      "address": "22 Rue Voltaire, Levallois-Perret",         "priority": "normal",   "is_cold": False, "is_suburban": True,  "boxes": 10, "time_window": ("09:00", "17:00")},
    {"id": "ORD-010", "name": "Clinique Aubervilliers",  "address": "83 Rue Édouard Vaillant, Aubervilliers",   "priority": "normal",   "is_cold": False, "is_suburban": True,  "boxes": 7,  "time_window": ("09:00", "17:00")},
]


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — GEOCODING
# ═══════════════════════════════════════════════════════════════════════════════

def geocode(name, address):
    """Convert address to lat/lon using ORS Geocoding API."""
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


def geocode_all(orders):
    """Geocode warehouse and all orders. Returns location list."""
    print("\n" + "="*65)
    print("  STEP 1 — GEOCODING ADDRESSES")
    print("="*65)

    # Geocode warehouse first
    wh = geocode(WAREHOUSE["name"], WAREHOUSE["address"])
    wh["id"] = "W0"
    print(f"  ✓ Warehouse: ({wh['lat']:.4f}, {wh['lon']:.4f})")

    # Geocode all orders
    locations = [wh]
    for order in orders:
        loc = geocode(order["name"], order["address"])
        if loc:
            loc["id"]          = order["id"]
            loc["priority"]    = order["priority"]
            loc["time_window"] = order["time_window"]
            loc["boxes"]       = order["boxes"]
            loc["is_cold"]     = order["is_cold"]
            loc["is_suburban"] = order["is_suburban"]
            locations.append(loc)
            print(f"  ✓ {order['name']}: ({loc['lat']:.4f}, {loc['lon']:.4f})")

    return locations


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — DISTANCE MATRIX
# ═══════════════════════════════════════════════════════════════════════════════

def get_distance_matrix(locations):
    """Get real road distances between all locations in one API call."""
    print("\n" + "="*65)
    print("  STEP 2 — FETCHING DISTANCE MATRIX")
    print("="*65)

    url     = "https://api.openrouteservice.org/v2/matrix/driving-car"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    coords  = [[loc["lon"], loc["lat"]] for loc in locations]

    body = {
        "locations": coords,
        "metrics":   ["distance", "duration"],
        "units":     "km"
    }

    print(f"  Calling ORS Matrix API with {len(locations)} locations...")
    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        print(f"  API Error {response.status_code}: {response.text}")
        return None, None

    data      = response.json()
    distances = data["distances"]                                      # km
    durations = [[s / 60 for s in row] for row in data["durations"]]  # minutes

    print(f"  ✓ Matrix ready: {len(locations)}x{len(locations)} ({len(locations)**2} pairs)")
    return distances, durations


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — VEHICLE ASSIGNMENT (from assign.py logic)
# ═══════════════════════════════════════════════════════════════════════════════

def assign_orders_to_vehicles(orders):
    """Assign each order to a vehicle based on constraints."""
    priority_rank  = {"critical": 0, "high": 1, "normal": 2}
    sorted_orders  = sorted(orders, key=lambda o: priority_rank[o["priority"]])
    vehicle_stops  = {v["id"]: 0 for v in VEHICLES}
    vehicle_orders = {v["id"]: [] for v in VEHICLES}

    print("\n" + "="*65)
    print("  STEP 3 — ASSIGNING ORDERS TO VEHICLES")
    print("="*65)

    for order in sorted_orders:
        vid = None

        # Rule 1: cold chain → refrigerated van only
        if order["is_cold"]:
            for v in VEHICLES:
                if v["type"] == "refrigerated" and vehicle_stops[v["id"]] < v["max_stops"]:
                    vid = v["id"]
                    reason = "cold chain → refrigerated"
                    break

        # Rule 2: suburban → large van
        elif order["is_suburban"]:
            for v in VEHICLES:
                if v["type"] == "large" and vehicle_stops[v["id"]] < v["max_stops"]:
                    vid = v["id"]
                    reason = "suburban → large van"
                    break
            # fallback to small if large full
            if not vid:
                for v in VEHICLES:
                    if v["type"] == "small" and vehicle_stops[v["id"]] < v["max_stops"]:
                        vid = v["id"]
                        reason = "suburban (large full) → small van"
                        break

        # Rule 3: city → small van
        else:
            for v in VEHICLES:
                if v["type"] == "small" and vehicle_stops[v["id"]] < v["max_stops"]:
                    vid = v["id"]
                    reason = "city → small van"
                    break

        if vid:
            vehicle_orders[vid].append(order)
            vehicle_stops[vid] += 1
            vlabel = next(v["label"] for v in VEHICLES if v["id"] == vid)
            print(f"  {order['id']} {order['name']:<28} → {vlabel} ({reason})")
        else:
            print(f"  {order['id']} {order['name']:<28} → ⚠ UNASSIGNED (no capacity)")

    return vehicle_orders


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — CLARKE-WRIGHT SAVINGS ALGORITHM
# ═══════════════════════════════════════════════════════════════════════════════

def clarke_wright(stop_indices, distances, warehouse_idx=0):
    """
    Clarke-Wright Savings Algorithm.

    Idea:
        Start: each stop has its own dedicated round trip from warehouse.
        Saving(i,j) = dist(W→i) + dist(W→j) - dist(i→j)
        → merging i and j into one trip saves this much distance.
        Sort savings descending, merge pairs greedily into one route.

    Returns: ordered list of stop indices (the route)
    """
    if not stop_indices:
        return []

    if len(stop_indices) == 1:
        return list(stop_indices)

    # Compute savings for every pair of stops
    savings = []
    for i in stop_indices:
        for j in stop_indices:
            if i >= j:
                continue
            saving = (distances[warehouse_idx][i] +
                      distances[warehouse_idx][j] -
                      distances[i][j])
            savings.append((saving, i, j))

    # Sort by saving descending — highest saving merged first
    savings.sort(reverse=True, key=lambda x: x[0])

    # Build route by merging pairs greedily
    # Each stop tracks its position in the growing route
    route = list(stop_indices)  # start with arbitrary order

    # Apply merges: reorder so high-saving pairs are adjacent
    visited  = set()
    ordered  = []

    for saving, i, j in savings:
        if i not in visited and j not in visited:
            ordered.append(i)
            ordered.append(j)
            visited.add(i)
            visited.add(j)

    # Add any remaining stops not yet in ordered list
    for idx in stop_indices:
        if idx not in visited:
            ordered.append(idx)

    return ordered


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — 2-OPT IMPROVEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def two_opt(route, distances):
    """
    2-opt local search improvement.

    Idea:
        Take any two edges in the route.
        Reverse the segment between them.
        If the new route is shorter → keep it.
        Repeat until no improvement found.

    Example:
        Before: W → A → D → B → C → W   (edges A-D and B-C cross)
        After:  W → A → B → D → C → W   (shorter, no crossing)
    """
    if len(route) <= 2:
        return route

    improved = True
    best_route = route[:]

    while improved:
        improved = False
        for i in range(len(best_route) - 1):
            for j in range(i + 2, len(best_route)):

                # Current distance: edge(i → i+1) + edge(j → j+1)
                current = distances[best_route[i]][best_route[i+1]] + \
                          distances[best_route[j]][best_route[(j+1) % len(best_route)]]

                # New distance after reversing segment between i+1 and j
                new = distances[best_route[i]][best_route[j]] + \
                      distances[best_route[i+1]][best_route[(j+1) % len(best_route)]]

                if new < current - 0.001:   # improvement found
                    # Reverse the segment between i+1 and j
                    best_route[i+1:j+1] = best_route[i+1:j+1][::-1]
                    improved = True

    return best_route


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — DRIVER ASSIGNMENT
# ═══════════════════════════════════════════════════════════════════════════════

def assign_drivers(vehicle_orders):
    """
    Assign a driver to each vehicle that has orders.
    Refrigerated van → certified driver only.
    All other vans   → any available driver.
    """
    certified     = [d for d in DRIVERS if d["certified_refrigerated"]]
    non_certified = [d for d in DRIVERS if not d["certified_refrigerated"]]

    driver_assignment = {}
    assigned_drivers  = set()

    # First: assign certified driver to refrigerated van
    for v in VEHICLES:
        if v["type"] == "refrigerated" and vehicle_orders.get(v["id"]):
            for d in certified:
                if d["id"] not in assigned_drivers:
                    driver_assignment[v["id"]] = d
                    assigned_drivers.add(d["id"])
                    break

    # Then: assign remaining drivers to other vehicles
    remaining = [d for d in DRIVERS if d["id"] not in assigned_drivers]
    idx = 0
    for v in VEHICLES:
        if vehicle_orders.get(v["id"]) and v["id"] not in driver_assignment:
            if idx < len(remaining):
                driver_assignment[v["id"]] = remaining[idx]
                idx += 1

    return driver_assignment


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — TIME SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

def time_to_min(t):
    """Convert HH:MM to minutes since midnight."""
    h, m = map(int, t.split(":"))
    return h * 60 + m

def min_to_time(m):
    """Convert minutes since midnight to HH:MM."""
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"

SERVICE_TIME_MIN = 10  # average unloading time per stop in minutes

def simulate_route(route_indices, locations, durations, driver):
    """
    Walk through the sequenced route and compute:
    - Arrival time at each stop
    - Whether the delivery is within the time window
    - Total route duration
    """
    results     = []
    current_min = time_to_min(driver["shift_start"])
    max_end_min = current_min + driver["max_hours"] * 60

    for idx in route_indices:
        loc = locations[idx]

        # Travel time from previous position (first stop from warehouse = index 0)
        prev_idx    = route_indices[route_indices.index(idx) - 1] if route_indices.index(idx) > 0 else 0
        travel_min  = durations[prev_idx][idx]
        arrival_min = current_min + travel_min

        # Wait if arriving before time window opens
        tw_start = time_to_min(loc["time_window"][0])
        tw_end   = time_to_min(loc["time_window"][1])

        if arrival_min < tw_start:
            arrival_min = tw_start  # driver waits

        is_late      = arrival_min > tw_end
        departure_min = arrival_min + SERVICE_TIME_MIN

        results.append({
            "id":           loc["id"],
            "name":         loc["name"],
            "arrival":      min_to_time(arrival_min),
            "departure":    min_to_time(departure_min),
            "window":       f"{loc['time_window'][0]}–{loc['time_window'][1]}",
            "is_late":      is_late,
            "late_by_min":  max(0, int(arrival_min - tw_end)),
        })

        current_min = departure_min

        # Check driver shift limit
        if departure_min > max_end_min:
            results[-1]["shift_exceeded"] = True

    total_duration = current_min - time_to_min(driver["shift_start"])
    return results, total_duration


# ═══════════════════════════════════════════════════════════════════════════════
# PRINT FINAL ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

def print_routes(vehicle_routes):
    print("\n" + "="*70)
    print("  FINAL DELIVERY PLAN")
    print("="*70)

    total_late = 0

    for entry in vehicle_routes:
        v       = entry["vehicle"]
        driver  = entry["driver"]
        stops   = entry["stops"]
        km      = entry["total_km"]
        dur_min = entry["total_duration_min"]

        if not stops:
            continue

        dname = driver["name"] if driver else "⚠ No driver"
        print(f"\n  🚐 {v['label']}  |  Driver: {dname}  |  {len(stops)} stops  |  {km:.1f} km  |  ~{int(dur_min)} min")
        print(f"  {'#':<4} {'Client':<28} {'Window':<14} {'Arrival':<10} {'Status'}")
        print("  " + "-"*65)

        for i, stop in enumerate(stops):
            status = "🔴 LATE" if stop["is_late"] else "✅"
            if stop.get("shift_exceeded"):
                status += " ⚠ SHIFT EXCEEDED"
            late_note = f" (+{stop['late_by_min']} min)" if stop["is_late"] else ""
            print(f"  {i+1:<4} {stop['name']:<28} {stop['window']:<14} {stop['arrival']:<10} {status}{late_note}")
            if stop["is_late"]:
                total_late += 1

    print("\n" + "="*70)
    print(f"  SUMMARY: {total_late} late deliveries across all routes")
    print("="*70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # Step 1: Geocode all addresses
    locations = geocode_all(ORDERS)

    # Step 2: Get real road distance matrix (one API call)
    distances, durations = get_distance_matrix(locations)
    if distances is None:
        print("Failed to get distance matrix.")
        exit(1)

    # Step 3: Assign orders to vehicles
    vehicle_orders = assign_orders_to_vehicles(ORDERS)

    # Step 4: Assign drivers to vehicles
    driver_assignment = assign_drivers(vehicle_orders)

    # Step 5: For each vehicle, run Clarke-Wright + 2-opt
    print("\n" + "="*65)
    print("  STEP 4 — ROUTING (Clarke-Wright + 2-opt)")
    print("="*65)

    # Build a lookup: order_id → location index
    loc_index = {loc["id"]: i for i, loc in enumerate(locations)}

    vehicle_routes = []

    for v in VEHICLES:
        orders = vehicle_orders.get(v["id"], [])
        if not orders:
            continue

        driver = driver_assignment.get(v["id"])
        dname  = driver["name"] if driver else "No driver"

        # Get location indices for this vehicle's stops
        stop_indices = [loc_index[o["id"]] for o in orders if o["id"] in loc_index]

        print(f"\n  {v['label']} ({dname}) — {len(stop_indices)} stops")

        # Clarke-Wright: compute best merge order
        cw_route = clarke_wright(stop_indices, distances, warehouse_idx=0)
        print(f"    Clarke-Wright route: {[locations[i]['name'] for i in cw_route]}")

        # 2-opt: improve the route
        opt_route = two_opt(cw_route, distances)
        print(f"    2-opt improved:      {[locations[i]['name'] for i in opt_route]}")

        # Calculate total distance
        total_km = distances[0][opt_route[0]]  # warehouse to first stop
        for k in range(len(opt_route) - 1):
            total_km += distances[opt_route[k]][opt_route[k+1]]
        total_km += distances[opt_route[-1]][0]  # last stop back to warehouse

        # Time simulation
        sim_stops, total_min = simulate_route(opt_route, locations, durations, driver or DRIVERS[0])

        vehicle_routes.append({
            "vehicle":           v,
            "driver":            driver,
            "stops":             sim_stops,
            "total_km":          total_km,
            "total_duration_min": total_min,
        })

    # Step 6: Print final plan
    print_routes(vehicle_routes)
