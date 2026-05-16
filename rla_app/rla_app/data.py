"""
data.py — Static data and data models based on client interview.
All constants reflect real operational values from the RLA client discussion.
"""

from dataclasses import dataclass, field
from typing import Optional
import random

# ── Geo bounds: Paris + petite couronne ──────────────────────────────────────
PARIS_CENTER = (48.8566, 2.3522)

# Real approximate coordinates for delivery zones
ZONE_COORDS = {
    "Paris Centre":       (48.860, 2.347),
    "Paris Nord":         (48.884, 2.345),
    "Paris Est":          (48.857, 2.389),
    "Paris Sud":          (48.831, 2.358),
    "Val-de-Marne":       (48.794, 2.471),
    "Hauts-de-Seine":     (48.830, 2.244),
    "Seine-Saint-Denis":  (48.914, 2.489),
}

WAREHOUSE = {
    "name": "Warehouse (Départ)",
    "lat": 48.845,
    "lon": 2.372,
}

# ── Vehicle fleet (from interview) ────────────────────────────────────────────
VEHICLES = [
    {"id": "V1", "type": "small",        "label": "Small Van 1",       "max_stops": 30, "max_km": 80,  "fuel_per_100km": 7.5,  "color": "#2196F3"},
    {"id": "V2", "type": "small",        "label": "Small Van 2",       "max_stops": 30, "max_km": 80,  "fuel_per_100km": 7.5,  "color": "#4CAF50"},
    {"id": "V3", "type": "small",        "label": "Small Van 3",       "max_stops": 30, "max_km": 80,  "fuel_per_100km": 7.5,  "color": "#FF9800"},
    {"id": "V4", "type": "large",        "label": "Large Van 1",       "max_stops": 20, "max_km": 150, "fuel_per_100km": 11.0, "color": "#9C27B0"},
    {"id": "V5", "type": "large",        "label": "Large Van 2",       "max_stops": 20, "max_km": 150, "fuel_per_100km": 11.0, "color": "#F44336"},
    {"id": "V6", "type": "refrigerated", "label": "Refrigerated Van",  "max_stops": 15, "max_km": 100, "fuel_per_100km": 13.0, "color": "#00BCD4"},
]

# ── Drivers (from interview) ───────────────────────────────────────────────────
DRIVERS = [
    {"id": "D1", "name": "Alexandre M.", "shift_start": "06:30", "max_hours": 8,  "can_drive_refrigerated": True},
    {"id": "D2", "name": "Fatima B.",    "shift_start": "06:30", "max_hours": 8,  "can_drive_refrigerated": True},
    {"id": "D3", "name": "Thomas L.",    "shift_start": "07:00", "max_hours": 8,  "can_drive_refrigerated": False},
    {"id": "D4", "name": "Yasmine K.",   "shift_start": "07:00", "max_hours": 8,  "can_drive_refrigerated": False},
    {"id": "D5", "name": "Romain D.",    "shift_start": "07:00", "max_hours": 8,  "can_drive_refrigerated": False},
]

