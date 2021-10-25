#!/bin/bash

XEN_IMAGE_NAME="router17"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r2r17) (${XEN_IMAGE_NAME}_vif2,br_r17r21) (${XEN_IMAGE_NAME}_vif3,br_r17r22) (${XEN_IMAGE_NAME}_vif4,br_r17r23) (${XEN_IMAGE_NAME}_vif5,br_r17r20) (${XEN_IMAGE_NAME}_vif6,br_r17r28) (${XEN_IMAGE_NAME}_vif7,br_r7r17)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

