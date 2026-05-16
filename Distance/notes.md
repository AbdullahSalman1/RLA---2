"We use a two-step process. First, geocoding converts plain addresses into GPS coordinates by querying the OpenStreetMap database through the OpenRouteService API — the client just types an address, no coordinates needed. Second, we send all coordinates to the ORS Matrix API in a single call, which runs Dijkstra's shortest-path algorithm on the real Paris road network to calculate driving distances and travel times between every pair of locations. This gives us a complete distance matrix that the routing algorithm then uses to plan deliveries."




1. All CRITICAL stops → sorted by earliest deadline
2. All HIGH stops     → sorted by earliest deadline  
3. All NORMAL stops   → Clarke-Wright + 2-opt (distance optimization)

No exceptions. No "but they're on the same street".