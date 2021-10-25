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
from sdn_testbed_spec_v2 import sdn_testbed_spec_v2
from constants_generate_spec import TOPOLOGY_DIR 

topoId = "nr_by_8" 
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoId

###### Experiment configuration ######
# configurations for endpoint load balancer

"""
eplb = model.testbed.apps.add("eplb")
eplb.config.cookie = "0x400"
eplb.config.targetSwitches.add("router10")
eplb.config.targetSwitches.add("router11")
appAssetsConfig2 = eplb.config.appAssets.add(1)
appAssetsConfig2.majorAsset.assetKey = "proxy_ip"
appAssetsConfig2.majorAsset.assetValue = "pc6"
appAssetsConfig2.minorAssets.assetKey = "servers"
appAssetsConfig2.minorAssets.assetItems = ["pc6","pc7","pc8","pc9"]


appAssetsConfig3 = eplb.config.appAssets.add(2)
appAssetsConfig3.majorAsset.assetKey = "proxy_ip"
appAssetsConfig3.majorAsset.assetValue = "pc2"
appAssetsConfig3.minorAssets.assetKey = "servers"
appAssetsConfig3.minorAssets.assetItems = ["pc2","pc3"]
"""

hs = model.testbed.apps.add("hs")
hs.config.cookie = "0x440"
hs.config.targetSwitches.add("router6")
hs.config.targetSwitches.add("router10")
appAssetsConfig3 = hs.config.appAssets.add(1)
appAssetsConfig3.majorAsset.assetKey = "frontend"
appAssetsConfig3.majorAsset.assetValue = "pc7"
appAssetsConfig3.minorAssets.assetKey = "backend"
appAssetsConfig3.minorAssets.assetValue = "pc6"

appAssetsConfig1 = hs.config.appAssets.add(2)
appAssetsConfig1.majorAsset.assetKey = "frontend"
appAssetsConfig1.majorAsset.assetValue = "pc3"
appAssetsConfig1.minorAssets.assetKey = "backend"
appAssetsConfig1.minorAssets.assetValue = "pc2"


plb = model.testbed.apps.add("plb")
bw = plb.config.appInvariants.add("bw_time")
bw.intValue = 3
ts = plb.config.targetSwitches.add("router9")
bw_thres = ts.switchInvariants.add("bw_threshold")
bw_thres.intValue = 10


"""
fw = model.testbed.apps.add("fw")
bw = fw.config.appInvariants.add("bw_time")
bw.intValue = 5
ts = fw.config.targetSwitches.add("router3")
bw_port_thres = ts.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 10
bw_flow_thres = ts.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 5

"""
pplb = model.testbed.apps.add("pplb4d")
pplb.config.targetSwitches.add("router10")
pplb.config.targetSwitches.add("router11")
servers = pplb.config.appAssets.add(1)
servers.minorAssets.assetKey = "servers"
servers.minorAssets.assetItems = ["pc2", "pc3", "pc4"]

"""
# configurations for path enforcer
pe = model.testbed.apps.add("pe")
switch = pe.config.targetSwitches.add("router3")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router5","router7"]
switch1 = pe.config.targetSwitches.add("router4")
protos1 = switch1.switchInvariants.add("protos")
protos1.intItems = [6, 17]
jumps1 = switch1.switchAssets.add(1)
jumps1.minorAssets.assetKey = "jumps"
jumps1.minorAssets.assetItems = ["router5","router7"]
"""

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
    if int(re.sub("pc","",e[0])) in [1,4,5,8,9]:
      pc._set_source("true")

  if "pc" not in e[1]:
    switches.add(e[1])
  else:
    pc = model.testbed.hosts.add(e[1])
    if int(re.sub("pc","",e[1])) in [1,4,5,8,9]:
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
