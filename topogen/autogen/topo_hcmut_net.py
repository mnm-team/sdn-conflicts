"""
Use this script to generate a sdn conflicts spec file 
programmatically. Nodes (switches, hosts) and edges can be defined.
The sdn control applications which are supposed to be deployed on a switch can be set. Hosts have an optional attribute that specifies them assource for network traffic. Otherwise the host will be a sink.
"""

import os
import json
import pyangbind.lib.pybindJSON as pybindJSON
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec_v2 import sdn_testbed_spec_v2
from constants_generate_spec import TOPOLOGY_DIR 
from itertools import combinations

topoId = "hcmut_net" 
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoId

###### Experiment configuration ######
# configurations for endpoint load balancer
# TODO app configs


# set traffic profile and types
model.testbed.trafficTypes = ["udp", "tcp"]
model.testbed.trafficProfiles = ["cbr", "vbr", "bursty"]


###### Topology definition ######
# add switches and set their apps, must be apps that correspond to the above added apps

for i in range(1,27):
  model.testbed.switches.add("router{}".format(i))

# add hosts and set specific hosts to be source of network traffic
for i in range(1,22):
  pc = model.testbed.hosts.add("pc{}".format(i))
  if i in [3,7,8,11,13,14,20,21]:
    pc._set_source("true")


# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router1","pc1"],["router1","pc2"],["router1","router2"],["router2","router4"],["router2","router7"],["router3","pc3"],["router3","pc4"],["router3","router6"],["router6","router3"],["router4","router5"],["router4","router7"],["router4","router8"],["router4","router17"],["router4","router16"],["router4","router15"],["router4","router14"],["router4","router12"],["router4","router11"],["router4","router13"],["router5","router7"],["router6","router12"],["router12","router6"],["router7","router8"],["router7","router11"],["router7","router12"],["router7","router13"],["router7","router14"],["router7","router15"],["router7","router16"],["router7","router17"],["router8","router9"],["router8","router10"],["router9","pc5"],["router9","pc6"],["router10","pc7"],["router10","pc8"],["router11","pc9"],["router11","pc10"],["router12","router18"],["router18","router12"],["router12","router19"],["router13","router20"],["router13","router21"],["router14","router22"],["router17","router23"],["router23","pc11"],["router23","router26"],["router26","pc21"],["router22","pc13"],["router22","router25"],["router25","pc20"],["router20","router24"],["router19","router24"],["router18","pc14"],["router24","pc15"],["router24","pc16"],["router24","pc17"],["router21","pc12"],["router21","pc18"],["router21","router19"]]

for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
