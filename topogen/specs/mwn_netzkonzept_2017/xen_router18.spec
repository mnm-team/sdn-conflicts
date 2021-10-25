#!/bin/bash

XEN_IMAGE_NAME="router18"

XEN_TEMPLATE_IMAGE="../../templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r17r18) (${XEN_IMAGE_NAME}_vif2,br_r18p17) (${XEN_IMAGE_NAME}_vif3,br_r18p18)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

