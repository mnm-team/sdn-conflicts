# !/bin/sh

usage()
{
  echo "usage $0 <-options> <vm_name> <pruefling_no>"
  echo "vm_name:      name of the qcow image"
  echo "pruefling_no: no of pruefling for mac address"
  echo "-options:     optional options"
  echo "    -d:       kvm directory [/srv/kvm]"
  echo "    -h:	      print this help"
}

start()
{
  VMNAME="$1"
  RUNDIR=${KVMDIR}/run/${VMNAME}
  MACPREFIX=52:54:13:37
  MACADDR="${MACPREFIX}:01:$2"
  mkdir -p ${RUNDIR}
  kvm -name ${VMNAME} \
  -hda ${KVMDIR}/${VMNAME}.qcow \
  -boot d -m 4096 \
  -net tap,ifname=${VMNAME} \
  -net nic,macaddr=${MACADDR},name=${VMNAME}nic0 \
  -chardev socket,id=monitor,path=${RUNDIR}/monitor.sock,server,nowait \
  -monitor chardev:monitor \
  -vnc none -daemonize

#  -drive file=${KVMDIR}/${VMNAME}.qcow,cache=writeback,index=0 \
#  -chardev socket,id=serial0,path=${RUNDIR}/console.sock,server,nowait \
#  -serial chardev:serial0 \
#  -vnc :$2 -daemonize
#-curses 

#   -net bridge,vlan=600,br=br0.600 \
#   -netdev user,id=user.0 -device e1000,netdev=user.0 \
#   -display curses \
}

KVMDIR="/srv/kvm"

while getopts "d:h" opt
  do
    case ${opt} in
      d)
        KVMDIR=${OPTARG};;
      h)
        usage
        exit 1 ;;
     \?)
        echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
    esac
  done

if [ "$#" -ne "2" ] 
then
  usage
  exit
else
  start $1 $2
fi
