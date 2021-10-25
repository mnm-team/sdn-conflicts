"""
Use this script to generate a sdn conflicts spec file 
programmatically. Nodes (switches, hosts) and edges can be defined.
The sdn control applications which are supposed to be deployed on a switch can be set. Hosts have an optional attribute that specifies them assource for network traffic. Otherwise the host will be a sink.
"""

import os
import json
import re
import pyangbind.lib.pybindJSON as pybindJSON
import random_topo
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec_v2 import sdn_testbed_spec_v2
from constants_generate_spec import TOPOLOGY_DIR 

topoName = "random_binomial_s30_h14"
topoFileName = os.path.join(TOPOLOGY_DIR, topoName + ".json")
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoName

###### Experiment configuration ######
# configurations for endpoint load balancer
# TODO app configs


# set traffic profile and types
model.testbed.trafficTypes = ["udp", "tcp"]
model.testbed.trafficProfiles = ["cbr", "vbr", "bursty"]


###### Topology definition ######
# add switches
agraph = random_topo.get_large_binomial_graph(10) # arg is seed
random_topo.draw_switches(agraph, topoName) # draw to local svg file
edges = random_topo.get_edges_from_agraph(agraph)
# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
# add hosts and set specific hosts to be source of network traffic
# need to add edges after drawing topo as svg for pcs
edges.append(["router5","pc1"])
edges.append(["router30","pc2"])
edges.append(["router30","pc3"])
edges.append(["router24","pc4"])
edges.append(["router9","pc5"])
edges.append(["router14","pc6"])
edges.append(["router27","pc7"])
edges.append(["router16","pc8"])
edges.append(["router11","pc9"])
edges.append(["router3","pc10"])
edges.append(["router3","pc11"])
edges.append(["router8","pc12"])
edges.append(["router6","pc13"])
edges.append(["router6","pc14"])

# make sure that no switches or hosts have the wrong format and add them to the topo
switches = set()
pc_sources = [1,2,3,4,5,6] # set pcs as sources
for e in edges:
  if "pc" not in e[0]:
    switches.add(e[0])
  else:
    pc = model.testbed.hosts.add(e[0])
    if int(re.sub("pc","",e[0])) in pc_sources:
      pc._set_source("true")

  if "pc" not in e[1]:
    switches.add(e[1])
  else:
    pc = model.testbed.hosts.add(e[1])
    if int(re.sub("pc","",e[1])) in pc_sources:
      pc._set_source("true")


# add switches and set their apps, must be apps that correspond to the above added apps
for s in switches:
  model.testbed.switches.add(s)

for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
