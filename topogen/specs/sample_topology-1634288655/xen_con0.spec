#!/bin/bash

XEN_IMAGE_NAME="con0"

XEN_TEMPLATE_IMAGE="/home/cuong/gitclone/conflictsdndev20-git/topogen/templates/controller/controller.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3e:"

XEN_TAR_LIST=""

