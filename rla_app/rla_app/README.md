# RLA — Medical Delivery Planner

EPITA RLA project — Delivery optimization for a Paris medical logistics company.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
rla_app/
├── app.py          # Streamlit UI — main entry point
├── data.py         # Data models: vehicles, drivers, clients, order generation
├── planner.py      # Greedy planning algorithm + route simulation
├── map_view.py     # Folium map rendering
└── requirements.txt
```

## Algorithm (planner.py)

**Naïve greedy strategy** — intentionally simple and explainable:

1. **Sort** orders by priority (critical → high → normal), then by time-window start
2. **Segregate** cold-chain orders → refrigerated vehicle only
3. **Zone assignment** — group warm orders by geographic zone, assign zones to vehicles
4. **Nearest-neighbour sequencing** within each vehicle's bucket
5. **Route simulation** — compute arrival times, check time windows, flag lateness

### Hard constraints checked:
- Cold-chain orders → refrigerated vehicle only
- Driver shift hours (8h standard, 10h max)
- Time windows (lateness flagged as violations)
- Vehicle stop capacity

### Soft constraints / optimisation criteria:
- Total distance (km)
- Fuel consumption (L)
- Number of late deliveries
- Number of unassigned orders

## Key Data (from client interview)

| Parameter | Value |
|---|---|
| Daily deliveries | 40–60 (Mon: up to 58) |
| Vehicles | 3 small vans, 2 large vans, 1 refrigerated |
| Drivers | 5 (8h shifts, start 06:30–07:00) |
| Coverage area | Paris + petite couronne |
| Hospital deadline | Before 09:00 AM |
| Cold chain products | ~15% of orders (vaccines, insulin) |
| 24h hard rule | All orders must be delivered within 24h |
