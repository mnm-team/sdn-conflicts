#!/bin/bash

XEN_IMAGE_NAME="router1"

XEN_TEMPLATE_IMAGE="/home/cuong/gitclone/conflictsdndev20-git/topogen/templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r1p1) (${XEN_IMAGE_NAME}_vif2,br_r1r2) (${XEN_IMAGE_NAME}_vif3,br_r1r3)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

