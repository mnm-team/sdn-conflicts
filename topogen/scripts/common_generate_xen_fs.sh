#!/bin/bash
# Generates the filesystem tree for a xen VM
#
# $1 = <spec file>
# $2 = <target root>



# Import variables
. ./constants_xen.sh
. ./constants_build_env.sh

# Import functions
. ./common_tar_helpers.sh




##################################################################
# 1. Sanity check
##################################################################


if [ -z $1 ] ; then usage ; exit 1; fi
if [ -z $2 ] ; then usage ; exit 1; fi

. $1

XEN_TREEROOT=$2


##################################################################
# 2. Create output directory
##################################################################

echo "Checking xen tree root: ${XEN_TREEROOT}"
# Ensure output directory exists
if [ ! -d ${XEN_TREEROOT} ] ; then
	mkdir ${XEN_TREEROOT}
fi

##################################################################
# 3. Set hostname
##################################################################

mkdir -p ${XEN_TREEROOT}/etc
echo -n ${XEN_IMAGE_NAME} > ${XEN_TREEROOT}/etc/hostname

##################################################################
# 4. Apply TARs
##################################################################
# Check if any definitions are missing in the spec file
if [ -z "${XEN_TAR_LIST}" ] 
then 
  echo "WARNING: Xen tar list is empty!"
else
  IFS=','
  for tarfile in ${XEN_TAR_LIST} ; do
	  apply_tar ${tarfile} ${XEN_TREEROOT}
  done
fi
