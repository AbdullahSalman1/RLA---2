"""
app.py — RLA Medical Delivery Planner
Streamlit dashboard for the EPITA RLA project.

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from data import VEHICLES, DRIVERS, generate_daily_orders
from planner import plan, minutes_to_time
from map_view import build_map

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RLA — Medical Delivery Planner",
    page_icon="🚐",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card { background: #f0f4f8; border-radius: 10px; padding: 14px 18px; margin-bottom: 8px; }
    .violation-box { background: #fff3cd; border-left: 4px solid #ff9800; padding: 8px 12px; border-radius: 4px; margin: 4px 0; font-size: 13px; }
    .ok-box { background: #e8f5e9; border-left: 4px solid #4caf50; padding: 8px 12px; border-radius: 4px; font-size: 13px; }
    .section-title { font-size: 1.1rem; font-weight: 700; color: #1F4E79; margin-top: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar: Controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/ambulance.png", width=60)
    st.title("🚐 Delivery Planner")
    st.markdown("**RLA — Medical Logistics**")
    st.divider()

    st.markdown("### 📅 Day Configuration")
    day_type = st.selectbox(
        "Day type",
        options=["normal", "monday", "friday"],
        format_func=lambda x: {"normal": "Normal day (~47 orders)", "monday": "Monday (heavy, ~58 orders)", "friday": "Friday (light, ~35 orders)"}[x],
        index=0,
    )

    seed = st.number_input("Random seed (reproducibility)", min_value=1, max_value=999, value=42)

    st.divider()
    st.markdown("### 🚗 Available Vehicles")
    selected_vehicles = []
    for v in VEHICLES:
        icon = "❄️" if v["type"] == "refrigerated" else ("🚐" if v["type"] == "small" else "🚛")
        checked = st.checkbox(f"{icon} {v['label']}", value=True, key=f"v_{v['id']}")
        if checked:
            selected_vehicles.append(v["id"])

    st.divider()
    st.markdown("### 👤 Available Drivers")
    selected_drivers = []
    for d in DRIVERS:
        fridge_badge = " ❄️" if d["can_drive_refrigerated"] else ""
        checked = st.checkbox(f"{d['name']}{fridge_badge} ({d['shift_start']})", value=True, key=f"d_{d['id']}")
        if checked:
            selected_drivers.append(d["id"])

    st.divider()
    run_btn = st.button("▶ Generate Plan", type="primary", use_container_width=True)

# ── Generate orders ───────────────────────────────────────────────────────────
orders = generate_daily_orders(day_type=day_type, seed=seed)

# Auto-run on first load
if "plan_result" not in st.session_state or run_btn:
    if not selected_vehicles:
        st.error("Please select at least one vehicle.")
        st.stop()
    if not selected_drivers:
        st.error("Please select at least one driver.")
        st.stop()
    st.session_state["plan_result"] = plan(orders, selected_vehicles, selected_drivers)

result = st.session_state["plan_result"]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏥 Medical Delivery Planner — Paris & Petite Couronne")
st.caption(f"Day type: **{day_type.capitalize()}** · {result.stats['total_orders']} orders generated · Seed {seed}")

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("📦 Total Orders",      result.stats["total_orders"])
k2.metric("✅ Assigned",          result.stats["assigned"])
k3.metric("⚠ Unassigned",        result.stats["unassigned"],     delta=None if result.stats["unassigned"] == 0 else f"-{result.stats['unassigned']}", delta_color="inverse")
k4.metric("🔴 Late Deliveries",   result.stats["late_deliveries"], delta=None if result.stats["late_deliveries"] == 0 else f"-{result.stats['late_deliveries']}", delta_color="inverse")
k5.metric("🛣 Total Distance",    f"{result.stats['total_km']} km")
k6.metric("⛽ Fuel Estimate",     f"{result.stats['total_fuel_liters']} L")

st.divider()

# ── Main content: map + schedule ─────────────────────────────────────────────
map_col, schedule_col = st.columns([3, 2])

with map_col:
    st.markdown('<div class="section-title">🗺 Route Map</div>', unsafe_allow_html=True)
    fmap = build_map(result.routes, result.unassigned)
    st_folium(fmap, width=None, height=520, returned_objects=[])

with schedule_col:
    st.markdown('<div class="section-title">📋 Vehicle Schedules</div>', unsafe_allow_html=True)

    if not result.routes:
        st.info("No routes generated. Check vehicle/driver availability.")
    else:
        tabs = st.tabs([f"{r.vehicle_label}" for r in result.routes])
        for tab, route in zip(tabs, result.routes):
            with tab:
                st.markdown(f"**Driver:** {route.driver_name} &nbsp;|&nbsp; **{len(route.stops)} stops** &nbsp;|&nbsp; {route.total_km} km &nbsp;|&nbsp; ⛽ {route.fuel_liters} L")

                if route.constraint_violations:
                    for v in route.constraint_violations:
                        st.markdown(f'<div class="violation-box">{v}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="ok-box">✅ No constraint violations</div>', unsafe_allow_html=True)

                if route.stops:
                    rows = []
                    for i, stop in enumerate(route.stops):
                        rows.append({
                            "#": i + 1,
                            "Client": stop.order.client_name,
                            "Priority": stop.order.priority.upper(),
                            "Window": f"{stop.order.time_window[0]}–{stop.order.time_window[1]}",
                            "Arrival": stop.arrival_time,
                            "Status": "🔴 LATE" if stop.is_late else "✅",
                            "❄️": "Yes" if stop.order.is_cold_chain else "",
                            "Dist (km)": stop.distance_from_prev_km,
                        })
                    df = pd.DataFrame(rows)
                    st.dataframe(df, hide_index=True, use_container_width=True,
                                 column_config={"Priority": st.column_config.TextColumn(width="small"),
                                                "Status": st.column_config.TextColumn(width="small")})

st.divider()

# ── Orders table ──────────────────────────────────────────────────────────────
with st.expander("📦 All Orders for Today", expanded=False):
    all_rows = []
    for o in orders:
        # Find which route this order is in
        assigned_to = "⚠ Unassigned"
        for r in result.routes:
            for s in r.stops:
                if s.order.order_id == o.order_id:
                    assigned_to = f"{r.vehicle_label} / {r.driver_name}"
                    break
        all_rows.append({
            "Order ID": o.order_id,
            "Client": o.client_name,
            "Zone": o.zone,
            "Priority": o.priority.upper(),
            "Time Window": f"{o.time_window[0]}–{o.time_window[1]}",
            "Cold Chain": "❄️" if o.is_cold_chain else "",
            "Urgent": "🚨" if o.is_urgent else "",
            "Assigned To": assigned_to,
        })
    st.dataframe(pd.DataFrame(all_rows), hide_index=True, use_container_width=True)

# ── Violations summary ────────────────────────────────────────────────────────
all_violations = result.stats["violations"]
if all_violations:
    with st.expander(f"⚠ Constraint Violations ({len(all_violations)})", expanded=True):
        for v in all_violations:
            st.markdown(f'<div class="violation-box">{v}</div>', unsafe_allow_html=True)

# ── Unassigned orders ─────────────────────────────────────────────────────────
if result.unassigned:
    with st.expander(f"🚫 Unassigned Orders ({len(result.unassigned)})", expanded=True):
        st.warning("These orders could not be assigned due to capacity constraints.")
        for o in result.unassigned:
            st.markdown(f"- **{o.order_id}** · {o.client_name} · {o.zone} · Priority: {o.priority.upper()}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("RLA — EPITA · Medical Delivery Optimization Project · Naïve greedy planner with nearest-neighbour sequencing")
