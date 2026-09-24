import json
import geopandas as gpd
from shapely.geometry import shape, Point, LineString, MultiLineString
import networkx as nx
import math
import numpy as np

# Load real datasets
roads = gpd.read_file('data/roads/roads.geojson')
pois = gpd.read_file('data/pois/facilities.geojson')
villages = gpd.read_file('data/boundaries/villages.geojson')

print(f"Roads count: {len(roads)}")
print(f"POIs count: {len(pois)}")
print(f"Villages count: {len(villages)}")

# Build NetworkX graph from roads
G = nx.Graph()

for idx, row in roads.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue
    lines = []
    if geom.geom_type == 'LineString':
        lines = [geom]
    elif geom.geom_type == 'MultiLineString':
        lines = list(geom.geoms)
    
    for line in lines:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            u = (round(coords[i][0], 6), round(coords[i][1], 6))
            v = (round(coords[i+1][0], 6), round(coords[i+1][1], 6))
            # Calculate distance in meters using haversine or euclidean approx
            d_lon = (v[0] - u[0]) * 111320 * math.cos(math.radians((u[1] + v[1]) / 2))
            d_lat = (v[1] - u[1]) * 110540
            dist = math.hypot(d_lon, d_lat)
            if dist > 0:
                G.add_edge(u, v, weight=dist, geometry=[coords[i], coords[i+1]])

print(f"Graph nodes: {G.number_of_nodes()}, edges: {G.number_of_edges()}")
print(f"Connected components: {nx.number_connected_components(G)}")
largest_cc = max(nx.connected_components(G), key=len)
print(f"Largest component nodes: {len(largest_cc)} ({len(largest_cc)/G.number_of_nodes()*100:.1f}%)")

# Let's inspect snapping endpoints
# If we snap nodes within e.g. 15-20 meters (or round to ~4 decimal places or snap close nodes)
# 0.0001 deg is ~11 meters.
# Let's test snapping with a spatial index or KDTree:
raw_nodes = list(G.nodes())
print(f"Total raw nodes before snapping: {len(raw_nodes)}")

# Let's test with a KDTree to cluster nodes within threshold (e.g. 25 meters ~ 0.00025 degrees)
from scipy.spatial import cKDTree

raw_coords = np.array(raw_nodes)
tree_raw = cKDTree(raw_coords)

# Build a unified graph with snapping
G_snapped = nx.Graph()
# Map each raw node to a representative node
threshold_deg = 0.00025 # ~25 meters
node_map = {}
for i, pt in enumerate(raw_coords):
    if i in node_map:
        continue
    neighbors = tree_raw.query_ball_point(pt, threshold_deg)
    for n_idx in neighbors:
        if n_idx not in node_map:
            node_map[n_idx] = tuple(pt)

for u, v, data in G.edges(data=True):
    u_idx = tree_raw.query(u)[1]
    v_idx = tree_raw.query(v)[1]
    u_rep = node_map[u_idx]
    v_rep = node_map[v_idx]
    if u_rep != v_rep:
        G_snapped.add_edge(u_rep, v_rep, weight=data['weight'], geometry=data.get('geometry'))

print(f"Snapped graph nodes: {G_snapped.number_of_nodes()}, edges: {G_snapped.number_of_edges()}")
print(f"Connected components after snapping: {nx.number_connected_components(G_snapped)}")
largest_cc_s = max(nx.connected_components(G_snapped), key=len)
print(f"Largest component in snapped graph: {len(largest_cc_s)} ({len(largest_cc_s)/G_snapped.number_of_nodes()*100:.1f}%)")

# Let's see what happens if we connect components that are close to each other (e.g. gaps < 50m)
# For each component smaller than the main one, find its nearest neighbor in another component
# and add a connecting edge if within e.g. 50-80m.
G_connected = G_snapped.copy()

# Add edges between endpoints of road lines that are within 50 meters
from scipy.spatial import cKDTree
snapped_pts = np.array(list(G_connected.nodes()))
tree_c = cKDTree(snapped_pts)

