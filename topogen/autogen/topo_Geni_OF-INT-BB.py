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

topoId = "Geni_OF-INT-BB.json" 
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

for i in range(1,31):
  model.testbed.switches.add("router{}".format(i))

# add hosts and set specific hosts to be source of network traffic
for i in range(1,11):
  pc = model.testbed.hosts.add("pc{}".format(i))
  if i in [8,2,3,10]:
    pc._set_source("true")

# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router1","pc1"],["router4","pc2"],["router5","pc3"],["router10","pc4"],["router13","pc5"],["router16","pc7"],["router20","pc8"],["router19","pc6"],["router28","pc9"],["router30","pc10"],["router1","router9"],["router1","router2"],["router2","router3"],["router3","router4"],["router3","router5"],["router4","router5"],["router4","router6"],["router5","router7"],["router6","router8"],["router7","router8"],["router7","router10"],["router8","router13"],["router9","router16"],["router10","router11"],["router10","router14"],["router10","router16"],["router11","router12"],["router12","router13"],["router13","router17"],["router13","router18"],["router14","router16"],["router15","router16"],["router15","router19"],["router16","router20"],["router17","router20"],["router18","router21"],["router19","router22"],["router19","router23"],["router20","router21"],["router20","router26"],["router22","router27"],["router23","router24"],["router24","router30"],["router25","router26"],["router25","router30"],["router27","router28"],["router28","router29"],["router29","router30"]]


for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
