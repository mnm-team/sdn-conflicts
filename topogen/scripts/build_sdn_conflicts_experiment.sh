#!/bin/bash

. constants_build_env.sh

usage()
{
  echo "$0 <specfilesdir>"
  echo "specfilepath: absolute path to a sdn conflicts spec file."
}

while getopts "h" opt
  do
    case ${opt} in
      h)
        usage
        exit 1 ;;
     \?)
        echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
    esac
  done

if [ ! -d "$1" ]
then
  echo "Need a path to a spec directory with spec files"
  usage
  exit1
fi


if [ -f "$MAC_FILE" ]
then
  echo "Removing any existing macfile at $MAC_FILE"
  rm "$MAC_FILE"
fi

mkdir "$SDN_TMP_DIR"
if [ ! -d  "$SDN_TMP_DIR" ]
then
  echo "Could not create directroy $SDN_TMP_DIR"
  exit 1
fi

# Try to determine the necessary memory for the outer vm
# Controllers will get 512MB and the outer machine 1024
# The memory for hosts and switches is specified in constants_xen.sh
num_nodes=$(ls $1 | grep -c -e "router" -e "pc")
num_controllers=$(ls $1 | grep -c -e "con")
maxmem_nodes=$(grep "maxmem" ./constants_xen.sh | grep -o -e "[0-9]*")
total_mem=$((maxmem_nodes*num_nodes + 512*num_controllers))

echo "Need ${total_mem}MB RAM for running the topology!"

printf "Use these setting or abort? y/n\n"
read -r ANSWER
if [ "$ANSWER" = "y" ]; then
  echo "Building topology!."
else
  echo "Stopping topology creation."
  exit 0
fi

./common_generate_xen_topology.sh "$1/qcow.spec"
/xen/rnp_vms start
