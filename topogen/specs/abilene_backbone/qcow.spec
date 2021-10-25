#!/bin/bash

QCOW_IMAGE_NAME="abilene_backbone"

QCOW_TEMPLATE_IMAGE="../templates/template-kvm-debian9-kernel4.9.0-13-amd64.qcow"

XEN_SPEC_LIST="../specs/abilene_backbone/xen_con0.spec,../specs/abilene_backbone/xen_pc1.spec,../specs/abilene_backbone/xen_pc2.spec,../specs/abilene_backbone/xen_pc3.spec,../specs/abilene_backbone/xen_pc4.spec,../specs/abilene_backbone/xen_pc5.spec,../specs/abilene_backbone/xen_pc6.spec,../specs/abilene_backbone/xen_pc7.spec,../specs/abilene_backbone/xen_pc8.spec,../specs/abilene_backbone/xen_pc9.spec,../specs/abilene_backbone/xen_pc10.spec,../specs/abilene_backbone/xen_pc11.spec,../specs/abilene_backbone/xen_router1.spec,../specs/abilene_backbone/xen_router2.spec,../specs/abilene_backbone/xen_router3.spec,../specs/abilene_backbone/xen_router4.spec,../specs/abilene_backbone/xen_router5.spec,../specs/abilene_backbone/xen_router6.spec,../specs/abilene_backbone/xen_router7.spec,../specs/abilene_backbone/xen_router8.spec,../specs/abilene_backbone/xen_router9.spec,../specs/abilene_backbone/xen_router10.spec,../specs/abilene_backbone/xen_router11.spec"

QCOW_TAR_LIST=""
