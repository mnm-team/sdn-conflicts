import os
import json
import random_topo
import pyangbind.lib.pybindJSON as pybindJSON
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec_v2 import sdn_testbed_spec_v2
from constants_generate_spec import TOPOLOGY_DIR 

topoId = "nr_1_test" 
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoId

# app configurations

eplb = model.testbed.apps.add("eplb")
eplb.config.cookie = "0x400"
eplb.config.targetSwitches.add("router4")
appAssetsConfig2 = eplb.config.appAssets.add(1)
appAssetsConfig2.majorAsset.assetKey = "proxy_ip"
appAssetsConfig2.majorAsset.assetValue = "pc2"
appAssetsConfig2.minorAssets.assetKey = "servers"
appAssetsConfig2.minorAssets.assetItems = ["pc3","pc4"]

hs = model.testbed.apps.add("hs")
hs.config.cookie = "0x440"
hs.config.targetSwitches.add("router2")
appAssetsConfig = hs.config.appAssets.add(1)
appAssetsConfig.majorAsset.assetKey = "frontend"
appAssetsConfig.majorAsset.assetValue = "pc3"
appAssetsConfig.minorAssets.assetKey = "backend"
appAssetsConfig.minorAssets.assetValue = "pc2"

pplb = model.testbed.apps.add("pplb4d")
hs.config.cookie = "0x900"
pplb.config.targetSwitches.add("router1")
servers = pplb.config.appAssets.add(1)
servers.minorAssets.assetKey = "servers"
servers.minorAssets.assetItems = ["pc2", "pc3", "pc4"]

# configurations for path enforcer
pe = model.testbed.apps.add("pe")
hs.config.cookie = "0x990"
switch = pe.config.targetSwitches.add("router1")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router3","router2"]

# set traffic profile and types
model.testbed.trafficTypes = ["udp", "tcp"]
model.testbed.trafficProfiles = ["cbr", "vbr", "bursty"]

# add switches and hosts, set host 1 as traffic source
for i in range(1,5):
  model.testbed.switches.add("router{}".format(i))
  pc = model.testbed.hosts.add("pc{}".format(i))
  if i == 1:
    pc._set_source("true")

# set the edges between nodes
# hosts need to be connected to one switch
# switches are connected to a switch or host
router_edges = [["router1","router2"],["router1","router3"],["router2","router3"],["router2","router4"],["router3","router4"]]

# draw the switches, hosts not supported yet
agraph = random_topo.create_agraph_fromedges(router_edges)
random_topo.draw_switches(agraph, topoId)

host_edges = [["router1","pc1"],["router4","pc2"],["router4","pc3"],["router4","pc4"]]

edges = host_edges + router_edges

for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write yang model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output, file=open(topoFileName, "w"))
print(output)
