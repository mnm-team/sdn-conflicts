#!/bin/bash

. ./constants_xen.sh
. ./common_network_helpers.sh



##################################################################
# Mounts a xen image file at the given mountpoint and echoes the used loop device
#
# $1 = <xen image>
# $2 = <mount dir>
##################################################################
mount_xen()
{
  if [ ! -d $2 ] ; then mkdir $2; fi
  #returns a loop dev
  dev=`losetup -f --show $1`
  mount ${dev} ${2}
  echo ${dev}
}


##################################################################
# Unmounts a xen image file
#
# $1 = <mount dir>
# $2 = <loop dev>
##################################################################
umount_xen()
{
  umount $1
  losetup -d $2
  if [ -d $2 ] ; then rm  -rf $2; fi
}



##################################################################
# Generates the config string for the virtual interfaces as needed in a xen config file
# Needs MAC_FILE to be defined
#
# $1 = <spec file>
##################################################################
xen_generate_VIF_string()
{
  . ${1}


  CLEANTUPLES=$(echo -n "${XEN_BRIDGES}" | tr -d '(' | tr -d ')')

  IFS=' '
  for tuple in ${CLEANTUPLES} ; do
	if [ -z "${RESULTSTRING}" ] ;
	then
		RESULTSTRING="";
	else
		RESULTSTRING="${RESULTSTRING},\n";
	fi
	declare -a VIF_ELEMENTS
	ELEMENT_INDEX=0
	IFS=','
	for d_id in ${tuple} ; do
		VIF_ELEMENTS[${ELEMENT_INDEX}]=${d_id}
		ELEMENT_INDEX=$((${ELEMENT_INDEX}+1))
	done
	RESULTSTRING="${RESULTSTRING}'mac=$(generate_MAC ${XEN_MACPREFIX}), vifname=${VIF_ELEMENTS[0]}, bridge=${VIF_ELEMENTS[1]}'"
  done
  echo -n "${RESULTSTRING}"
}


##################################################################
# Generates a xen config file from a (xen) spec file
# Needs MAC_FILE to be defined
#
# $1 = <spec file>
# $2 = <target config file>
##################################################################
xen_generate_config()
{
  XEN_SPEC_FILE=${1}
  XEN_CONFIG_FILE=${2}

  . ${XEN_SPEC_FILE}

  # Generate Header
  echo "# Xen config for ${XEN_IMAGE_NAME}" >> ${XEN_CONFIG_FILE}
  echo "# Generated on $(date)" >> ${XEN_CONFIG_FILE}
  echo "" >> ${XEN_CONFIG_FILE}

  # Set image parameters
  echo -e "${LIT_MACHINE_STATIC}" >> ${XEN_CONFIG_FILE}
  echo -e "disk   = [\n'file:/xen/domains/${XEN_IMAGE_NAME}/disk.img,xvda1,w'\n] \n" >> ${XEN_CONFIG_FILE}
  echo -e "name   = '${XEN_IMAGE_NAME}' \n" >> ${XEN_CONFIG_FILE}
  echo -e "vif = [\n$(xen_generate_VIF_string ${XEN_SPEC_FILE})\n]" >> ${XEN_CONFIG_FILE}
  echo -e "\n${LIT_BEHAVIOUR}" >> ${XEN_CONFIG_FILE}
}




##################################################################
# Generates a script to set bridges up
#
# $1 = <spec file>
# $2 = <target config file>
##################################################################
xen_generate_bridges()
{
  echo "Creating bridges..."

  . ${1}
  BRIDGEFILE=${2}

  if [ ! -e "${BRIDGEFILE}" ]; then
	  echo -e "#!/bin/bash" > ${BRIDGEFILE}
	  echo -e "# Bridge config generated on `date`\n" >> ${BRIDGEFILE}
  fi

  CLEANTUPLES=$(echo -n "${XEN_BRIDGES}" | tr -d '(' | tr -d ')')

  IFS=' '
  for tuple in ${CLEANTUPLES} ; do
  	c_br=$(echo "$tuple" | cut -d ',' -f 2)
  	echo -e "brctl addbr ${c_br}" >> ${BRIDGEFILE}
	echo -e "ip l set ${c_br} up" >> ${BRIDGEFILE}
  done
  chmod +x $BRIDGEFILE
}

