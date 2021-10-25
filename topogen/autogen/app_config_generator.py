# 0. start the spec generation
import parameter_space_loader
import os
import re
import json
import sys

XEN_MAC_PREFIX = "00:16:3e:" # mac vendor prefix for xen domains interfaces
XEN_HOST_IFACE_MAC_PREFIX = XEN_MAC_PREFIX + "11:11:" # custom prefix of eth1 interface
XEN_HOST_IFACE_IP_PREFIX = "192.168.1." # custom prefix for eth1 ip of xen domains

PROTOMAP = {
  "tcp": 6,
  "udp": 17
}

class AppConfigGenerator(parameter_space_loader.ParameterSpaceLoader):
  """ 
  This module can be used to generate new app config files
  and a global app config. It can be imported or used from
  command line to generate config files in a given directory.
  The mandatory arguments are a topology YANG model file path,
  a target directory and the location of the parameter_space.bash file.
  """
  def __init__(self, spec_file_path, configsFolder, paramf):
    model,version = self.loadSdnTestbedSpec(spec_file_path)
    self.testbed = model.testbed
    self.configFolder = os.path.abspath(configsFolder)
    self.globalParams = os.path.abspath(paramf)
    if version == 1:
      self.generateAppConfigsV1()
    if version == 2:
      self.generateAppConfigsV2()

  # removes any characters from string that are not a number
  def removeNodeType(self, string):
    return re.sub(r'[a-zA-Z]*', '', string)

  # converts a host id to tuple (mac,ip) with the id as last byte in the strings
  def hostIdToIPAndMac(self, hostId):
    hostId = self.removeNodeType(hostId)
    macFiller = ""
    if int(hostId) < 10:
      macFiller = "0"
    touple =  lambda s, f : [XEN_HOST_IFACE_IP_PREFIX + s, XEN_HOST_IFACE_MAC_PREFIX + f + s]
    return touple(hostId, macFiller)

  def nodeIdToAsset(self, string):
    if "pc" in string:
      return self.hostIdToIPAndMac(string)
    else: 
      return self.removeNodeType(string)
  
  def strProtoToHex(self, strProto):
    # convert string representation of openflow proto to hex representation
    # that is used by ryu
    return PROTOMAP[strProto]

  # generic method to write a complete app configuration to a file
  # config files are enumerated from xxx1 to xxxN
  def writeAppConfig(self, app, num, configJson):
    filePath = os.path.join(self.configFolder,"".join([app,"_config_local",str(num)]))
    with open(filePath, 'w') as configFile:
      json.dump(configJson, configFile, indent=2)


  def writeGlobalConfig(self, apps):
    # write contents to parameter_space.bash for global SDN config and control scripts
    with open(self.globalParams, 'w') as paramf:
      targetSWLines = []
      appsLine = []
      appsConfsLine = []
      sourcesLine = [] # will hold ids of host source nodes
      sinksLine = [] # will hold ids of host sink nodes

      for key,value in self.testbed.hosts.items():
        # check if host is sink or source
        hostId = re.sub('pc', '', value.id)
        if value.source:
          sourcesLine.append(hostId)
        else:
          sinksLine.append(hostId)

      for key,value in apps.items():
        appsLine.append(key)
        targetSWLines.append(" ".join(map(self.removeNodeType,value[0])))
        appsConfsLine.append(value[1])
      targetSWLine = " : ".join(targetSWLines)
      paramf.write(" ".join(appsLine) + "\n")
      paramf.write(" ".join(map(str, appsConfsLine)) + "\n")
      paramf.write(" ".join(self.testbed.trafficTypes) + "\n")
      paramf.write(targetSWLine + "\n")
      paramf.write(" ".join(self.testbed.trafficProfiles) + "\n")
      paramf.write(str(len(self.testbed.switches)) + "\n")
      paramf.write(str(len(self.testbed.hosts)) + "\n")
      paramf.write(" : ".join([" ".join(map(str, sourcesLine)), " ".join(map(str, sinksLine))]) + "\n")
      paramf.write(self.testbed.topologyId + "\n")
      paramf.write("\n")

  def buildAssets(self, assets, context, appId):
    for it, asset in assets.items():
      if asset.majorAsset.assetValue:
        mAssetId = self.hostIdToIPAndMac(asset.majorAsset.assetValue)
        context[mAssetId[1]] = {}
        context[mAssetId[1]][asset.majorAsset.assetKey] = mAssetId[0]
        mAsset = context[mAssetId[1]]
        if asset.minorAssets:
          if asset.minorAssets.assetValue:
            mAsset[asset.minorAssets.assetKey] = self.nodeIdToAsset(asset.minorAssets.assetValue)
          else:
            ass = list(map(self.nodeIdToAsset, asset.minorAssets.assetItems))
            mAsset[asset.minorAssets.assetKey] = ass
        else:
          raise Exception("A major asset can only be used if minorAssets are mapped to it!")
      else:
        if asset.minorAssets.assetValue:
          context[asset.minorAssets.assetKey] = asset.minorAssets.assetValue
        else:
          context[asset.minorAssets.assetKey] = list(map(self.nodeIdToAsset,asset.minorAssets.assetItems))
        
  def buildInvariants(self, invariants, context):
    for it, inv in invariants.items():
      val = None
      if len(inv.intItems):
        val = list(inv.intItems)
      elif len(inv.stringItems):
        val = list(inv.stringItems)
      elif inv.stringValue:
        val = inv.stringValue
      else:
        val = inv.intValue
      context[inv.invariantKey] = val

  # v2 model only support one configuration per app!
  def generateAppConfigsV2(self):
    apps = dict() # will hold data for apps, their configs and the target switches are added later on
    for it, app in self.testbed.apps.items():
      appId = app.id
      try:
        config = app.config
        tSwitches = []
        configJson = {}
        configJson["cookie"] = config.cookie
        for it, switch in config.targetSwitches.items():
          switchId = self.removeNodeType(switch.id)
          tSwitches.append(switchId)
          sAssetsLen = len(switch.switchAssets)
          sInvsLen = len(switch.switchInvariants)
          if sInvsLen > 0 or sAssetsLen > 0:
            if not "switchConfigs" in configJson:
              configJson["switchConfigs"] = {}
            configJson["switchConfigs"][switchId] = {}
            if sInvsLen:
              self.buildInvariants(switch.switchInvariants, configJson["switchConfigs"][switchId])
            if sAssetsLen:
              configJson["switchConfigs"][switchId]["switchAssets"] = {}
              self.buildAssets(switch.switchAssets, configJson["switchConfigs"][switchId]["switchAssets"], appId)
        if len(config.appAssets):
          configJson["appAssets"] = {}
          self.buildAssets(config.appAssets, configJson["appAssets"], appId)
        if len(config.appInvariants):
          self.buildInvariants(config.appInvariants, configJson)     
        apps[appId] = (tSwitches, 1) # v2 model only supports one config per app
        self.writeAppConfig(appId, 1, configJson)
      except Exception as e:
        print("ERROR: Failed to read config for app {}: ".format(appId))
        print(e)      

    self.writeGlobalConfig(apps)


  def generateAppConfigsV1(self):
    apps = dict() # will hold data for apps, their configs and the target switches are added later on
    # initialize app data

    # read eplb config and params
    try:
      eplb = self.testbed.apps.eplb
      if len(eplb.targetSwitches):
        apps["eplb"] = (eplb.targetSwitches, len(eplb.configs))
        for it,appConfig in eplb.configs.items():
          configJson = {}
          for proxy,proxyConfig in appConfig.proxyConfigs.items():
            proxyId = self.hostIdToIPAndMac(proxy)
            configJson[proxyId[1]] = dict()
            configJson[proxyId[1]]["proxy_ip"] = proxyId[0]
            configJson[proxyId[1]]["servers"] = list(map(self.hostIdToIPAndMac, proxyConfig.servers))
          self.writeAppConfig("eplb", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for eplb: ")
      print(e)

    # read hs config and params
    try:
      hs = self.testbed.apps.hs
      if len(hs.targetSwitches):
        apps["hs"] = (hs.targetSwitches, len(hs.configs))
        for it,appConfig in hs.configs.items():
          configJson = {}
          for mac,hostConfig in appConfig.hostConfigs.items():
            frontendId = self.hostIdToIPAndMac(mac)
            configJson[frontendId[1]] = dict()
            configJson[frontendId[1]]["frontend"] = frontendId[0]
            mappedValues = self.hostIdToIPAndMac(hostConfig.backend)
            configJson[frontendId[1]]["backend"] = [mappedValues[0],mappedValues[1]]
          self.writeAppConfig("hs", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for hs: ")
      print(e)

    # read plb config and params
    try:
      plb = self.testbed.apps.plb
      if len(plb.configs):
        apps["plb"] = ([], len(plb.configs))
        for it, appConfig in plb.configs.items():
          configJson = {}
          configJson["bw_time"] = appConfig.bw_time
          configJson["switchConfigs"] = {}
          for targetSwitch, invsConfig in appConfig.invariantsConfigs.items():
            dpid = self.removeNodeType(targetSwitch)
            apps["plb"][0].append(dpid)
            configJson["switchConfigs"][dpid] = {"bw_threshold":invsConfig.bw_threshold}
          self.writeAppConfig("plb", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for plb: ")
      print(e)

    # read pplb config and params
    try:
      pplb = self.testbed.apps.pplb4d
      if len(pplb.targetSwitches):
        apps["pplb4d"] = (pplb.targetSwitches, len(pplb.configs))
        for it, appConfig in pplb.configs.items():
          configJson = {"servers": list(map(self.hostIdToIPAndMac, appConfig.servers))}
          self.writeAppConfig("pplb4d", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for pplb application: ")
      print(e)

    # read pplb config and params
    try:
      pplb = self.testbed.apps.pplb4s
      if len(pplb.targetSwitches):
        apps["pplb4s"] = (pplb.targetSwitches, len(pplb.configs))
        for it, appConfig in pplb.configs.items():
          configJson = {"servers": list(map(self.hostIdToIPAndMac, appConfig.servers))}
          self.writeAppConfig("pplb4s", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for pplb application: ")
      print(e)

    # read pe config and params
    try:
      pe = self.testbed.apps.pe
      if len(pe.targetSwitches):
        apps["pe"] = (pe.targetSwitches, len(pe.configs))
        for it, appConfig in pe.configs.items():
          configJson = {}
          for switchId, appConfig in appConfig.invariantsConfigs.items():
            targetSwitch = self.removeNodeType(switchId)
            configJson[targetSwitch] = {}
            configJson[targetSwitch]["protos"] = []
            # if key "ip" is given all other protos will be ignored
            if not "ip" in appConfig.protos:
              configJson[targetSwitch]["protos"] = list(map(self.strProtoToHex,appConfig.protos))
            configJson[targetSwitch]["jumps"] = list(map(self.removeNodeType, appConfig.jumps))
          self.writeAppConfig("pe", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for pe application: ")
      print(e)

    # read fw config and params
    try:
      fw = self.testbed.apps.fw
      if len(fw.configs):
        apps["fw"] = ([], len(fw.configs))
        for it, appConfig in fw.configs.items():
          configJson = {}
          configJson["bw_time"] = appConfig.bw_time
          configJson["switchConfigs"] = {}
          for targetSwitch, invsConfig in appConfig.invariantsConfigs.items():
            dpid = self.removeNodeType(targetSwitch)
            apps["fw"][0].append(dpid)
            configJson["switchConfigs"][dpid] = dict()
            switchConfig = configJson["switchConfigs"][dpid] 
            switchConfig["bw_port_threshold"] = invsConfig.bw_port_threshold
            switchConfig["bw_flow_threshold"] = invsConfig.bw_flow_threshold
          self.writeAppConfig("fw", it, configJson)
    except Exception as e:
      print("ERROR: Failed to read config for fw application: ")
      print(e)

    self.writeGlobalConfig(apps)

if __name__ == "__main__":
  if (len(sys.argv) != 4):
    print("Need three arguments!")
    print("<specfilepath> of a json topo definition.")
    print("A path to a folder to place the app configs in.")
    print("A path to the legacy parameter space bash script.")
    sys.exit()

  spec_file_path = os.path.abspath(sys.argv[1])
  configsPath =  os.path.abspath(sys.argv[2])
  paramf =  os.path.abspath(sys.argv[3])

  # check if spec file exists
  if not (os.path.isfile(spec_file_path)) or not (os.path.isdir(configsPath)) or not (os.path.isfile(paramf)):
    print("One of the arguments points to a file/directory that does not exist")
    print(sys.argv)
    sys.exit()

  appConfigGenerator = AppConfigGenerator(spec_file_path, configsPath, paramf)
