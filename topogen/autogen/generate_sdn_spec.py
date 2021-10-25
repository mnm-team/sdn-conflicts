# TODO -*- coding: utf-8 -*-
"""
Given a json spec file for an SDN topology, this script generates
a directory for spec files that are used to generate an outer vm image, containing inner vm images and their correct setup for simulating a network.
"""
import os
import json
import time
import subprocess
import sys
import shutil
import re
import tarfile
from distutils import dir_util
import parameter_space_loader
import app_config_generator
from constants_generate_spec import *

SPEC_NAME_FORMAT_OUTER = "qcow.spec"
SPEC_NAME_FORMAT = "xen_{}.spec" # Template string for xen spec files
vif_counters = {} # Dict to store counters for defining interface names in xen spec files
spec_file_paths = [] # Store file paths and insert in root topo spec
topo_spec_dir = None # Needs to be set first to generate dir for spec files
topo_name = None # used in topo_spec_dir and to set a unique name in the topo root spec
XEN_MAC_PREFIX = "00:16:3e:" # mac vendor prefix for xen domains interfaces
CONTROL_TAR_FILE = "sdn_control.tar"
START_XEN_TAR_FILE = "sdn_start_xen.tar"
specFileLoader = parameter_space_loader.ParameterSpaceLoader()

########################################################
### GENERATE SPEC FILE NEEDED FOR SCRIPTS IN TOPOGEN ###
########################################################

def cleanupTopoSpec(retain=False):
  """ If any error occurs while generating 
  the topology definition and its files
  the directory tree for the topology is deleted. 
  An optional argument True can be passed to retain 
  a directory tree for debugging purposes.
  """
  if not (topo_spec_dir == None) and not retain:
    print("Deleting directory tree {}".format(topo_spec_dir))
    shutil.rmtree(topo_spec_dir)
  else:
    print("Nothing to cleanup or retain flag was set!")


def makeTopoDirTree(path):
  """ Creates a directory to hold the spec files for 
  an sdn topology based on a path and a name for the topology.
  """
  try:
    print("New directory for topo will be at {}".format(path))
    os.mkdir(path)
  except OSError as e:
    print("Could not create root directory for sdn topology {}".format(path))
    print(e)
    sys.exit()
 

def generateSpecFile(node_name, image_file, is_outer_node=False, tarFile=None):
  """ Generates a specification file based on the 
  given example files for every host, switch or controller 
  VM that is defined in a topology model. The line that
  defines interfaces and associated bridges is filled
  with a single bridge to the outer VM only at this point.
  """
  spec_file = None
  if is_outer_node:
    spec_file = SPEC_NAME_FORMAT_OUTER
  else:
    # initialize counter since vif0 for inner vm is always set below
    vif_counters[node_name] = 0 
    spec_file = SPEC_NAME_FORMAT.format(node_name)
    spec_file_paths.append(os.path.join(topo_spec_dir, spec_file))

  spec_file_path = os.path.join(topo_spec_dir, spec_file)
  file_handler = None
  try:
    file_handler = open(spec_file_path, "x") # only write to new files
    
    # generate a common header
    file_handler.write("#!/bin/bash\n\n")
    
    # generate common content depending on vm type
    content_head = ""
    if is_outer_node:
      content_head = "QCOW"
    else:
      content_head = "XEN"

    file_handler.write("".join([content_head, "_IMAGE_NAME=\"{}\"\n\n".format(node_name)]))
    # tar list will be empty since images are preconfigured
    file_handler.write("".join([content_head, "_TEMPLATE_IMAGE=\"", os.path.join(TEMPLATE_PATH, image_file), "\"\n\n"]))

    # generate content that is specific to inner or outer vm
    if is_outer_node:
      file_handler.write("".join(['XEN_SPEC_LIST="', ",".join(spec_file_paths), '"']) + "\n\n")
      sdn_ssh_tar = ''
      # ssh config file path is set in constants_generate_spec.py
      # since the path to the tar file directory is set in the scipts config we only add the filename
      if os.path.exists(SDN_SSH_CONFIG):
        sdn_ssh_tar = str(os.path.basename(SDN_SSH_CONFIG))
        sdn_ssh_tar +=','
      start_xen_vms = START_XEN_TAR_FILE+","
      file_handler.write("".join(['QCOW_TAR_LIST="', sdn_ssh_tar, start_xen_vms, tarFile, '"']))
    else:
      file_handler.write("XEN_BRIDGES=\"(${XEN_IMAGE_NAME}_vif0,br_man)\"\n\n")
      file_handler.write("XEN_AUTOCONF=\"${XEN_IMAGE_NAME}_vif0\"\n\n")
      file_handler.write("XEN_MACPREFIX=\"" + XEN_MAC_PREFIX + "\"\n\n") 
      file_handler.write("".join(["XEN_TAR_LIST=\"\"\n\n"])) 
    
    file_handler.close()
  except OSError as e:
    print("Error while trying to create and populate xen spec file {}".format(spec_file_path))
    print(e)
    file_handler.close()
    cleanupTopoSpec()
    sys.exit()


