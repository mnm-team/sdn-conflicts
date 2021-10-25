import networkx as nx
import pygraphviz
import os

def get_edges_from_agraph(agraph):
  edges = agraph.edges()
  edges = list(map(lambda e: [e[0],e[1]],edges))
  nodes = agraph
  return edges

def draw_switches(agraph, toponame):
  # layout of the graph that adjust placing of nodes for no overlaps and without redundant artifacts
  agraph.layout(prog="neato", args="-Gbgcolor=transparent -Nfontcolor=#0096d4 -Nfixedsize=true -Nwidth=0.4 -Nheight=0.4 -Npenwidth=0 -Nfontsize=1 -Goverlap=false -Gsplines=true -Nshape=box -Nshapefile=switch.png")
  agraph.draw(toponame + ".svg")
  
  agraph.layout(prog="neato", args="-Nfontcolor=#000000 -Nfixedsize=true -Nwidth=0.4 -Nheight=0.4 -Npenwidth=0 -Nfontsize=3 -Goverlap=false -Gsplines=true -Nshape=box -Nshapefile=switch.png")
  # individual file name here
  agraph.draw(toponame + "_labels.svg")

def create_agraph_fromedges(edges):
  G = nx.Graph()
  N = set()
  for e in edges:
    if len(e) != 2:
      raise ValueError("An edge can only contain two nodes: {}".format(e))
    if "router" in e[0] or "router" in e[1]:
      N.add(e[0])
      N.add(e[1])
    else:
      raise ValueError("Graph creation and drawing is only supported for switches, not hosts")
  E = set(map(lambda e: (e[0],e[1]),edges))
  G.add_nodes_from(N)
  G.add_edges_from(E)
  G = nx.nx_agraph.to_agraph(G)
  return G 

def create_agraph_from_graph(graph):
  G = nx.Graph()
  E = map(lambda e: (e[0]+1,e[1]+1),graph.edges())
  V = map(lambda v: v+1, graph.nodes())
  G.add_nodes_from(set(V))
  G.add_edges_from(set(E))
  G = nx.relabel_nodes(G, lambda n: "router" + str(n))
  G = nx.nx_agraph.to_agraph(G)
  return G

def _get_binomial_graph(n,p,seed):
  return create_agraph_from_graph(nx.erdos_renyi_graph(n,p,seed))

def get_small_binomial_graph(seed):
  return _get_binomial_graph(10,0.28,seed)

def get_mid_binomial_graph(seed):
  return _get_binomial_graph(20,0.18,seed)

def get_large_binomial_graph(seed):
  return _get_binomial_graph(30,0.136,seed)

def _get_sworld_graph(n,m,p,seed):
  return create_agraph_from_graph(nx.newman_watts_strogatz_graph(n,m,p,seed))

def get_small_smallworld_graph(seed):
  return _get_sworld_graph(10,2,0.75,seed)

def get_mid_smallworld_graph(seed):
  return _get_sworld_graph(20,2,0.5,seed)

def get_large_smallworld_graph(seed):
  return _get_sworld_graph(30,2,0.25,seed)

def _get_reconnected_graph(n,m,p,q,seed):
  return create_agraph_from_graph(nx.extended_barabasi_albert_graph(n,m,p,q,seed))

def get_small_reconnected_graph(seed):
  return _get_reconnected_graph(10,1,0.5,0.3,seed)

def get_mid_reconnected_graph(seed):
  return _get_reconnected_graph(20,1,0.5,0.2,seed)

def get_large_reconnected_graph(seed):
  return _get_reconnected_graph(30,1,0.5,0.1,seed)
