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

topoId = "mwn_netzkonzept_2017_multi_transform_run_01" 
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("true")
model.testbed.topologyId = topoId

###### Experiment configuration ######
# configurations for endpoint load balancer

# endpoint load balancer
eplb = model.testbed.apps.add("eplb")
eplb.config.cookie = "0x400"
eplb.config.targetSwitches.add("router3")
eplb.config.targetSwitches.add("router4")
appAssetsConfig2 = eplb.config.appAssets.add(1)
appAssetsConfig2.majorAsset.assetKey = "proxy_ip"
appAssetsConfig2.majorAsset.assetValue = "pc1"
appAssetsConfig2.minorAssets.assetKey = "servers"
appAssetsConfig2.minorAssets.assetItems = ["pc1","pc2","pc3","pc4"]

# host shadower
hs = model.testbed.apps.add("hs")
hs.config.cookie = "0x440"
hs.config.targetSwitches.add("router6")
hs.config.targetSwitches.add("router8")
appAssetsConfig3 = hs.config.appAssets.add(1)
appAssetsConfig3.majorAsset.assetKey = "frontend"
appAssetsConfig3.majorAsset.assetValue = "pc2"
appAssetsConfig3.minorAssets.assetKey = "backend"
appAssetsConfig3.minorAssets.assetValue = "pc1"

"""
# path load balancer
plb = model.testbed.apps.add("plb")
plb.config.cookie = "0x300"
bw = plb.config.appInvariants.add("bw_time")
bw.intValue = 5
ts = plb.config.targetSwitches.add("router2")
bw_thres = ts.switchInvariants.add("bw_threshold")
bw_thres.intValue = 2

# REST firewall
fw = model.testbed.apps.add("fw")
fw.config.cookie = "0x800"
bw = fw.config.appInvariants.add("bw_time")
bw.intValue = 3
ts = fw.config.targetSwitches.add("router5")
bw_port_thres = ts.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 5
bw_flow_thres = ts.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 2
ts = fw.config.targetSwitches.add("router1")
bw_port_thres = ts.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 5
bw_flow_thres = ts.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 2


# passive path load balancer desination based
pplb4d = model.testbed.apps.add("pplb4d")
pplb4d.config.cookie = "0x700"
pplb4d.config.targetSwitches.add("router11")
pplb4d.config.targetSwitches.add("router15")
pplb4d.config.targetSwitches.add("router20")
servers = pplb4d.config.appAssets.add(1)
servers.minorAssets.assetKey = "servers"
servers.minorAssets.assetItems = ["pc1","pc3","pc5","pc6","pc8", "pc9", "pc10"]


# passive path load balancer source based
pplb4s = model.testbed.apps.add("pplb4s")
pplb4s.config.cookie = "0x900"
pplb4s.config.targetSwitches.add("router7")
pplb4s.config.targetSwitches.add("router10")
servers = pplb4s.config.appAssets.add(1)
servers.minorAssets.assetKey = "servers"
servers.minorAssets.assetItems = ["pc2", "pc3", "pc4","pc7","pc8", "pc9"]

# path enforcer
pe = model.testbed.apps.add("pe")
pe.config.cookie = "0x990"
switch = pe.config.targetSwitches.add("router4")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router10"]
"""

# set traffic profile and types
model.testbed.trafficTypes = ["udp", "tcp"]
model.testbed.trafficProfiles = ["cbr", "vbr", "bursty"]

###### Topology definition ######
# add switches and set their apps, must be apps that correspond to the above added apps

# switches
for i in range(1,22):
  model.testbed.switches.add("router{}".format(i))

source_hosts = [10] #,11,12,8,9,13,14,16,20] #,7,16,14,19]
# add hosts and set specific hosts to be source of network traffic
for i in range(1,22):
  pc = model.testbed.hosts.add("pc{}".format(i))
  if i in source_hosts:
    pc._set_source("true")

# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router1","pc1"],["router1","pc2"],["router1","router2"],["router1","router3"],["router1","router4"],["router2","pc3"],["router2","pc4"],["router2","router3"],["router2","router4"],["router3","router4"],["router4","router3"],["router3","router5"],["router3","router6"],["router4","router5"],["router4","router8"],["router5","pc5"],["router5","pc6"],["router6","router7"],["router6","router8"],["router6","router10"],["router10","router6"],["router6","router16"],["router16","router6"],["router7","pc7"],["router7","router8"],["router8","router7"],["router8","router9"],["router8","router10"],["router10","router8"],["router8","router20"],["router20","router8"],["router8","router13"],["router9","pc8"],["router9","pc9"],["router10","router11"],["router10","pc10"],["router11","router12"],["router11","pc11"],["router12","pc12"],["router12","router20"],["router13","router16"],["router13","pc13"],["router14","pc14"],["router14","router15"],["router15","router14"],["router14","router17"],["router15","pc15"],["router15","router20"],["router16","pc16"],["router16","router17"],["router16","router19"],["router19","router16"],["router17","router18"],["router17","router20"],["router20","router17"],["router18","pc17"],["router18","pc18"],["router19","pc19"],["router19","router20"],["router20","router19"],["router20","router21"],["router21","pc20"],["router21","pc21"]]

print(len(edges))

for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
