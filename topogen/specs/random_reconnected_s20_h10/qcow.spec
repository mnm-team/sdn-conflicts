#!/bin/bash

QCOW_IMAGE_NAME="random_reconnected_s20_h10"

QCOW_TEMPLATE_IMAGE="../templates/template-kvm-debian9-kernel4.9.0-13-amd64.qcow"

XEN_SPEC_LIST="../specs/random_reconnected_s20_h10/xen_con0.spec,../specs/random_reconnected_s20_h10/xen_pc1.spec,../specs/random_reconnected_s20_h10/xen_pc2.spec,../specs/random_reconnected_s20_h10/xen_pc3.spec,../specs/random_reconnected_s20_h10/xen_pc4.spec,../specs/random_reconnected_s20_h10/xen_pc5.spec,../specs/random_reconnected_s20_h10/xen_pc6.spec,../specs/random_reconnected_s20_h10/xen_pc7.spec,../specs/random_reconnected_s20_h10/xen_pc8.spec,../specs/random_reconnected_s20_h10/xen_pc9.spec,../specs/random_reconnected_s20_h10/xen_pc10.spec,../specs/random_reconnected_s20_h10/xen_router8.spec,../specs/random_reconnected_s20_h10/xen_router4.spec,../specs/random_reconnected_s20_h10/xen_router16.spec,../specs/random_reconnected_s20_h10/xen_router20.spec,../specs/random_reconnected_s20_h10/xen_router17.spec,../specs/random_reconnected_s20_h10/xen_router14.spec,../specs/random_reconnected_s20_h10/xen_router11.spec,../specs/random_reconnected_s20_h10/xen_router7.spec,../specs/random_reconnected_s20_h10/xen_router3.spec,../specs/random_reconnected_s20_h10/xen_router19.spec,../specs/random_reconnected_s20_h10/xen_router2.spec,../specs/random_reconnected_s20_h10/xen_router12.spec,../specs/random_reconnected_s20_h10/xen_router15.spec,../specs/random_reconnected_s20_h10/xen_router18.spec,../specs/random_reconnected_s20_h10/xen_router5.spec,../specs/random_reconnected_s20_h10/xen_router9.spec,../specs/random_reconnected_s20_h10/xen_router1.spec,../specs/random_reconnected_s20_h10/xen_router6.spec,../specs/random_reconnected_s20_h10/xen_router10.spec,../specs/random_reconnected_s20_h10/xen_router13.spec"

QCOW_TAR_LIST=""
