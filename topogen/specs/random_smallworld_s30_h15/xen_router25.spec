#!/bin/bash

XEN_IMAGE_NAME="router25"

XEN_TEMPLATE_IMAGE="../templates/template-switch.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r24r25) (${XEN_IMAGE_NAME}_vif2,br_r25r26) (${XEN_IMAGE_NAME}_vif3,br_r18r25)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

