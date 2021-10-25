#!/bin/bash
# Generates a qcow image containing preconfigured xen images
#
# $1 = <qcow spec file>
# $2 = <target image file>



# Import variables
. ./constants_qcow.sh
. ./constants_build_env.sh

# Import functions
. ./common_qcow_helpers.sh
. ./common_xen_helpers.sh
. ./common_tar_helpers.sh




##################################################################
# 1. Sanity check
##################################################################


if [ -z $1 ] ; then usage ; exit 1; fi
if [ -z $2 ] ; then usage ; exit 1; fi

. ${1}

QCOW_TARGET_IMAGE=${2}

# Check if any definitions are missing in the spec file
if [ -z $QCOW_IMAGE_NAME ] ; then echo "ERROR: Image name not defined!"; exit 1; fi
if [ -z $QCOW_TEMPLATE_IMAGE ] ; then echo "ERROR: Template image not defined!"; exit 1; fi



##################################################################
# 2. Copy default image
##################################################################
echo -n "Copying default image "${QCOW_TEMPLATE_IMAGE}" to "${QCOW_TARGET_IMAGE}
cp ${QCOW_TEMPLATE_IMAGE} ${QCOW_TARGET_IMAGE}
echo "done."


##################################################################
# 3. Mount qcow
##################################################################

echo "Mounting qcow..."
QCOW_MOUNT_POINT=${TMP_DIR}/$(basename ${QCOW_TARGET_IMAGE})
mkdir -p ${QCOW_MOUNT_POINT}/
mount_qcow ${QCOW_TARGET_IMAGE} ${QCOW_MOUNT_POINT}
echo "qcow mounted at ${QCOW_MOUNT_POINT}"


##################################################################
# 4. Create and insert xen VMs
##################################################################

echo "Inserting xen VMs..."
IFS=','
for xenspec in ${XEN_SPEC_LIST} ; do
	. ${xenspec}
	echo "Loading xen spec: ${xenspec}"
	echo "Creating directory ${QCOW_MOUNT_POINT}/xen/domains/${XEN_IMAGE_NAME}"
	mkdir -p ${QCOW_MOUNT_POINT}/xen/domains/${XEN_IMAGE_NAME}
	${RNP}/scripts/common_generate_xen_fs.sh ${xenspec} ${TMP_DIR}/$(basename ${xenspec})/
	${RNP}/scripts/common_generate_xen_image.sh ${xenspec} ${TMP_DIR}/$(basename ${xenspec})/ ${QCOW_MOUNT_POINT}/xen/domains/${XEN_IMAGE_NAME}/disk.img
	xen_generate_config ${xenspec} ${QCOW_MOUNT_POINT}/xen/domains/${XEN_IMAGE_NAME}/${XEN_IMAGE_NAME}.cfg
	xen_generate_bridges ${xenspec} ${QCOW_MOUNT_POINT}/xen/bridges.sh
done

##################################################################
# 5. Apply tars to outer VM
##################################################################

# Check if any definitions are missing in the spec file
if [ -z "${QCOW_TAR_LIST}" ]
then 
  echo "WARNING: QCOW tar list is empty!"
else
  IFS=','
  for tarfile in ${QCOW_TAR_LIST}
  do
	  apply_tar ${tarfile} ${QCOW_MOUNT_POINT}/
  done
fi

##################################################################
# 6. Unmount qcow
##################################################################

echo "Waiting for sync..."
sync
echo "Waiting 10s before umount..."
sleep 10
echo "Unmounting qcow."
umount_qcow ${QCOW_MOUNT_POINT}
