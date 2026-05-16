"""
planner.py — Naïve greedy delivery planner.

Strategy (justified by RLA objectives):
  1. Sort orders by priority: critical → high → normal
  2. Within same priority, sort by time-window start (earliest first)
  3. Cold-chain orders go to the refrigerated vehicle exclusively
  4. Assign remaining orders to available vehicles by geographic zone
  5. Sequence stops within each vehicle using a nearest-neighbour heuristic

This is intentionally simple and explainable — not optimal.
It mirrors how the client manually plans today, with structure added.
"""

import math
from dataclasses import dataclass
from typing import Optional
from data import DeliveryOrder, VEHICLES, DRIVERS, WAREHOUSE


# ── Helpers ───────────────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Straight-line distance in km between two GPS points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to 'HH:MM'."""
    return f"{m // 60:02d}:{m % 60:02d}"


CITY_SPEED_KMH = 25   # realistic Paris city speed (traffic factored in)
UNLOAD_MIN = 10       # average stop service time in minutes


# ── Result structures ─────────────────────────────────────────────────────────

@dataclass
class Stop:
    order: DeliveryOrder
    arrival_time: str
    departure_time: str
    is_late: bool
    distance_from_prev_km: float


@dataclass
class VehicleRoute:
    vehicle_id: str
    vehicle_label: str
    vehicle_type: str
    vehicle_color: str
    driver_id: Optional[str]
    driver_name: str
    stops: list
    total_km: float
    total_duration_min: int
    fuel_liters: float
    constraint_violations: list


@dataclass
class PlanResult:
    routes: list
    unassigned: list
    stats: dict


# ── Main planner ──────────────────────────────────────────────────────────────

def plan(orders: list[DeliveryOrder], available_vehicle_ids: list[str], available_driver_ids: list[str]) -> PlanResult:
    """
    Main planning function. Returns a PlanResult with routes and unassigned orders.
    """
    vehicles = [v for v in VEHICLES if v["id"] in available_vehicle_ids]
    drivers  = [d for d in DRIVERS  if d["id"] in available_driver_ids]

    # Step 1: Sort orders by priority then time window
    priority_rank = {"critical": 0, "high": 1, "normal": 2}
    sorted_orders = sorted(
        orders,
        key=lambda o: (priority_rank[o.priority], time_to_minutes(o.time_window[0]))
    )

    # Step 2: Separate cold-chain orders
    cold_orders  = [o for o in sorted_orders if o.is_cold_chain]
    warm_orders  = [o for o in sorted_orders if not o.is_cold_chain]

    # Step 3: Assign vehicles to driver pools
    fridge_vehicles = [v for v in vehicles if v["type"] == "refrigerated"]
    other_vehicles  = [v for v in vehicles if v["type"] != "refrigerated"]

    fridge_drivers  = [d for d in drivers if d["can_drive_refrigerated"]]
    other_drivers   = [d for d in drivers if not d["can_drive_refrigerated"]]
    # If no non-fridge drivers, spill over
    if not other_drivers:
        other_drivers = [d for d in drivers if d not in fridge_drivers]

    # Step 4: Build route buckets
    route_buckets = {}  # vehicle_id → list of orders

    # Assign cold orders to refrigerated vehicles
    for v in fridge_vehicles:
        route_buckets[v["id"]] = []
    for order in cold_orders:
        if fridge_vehicles:
            # Put all cold orders in first available fridge vehicle (simple)
            route_buckets[fridge_vehicles[0]["id"]].append(order)

    # Assign warm orders to other vehicles by zone affinity
    for v in other_vehicles:
        route_buckets[v["id"]] = []

    zone_to_vehicle = _assign_zones_to_vehicles(other_vehicles)

    unassigned = []
    for order in warm_orders:
        target_vid = zone_to_vehicle.get(order.zone)
        if target_vid and target_vid in route_buckets:
            bucket = route_buckets[target_vid]
            v = next(vv for vv in other_vehicles if vv["id"] == target_vid)
            if len(bucket) < v["max_stops"]:
                bucket.append(order)
            else:
                # Overflow: find vehicle with spare capacity
                placed = False
                for vv in other_vehicles:
                    if len(route_buckets[vv["id"]]) < vv["max_stops"]:
                        route_buckets[vv["id"]].append(order)
                        placed = True
                        break
                if not placed:
                    unassigned.append(order)
        else:
            unassigned.append(order)

    # Step 5: Sequence each bucket with nearest-neighbour + time window respect
    routes = []
    driver_pool = fridge_drivers + other_drivers
    driver_index = 0

    for v in vehicles:
        bucket = route_buckets.get(v["id"], [])
        if not bucket:
            continue

        # Assign a driver
        if driver_index < len(driver_pool):
            driver = driver_pool[driver_index]
            driver_index += 1
        else:
            driver = {"id": None, "name": "⚠ No driver", "shift_start": "07:00", "max_hours": 8, "can_drive_refrigerated": False}

        # Sequence stops
        sequenced = _nearest_neighbour_sequence(bucket)

        # Simulate route timing
        stops, total_km, violations = _simulate_route(sequenced, driver, v)

        fuel = (total_km / 100) * v["fuel_per_100km"]
        total_min = sum((time_to_minutes(s.departure_time) - time_to_minutes(s.arrival_time) + s.distance_from_prev_km / CITY_SPEED_KMH * 60) for s in stops) if stops else 0

        routes.append(VehicleRoute(
            vehicle_id=v["id"],
            vehicle_label=v["label"],
            vehicle_type=v["type"],
            vehicle_color=v["color"],
            driver_id=driver.get("id"),
            driver_name=driver["name"],
            stops=stops,
            total_km=round(total_km, 1),
            total_duration_min=int(total_min),
            fuel_liters=round(fuel, 1),
            constraint_violations=violations,
        ))

    # Step 6: Summary stats
    total_orders = len(orders)
    assigned = total_orders - len(unassigned)
    late_stops = sum(1 for r in routes for s in r.stops if s.is_late)
    total_km = sum(r.total_km for r in routes)
    total_fuel = sum(r.fuel_liters for r in routes)
    all_violations = [v for r in routes for v in r.constraint_violations]

    stats = {
        "total_orders": total_orders,
        "assigned": assigned,
        "unassigned": len(unassigned),
        "late_deliveries": late_stops,
        "total_km": round(total_km, 1),
        "total_fuel_liters": round(total_fuel, 1),
        "violations": all_violations,
        "vehicles_used": len(routes),
    }

    return PlanResult(routes=routes, unassigned=unassigned, stats=stats)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _assign_zones_to_vehicles(vehicles: list) -> dict:
    """Map each geographic zone to a vehicle ID (simple round-robin by zone)."""
    from data import ZONE_COORDS
    zones = list(ZONE_COORDS.keys())
    mapping = {}
    if not vehicles:
        return mapping
    for i, zone in enumerate(zones):
        mapping[zone] = vehicles[i % len(vehicles)]["id"]
    return mapping


