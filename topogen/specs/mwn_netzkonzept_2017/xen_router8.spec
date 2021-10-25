#!/bin/bash

XEN_IMAGE_NAME="router8"

XEN_TEMPLATE_IMAGE="../../templates/router/router.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r4r8) (${XEN_IMAGE_NAME}_vif2,br_r6r8) (${XEN_IMAGE_NAME}_vif3,br_r7r8) (${XEN_IMAGE_NAME}_vif4,br_r8r7) (${XEN_IMAGE_NAME}_vif5,br_r8r9) (${XEN_IMAGE_NAME}_vif6,br_r8r10) (${XEN_IMAGE_NAME}_vif7,br_r10r8) (${XEN_IMAGE_NAME}_vif8,br_r8r20) (${XEN_IMAGE_NAME}_vif9,br_r20r8) (${XEN_IMAGE_NAME}_vif10,br_r8r13)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

