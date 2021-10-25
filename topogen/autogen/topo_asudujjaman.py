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

topoId = "asu_inc_trans_2" 
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoId

eplb = model.testbed.apps.add("eplb")
eplb.config.targetSwitches.add("router7")
eplb.config.cookie = "0x400"
appAssetsConfig = eplb.config.appAssets.add(1)
appAssetsConfig.majorAsset.assetKey = "proxy_ip"
appAssetsConfig.majorAsset.assetValue = "pc1"
appAssetsConfig.minorAssets.assetKey = "servers"
appAssetsConfig.minorAssets.assetItems = ["pc1","pc3"]
appAssetsConfig0 = eplb.config.appAssets.add(2)
appAssetsConfig0.majorAsset.assetKey = "proxy_ip"
appAssetsConfig0.majorAsset.assetValue = "pc2"
appAssetsConfig0.minorAssets.assetKey = "servers"
appAssetsConfig0.minorAssets.assetItems = ["pc2","pc4"]

hs = model.testbed.apps.add("hs")
hs.config.cookie = "0x440"
hs.config.targetSwitches.add("router6")
appAssetsConfig1 = hs.config.appAssets.add(1)
appAssetsConfig1.majorAsset.assetKey = "frontend"
appAssetsConfig1.majorAsset.assetValue = "pc3"
appAssetsConfig1.minorAssets.assetKey = "backend"
appAssetsConfig1.minorAssets.assetValue = "pc4"

appAssetsConfig2 = hs.config.appAssets.add(2)
appAssetsConfig2.majorAsset.assetKey = "frontend"
appAssetsConfig2.majorAsset.assetValue = "pc1"
appAssetsConfig2.minorAssets.assetKey = "backend"
appAssetsConfig2.minorAssets.assetValue = "pc2"

"""
appAssetsConfig2 = hs.config.appAssets.add(2)
appAssetsConfig2.majorAsset.assetKey = "frontend"
appAssetsConfig2.majorAsset.assetValue = "pc3"
appAssetsConfig2.minorAssets.assetKey = "backend"
appAssetsConfig2.minorAssets.assetValue = "pc4"

plb = model.testbed.apps.add("plb")
plb.config.cookie = "0x300"
bw = plb.config.appInvariants.add("bw_time")
bw.intValue = 5
ts = plb.config.targetSwitches.add("router8")
bw_thres = ts.switchInvariants.add("bw_threshold")
bw_thres.intValue = 3


fw = model.testbed.apps.add("fw")
fw.config.cookie = "0x880"
bw = fw.config.appInvariants.add("bw_time")
bw.intValue = 5
ts = fw.config.targetSwitches.add("router3")
bw_port_thres = ts.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 10
bw_flow_thres = ts.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 3
"""

pplb = model.testbed.apps.add("pplb4d")
pplb.config.cookie = "0x700"
pplb.config.targetSwitches.add("router8")
servers = pplb.config.appAssets.add(1)
servers.minorAssets.assetKey = "servers"
servers.minorAssets.assetItems = ["pc1", "pc2", "pc3", "pc4"]


# configurations for path enforcer
pe = model.testbed.apps.add("pe")
pe.config.cookie = "0x990"
switch = pe.config.targetSwitches.add("router3")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6,17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router5","router7"]

"""
switch1 = pe.config.targetSwitches.add("router14")
protos1 = switch1.switchInvariants.add("protos")
protos1.intItems = [6, 17]
jumps1 = switch1.switchAssets.add(1)
jumps1.minorAssets.assetKey = "jumps"
jumps1.minorAssets.assetItems = ["router17"]
"""

# set traffic profile and types
model.testbed.trafficTypes = ["udp", "tcp"]
model.testbed.trafficProfiles = ["cbr", "vbr", "bursty"]


###### Topology definition ######
# add switches and set their apps, must be apps that correspond to the above added apps
# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router1","pc1"],["router1","pc2"],["router2","pc3"],["router2","pc4"],["router12","pc5"],["router19","pc6"],["router19","pc7"],["router1","router2"],["router1","router3"],["router2","router3"],["router3","router4"],["router3","router5"],["router4","router6"],["router5","router7"],["router6","router7"],["router6","router8"],["router7","router8"],["router8","router9"],["router8","router10"],["router9","router11"],["router10","router13"],["router12","router14"],["router12","router15"],["router13","router16"],["router14","router15"],["router14","router17"],["router14","router19"],["router16","router18"],["router17","router19"],["router18","router19"],["router14","router11"]]

# make sure that no switches or hosts have the wrong format and add them to the topo
switches = set()
pc_sources = [5,6,7] # set pcs as sources
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