def _nearest_neighbour_sequence(orders: list[DeliveryOrder]) -> list[DeliveryOrder]:
    """
    Nearest-neighbour TSP heuristic.
    Critical/high priority orders jump to the front first.
    """
    if not orders:
        return []

    # Force critical orders to front
    critical = [o for o in orders if o.priority == "critical"]
    rest     = [o for o in orders if o.priority != "critical"]

    result = list(critical)
    remaining = list(rest)

    if not remaining:
        return result

    # Start from warehouse
    cur_lat, cur_lon = WAREHOUSE["lat"], WAREHOUSE["lon"]
    if result:
        cur_lat, cur_lon = result[-1].lat, result[-1].lon

    while remaining:
        nearest = min(remaining, key=lambda o: haversine_km(cur_lat, cur_lon, o.lat, o.lon))
        result.append(nearest)
        remaining.remove(nearest)
        cur_lat, cur_lon = nearest.lat, nearest.lon

    return result


def _simulate_route(orders: list[DeliveryOrder], driver: dict, vehicle: dict) -> tuple:
    """
    Walk through a sequenced list of orders and compute arrival times,
    lateness, and constraint violations.
    Returns: (list[Stop], total_km, violations)
    """
    stops = []
    violations = []
    total_km = 0.0

    shift_start = time_to_minutes(driver["shift_start"])
    max_end = shift_start + driver["max_hours"] * 60
    current_time = shift_start
    cur_lat, cur_lon = WAREHOUSE["lat"], WAREHOUSE["lon"]

    for order in orders:
        dist_km = haversine_km(cur_lat, cur_lon, order.lat, order.lon)
        travel_min = (dist_km / CITY_SPEED_KMH) * 60
        total_km += dist_km

        arrival_min = current_time + travel_min
        tw_start = time_to_minutes(order.time_window[0])
        tw_end   = time_to_minutes(order.time_window[1])

        # Wait if arriving before time window opens
        if arrival_min < tw_start:
            arrival_min = tw_start

        is_late = arrival_min > tw_end
        if is_late:
            violations.append(f"⚠ {order.client_name}: late by {int(arrival_min - tw_end)} min")

        service_min = order.estimated_service_min
        departure_min = arrival_min + service_min

        # Check driver hours
        if departure_min > max_end:
            violations.append(f"⚠ Driver shift exceeded at {order.client_name}")

        stops.append(Stop(
            order=order,
            arrival_time=minutes_to_time(int(arrival_min)),
            departure_time=minutes_to_time(int(departure_min)),
            is_late=is_late,
            distance_from_prev_km=round(dist_km, 2),
        ))

        current_time = departure_min
        cur_lat, cur_lon = order.lat, order.lon

    # Add return to warehouse
    return_dist = haversine_km(cur_lat, cur_lon, WAREHOUSE["lat"], WAREHOUSE["lon"])
    total_km += return_dist

    return stops, round(total_km, 1), violations