# Query pairs within ~60 meters (0.00055 deg)
pairs = tree_c.query_pairs(0.00055)
print(f"Candidate bridge pairs within ~60m: {len(pairs)}")

node_list = list(G_connected.nodes())
for i, j in pairs:
    u = node_list[i]
    v = node_list[j]
    if not nx.has_path(G_connected, u, v):
        d_lon = (v[0] - u[0]) * 111320 * math.cos(math.radians((u[1] + v[1]) / 2))
        d_lat = (v[1] - u[1]) * 110540
        dist = math.hypot(d_lon, d_lat)
        G_connected.add_edge(u, v, weight=dist, geometry=[u, v], is_bridge=True)

print(f"Connected graph components after bridging: {nx.number_connected_components(G_connected)}")
largest_cc_c = max(nx.connected_components(G_connected), key=len)
print(f"Largest component in bridged graph: {len(largest_cc_c)} ({len(largest_cc_c)/G_connected.number_of_nodes()*100:.1f}%)")

tree_final = tree_c
print("Villages:")
for idx, row in villages.iterrows():
    c = (row.geometry.centroid.x, row.geometry.centroid.y)
    _, n_idx = tree_final.query(c)
    node = node_list[n_idx]
    # find which component node is in
    comp_size = len(nx.node_connected_component(G_connected, node))
    print(f"  {row['name']}: {c} -> nearest road node {node}, comp size: {comp_size}")

# Let's connect disconnected components to the main component
# Find the shortest distance between any node in component C and any node in main component
main_comp = max(nx.connected_components(G_connected), key=len)
main_nodes = np.array(list(main_comp))
tree_main = cKDTree(main_nodes)

all_comps = list(nx.connected_components(G_connected))
print(f"Connecting {len(all_comps)} components to main network...")

for comp in all_comps:
    if comp == main_comp:
        continue
    c_nodes = np.array(list(comp))
    # Find closest pair between comp and main_comp
    dists, indices = tree_main.query(c_nodes)
    best_i = np.argmin(dists)
    best_dist = dists[best_i]
    u = tuple(c_nodes[best_i])
    v = tuple(main_nodes[indices[best_i]])
    # Add connecting edge
    d_lon = (v[0] - u[0]) * 111320 * math.cos(math.radians((u[1] + v[1]) / 2))
    d_lat = (v[1] - u[1]) * 110540
    dist_m = math.hypot(d_lon, d_lat)
    G_connected.add_edge(u, v, weight=dist_m, geometry=[u, v], is_connector=True)

print(f"After connecting all components: connected components = {nx.number_connected_components(G_connected)}")

from shapely.ops import nearest_points

print("\n--- Testing Candidate-by-Candidate Route Calculation ---")
kallara = villages[villages['name'].str.contains('Kallara', case=False, na=False)].iloc[0]
flood_boundary = kallara.geometry.boundary # Kallara flood boundary
for idx, poi in pois.iterrows():
    p_geom = poi.geometry
    # 1. Point on flood boundary nearest to this POI
    nearest_flood_pt, _ = nearest_points(flood_boundary, p_geom)
    
    # 2. Nearest road node to that flood boundary point
    _, orig_idx = tree_final.query((nearest_flood_pt.x, nearest_flood_pt.y))
    orig_node = node_list[orig_idx]
    
    # 3. Nearest road node to POI
    _, tgt_idx = tree_final.query((p_geom.x, p_geom.y))
    tgt_node = node_list[tgt_idx]
    
    # 4. Shortest path
    path = nx.shortest_path(G_connected, orig_node, tgt_node, weight='weight')
    path_len_m = nx.shortest_path_length(G_connected, orig_node, tgt_node, weight='weight')
    
    # 5. Extract coordinates
    coords = [orig_node] + [node for node in path[1:]]
    print(f"Candidate: {poi.get('name')[:32]} -> route: {path_len_m/1000:.2f} km ({len(coords)} nodes), flood exit: ({nearest_flood_pt.x:.4f}, {nearest_flood_pt.y:.4f})")









