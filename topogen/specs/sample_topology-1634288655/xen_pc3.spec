#!/bin/bash

XEN_IMAGE_NAME="pc3"

XEN_TEMPLATE_IMAGE="/home/cuong/gitclone/conflictsdndev20-git/topogen/templates/pc/disk.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r3p3)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

