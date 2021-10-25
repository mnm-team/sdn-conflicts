#!/bin/bash

XEN_IMAGE_NAME="router3"

XEN_TEMPLATE_IMAGE="/home/cuong/gitclone/conflictsdndev20-git/topogen/templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r3p3) (${XEN_IMAGE_NAME}_vif2,br_r3p4) (${XEN_IMAGE_NAME}_vif3,br_r1r3) (${XEN_IMAGE_NAME}_vif4,br_r2r3)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