def insertXenBridgeInSpecFiles(first_node, second_node):
  """ Adapts a xen spec file by adding a string that defines 
  a bridge between two nodes. The resulting string that will
  be added to the spec file will consist of a unique interface
  for every node e.g. 'pc1_vif1', 'pc1_vif2', 'router1_vif1', etc 
  and a unique part for the bridge name e.g. 'br_p1r1'.
  The counters for the interface names are incremented and the orginal
  file content is overwritten. The params first_node and second_node are
  names for a host and a switch or for two switches.
  """ 
  try:
    vif_counters[first_node] += 1
    vif_counters[second_node] += 1
  except KeyError as e:
    print("Counter for interfaces in spec file of a node was not initialized during creation.")
    print(e)
    cleanupTopoSpec()
    sys.exit()
  
  # swap names if first node is a host to keep all bridge names consistent
  if not (re.match(r'pc', first_node) == None):
    temp_node = first_node
    first_node = second_node
    second_node = temp_node
  
  # bridge name for two connected nodes will be the same and interface name can deviate
  # we only keep the first letter and the number in node names
  common_string_head = "(${XEN_IMAGE_NAME}_vif"
  common_string_tail = "".join([",", "br_", re.sub(r'c|outer', '', first_node + second_node), ")"])
  bridge_first_node = "".join([common_string_head, str(vif_counters[first_node]), common_string_tail])
  bridge_second_node = "".join([common_string_head, str(vif_counters[second_node]), common_string_tail])

  def insertIntoNode(node_name, bridge_string):
    spec_file_path = os.path.join(topo_spec_dir, SPEC_NAME_FORMAT.format(node_name))
    file_handler = None
    try:
      # get original content in spec file
      file_handler = open(spec_file_path, "r")
      file_content = file_handler.read()
      file_handler.close()
      # overwrite content in spec file after adding bridge_string
      file_handler = open(spec_file_path, "w")
      new_file_content = re.sub(r'\)"', "".join([') ', bridge_string, '"']), file_content)
      file_handler.write(new_file_content)
      file_handler.close()
    except OSError as e:
      print("Could not adapt bridge configuration string in file {}".format(spec_file_path))
      print(e)
      file_handler.close()
      cleanupTopoSpec()
      sys.exit()

  insertIntoNode(first_node, bridge_first_node)
  insertIntoNode(second_node, bridge_second_node)

# 0. start the spec generation
if (len(sys.argv) != 2):
  print("need one argument <specfilepath> of a json topo definition")
  sys.exit()

spec_file_path = os.path.abspath(sys.argv[1])
spec_file_name = os.path.basename(spec_file_path)
topo_name = "{}-{}".format(os.path.splitext(spec_file_name)[0], int(time.time()))
topo_spec_dir = os.path.abspath(os.path.join(ROOT_DIR, "specs", topo_name))

