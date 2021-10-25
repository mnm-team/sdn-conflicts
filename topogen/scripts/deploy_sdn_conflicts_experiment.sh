#!/bin/bash

. constants_build_env.sh

VDI_START=deploy_vbox.sh

usage()
{
  echo "$0 <specfilesdir> [<remotehost> <sshconfig> <identityfile]"
  echo "specfilepath: absolute path to a sdn conflicts spec file."
  echo "remotehost: optional, if given the setup is deployed on a remote host as defined in ~/.ssh/config."
}

convertToVdi()
{
  vdi=$(realpath "$1")
  vdi=$(echo "$vdi" | sed 's/qcow/vdi/')
  qemu-img convert -f qcow2 "$1" -O vdi "$vdi"
  #rm "$1"
  echo "$vdi"
}


copyToRemote()
{
  scp -F "$3" -i "$4" "$1" "$2":
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
  echo "Could not create directory $SDN_TMP_DIR"
  exit 1
fi

# Try to determine the necessary memory for the outer vm
# Controllers will get 512MB and the outer machine 1024
# The memeory for hosts and switches is specified in constants_xen.sh
num_nodes=$(ls "$1" | grep -c -e "router" -e "pc")
num_controllers=$(ls "$1" | grep -c -e "con")
maxmem_nodes=$(cat ./constants_xen.sh | grep "maxmem" | grep -o -e "[0-9]*")
total_mem=$((maxmem_nodes*num_nodes + 512*num_controllers + 1024))

# try to determine how many cpu cores the local/remote machine provides
cpus="NULL"
if [ "$2" == "" ]
then
  cpus=$(echo $(lscpu) | grep -o -E "CPU\(s\):\s[1-9]+" | awk '{print $2}') 
else
  if [ -f "$3" ] && [ -f "$4" ]
  then
    cpus=$(ssh -t -F "$3" -i "$4" "$2" "echo $(lscpu) | grep -o -E 'CPU\(s\):\s[1-9]+' | awk '{print $2}'")
  else
    echo "ERROR: No ssh config file or/and identity file specified, which is required for remote deployment."
  fi
fi
# check if reading cpus was successfull
if [ "$cpus" = "NULL" ]; then
  echo "Could not get number of cpu cores on the host machine."
  cpus=1
else
  echo "Number of cpus is: ${cpus}"
fi
# get user input for number of cpus
printf "How many cpus should be used? Enter a number larger than 0 and lower or equal to the number of cores on the host machine.\n"
read -r INCPUS
if [ $INCPUS -gt $cpus ]
then
  echo "To many cpus, defaulting to max detected cpus!"
  INCPUS=$cpus
elif [ $INCPUS -lt 1 ]
then
  echo "Number of cpus needs to be larger that 0! Defaulting to one cpu."
  INCPUS=1
fi

# get a port for local port forwarding and ssh acces to the machine
printf "Which port should be used on the host machine for local ssh access to the VM? Enter a number starting from 2000 up. If you deploy multiple topologies on a host this needs to be unique per topology!\n"
read -r SSHPORT
if [ $SSHPORT -lt 2000 ]
then
  echo "Given port for port forwarding is lower than 226. Defaulting to 226 to avoid collisions with any standard ports on the host machine."
  SSHPORT=2000
fi

echo "Using ${INCPUS} cpus for outer VM."
echo "Need ${total_mem}MB RAM for running the topology!"
echo "To access topology on the host machine use > ssh -p${SSHPORT} root@127.0.0.1 < ."

printf "Use these setting or abort? y/n\n"
read -r ANSWER
if [ "$ANSWER" = "y" ]; then
  echo "Building topology!."
else
  echo "Stopping topology creation."
  exit 0
fi

spec_dir_name=$(basename "$1")
qcow_image=$(realpath "$SDN_TMP_DIR/$spec_dir_name""_target.qcow")
./common_generate_qcow_image.sh "$1/qcow.spec" "$qcow_image"
if [ ! -e "$qcow_image" ]
then
  echo "Something went wrong, could not find a qcow image at ""$qcow_image""."
  exit 1
fi

echo "Converting .qcow to .vdi. That takes a bit..."
vdi_image=$(convertToVdi "$qcow_image")
if [ ! -e "$vdi_image" ]
then
  echo "Something went wrong, could not find a vdi image at ""$vdi_image""."
  exit 1
fi
echo "Created virtualbox image at ""$vdi_image""."


if [ "$2" == "" ]
then
  echo "Starting up topology on the local machine."
  ./$VDI_START "$vdi_image" $total_mem $INCPUS $SSHPORT
else
  if [ -f "$3" ] && [ -f "$4" ]
  then
    echo "Copy necessary files to the provided remote host."
    copyToRemote "$vdi_image" "$2" "$3" "$4"
    copyToRemote $VDI_START "$2" "$3" "$4"
    vdi_image_name=$(basename "$vdi_image")
    ssh -t -F "$3" -i "$4" "$2" "./${VDI_START} ${vdi_image_name} ${total_mem} ${INCPUS} ${SSHPORT}"
  else
    echo "ERROR: No ssh config file or/and identity file specified, which is required for remote deployment."
  fi
fi
