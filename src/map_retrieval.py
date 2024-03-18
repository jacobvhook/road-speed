import geopandas as gpd
import matplotlib
import networkx as nx
import osmnx as ox

ny = ox.graph_from_place(query="Manhattan, NYC, NY, USA")
ny = ox.speed.add_edge_speeds(ny)  # add "speed_kph" attribute to edges
ec = ox.plot.get_edge_colors_by_attr(ny, "speed_kph")

fig, ax = ox.plot_graph(ny, edge_color=ec, edge_linewidth=2, node_size=0)
