#!/bin/bash

WORK_FOLDER=/root/autoexam/work
usage()
{
  echo "$0 <qcow> <name> <number>"
  echo "qcow:	The qcow to be converted and deployed"
  echo "name:	The name of the VM Image and Guest"
}

# Convert .qcow to .vmdk
# param1: input filename (.qcow)
# param2: vm image name
# return: .vmdk-file
convert()
{
  local vmdk=${WORK_FOLDER}/$2.vmdk
  echo "converting .qcow to .vmdk. That takes a bit..."
  qemu-img convert -f qcow2 -O vmdk $1 $vmdk
  echo "$vmdk"
}

#Generate a vmx file with the config for vmware
#param1: name of the vmware guest / vm Image
#return: vmxfile
generate_vmx()
{
  local name=$1
  local vmxfile=${WORK_FOLDER}/$name.vmx
  echo ".encoding = \"UTF-8\"" > $vmxfile
  echo "virtualHW.version = \"7\"" >> $vmxfile
  echo "nvram = \"$name.nvram\"" >> $vmxfile
  echo "pciBridge0.present = \"TRUE\"" >> $vmxfile
  echo "svga.present = \"TRUE\"" >> $vmxfile
  echo "pciBridge4.present = \"TRUE\"" >> $vmxfile
  echo "pciBridge4.virtualDev = \"pcieRootPort\"" >> $vmxfile
  echo "pciBridge4.functions = \"8\"" >> $vmxfile
  echo "pciBridge5.present = \"TRUE\"" >> $vmxfile
  echo "pciBridge5.virtualDev = \"pcieRootPort\"" >> $vmxfile
  echo "pciBridge5.functions = \"8\"" >> $vmxfile
  echo "pciBridge6.present = \"TRUE\"" >> $vmxfile
  echo "pciBridge6.virtualDev = \"pcieRootPort\"" >> $vmxfile
  echo "pciBridge6.functions = \"8\"" >> $vmxfile
  echo "pciBridge7.present = \"TRUE\"" >> $vmxfile
  echo "pciBridge7.virtualDev = \"pcieRootPort\"" >> $vmxfile
  echo "pciBridge7.functions = \"8\"" >> $vmxfile
  echo "vmci0.present = \"TRUE\"" >> $vmxfile
  echo "displayName = \"$name\"" >> $vmxfile
  echo "virtualHW.productCompatibility = \"hosted\"" >> $vmxfile
  echo "numvcpus = \"2\"" >> $vmxfile
  echo "memSize = \"4096\"" >> $vmxfile
  echo "floppy0.present = \"FALSE\"" >> $vmxfile
  echo "ide0:0.fileName = \"$name.vmdk\"" >> $vmxfile
  echo "ide0:0.present = \"TRUE\"" >> $vmxfile
  echo "guestOS = \"other\"" >> $vmxfile
  echo "toolScripts.afterPowerOn = \"TRUE\"" >> $vmxfile
  echo "toolScripts.afterResume = \"TRUE\"" >> $vmxfile
  echo "toolScripts.beforeSuspend = \"TRUE\"" >> $vmxfile
  echo "toolScripts.beforePowerOff = \"TRUE\"" >> $vmxfile

  echo $vmxfile
}

#copy a file on vmsphere Scratchspace
#param1: filename
#param2: lxnm20 username
copy_on_vmsphere()
{
  echo "copying $1 to lxnm20..."
  echo "scp $1 $2@lxnm20.nm.ifi.lmu.de:/proj/rnpadm/VMwareShare/$1"
}

#Run start command on vmsphere
#param1: guest name
#param2: MAC Address last number
start_guest_on_vmsphere()
{
  echo "run these two commands on VMSphere CLI"
  echo "New-VM -VMHost \"esxi1.lab.nm.ifi.lmu.de\" -ResourcePool \"RNP\" -VMFilePath \"[LRZ-Scratchspace] RNP/$1.vmx\""
  echo "Get-VM \"$1\" | Set-NetworkAdapter -Portgroup \"RNP\" -MACAddress \"00:50:56:03:00:$2\""
}

qcow=$1
name=$2
number=$3

vmdk=`convert $qcow $name`
vmx=`generate_vmx $name`
copy_on_vmsphere $vmdk "guggemos"
copy_on_vmsphere $vmx "guggemos"
start_guest_on_vmsphere $name $number

