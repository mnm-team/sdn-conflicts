#!/bin/bash

XEN_IMAGE_NAME="pc4"

XEN_TEMPLATE_IMAGE="../templates/template-pc.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man) (${XEN_IMAGE_NAME}_vif1,br_r29p4)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

