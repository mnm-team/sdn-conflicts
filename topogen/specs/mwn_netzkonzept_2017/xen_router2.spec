#!/bin/bash

XEN_IMAGE_NAME="router2"

XEN_TEMPLATE_IMAGE="../../templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r1r2) (${XEN_IMAGE_NAME}_vif2,br_r2p3) (${XEN_IMAGE_NAME}_vif3,br_r2p4) (${XEN_IMAGE_NAME}_vif4,br_r2r3) (${XEN_IMAGE_NAME}_vif5,br_r2r4)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

