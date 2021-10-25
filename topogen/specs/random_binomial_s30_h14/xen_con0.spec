#!/bin/bash

XEN_IMAGE_NAME="con0"

XEN_TEMPLATE_IMAGE="../templates/template-controller.img"

XEN_BRIDGES="(${XEN_IMAGE_NAME}_vif0,br_man)"

XEN_AUTOCONF="${XEN_IMAGE_NAME}_vif0"

XEN_MACPREFIX="00:16:3E:"

XEN_TAR_LIST=""

