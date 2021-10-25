#!/usr/bin/env python

""" 
These are user/machine specific paths that need to be set to run 
python scripts in this directory.
"""

import os

# no reason to change this
# this points to the topogen directory of the conflicts repo
ROOT_DIR = os.path.abspath("..") 
SPEC_DIR = os.path.join(ROOT_DIR, "specs")
TOPOLOGY_DIR = os.path.join(ROOT_DIR, "topology")
REPO_DIR = os.path.abspath(os.path.join(ROOT_DIR, os.pardir))
CONTROL_DIR = os.path.join(REPO_DIR, "control")
CONTROLLER_DIR = os.path.join(REPO_DIR, "controller", "massive")
TAR_DIR = os.path.join(ROOT_DIR, "tars", "sdn")

##### User specific paths #####
# set some absolute path to the sdn image templates on your fs
# or put them in the templates folder of the repo which is preset here
TEMPLATE_PATH = os.path.join("/home/cuong/gitclone/conflictsdndev20-git/topogen", "templates")
SDN_SSH_CONFIG = os.path.join(TAR_DIR, "sdn_ssh_config_nick.tar")
CONTROLLER_IMAGE = os.path.join(TEMPLATE_PATH, "controller", "controller.img")
SWITCH_IMAGE = os.path.join(TEMPLATE_PATH, "router", "router.img")
HOST_IMAGE = os.path.join(TEMPLATE_PATH, "pc", "disk.img")
# This will be converted to a VirtualBox .vdi file, but already contains some VBox specific settings for e.g. network-interfaces
VBOX_IMAGE = os.path.join(TEMPLATE_PATH, "outermachine", "template-kvm-debian9-kernel4.9.0-13-amd64-large-multicore.qcow")

#TEMPLATE_PATH = "../templates/"
#CONTROLLER_IMAGE = "template-controller.img"
#SWITCH_IMAGE = "template-switch.img"
#HOST_IMAGE = "template-pc.img"
# This will be converted to a VirtualBox .vdi file, but already contains some VBox specific settings for e.g. network-interfaces
#VBOX_IMAGE = "template-kvm-debian9-kernel4.9.0-13-amd64.qcow"
