#!/bin/bash

XEN_IMAGE_NAME="router14"

XEN_TEMPLATE_IMAGE="../../templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r14p14) (${XEN_IMAGE_NAME}_vif2,br_r14r15) (${XEN_IMAGE_NAME}_vif3,br_r15r14) (${XEN_IMAGE_NAME}_vif4,br_r14r17)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

