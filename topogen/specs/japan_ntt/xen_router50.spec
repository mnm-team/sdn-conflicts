#!/bin/bash

XEN_IMAGE_NAME="router50"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r48r50) (${XEN_IMAGE_NAME}_vif2,br_r50r51) (${XEN_IMAGE_NAME}_vif3,br_r50r52)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

