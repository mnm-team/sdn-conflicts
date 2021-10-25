"""
Use this script to generate a sdn conflicts spec file 
programmatically. Nodes (switches, hosts) and edges can be defined.
The sdn control applications which are supposed to be deployed on a switch can be set. Hosts have an optional attribute that specifies them assource for network traffic. Otherwise the host will be a sink.
"""

import os
import re
import json
import pyangbind.lib.pybindJSON as pybindJSON
import random_topo
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec_v2 import sdn_testbed_spec_v2
from constants_generate_spec import TOPOLOGY_DIR 

topoName = "random_smallworld_s20_h12_spuriousness_run_01"
topoFileName = os.path.join(TOPOLOGY_DIR, topoName + ".json")
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("true")
model.testbed.topologyId = topoName

###### Experiment configuration ######
# configurations for endpoint load balancer
# TODO app configs

"""
# endpoint load balancer
eplb = model.testbed.apps.add("eplb")
eplb.config.cookie = "0x400"
eplb.config.targetSwitches.add("router7")
eplb.config.targetSwitches.add("router6")
appAssetsConfig2 = eplb.config.appAssets.add(1)
appAssetsConfig2.majorAsset.assetKey = "proxy_ip"
appAssetsConfig2.majorAsset.assetValue = "pc1"
appAssetsConfig2.minorAssets.assetKey = "servers"
appAssetsConfig2.minorAssets.assetItems = ["pc1","pc2"]
"""

# host shadower
hs = model.testbed.apps.add("hs")
hs.config.cookie = "0x440"
hs.config.targetSwitches.add("router15")
hs.config.targetSwitches.add("router2")
hs.config.targetSwitches.add("router7")
hs.config.targetSwitches.add("router6")
appAssetsConfig3 = hs.config.appAssets.add(1)
appAssetsConfig3.majorAsset.assetKey = "frontend"
appAssetsConfig3.majorAsset.assetValue = "pc5"
appAssetsConfig3.minorAssets.assetKey = "backend"
appAssetsConfig3.minorAssets.assetValue = "pc6"
appAssetsConfig3 = hs.config.appAssets.add(2)
appAssetsConfig3.majorAsset.assetKey = "frontend"
appAssetsConfig3.majorAsset.assetValue = "pc1"
appAssetsConfig3.minorAssets.assetKey = "backend"
appAssetsConfig3.minorAssets.assetValue = "pc2"


"""
# path load balancer
plb = model.testbed.apps.add("plb")
plb.config.cookie = "0x300"
bw = plb.config.appInvariants.add("bw_time")
bw.intValue = 5
ts = plb.config.targetSwitches.add("router2")
bw_thres = ts.switchInvariants.add("bw_threshold")
bw_thres.intValue = 2
"""

# REST firewall
fw = model.testbed.apps.add("fw")
fw.config.cookie = "0x800"
bw = fw.config.appInvariants.add("bw_time")
bw.intValue = 3
ts = fw.config.targetSwitches.add("router20")
bw_port_thres = ts.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 2
bw_flow_thres = ts.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 1
ts = fw.config.targetSwitches.add("router4")
bw_port_thres = ts.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 2
bw_flow_thres = ts.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 1

"""
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
# add switches
agraph = random_topo.get_mid_smallworld_graph(10) # arg is seed
#random_topo.draw_switches(agraph, topoName) # draw to local svg file
edges = random_topo.get_edges_from_agraph(agraph)
# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
# add hosts and set specific hosts to be source of network traffic
# need to add edges after drawing topo as svg for pcs
edges.append(["router20","pc1"])
edges.append(["router20","pc2"])
edges.append(["router16","pc3"])
edges.append(["router8","pc4"])
edges.append(["router4","pc5"])
edges.append(["router4","pc6"])
edges.append(["router11","pc7"])
edges.append(["router11","pc8"])
edges.append(["router10","pc9"])
edges.append(["router10","pc10"])
edges.append(["router13","pc11"])
edges.append(["router14","pc12"])

# make sure that no switches or hosts have the wrong format and add them to the topo
switches = set()
pc_sources = [8] # set pcs as sources
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
