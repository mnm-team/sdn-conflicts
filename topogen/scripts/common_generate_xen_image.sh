#!/bin/bash
# Generates a harddisk image from a preconfigured xen filessytem tree and a default image
#
# $1 = <spec file>
# $2 = <config tree root>
# $3 = <target image> (OPTIONAL!)



# Import variables
. ./constants_xen.sh
. ./constants_build_env.sh

# Import functions
. ./common_xen_helpers.sh




##################################################################
# 1. Sanity check
##################################################################


if [ -z $1 ] ; then usage ; exit 1; fi
if [ -z $2 ] ; then usage ; exit 1; fi

. ${1}

# Check if any definitions are missing in the spec file
if [ -z $XEN_IMAGE_NAME ] ; then echo "ERROR: Image name not defined!"; exit 1; fi
if [ -z $XEN_TEMPLATE_IMAGE ] ; then echo "ERROR: Template image not defined!"; exit 1; fi


XEN_TREEROOT=$2
if [ -z $3 ] ; then
	XEN_TARGET_IMAGE="${TMP_DIR}/${XEN_IMAGE_NAME}.img";
else
	XEN_TARGET_IMAGE=${3};
fi




##################################################################
# 2. Copy default image
##################################################################


echo -n "Copying default image... "
# Ensure output directory exists
cp ${XEN_TEMPLATE_IMAGE} ${XEN_TARGET_IMAGE}
echo "done."


##################################################################
# 3. Mount target image
##################################################################


XEN_MOUNTPOINT="${TMP_DIR}/${XEN_TARGET_IMAGE##*/}"
echo "Mounting image at ${XEN_MOUNTPOINT}"
XEN_LOOPDEV="$(mount_xen ${XEN_TARGET_IMAGE} ${XEN_MOUNTPOINT})"



##################################################################
# 4. Apply config tree
##################################################################


echo -n "Copying config tree... "
cp -ar ${XEN_TREEROOT}/* ${XEN_MOUNTPOINT}/
echo "done."



##################################################################
# 5. Unmount target image
##################################################################


echo "Unmounting image from loop device ${XEN_LOOPDEV}"
umount_xen ${XEN_MOUNTPOINT} ${XEN_LOOPDEV}


