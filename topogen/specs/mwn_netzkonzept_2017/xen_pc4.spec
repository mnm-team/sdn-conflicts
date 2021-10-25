#!/bin/bash

XEN_IMAGE_NAME="pc4"

XEN_TEMPLATE_IMAGE="../../templates/pc/disk.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r2p4)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

