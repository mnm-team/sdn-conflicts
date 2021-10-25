#!/bin/bash
# Generates a topology of xen domains based on the normal format of a spec file directory.
# This will only use ${XEN_SPEC_LIST} and ${QCOW_TAR_LIST} from qcow spec, without building a wrapper qcow image
#
# $1 = <qcow spec file>

# Import variables
. ./constants_build_env.sh

# Import functions
. ./common_xen_helpers.sh
. ./common_tar_helpers.sh

##################################################################
# 1. Sanity check
##################################################################
if [ -z $1 ] ; then usage ; exit 1; fi

# source the qcow spec file for all xen vms paths and for any tars
. ${1}

##################################################################
# 2. Create and insert xen VMs
##################################################################

echo "Creating xen VMs..."
IFS=','
for xenspec in ${XEN_SPEC_LIST} ; do
	. "${xenspec}"
	echo "Loading xen spec: ${xenspec}"
	echo "Creating directory /xen/domains/${XEN_IMAGE_NAME}"
	mkdir -p /xen/domains/"${XEN_IMAGE_NAME}"
	"${RNP}"/scripts/common_generate_xen_fs.sh "${xenspec}" "${TMP_DIR}"/"$(basename ${xenspec})"/
	"${RNP}"/scripts/common_generate_xen_image.sh ${xenspec} ${TMP_DIR}/"$(basename ${xenspec})"/ /xen/domains/${XEN_IMAGE_NAME}/disk.img
	xen_generate_config "${xenspec}" /xen/domains/"${XEN_IMAGE_NAME}"/"${XEN_IMAGE_NAME}".cfg
	xen_generate_bridges "${xenspec}" /xen/bridges.sh
done

##################################################################
# 3. Apply tars to local machine
##################################################################

# Check if any definitions are missing in the spec file
if [ -z "${QCOW_TAR_LIST}" ]
then 
  echo "WARNING: QCOW tar list is empty!"
else
  IFS=','
  for tarfile in ${QCOW_TAR_LIST}
  do
	  apply_tar ${tarfile} /
  done
fi
