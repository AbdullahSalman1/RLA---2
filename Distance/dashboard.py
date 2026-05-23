import pandas as pd
import plotly.express as px
import streamlit as st

from main import ORDERS, VEHICLES, DRIVERS, WAREHOUSE

st.set_page_config(
    page_title="Delivery Operations Dashboard",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .hero {
            padding: 1.25rem 1.4rem;
            border-radius: 1.2rem;
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #7c3aed 100%);
            color: white;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
            margin-bottom: 1rem;
        }
        .subtle {
            color: rgba(255,255,255,0.82);
            font-size: 0.95rem;
        }
        .metric-card {
            padding: 1rem;
            border-radius: 1rem;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }
        .section-title {
            font-size: 1.08rem;
            font-weight: 700;
            margin: 0.6rem 0 0.4rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_data():
    orders_df = pd.DataFrame(ORDERS)
    vehicles_df = pd.DataFrame(VEHICLES)
    drivers_df = pd.DataFrame(DRIVERS)
    return orders_df, vehicles_df, drivers_df


def priority_order(priority: str) -> int:
    return {"critical": 0, "high": 1, "normal": 2}.get(str(priority).lower(), 99)


orders_df, vehicles_df, drivers_df = load_data()
orders_df = orders_df.copy()
orders_df["priority_rank"] = orders_df["priority"].map(priority_order)
orders_df = orders_df.sort_values(["priority_rank", "boxes", "name"], ascending=[True, False, True])

# Sidebar controls
st.sidebar.header("Filters")
priority_options = ["critical", "high", "normal"]
selected_priorities = st.sidebar.multiselect(
    "Priority",
    priority_options,
    default=priority_options,
)
selected_cold = st.sidebar.multiselect(
    "Cold chain",
    ["cold", "regular"],
    default=["cold", "regular"],
)
selected_area = st.sidebar.multiselect(
    "Area",
    ["suburban", "city"],
    default=["suburban", "city"],
)
min_boxes, max_boxes = int(orders_df["boxes"].min()), int(orders_df["boxes"].max())
boxes_range = st.sidebar.slider("Boxes", min_boxes, max_boxes, (min_boxes, max_boxes))

filtered_orders = orders_df[
    orders_df["priority"].isin(selected_priorities)
    & orders_df["is_cold"].map(lambda x: (x and "cold" in selected_cold) or (not x and "regular" in selected_cold))
    & orders_df["is_suburban"].map(lambda x: (x and "suburban" in selected_area) or (not x and "city" in selected_area))
    & orders_df["boxes"].between(boxes_range[0], boxes_range[1])
]

# Header
st.markdown(
    f"""
    <div class="hero">
        <div style="font-size: 2rem; font-weight: 800;">🚚 Delivery Operations Dashboard</div>
        <div class="subtle">Warehouse: {WAREHOUSE['name']} · {WAREHOUSE['address']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Metrics
col1, col2, col3, col4, col5 = st.columns(5)
metrics = [
    ("Orders", len(orders_df)),
    ("Filtered", len(filtered_orders)),
    ("Critical", int((orders_df["priority"] == "critical").sum())),
    ("Cold chain", int(orders_df["is_cold"].sum())),
    ("Total boxes", int(orders_df["boxes"].sum())),
]
for col, (label, value) in zip([col1, col2, col3, col4, col5], metrics):
    col.markdown(
        f'<div class="metric-card"><div style="color:#6b7280;font-size:0.85rem;">{label}</div><div style="font-size:1.7rem;font-weight:800;">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# Charts
left, right = st.columns([1.1, 0.9])
with left:
    st.markdown('<div class="section-title">Priority mix</div>', unsafe_allow_html=True)
    priority_counts = orders_df["priority"].value_counts().reindex(priority_options, fill_value=0).reset_index()
    priority_counts.columns = ["priority", "count"]
    fig = px.bar(
        priority_counts,
        x="priority",
        y="count",
        color="priority",
        color_discrete_map={"critical": "#dc2626", "high": "#f59e0b", "normal": "#2563eb"},
        text="count",
    )
    fig.update_layout(height=320, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown('<div class="section-title">Delivery types</div>', unsafe_allow_html=True)
    pie_df = pd.DataFrame(
        {
            "type": ["Cold chain", "Regular"],
            "count": [int(orders_df["is_cold"].sum()), int((~orders_df["is_cold"]).sum())],
        }
    )
    fig2 = px.pie(pie_df, names="type", values="count", hole=0.55, color_discrete_sequence=["#7c3aed", "#22c55e"])
    fig2.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True)

# Tables
orders_view = filtered_orders[
    ["id", "name", "address", "priority", "is_cold", "is_suburban", "boxes", "time_window"]
].rename(
    columns={
        "id": "Order ID",
        "name": "Client",
        "address": "Address",
        "priority": "Priority",
        "is_cold": "Cold",
        "is_suburban": "Suburban",
        "boxes": "Boxes",
        "time_window": "Time window",
    }
)

fleet_left, fleet_right = st.columns(2)
with fleet_left:
    st.subheader("Orders")
    st.dataframe(orders_view, width="stretch", hide_index=True)

with fleet_right:
    st.subheader("Fleet")
    fleet_tabs = st.tabs(["Vehicles", "Drivers"])
    with fleet_tabs[0]:
        st.dataframe(
            vehicles_df.rename(
                columns={
                    "id": "Vehicle ID",
                    "type": "Type",
                    "label": "Vehicle",
                    "max_stops": "Max stops",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    with fleet_tabs[1]:
        st.dataframe(
            drivers_df.rename(
                columns={
                    "id": "Driver ID",
                    "name": "Driver",
                    "certified_refrigerated": "Cold certified",
                    "shift_start": "Shift start",
                    "max_hours": "Max hours",
                }
            ),
            width="stretch",
            hide_index=True,
        )

st.subheader("Workbook summary")
summary_cols = st.columns(3)
summary_cols[0].metric("Vehicles", len(vehicles_df))
summary_cols[1].metric("Drivers", len(drivers_df))
summary_cols[2].metric("Warehouse", WAREHOUSE["name"])

st.info(
    "This dashboard is ready to sit on top of your routing pipeline. Next step: connect the live route results, KPIs, and maps.")
