#!/bin/bash

XEN_IMAGE_NAME="router15"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r1r15) (${XEN_IMAGE_NAME}_vif2,br_r15r29) (${XEN_IMAGE_NAME}_vif3,br_r15r27) (${XEN_IMAGE_NAME}_vif4,br_r15r16) (${XEN_IMAGE_NAME}_vif5,br_r10r15)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

