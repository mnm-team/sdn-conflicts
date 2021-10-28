import re
import json

def parseGlobalConfig(appString):
        priority = None
        blp = {}
        with open(appString + "_config_global") as globalfile:
            i = 1
            for line in globalfile:
                line = line.strip()  # preprocess line
                if i == 1:  # first line, priority
                    priority = int(line.split()[0])
                if i == 2:  # second line, for balance point, i.e., switch dpid
                    blp_str = line.split()
                    for dpid in blp_str:
                        if re.fullmatch(r'[0-9]*',dpid) == None:  # a comment
                            break
                        blp[int(dpid)] = {} 
                if i == 3:  # third line, app config (see the parameter space)
                    appconfig = int(line.split()[0])
                    break
                i += 1
        return priority, blp


def localConfigPE(blp):
    local_config = json.load(open("pe_config_local","r"))
    # workaround for v2 yang model
    if "switchConfigs" in local_config:
      local_config = local_config["switchConfigs"]
    for switchId,config in local_config.items():
        targetSwitch = int(switchId)
        # workaround for v2 yang model
        jumps = None
        if "switchAssets" in config:
          jumps = config["switchAssets"]["jumps"]
        else:
          jumps = config["jumps"]
        if targetSwitch in blp:
            blp[targetSwitch]["protos"] = config["protos"]
            blp[targetSwitch]["jumps"] = list(map(int,jumps))
        else:
            log_msg = "Local config and global config in PathEnforcer not matching: {}\n{}"
            print(log_msg.format(config,blp))
    return blp

def localConfigPPLB(app):
    local_config = json.load(open("{}_config_local".format(app),"r"))
    if "appAssets" in local_config:
      local_config = local_config["appAssets"]
    return local_config

def localConfigPPLB4d():
    return localConfigPPLB("pplb4d")

def localConfigPPLB4s():
    return localConfigPPLB("pplb4s")

def localConfigHS():
    local_config = json.load(open("hs_config_local", "r"))
    hosts_config = {}
    # workaround for v2 yang model
    if "appAssets" in local_config:
      local_config = local_config["appAssets"]
    for mac, value in local_config.items():
        hosts_config[(value["frontend"],mac)] = (value["backend"][0],value["backend"][1])
    return hosts_config


def localConfigEPLB():
    local_config = json.load(open("eplb_config_local", "r"))
    proxy_config = {}
    # workaround for v2 yang model
    if "appAssets" in local_config:
      local_config = local_config["appAssets"]
    for key,value in local_config.items():
        proxy_config[(value["proxy_ip"],key)] = {"index": 0, "servers": list(map(lambda v: tuple(v), value["servers"]))}
    return proxy_config
