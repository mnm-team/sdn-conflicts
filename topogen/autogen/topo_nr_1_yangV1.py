"""
Use this script to generate a sdn conflicts spec file 
programmatically. Nodes (switches, hosts) and edges can be defined.
The sdn control applications which are supposed to be deployed on a switch can be set. Hosts have an optional attribute that specifies them assource for network traffic. Otherwise the host will be a sink.
"""

import os
import json
import pyangbind.lib.pybindJSON as pybindJSON
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec import sdn_testbed_spec
from constants_generate_spec import TOPOLOGY_DIR 

topoId = "nr_1" 
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
hsConfig1 = config1.hostConfigs.add("pc3")
hsConfig1.backend = "pc4"

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
# add switches and set their apps, must be apps that correspond to the above added apps
model.testbed.switches.add("router1")
model.testbed.switches.add("router2")
model.testbed.switches.add("router3")
model.testbed.switches.add("router4")

# add hosts and set specific hosts to be source of network traffic
pc1 = model.testbed.hosts.add("pc1")
model.testbed.hosts.add("pc2")
model.testbed.hosts.add("pc3")
model.testbed.hosts.add("pc4")
pc1._set_source("true")

# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router1","pc1"],["router1","router2"],["router1","router3"],["router2","router3"],["router2","router4"],["router3","router4"],["router4","pc2"],["router4","pc3"],["router4","pc4"]]

for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
