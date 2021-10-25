#!/bin/bash




##################################################################
# Generates a valid and (locally) unique MAC address
# Needs MAC_FILE to be defined
#
# TODO: use all 3 bytes instead of just the last one
#
# $1 = <mac vendor prefix> AA:BB:CC:
# $2 = <group id>
# $3 = <device name (e.g. router, pc) (OPTIONAL)
##################################################################
generate_MAC()
{
  prefix=$1

  if [ -z $2 ]; then

	  if [ ! -s ${MAC_FILE} ]; then
		echo -n "$(printf %s%.2d:%.2d:%.2d ${prefix} 0 0 1)" > ${MAC_FILE}
  	fi
  
 	 RESULT_MAC="FAIL"
	  MAC_FOUND="NO"
	  MAC_STRING=$(cat ${MAC_FILE})
	  declare -a MAC_LIST
	  MAC_INDEX=0
	  IFS='\n'
	  for c_mac in $MAC_STRING ; do
		MAC_LIST[${MAC_INDEX}]=${c_mac}
		if [ "$prefix" == "$(echo -n ${c_mac} | cut -c 1-9)" ]; then
			MAC_FOUND="${c_mac}"
		fi
		MAC_INDEX=$((${MAC_INDEX}+1))
	  done
	  if [ ${MAC_FOUND} != "NO" ]; then
		RESULT_MAC=${MAC_FOUND}       
    LAST_BYTES=$(echo ${MAC_FOUND} | cut -c 10-17)
    # TODO It would really be safer to check for upper bound in next line even if it is a large number of addresses
		LAST_BYTES=$(echo "${LAST_BYTES}" | sed 's/://g')
    LAST_BYTES=$(($(echo -n "${LAST_BYTES}" | sed 's/^0*//')+1))
    LAST_BYTES="000000"$(echo -n "${LAST_BYTES}" | sed 's/^0*//') 
    LAST_BYTES=$(echo -n "${LAST_BYTES: -6}" | sed 's/.\{2\}/&:/g;s/:$//')
		NEXT_MAC="$(echo ${MAC_FOUND} | cut -c 1-9)$LAST_BYTES"
		sed -i "s/${MAC_FOUND}/${NEXT_MAC}/g" "${MAC_FILE}"
	  else
	  	RESULT_MAC="$(printf %s%.2d:%.2d:%.2d ${prefix} 0 0 1)"
		echo -ne "\n$(printf %s%.2d:%.2d:%.2d ${prefix} 0 0 2)" >> ${MAC_FILE}
	  fi
	
  else # Not important for now
	g_id=${2}
	d_id=0 #default
	if [[ $3 == *"pc"* ]]; then
		d_id=1
	elif [[ $3 == *"router"* ]]; then
		d_id=2
	fi
	d_no=${3//[!0-9]}
	
	RESULT_MAC=$(printf %s%.2d:%.2d:%.2d ${prefix} ${g_id} ${d_id} ${d_no})
  fi
  echo -n "${RESULT_MAC}"
}
