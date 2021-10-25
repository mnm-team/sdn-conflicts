"""
Use this script to generate a sdn conflicts spec file 
programmatically. Nodes (switches, hosts) and edges can be defined.
The sdn control applications which are supposed to be deployed on a switch can be set. Hosts have an optional attribute that specifies them assource for network traffic. Otherwise the host will be a sink.
"""

import os
import json
import re
import pyangbind.lib.pybindJSON as pybindJSON
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec import sdn_testbed_spec
from constants_generate_spec import TOPOLOGY_DIR 

topoId = "nr_2" 
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoId

###### Experiment configuration ######
# configurations for endpoint load balancer
eplb = model.testbed.apps.eplb
eplb.targetSwitches = ["router4"]
config1 = eplb.configs.add(1)
proxyConfig1 = config1.proxyConfigs.add("pc2")
proxyConfig1.servers = ["pc2","pc3","pc4"]

# configurations for endpoint load balancer
hs = model.testbed.apps.hs
hs.targetSwitches = ["router2","router3"]
config1 = hs.configs.add(1)
hsConfig1 = config1.hostConfigs.add("pc5")
hsConfig1.backend = "pc6"
hsConfig1 = config1.hostConfigs.add("pc7")
hsConfig1.backend = "pc8"

# configurations for path load balancer
plb = model.testbed.apps.plb
config1 = plb.configs.add(1)
config1.bw_time = 5
invConfig1 = config1.invariantsConfigs.add("router2")
invConfig1.bw_threshold = 10

# configurations for firewall
fw = model.testbed.apps.fw
config1 = fw.configs.add(1)
config1.bw_time = 5
invConfig1 = config1.invariantsConfigs.add("router1")
invConfig1.bw_port_threshold = 25
invConfig1.bw_flow_threshold = 10

# configurations for passive path load balancer
pplb = model.testbed.apps.pplb4s
pplb.targetSwitches = ["router3"]
config1 = pplb.configs.add(1)
config1.servers = ["pc1"]

# configurations for path enforcer
pe = model.testbed.apps.pe
pe.targetSwitches = ["router1"]
config1 = pe.configs.add(1)
invConfig1 = config1.invariantsConfigs.add("router1")
invConfig1.protos = ["ip", "tcp", "udp"]
invConfig1.jumps = ["router3","router2"]


# set traffic profile and types
model.testbed.trafficTypes = ["udp", "tcp"]
model.testbed.trafficProfiles = ["cbr", "vbr", "bursty"]

###### Topology definition ######
# add hosts and set specific hosts to be source of network traffic
# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router1","pc1"],["router1","router3"],["router1","router4"],["router2","pc2"],["router2","pc3"],["router2","router3"],["router3","router5"],["router3","router6"],["router4","pc4"],["router4","router5"],["router4","router8"],["router5","router7"],["router6","router9"],["router7","router9"],["router8","router9"],["router9","pc5"],["router9","router10"],["router9","router11"],["router10","router12"],["router10","router13"],["router10","router14"],["router11","router13"],["router11","router14"],["router11","router15"],["router12","pc6"],["router12","router13"],["router13","pc7"],["router14","pc8"],["router14","router15"],["router15","pc9"]]


# make sure that no switches or hosts have the wrong format and add them to the topo
switches = set()
for e in edges:
  if "pc" not in e[0]:
    switches.add(e[0])
  else:
    pc = model.testbed.hosts.add(e[0])
    if int(re.sub("pc","",e[0])) in [1,4,5]:
      pc._set_source("true")

  if "pc" not in e[1]:
    switches.add(e[1])
  else:
    pc = model.testbed.hosts.add(e[1])
    if int(re.sub("pc","",e[1])) in [1,4,5]:
      pc._set_source("true")


# add switches and set their apps, must be apps that correspond to the above added apps
for s in switches:
  model.testbed.switches.add(s)

# now add all the edges
for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
