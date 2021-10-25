#!/bin/bash


##################################################################
# Mount a qcow image
# Requires: sysfs
# Params: <qcow image file> <mount point> 
# Example: qcowloopmount ./foo.qcow ./qcow_mnt 
##################################################################
qcowloopmount () {
  # QCow image
  img=$1
  # Mount point
  mnt=$2
  
  
  # Check parameters
  if [ ! -e $img ] ; then echo "Fatal: Image file $img does not exist." >&2 ; return 1; fi
  if [ ! -d $mnt ] ; then echo "Mount point $mnt is not a directory."  >&2 ; return 2; fi

  # Load nbd module if not already loaded
  lsmod | grep nbd > /dev/null 2>&1
  if (( $? == 0 )) ; then 
    #echo "nbd module already loaded, good." >&2 ;
    true 
  else 
    modprobe nbd max_part=63 ;
    if (( $? != 0 )) ; then echo "Fatal: could not load nbd module."  >&2 ; return 3; fi;
  fi
  
  # Network Block Device
  loopdev=$(getfreenbd)
  if [ -z $loopdev ] ; then echo "Fatal: Cannot find free NBD." >&2 ; return 7; fi


  # NBD partition
  loopdevpart=${loopdev}p1

  qemu-nbd  --cache=none --aio=native -c $loopdev  $img
  if (( $? != 0 )) ; then echo "Fatal: failed loopback on $loopdev ."  >&2 ; return 4; fi;
  # Ensure device is actually there, because qemu-nbd tends to lie
  echo "Waiting for loop device ${loopdevpart}" >&2
  waitforit ${loopdevpart} 10
  res=$?
  if (( $res != 0 )) ; then 
    echo "Error: loop device ${loopdevpart} did not appear; aborting mount." >&2
  else
    mount $loopdevpart $mnt
    res=$?
  fi
  if (( $res != 0 )) ; then 
    echo "Error failed mount on ${loopdevpart} to ${mnt} . "  >&2 ; 
    echo "Attempting to disconnect $loopdev ..."  >&2 ;
    qemu-nbd -d $loopdev ; 
    if (( $? != 0 )) ; then 
      echo "...sorry, failed cleaning up."  >&2; 
    else 
      echo ...success cleaning up.  >&2; 
    fi;
    return 5; 
  fi;
  return 0
}

##################################################################
# Wait for a file to appear.
# Params: <file> <timeout>
# 
# timeout is the number of 0.1 sec  units
##################################################################
waitforit () {
  SLEEPUNIT=0.1 
  filename=$1
  declare -i timeoutleft=$2
  while [ ! -e ${filename} ] ; do
    echo -n "." >&2
    sleep ${SLEEPUNIT} ;
    if ((--timeoutleft <= 0)); then return 1; fi
  done
  return 0
}

##################################################################
# Return a Network Block Device (NBD) that is not currently in use
# Src: http://stackoverflow.com/questions/22535222/next-free-device-option-for-qemu-nb
##################################################################
getfreenbd () {
for nb in /sys/class/block/nbd* ; do
  sizevar=${nb}/size
  #echo trying $nb >&2
  size=$(cat $sizevar) ;
  #echo size is $size >&2
  if [ "${size}" == "0" ] ; then
    nbd=/dev/`basename ${nb}` ;
    #echo "Using $nbd" >&2 ;
    # Now, return the device name to caller on STDOUT
    echo $nbd ;
    return 0 ;
  fi;
done
return 1
}

##################################################################
# Return the Network Block Device (NBD) mounted at a given location
# Params: <mountpoint>
##################################################################
getnbdbymountpoint () {
  local result=$(grep $1 /proc/mounts | cut -d " " -f 1)
  echo "$result"
}



##################################################################
# Unmounts an image and detaches it from loopback
# Params: [<mount point>]
# Example qcowunmount ./qcow_mnt 
##################################################################
qcowunmount () {
  if [ -z $1 ] ; then echo "Usage: $FUNCNAME [<mount point>]" >&2 ; return 0; fi
  mnt=$1
  mountpoint -q $mnt
  if (( $? != 0 )) ; then echo "$mnt is not a mountpoint" >&2; return 1; fi 

  nbd=$(getnbdbymountpoint $mnt)
  if [ -z $nbd ]; then echo "no device found for $mnt." >&2; return 2; fi
  qemu-nbd -d $nbd
  if (( $? != 0 )) ; then echo "cannot disconnect NBD $nbd" >&2 ; return 3; fi
  umount -l $mnt
  if (( $? != 0 )) ; then echo "umount failed." >&2 ; return 2; fi
  return 0
}

##################################################################
# Warn if not root
##################################################################
warnifnotrootuser () {
  if (( $(id -u) != 0 )) ; 
  then echo "$0 Warning: attempting to run for non-root user." >&2 ;fi
}



##################################################################
# Mount qcow image
# $1 <qcow image file>
# $2 <mount point> (OPTIONAL)
# Returns: <mount point>
##################################################################
mount_qcow()
{
  qcow_image=${1}
  qcow_mount_dir=${2}

  # Warn if not root
  if (( $(id -u) != 0 )) ; 
  then echo "$0 Warning: attempting to run for non-root user." >&2 ;fi

  qcow_mount_dir=$2
  if [ -z ${qcow_mount_dir} ] ;  then
    # Make temporary directory
    qcow_mount_dir=$(mktemp -d qcow_tmpmnt_XXX) 
    if (( $? != 0 )) ; then echo "Cannot create temporary directory." >&2 ; exit 2; fi ;
  fi

  # Do loopbackmount
  qcowloopmount ${qcow_image} ${qcow_mount_dir}
  if (( $? != 0 )) ; then echo "Failed to loopback and mount ${qcow_image} ." >&2 ; exit 3; fi
  echo ${qcow_mount_dir}
}



##################################################################
# Unmount qcow image
# $1 <mount point>
# Returns: <mount point>
##################################################################
umount_qcow()
{
  warnifnotrootuser

  # Unmount and unloop the image
  qcowunmount $1
}

usage()
{
  echo "$0 mount <qcow> <mountpoint>: mounts qcow to mountpoint"
  echo "$0 mount <qcow>:              mounts qcow"
  echo "$0 umount <mountpoint>:      ummounts <mountpoint>"
}

action=$1
echo "$action"
if [ -z $action ]; then
  usage
elif [ "$action" = "umount" ]; then
 mountpoint=$2
 umount_qcow $mountpoint
elif [ "$action" = "mount" ]; then
  qcow=$2
  mountpoint=$3
  mount_qcow $qcow $mountpoint
else 
  usage
fi