# check if spec file exists
if not (os.path.isfile(spec_file_path)):
  print("File {} doesn't exist. Aborting...".format(spec_file_path))
  sys.exit()

# 1. create directory fro given name to hold spec files
makeTopoDirTree(topo_spec_dir)

# 2. read json topo definition into a YANG based model
new_model, model_version = specFileLoader.loadSdnTestbedSpec(spec_file_path)
testbed = new_model.testbed

# 3. create a controller xen spec file based on preconfigured controller image
generateSpecFile("con0", CONTROLLER_IMAGE)

# create host xen spec files based on preconfigured host image
for key,value in testbed.hosts.items():
  generateSpecFile(value.id, HOST_IMAGE)

# create switch xen spec files based on preconfigured switch image
for key,value in testbed.switches.items(): 
  generateSpecFile(value.id, SWITCH_IMAGE)

# insert specification of bridges in host and switch spec files
for key,value in testbed.edges.items():
  insertXenBridgeInSpecFiles(value.nodes[0], value.nodes[1])

# Outer VM spec file
sdnControlFolder = "".join([topo_name,"_",CONTROL_TAR_FILE])
generateSpecFile(topo_name, VBOX_IMAGE, True, sdnControlFolder)

#############################################
### DONE WITH TOPOGEN CONFIGURATION FILES ###
#############################################

########################################
### GENERATE SDN CONFIGURATION FILES ###
########################################

try:
  # copy folder control from repo
  dst = os.path.abspath(os.path.join(TAR_DIR, "root", "control"))
  shutil.copytree(CONTROL_DIR, dst)
except Exception as e:
  print(e)
  cleanupTopoSpec()

# creates/copies folder for app configs 
automateFolder = os.path.join(dst, "automating_experiment")
configsFolder = os.path.join(automateFolder, "app_files")
# copy all current app versions and create folder for them
dir_util.copy_tree(CONTROLLER_DIR, configsFolder)
# adds the spec file to the outervm
shutil.copy(spec_file_path, os.path.join(automateFolder, "parameter_space.json"))
# copy scripts to generate app configs from paramter_space.json to automate folder
shutil.copy("app_config_generator.py", automateFolder)
shutil.copy("parameter_space_loader.py", automateFolder)
shutil.copy("sdn_testbed_spec.py", automateFolder)
shutil.copy("sdn_testbed_spec_v2.py", automateFolder)
# open parameters file to change the content for this experiment setup
paramFile = os.path.join(automateFolder, "parameter_space.bash")

# remove experiment start script that is executed from system daemon on startup
if not testbed.autostart:
  print("INFO: Experiment is not autostarted!")
  autostartScript = os.path.join(dst, "config_and_start.bash")
  os.remove(autostartScript)

if model_version > 1:
  print("Version 2 YANG model, switching to updated version for result generation in read_parameter_space.bash")
  new_read_param_space = os.path.join(automateFolder, "read_parameter_space_v2.bash")
  read_param_space = os.path.join(automateFolder, "read_parameter_space.bash")
  old_read_param_space = os.path.join(automateFolder, "read_parameter_space_v1.bash")
  shutil.move(read_param_space, old_read_param_space)
  shutil.move(new_read_param_space, read_param_space) 

# this generates the app configuration files given a path to a topology json, a folder for the config files and a path to parameter_space.bash
appConfigGenerator = app_config_generator.AppConfigGenerator(spec_file_path, configsFolder, paramFile)

# create a tar file specified for outer vm
os.chdir(TAR_DIR)
print("Creating tar file for insertion in outer machine with apps, app configs and control folder at {}/{}".format(TAR_DIR, sdnControlFolder))
with tarfile.open(sdnControlFolder, 'w') as archfile:
  archfile.add("root")

# remove file tree for SDN configuration after tar file has been created from it
shutil.rmtree(os.path.abspath(os.path.join(dst, os.pardir)))
