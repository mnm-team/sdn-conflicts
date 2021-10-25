#!/bin/bash

QCOW_IMAGE_NAME="random_reconnected_s10_h8"

QCOW_TEMPLATE_IMAGE="../templates/template-kvm-debian9-kernel4.9.0-13-amd64.qcow"

XEN_SPEC_LIST="../specs/random_reconnected_s10_h8/xen_con0.spec,../specs/random_reconnected_s10_h8/xen_pc1.spec,../specs/random_reconnected_s10_h8/xen_pc2.spec,../specs/random_reconnected_s10_h8/xen_pc3.spec,../specs/random_reconnected_s10_h8/xen_pc4.spec,../specs/random_reconnected_s10_h8/xen_pc5.spec,../specs/random_reconnected_s10_h8/xen_pc6.spec,../specs/random_reconnected_s10_h8/xen_pc7.spec,../specs/random_reconnected_s10_h8/xen_pc8.spec,../specs/random_reconnected_s10_h8/xen_router8.spec,../specs/random_reconnected_s10_h8/xen_router6.spec,../specs/random_reconnected_s10_h8/xen_router9.spec,../specs/random_reconnected_s10_h8/xen_router4.spec,../specs/random_reconnected_s10_h8/xen_router1.spec,../specs/random_reconnected_s10_h8/xen_router7.spec,../specs/random_reconnected_s10_h8/xen_router5.spec,../specs/random_reconnected_s10_h8/xen_router2.spec,../specs/random_reconnected_s10_h8/xen_router10.spec,../specs/random_reconnected_s10_h8/xen_router3.spec"

QCOW_TAR_LIST=""
