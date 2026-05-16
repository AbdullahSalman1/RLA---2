"""
map_view.py — Builds a folium map showing delivery routes per vehicle.
"""

import folium
from data import WAREHOUSE
from planner import VehicleRoute


def build_map(routes: list[VehicleRoute], unassigned: list) -> folium.Map:
    m = folium.Map(
        location=[WAREHOUSE["lat"], WAREHOUSE["lon"]],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    # Warehouse marker
    folium.Marker(
        location=[WAREHOUSE["lat"], WAREHOUSE["lon"]],
        tooltip="🏭 Warehouse (Départ)",
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
    ).add_to(m)

    for route in routes:
        if not route.stops:
            continue

        color = route.vehicle_color
        coords = [[WAREHOUSE["lat"], WAREHOUSE["lon"]]]

        for stop in route.stops:
            coords.append([stop.order.lat, stop.order.lon])
            # Color-code marker by lateness
            marker_color = "red" if stop.is_late else ("orange" if stop.order.priority == "high" else "blue")
            if stop.order.priority == "critical":
                marker_color = "darkred"

            icon_name = "hospital-o" if stop.order.priority == "critical" else (
                "snowflake-o" if stop.order.is_cold_chain else "map-marker"
            )

            tooltip_html = f"""
                <b>{stop.order.client_name}</b><br>
                Order: {stop.order.order_id}<br>
                Priority: {stop.order.priority.upper()}<br>
                Window: {stop.order.time_window[0]}–{stop.order.time_window[1]}<br>
                Arrival: <b>{stop.arrival_time}</b> {'🔴 LATE' if stop.is_late else '✅'}<br>
                Cold chain: {'❄️ Yes' if stop.order.is_cold_chain else 'No'}<br>
                Vehicle: {route.vehicle_label}<br>
                Driver: {route.driver_name}
            """
            folium.Marker(
                location=[stop.order.lat, stop.order.lon],
                tooltip=folium.Tooltip(tooltip_html),
                icon=folium.Icon(color=marker_color, icon=icon_name, prefix="fa"),
            ).add_to(m)

        # Return to warehouse
        coords.append([WAREHOUSE["lat"], WAREHOUSE["lon"]])

        # Draw route line
        folium.PolyLine(
            locations=coords,
            color=color,
            weight=3,
            opacity=0.75,
            tooltip=f"{route.vehicle_label} — {route.driver_name} ({len(route.stops)} stops, {route.total_km} km)",
        ).add_to(m)

    # Unassigned markers
    for order in unassigned:
        folium.CircleMarker(
            location=[order.lat, order.lon],
            radius=8,
            color="gray",
            fill=True,
            fill_color="gray",
            tooltip=f"⚠ UNASSIGNED: {order.client_name} ({order.order_id})",
        ).add_to(m)

    return m
