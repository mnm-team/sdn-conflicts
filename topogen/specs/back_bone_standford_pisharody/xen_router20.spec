#!/bin/bash

XEN_IMAGE_NAME="router20"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r6r20) (${XEN_IMAGE_NAME}_vif2,br_r9r20) (${XEN_IMAGE_NAME}_vif3,br_r19r20) (${XEN_IMAGE_NAME}_vif4,br_r20r19) (${XEN_IMAGE_NAME}_vif5,br_r20p8)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

