#!/bin/bash

QCOW_IMAGE_NAME="hcmut_net"

QCOW_TEMPLATE_IMAGE="../templates/template-kvm-debian9-kernel4.9.0-13-amd64.qcow"

XEN_SPEC_LIST="../specs/hcmut_net/xen_con0.spec,../specs/hcmut_net/xen_pc1.spec,../specs/hcmut_net/xen_pc2.spec,../specs/hcmut_net/xen_pc3.spec,../specs/hcmut_net/xen_pc4.spec,../specs/hcmut_net/xen_pc5.spec,../specs/hcmut_net/xen_pc6.spec,../specs/hcmut_net/xen_pc7.spec,../specs/hcmut_net/xen_pc8.spec,../specs/hcmut_net/xen_pc9.spec,../specs/hcmut_net/xen_pc10.spec,../specs/hcmut_net/xen_pc11.spec,../specs/hcmut_net/xen_pc12.spec,../specs/hcmut_net/xen_pc13.spec,../specs/hcmut_net/xen_pc14.spec,../specs/hcmut_net/xen_pc15.spec,../specs/hcmut_net/xen_pc16.spec,../specs/hcmut_net/xen_pc17.spec,../specs/hcmut_net/xen_pc18.spec,../specs/hcmut_net/xen_pc19.spec,../specs/hcmut_net/xen_pc20.spec,../specs/hcmut_net/xen_pc21.spec,../specs/hcmut_net/xen_router1.spec,../specs/hcmut_net/xen_router2.spec,../specs/hcmut_net/xen_router3.spec,../specs/hcmut_net/xen_router4.spec,../specs/hcmut_net/xen_router5.spec,../specs/hcmut_net/xen_router6.spec,../specs/hcmut_net/xen_router7.spec,../specs/hcmut_net/xen_router8.spec,../specs/hcmut_net/xen_router9.spec,../specs/hcmut_net/xen_router10.spec,../specs/hcmut_net/xen_router11.spec,../specs/hcmut_net/xen_router12.spec,../specs/hcmut_net/xen_router13.spec,../specs/hcmut_net/xen_router14.spec,../specs/hcmut_net/xen_router15.spec,../specs/hcmut_net/xen_router16.spec,../specs/hcmut_net/xen_router17.spec,../specs/hcmut_net/xen_router18.spec,../specs/hcmut_net/xen_router19.spec,../specs/hcmut_net/xen_router20.spec,../specs/hcmut_net/xen_router21.spec,../specs/hcmut_net/xen_router22.spec,../specs/hcmut_net/xen_router23.spec,../specs/hcmut_net/xen_router24.spec,../specs/hcmut_net/xen_router25.spec,../specs/hcmut_net/xen_router26.spec"

QCOW_TAR_LIST=""