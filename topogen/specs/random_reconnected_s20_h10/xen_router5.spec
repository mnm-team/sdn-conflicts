#!/bin/bash

XEN_IMAGE_NAME="router5"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r1r5) (${XEN_IMAGE_NAME}_vif2,br_r5r7) (${XEN_IMAGE_NAME}_vif3,br_r5r6) (${XEN_IMAGE_NAME}_vif4,br_r5r8) (${XEN_IMAGE_NAME}_vif5,br_r5r10) (${XEN_IMAGE_NAME}_vif6,br_r5r11) (${XEN_IMAGE_NAME}_vif7,br_r5r15) (${XEN_IMAGE_NAME}_vif8,br_r3r5)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

