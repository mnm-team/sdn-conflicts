#!/bin/bash

XEN_IMAGE_NAME="router12"

XEN_TEMPLATE_IMAGE="../../templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r11r12) (${XEN_IMAGE_NAME}_vif2,br_r12p12) (${XEN_IMAGE_NAME}_vif3,br_r12r20)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

