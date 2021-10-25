#!/bin/bash

XEN_IMAGE_NAME="router4"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r2r4) (${XEN_IMAGE_NAME}_vif2,br_r4r5) (${XEN_IMAGE_NAME}_vif3,br_r4r7) (${XEN_IMAGE_NAME}_vif4,br_r4r8) (${XEN_IMAGE_NAME}_vif5,br_r4r17) (${XEN_IMAGE_NAME}_vif6,br_r4r16) (${XEN_IMAGE_NAME}_vif7,br_r4r15) (${XEN_IMAGE_NAME}_vif8,br_r4r14) (${XEN_IMAGE_NAME}_vif9,br_r4r12) (${XEN_IMAGE_NAME}_vif10,br_r4r11) (${XEN_IMAGE_NAME}_vif11,br_r4r13)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

