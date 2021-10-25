#!/bin/bash

TOTAL_MEM=$2
CPUS=$3
OUTER_VM=$(basename "$1" .vdi)
HDD_MAIN=$1
LOOPBACK_IP="127.0.0.1"
# this is assigned by vbox if using local NAT without a natnet
STATIC_IP="10.0.2.15" 
FORWARD_PORT_STATIC=$4

ref_exists () {
  echo $(vboxmanage list $1 | grep -c "$OUTER_VM")
}

stop_vm () {
  echo "Stopping existing VM to make changes to it!"
  vboxmanage controlvm "$OUTER_VM" "$1"
}

start_vm () {
  vboxmanage startvm "$OUTER_VM" --type headless
}

destroy_vm () { 
  echo "Unregistering and deleting VirtualBox vm $OUTER_VM!"
  stop_vm "poweroff"
  vboxmanage unregistervm "$OUTER_VM" --delete
}

create_vm () {
  echo "Setting up VM"
  CONTROLLER="SATA Controller"
  vboxmanage internalcommands sethduuid "$HDD_MAIN"
  vboxmanage createvm --name "$OUTER_VM" --ostype Debian_64 --register
  vboxmanage modifyvm "$OUTER_VM" --memory $TOTAL_MEM
  vboxmanage modifyvm "$OUTER_VM" --cpus $CPUS
  vboxmanage storagectl "$OUTER_VM" --name "$CONTROLLER" --add sata --controller IntelAhci 
  vboxmanage storageattach "$OUTER_VM" --storagectl "$CONTROLLER" --port 0 --device 0 --type hdd --medium $HDD_MAIN
  echo "Done with VM configuration!"
}

create_port_forward () {
 echo "Configuring port forwarding for VM $OUTER_VM"
 vboxmanage modifyvm "$OUTER_VM" --natpf1 "pfsdnconflicts,tcp,$LOOPBACK_IP,$FORWARD_PORT_STATIC,$STATIC_IP,22"
}

if [ $(ref_exists "vms") -eq 1 ]; then
  destroy_vm
  create_vm
else
  create_vm
fi

create_port_forward

echo "Starting VM and copying $OUTER_VM"
start_vm
if [ $(ref_exists runningvms) -gt 0 ]
then
  echo "Sucessfully started $OUTER_VM"
else
  echo "Failed to start vm $OUTER_VM"
fi
