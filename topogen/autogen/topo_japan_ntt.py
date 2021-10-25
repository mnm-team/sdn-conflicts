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

topoId = "japan_ntt_27"
topoFileName = os.path.join(TOPOLOGY_DIR, "".join([topoId, ".json"]))
model = sdn_testbed_spec_v2()

model.testbed._set_autostart("false")
model.testbed.topologyId = topoId

###### Experiment configuration ######
# configurations for endpoint load balancer
# endpoint load balancer
eplb = model.testbed.apps.add("eplb")
eplb.config.cookie = "0x400"
eplb.config.targetSwitches.add("router21")
eplb.config.targetSwitches.add("router42")
eplb.config.targetSwitches.add("router13")
appAssetsConfig2 = eplb.config.appAssets.add(1)
appAssetsConfig2.majorAsset.assetKey = "proxy_ip"
appAssetsConfig2.majorAsset.assetValue = "pc11"
appAssetsConfig2.minorAssets.assetKey = "servers"
appAssetsConfig2.minorAssets.assetItems = ["pc11","pc12"]
appAssetsConfig3 = eplb.config.appAssets.add(2)
appAssetsConfig3.majorAsset.assetKey = "proxy_ip"
appAssetsConfig3.majorAsset.assetValue = "pc4"
appAssetsConfig3.minorAssets.assetKey = "servers"
appAssetsConfig3.minorAssets.assetItems = ["pc4","pc5"]
appAssetsConfig3 = eplb.config.appAssets.add(3)
appAssetsConfig3.majorAsset.assetKey = "proxy_ip"
appAssetsConfig3.majorAsset.assetValue = "pc1"
appAssetsConfig3.minorAssets.assetKey = "servers"
appAssetsConfig3.minorAssets.assetItems = ["pc1","pc2","pc3"]

"""
# host shadower
hs = model.testbed.apps.add("hs")
hs.config.cookie = "0x440"
hs.config.targetSwitches.add("router43")
hs.config.targetSwitches.add("router24")
hs.config.targetSwitches.add("router7")
hs.config.targetSwitches.add("router48")
appAssetsConfig3 = hs.config.appAssets.add(1)
appAssetsConfig3.majorAsset.assetKey = "frontend"
appAssetsConfig3.majorAsset.assetValue = "pc2"
appAssetsConfig3.minorAssets.assetKey = "backend"
appAssetsConfig3.minorAssets.assetValue = "pc4"
appAssetsConfig3 = hs.config.appAssets.add(2)
appAssetsConfig3.majorAsset.assetKey = "frontend"
appAssetsConfig3.majorAsset.assetValue = "pc12"
appAssetsConfig3.minorAssets.assetKey = "backend"
appAssetsConfig3.minorAssets.assetValue = "pc11"
"""

# path load balancer
plb = model.testbed.apps.add("plb")
plb.config.cookie = "0x300"
bw = plb.config.appInvariants.add("bw_time")
bw.intValue = 5
ts = plb.config.targetSwitches.add("router21")
bw_thres = ts.switchInvariants.add("bw_threshold")
bw_thres.intValue = 4
ts1 = plb.config.targetSwitches.add("router24")
bw_thres = ts1.switchInvariants.add("bw_threshold")
bw_thres.intValue = 4

"""
# REST firewall
fw = model.testbed.apps.add("fw")
fw.config.cookie = "0x800"
bw = fw.config.appInvariants.add("bw_time")
bw.intValue = 5
ts1 = fw.config.targetSwitches.add("router21")
bw_port_thres = ts1.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 7
bw_flow_thres = ts1.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 4
ts2 = fw.config.targetSwitches.add("router24")
bw_port_thres = ts2.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 7
bw_flow_thres = ts2.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 4
ts3 = fw.config.targetSwitches.add("router43")
bw_port_thres = ts3.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 7
bw_flow_thres = ts3.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 4
ts4 = fw.config.targetSwitches.add("router42")
bw_port_thres = ts4.switchInvariants.add("bw_port_threshold")
bw_port_thres.intValue = 7
bw_flow_thres = ts4.switchInvariants.add("bw_flow_threshold")
bw_flow_thres.intValue = 4


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
"""

# path enforcer
pe = model.testbed.apps.add("pe")
pe.config.cookie = "0x990"
switch = pe.config.targetSwitches.add("router6")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router18"]
switch = pe.config.targetSwitches.add("router8")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router18"]
switch = pe.config.targetSwitches.add("router52")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router44"]
switch = pe.config.targetSwitches.add("router51")
protos = switch.switchInvariants.add("protos")
protos.intItems = [6, 17]
jumps = switch.switchAssets.add(1)
jumps.minorAssets.assetKey = "jumps"
jumps.minorAssets.assetItems = ["router44"]

###### Topology definition ######
# add switches and set their apps, must be apps that correspond to the above added apps

# switches
for i in range(1,56):
  model.testbed.switches.add("router{}".format(i))

# add hosts and set specific hosts to be source of network traffic
source_hosts = [6,7,8,9,10]
for i in range(1,13):
  pc = model.testbed.hosts.add("pc{}".format(i))
  if i in source_hosts:
    pc._set_source("true")

# set the edges between nodes
# hosts need to be connected to at least one switch
# switches are connected to a switch or host
edges = [["router4","pc1"],["router4","pc2"],["router4","pc3"],["router1","pc4"],["router1","pc5"],["router2","pc6"],["router5","pc7"],["router14","pc8"],["router38","pc9"],["router38","pc10"],["router55","pc11"],["router55","pc12"],["router1","router3"],["router2","router3"],["router3","router6"],["router3","router8"],["router4","router6"],["router5","router8"],["router6","router7"],["router6","router12"],["router7","router8"],["router7","router9"],["router8","router11"],["router9","router10"],["router10","router18"],["router11","router13"],["router12","router15"],["router13","router16"],["router14","router16"],["router15","router20"],["router16","router17"],["router17","router21"],["router17","router24"],["router18","router19"],["router19","router20"],["router19","router21"],["router20","router21"],["router22","router23"],["router24","router26"],["router25","router30"],["router26","router29"],["router26","router32"],["router27","router28"],["router28","router36"],["router29","router30"],["router29","router31"],["router30","router31"],["router31","router34"],["router32","router33"],["router33","router37"],["router34","router35"],["router34","router37"],["router35","router36"],["router35","router39"],["router35","router43"],["router37","router38"],["router38","router41"],["router39","router40"],["router40","router41"],["router40","router42"],["router41","router42"],["router42","router43"],["router42","router46"],["router43","router44"],["router43","router52"],["router44","router47"],["router44","router45"],["router45","router46"],["router46","router49"],["router47","router48"],["router48","router49"],["router48","router50"],["router49","router51"],["router50","router51"],["router50","router52"],["router51","router52"],["router51","router54"],["router52","router53"],["router53","router55"],["router54","router55"]]

for i in range(len(edges)):
  edge = model.testbed.edges.add(i)
  edge.nodes = edges[i]

# write model to json in ietf format
output = pybindJSON.dumps(model, mode="ietf")
print(output)
print(output, file=open(topoFileName, "w"))
print("Topology definition file was generated at: " + topoFileName)
