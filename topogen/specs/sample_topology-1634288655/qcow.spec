#!/bin/bash

QCOW_IMAGE_NAME="sample_topology-1634288655"

QCOW_TEMPLATE_IMAGE="/home/cuong/gitclone/conflictsdndev20-git/topogen/templates/outermachine/template-kvm-debian9-kernel4.9.0-13-amd64-large-multicore.qcow"

XEN_SPEC_LIST="/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_con0.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_pc1.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_pc2.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_pc3.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_pc4.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_router1.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_router2.spec,/home/cuong/gitclone/conflictsdndev20-git/topogen/specs/sample_topology-1634288655/xen_router3.spec"

QCOW_TAR_LIST="sdn_start_xen.tar,sample_topology-1634288655_sdn_control.tar"