# ── Client list (from interview: ~35 clients) ─────────────────────────────────
CLIENTS = [
    # Hospital (top priority)
    {"id": "C00", "name": "Hôpital Saint-Antoine",   "type": "hospital",  "zone": "Paris Est",         "lat": 48.848, "lon": 2.390, "priority": "critical",  "time_window": ("06:30", "09:00")},
    # Pharmacies with strict windows
    {"id": "C01", "name": "Pharmacie du Marais",      "type": "pharmacy",  "zone": "Paris Centre",      "lat": 48.857, "lon": 2.356, "priority": "high",      "time_window": ("08:00", "10:00")},
    {"id": "C02", "name": "Pharmacie Bastille",       "type": "pharmacy",  "zone": "Paris Est",         "lat": 48.853, "lon": 2.369, "priority": "high",      "time_window": ("08:00", "11:00")},
    {"id": "C03", "name": "Pharmacie Montparnasse",   "type": "pharmacy",  "zone": "Paris Sud",         "lat": 48.842, "lon": 2.322, "priority": "high",      "time_window": ("09:00", "11:00")},
    {"id": "C04", "name": "Pharmacie Nation",         "type": "pharmacy",  "zone": "Paris Est",         "lat": 48.848, "lon": 2.396, "priority": "normal",    "time_window": ("08:00", "17:00")},
    {"id": "C05", "name": "Pharmacie Opéra",          "type": "pharmacy",  "zone": "Paris Centre",      "lat": 48.871, "lon": 2.332, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C06", "name": "Pharmacie Belleville",     "type": "pharmacy",  "zone": "Paris Nord",        "lat": 48.872, "lon": 2.378, "priority": "normal",    "time_window": ("08:00", "17:00")},
    {"id": "C07", "name": "Pharmacie Châtelet",       "type": "pharmacy",  "zone": "Paris Centre",      "lat": 48.860, "lon": 2.347, "priority": "high",      "time_window": ("08:00", "10:30")},
    {"id": "C08", "name": "Pharmacie Pigalle",        "type": "pharmacy",  "zone": "Paris Nord",        "lat": 48.882, "lon": 2.336, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C09", "name": "Pharmacie Vincennes",      "type": "pharmacy",  "zone": "Val-de-Marne",      "lat": 48.848, "lon": 2.440, "priority": "normal",    "time_window": ("08:00", "17:00")},
    {"id": "C10", "name": "Pharmacie Créteil",        "type": "pharmacy",  "zone": "Val-de-Marne",      "lat": 48.790, "lon": 2.455, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C11", "name": "Pharmacie Neuilly",        "type": "pharmacy",  "zone": "Hauts-de-Seine",    "lat": 48.884, "lon": 2.268, "priority": "high",      "time_window": ("08:00", "10:00")},
    {"id": "C12", "name": "Pharmacie Boulogne",       "type": "pharmacy",  "zone": "Hauts-de-Seine",    "lat": 48.836, "lon": 2.240, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C13", "name": "Pharmacie Saint-Denis",    "type": "pharmacy",  "zone": "Seine-Saint-Denis", "lat": 48.936, "lon": 2.357, "priority": "normal",    "time_window": ("08:00", "17:00")},
    {"id": "C14", "name": "Pharmacie Montreuil",      "type": "pharmacy",  "zone": "Seine-Saint-Denis", "lat": 48.863, "lon": 2.443, "priority": "normal",    "time_window": ("09:00", "17:00")},
    # Clinics
    {"id": "C15", "name": "Clinique du Parc",         "type": "clinic",    "zone": "Paris Sud",         "lat": 48.827, "lon": 2.310, "priority": "high",      "time_window": ("08:00", "12:00")},
    {"id": "C16", "name": "Clinique Monceau",         "type": "clinic",    "zone": "Paris Centre",      "lat": 48.878, "lon": 2.307, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C17", "name": "Clinique Val-de-Marne",    "type": "clinic",    "zone": "Val-de-Marne",      "lat": 48.800, "lon": 2.460, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C18", "name": "Clinique Levallois",       "type": "clinic",    "zone": "Hauts-de-Seine",    "lat": 48.895, "lon": 2.288, "priority": "normal",    "time_window": ("09:00", "17:00")},
    {"id": "C19", "name": "Clinique Aubervilliers",   "type": "clinic",    "zone": "Seine-Saint-Denis", "lat": 48.915, "lon": 2.382, "priority": "normal",    "time_window": ("09:00", "17:00")},
]

# ── Delivery order template ────────────────────────────────────────────────────
@dataclass
class DeliveryOrder:
    order_id: str
    client_id: str
    client_name: str
    lat: float
    lon: float
    zone: str
    priority: str           # critical / high / normal
    time_window: tuple      # ("HH:MM", "HH:MM")
    is_cold_chain: bool
    is_urgent: bool
    estimated_service_min: int = 10   # unload time in minutes
    assigned_vehicle: Optional[str] = None
    assigned_driver: Optional[str] = None
    sequence: Optional[int] = None
    status: str = "pending"           # pending / on_time / late / unassigned


def generate_daily_orders(day_type: str = "normal", seed: int = 42) -> list[DeliveryOrder]:
    """
    Generate a realistic daily order list based on day type.
    day_type: 'normal' | 'monday' | 'friday'
    """
    random.seed(seed)

    # Volume by day type (from interview: 40-60/day, Mondays higher)
    volumes = {"monday": 58, "normal": 47, "friday": 35}
    n = volumes.get(day_type, 47)

    # Cold-chain products: vaccines/insulin (~15% of orders)
    # Urgent orders: ~20% of orders
    orders = []
    client_pool = CLIENTS * 3  # allow repeats
    random.shuffle(client_pool)

    for i in range(n):
        client = client_pool[i % len(client_pool)]
        is_cold = random.random() < 0.15
        is_urgent = client["priority"] == "critical" or (
            client["priority"] == "high" and random.random() < 0.4
        ) or random.random() < 0.1

        orders.append(DeliveryOrder(
            order_id=f"ORD-{i+1:03d}",
            client_id=client["id"],
            client_name=client["name"],
            lat=client["lat"] + random.uniform(-0.003, 0.003),
            lon=client["lon"] + random.uniform(-0.003, 0.003),
            zone=client["zone"],
            priority=client["priority"],
            time_window=client["time_window"],
            is_cold_chain=is_cold,
            is_urgent=is_urgent,
            estimated_service_min=random.randint(8, 15),
        ))

    # Always include at least one hospital order
    hospital = CLIENTS[0]
    orders.insert(0, DeliveryOrder(
        order_id="ORD-000",
        client_id=hospital["id"],
        client_name=hospital["name"],
        lat=hospital["lat"],
        lon=hospital["lon"],
        zone=hospital["zone"],
        priority="critical",
        time_window=hospital["time_window"],
        is_cold_chain=False,
        is_urgent=True,
        estimated_service_min=20,
    ))

    return orders
