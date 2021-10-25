#!/bin/bash

XEN_IMAGE_NAME="router30"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r30p10) (${XEN_IMAGE_NAME}_vif2,br_r24r30) (${XEN_IMAGE_NAME}_vif3,br_r25r30) (${XEN_IMAGE_NAME}_vif4,br_r29r30)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

