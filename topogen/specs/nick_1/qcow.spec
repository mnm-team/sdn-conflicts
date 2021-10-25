#!/bin/bash

QCOW_IMAGE_NAME="nick_1"

QCOW_TEMPLATE_IMAGE="../templates/template-kvm-debian9-kernel4.9.0-13-amd64.qcow"

XEN_SPEC_LIST="../specs/nick_1/xen_con0.spec,../specs/nick_1/xen_pc1.spec,../specs/nick_1/xen_pc2.spec,../specs/nick_1/xen_pc3.spec,../specs/nick_1/xen_pc4.spec,../specs/nick_1/xen_router1.spec,../specs/nick_1/xen_router2.spec,../specs/nick_1/xen_router3.spec,../specs/nick_1/xen_router4.spec"

QCOW_TAR_LIST=""
