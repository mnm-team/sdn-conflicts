#!/bin/bash
#Deploy an exam on the exam infrastructure
SCRIPT_DIR=/root/autoexam/scripts/
CONFIG_FILE=${SCRIPT_DIR}/deploy_config.cfg
publish=0
create=0
start=0
prueflingprefix="pruefling"
noargs=0
slave=""
usage()
{
  echo "$0 <options> <exam> <first_instance> <last_instance>"
  echo "exam: 		 name of the directory with the exam specs"
  echo "                 It's loaded from <exam_dir> [${EXAM_FS}]"
  echo "first_instance:  number of first KVM instance for this exam"
  echo "last_instance:   number of last KVM instance for this exam"
  echo "config_file: 	 config_file for the deployment"
  echo ""
  echo "Options:"
  echo " by default, options are loaded from <config_file>"
  echo "   --config config_file [${CONFIG_FILE}]: must always come first!"
  echo "   -c --create: creates the exam.qcow for the exam_config in "
  echo "                <working_dir>/<exam>/exam.qcow"
  echo "   -p --publish: publish the qcow for the exam. "
  echo "                 there must be a exam.qcow in the work directory "
  echo "      <working_dir>/<exam>/exam.qcow"
  echo "   -s --start: starts all matching kvms placed in ${KVM_DIR}"
  echo "   -P <nameprefix> -- use <nameprefix> when naming KVM instances," 
  echo "                      instead of the default \"${prueflingprefix}\""
  echo "   -e exam_dir [${EXAM_FS}]"
  echo "   -w working_dir [${WORKING_DIR}]"
  echo "   -x xen_dir [${XEN_DOMAINS}]"
  echo "   -k kvm_domains [${KVM_DIR}]"
  echo "   --slave <slave_machine>"
  echo "           copies aufgabe and templates via scp to slave and runs the command there"
  echo "           it will clean up slave before copying, so make sure there are no unsaved"
  echo "           files on the slave"
  echo "           It makes sense to copy your public ssh-key on the slave first, otherwise"
  echo "           you'll be asked to prompt your password all the time :-) "
  echo "           e.g. --slave root@autoexam2"
  echo "examples create:"
  echo "$0 -c aufgabe00"
  echo "    creates ${WORKING_DIR}/aufgabe00/exam.qcow from ${EXAM_FS}/aufgabe00"
  echo "examples publish:"
  echo "$0 -p aufgabe00 1 10"
  echo "    deploys ${WORKING_DIR}/aufgabe00/exam.qcow  for 10 ${prueflingprefix} (no 01 - 10)"
  echo "$0 -p aufgabe01 11 20"
  echo "    deploys ${WORKING_DIR}/aufgabe01/exam.qcow  for 10 ${prueflingprefix} (no 11 - 20)"
  echo "$0 -p aufgabe02 20 25"
  echo "    deploys ${WORKING_DIR}/aufgabe02/exam.qcow for 5 ${prueflingprefix} (no 21 - 25)"
  echo "examples start:"
  echo "$0 -s 1 10"
  echo "    starts ${KVM_DIR}/${prueflingprefix}01 - ${KVM_DIR}/${prueflingprefix}10"
}

#Makes a wallpaper.png from a wallpaper.fig
#$1 Hostname of the machine, will be added in the png
#$2 Path where the wallpaper.fig is located and where the png will be written.
mkwallpaper()
{
  hname=$1
  fig_path=$2
  infig=${fig_path}/wallpaper.fig
  tmpfig=$(mktemp)
  outbitmap=${fig_path}/wallpaper.png

  sed -e "s/KVMMASTER/$hname/g" < $infig > $tmpfig
  mv $tmpfig $infig
  fig2dev -L png -S 1 -Z 30 $infig $outbitmap
}

#$1 = xen_img
#$2 = mount_dir
mount_xen()
{
  if [ ! -d $2 ] ; then mkdir $2; fi
  #returns a loop dev
  dev=`losetup -f --show $1`
  mount ${dev} $2
  echo ${dev}
}

#$1 = mount_dir
#$2 = loop dev
umount_xen()
{
  umount $1
  losetup -d $2
  if [ -d $2 ] ; then rm  -rf $2; fi
}

#creates a disk.img in xen/domains and copies the config for the $machine
#$1 machine_name
#$2 xen image template
#$3 target path to xen/domains
#$4 config commons_dir
#$5 config vmimages_dir
conf_xen()
{
    local machine=$1
    local xen_img_tmp=$2
    local xen_domains_dir=$3
    local commons_dir=$4
    local vmimages_dir=$5

    local xen_img=${xen_domains_dir}/${machine}/disk.img
    local xen_mnt_dir=${xen_domains_dir}/${machine}/mnt
    if [ ! -d ${xen_mnt_dir} ] ; then mkdir ${xen_mnt_dir}; fi

    echo "    create ${machine} from  ${xen_img_tmp}"
#    mv ${xen_img_tmp} ${xen_img}
    cp ${xen_img_tmp} ${xen_img}

    #store the mounted /dev/loop in a variable for a save umount
    echo "Mount xen image ${xen_img}"
    dev=`mount_xen ${xen_img} ${xen_mnt_dir}`

    echo "  copying vm configuration"
    echo "    ${common_dir}/"
    echo "    ${vmimages_dir}/${machine}/"
    cp -rv ${common_dir}/* ${xen_mnt_dir}
    cp -rv ${vmimages_dir}/${machine}/* ${xen_mnt_dir}

    echo "  umount_xen ${xen_mnt_dir} ${dev}"
    umount_xen ${xen_mnt_dir} ${dev}
}

# takes care of the init-system of the outer vm.
# param1: mnt_dir for chroot
# return: -nothing-
configure_init_kvmmaster()
{
  # start inner vms
  chroot $1 insserv rnp_vms
  # start display manager
  chroot $1 insserv xdm
}

# Given a template image, create a master image for an outer VM 
# with a specific internal infrastructure topology and configuration.
# PARAMS:
# src_outer_img -- a template image used as a starting point
# src_inner_img -- a template image used as a starting point
# xen_dir_offset -- path within outer VM where inner images reside
# work_dir -- the temporary work directory for exam-specific images
# common_conf_dir -- fs subtree for all VMs
# inner_conf_dir -- fs subtree for inner VMs, by their hostnames
# outer_conf_dir -- fs subtree for outer VM only
create_exam_qcow()
{
  src_outer_img=$1 
  src_inner_img=$2
  xen_dir_offset=$3 
  work_dir=$4
  common_conf_dir=$5 
  inner_conf_dir=$6
  outer_conf_dir=$7
  
  . ${SCRIPT_DIR}/common_qcow_helpers.sh

  echo "Prepare a qcow image with all the xen configuration for ${work_dir}" >&2
  qcow_mnt_dir=${work_dir}/mnt
  target_outer_img=${work_dir}/exam.qcow
  if [ ! -d ${qcow_mnt_dir} ] ; then mkdir ${qcow_mnt_dir}; fi
  echo "--copying qcow image. That takes a bit..." >&2
  cp -v ${src_outer_img} ${target_outer_img}
  echo "--copying done." >&2

  mount_qcow ${target_outer_img} ${qcow_mnt_dir}
  if (( $? != 0 )); then return 1; fi
  echo "--copy conf files from " >&2
  echo "--  ${common_conf_dir}/" >&2
  cp -rv ${common_conf_dir}/* ${qcow_mnt_dir}
  echo "--  ${outer_conf_dir}/" >&2
  cp -rv ${outer_conf_dir}/* ${qcow_mnt_dir}

  configure_init_kvmmaster ${qcow_mnt_dir}

#----- copy conf for inner VMs
  local i=0
  local xen_domains_dir=${qcow_mnt_dir}/${xen_dir_offset}
  for machine in $(ls ${outer_conf_dir}/${xen_dir_offset})
  do
    let "i++"
    local xen_img_tmp=${xen_domains_dir}/${src_inner_img}
    #local xen_img_tmp=${xen_domains_dir}/${src_inner_img}
    echo "..conf_xen 1 $machine 2 ${xen_img_tmp} 3 ${xen_domains_dir} 4 ${common_conf_dir} 5 ${inner_conf_dir}"
    conf_xen $machine ${xen_img_tmp} ${xen_domains_dir} ${common_conf_dir} ${inner_conf_dir}
  done
  echo "--umount qcow" >&2
  umount_qcow ${qcow_mnt_dir}
  echo "Finished preparing golden image for ${exam}" >&2
  echo $target_outer_img
}

publish_exam_qcows()
{
  . ${SCRIPT_DIR}/common_qcow_helpers.sh
  #make ip and hostname modification for each KVM instance
  echo "Populate the master qcow image for each KVM instance"
  for ((i=$1;i<=$2;i++)) ;
  do
    local pruefling_no=`printf %02d $i`
    local pruefling_str="${prueflingprefix}${pruefling_no}"
    work_dir_pruef=${work_dir}/${pruefling_str}
    local pruefling_qcow=${work_dir_pruef}/${pruefling_str}.qcow
    local qcow_mnt_dir=${work_dir_pruef}/mnt

    echo "clean working dir ${work_dir_pruef}"
    if [ -d ${work_dir_pruef} ] ; then rm -rf ${work_dir_pruef}/*; fi
    if [ ! -d ${work_dir_pruef} ] ; then mkdir ${work_dir_pruef}; fi
    if [ ! -d ${qcow_mnt_dir} ] ; then mkdir ${qcow_mnt_dir}; fi

    echo "deploying ${exam} for ${pruefling_str}"
    echo "  copying qcow image. That takes a bit..."
    qemu-img create -f qcow2 -o backing_file=${exam_qcow} ${pruefling_qcow}
    if (( $? != 0 )); then 
      echo "Failed creating backing file ${exam_qcow} for image ${pruefling_qcow}" >&2 ;
      exit 1; 
    fi
    #cp -v ${exam_qcow} ${pruefling_qcow}
    echo "  mount qcow image to ${qcow_mnt_dir}"
    #mount_qcow ${pruefling_qcow} ${qcow_mnt_dir} ${QCOW_DEV}
    mount_qcow ${pruefling_qcow} ${qcow_mnt_dir}
    if (( $? != 0 )); then exit 2; fi

    #set hostname
    echo "${pruefling_str}" > ${qcow_mnt_dir}/etc/hostname
    sed -i s/kvmmaster/${pruefling_str}/g ${qcow_mnt_dir}/etc/hosts

    #set IP for kvm-master
    local temp_ip=${KVM_MASTER_IP_ADDR}${KVM_MASTER_TEMP_IP}
    let "new_ip=${KVM_MASTER_IP_RANGE_START}+i"
    local new_ip=${KVM_MASTER_IP_ADDR}${new_ip}
    sed -i s/${temp_ip}/${new_ip}/g ${qcow_mnt_dir}/etc/network/interfaces

    #update /etc/hosts
    echo "add ${pruefling_str} with ${new_ip} to /etc/hosts"
    grep -v ${pruefling_str} /etc/hosts > /etc/temp_hosts
    mv /etc/temp_hosts /etc/hosts
    echo "${new_ip}   ${pruefling_str}" >> /etc/hosts

    #generate wallpaper
    mkwallpaper ${pruefling_str} ${qcow_mnt_dir}/home/rnp

    echo "  umount qcow"
    umount_qcow ${qcow_mnt_dir} ${QCOW_DEV}
    #./qcow-umount.sh ${qcow_mnt_dir}

    rm -f ${KVM_DIR}/${pruefling_str}.qcow
    echo "  move qcow to ${KVM_DIR}"
    mv ${pruefling_qcow} ${KVM_DIR}
    echo "  clean work dir ${work_dir_pruef}"
    rm -rf ${work_dir_pruef}
  done

}

start_kvms()
{
  echo "Start kvm for each ${prueflingprefix}"
  for ((i=$1;i<=$2;i++)) ;
  do
    local pruefling_no=`printf %02d $i`
    local pruefling_str="${prueflingprefix}${pruefling_no}"

    #start kvm for pruefling
    echo "  start vm ${pruefling_str}"
    #echo "------------------ ACHTUNG ------------------" 
    #echo "KVM Instanz wird NICHT gestartet, da sie sonst vor dem Testat auf den Terminals verfügbar wäre."
    #echo "Wenn sie gestartet wird, sollte kurz danach XDM abgedreht werden, bis kurz vor der Prüfung."
    echo "${EXEC_START_KVM_MASTER} ${pruefling_str} ${pruefling_no} &"
    ${EXEC_START_KVM_MASTER} ${pruefling_str} ${pruefling_no} &
  done

}

#$1 = slave
#$2 = skript
#$3 = parameter
#$4 = exam_dir
#$5 = TEMPLATE_DIR
#$6 = work_dir
run_on_slave()
{
  local slave=$1
  local skript=$2
  local parameter=$3
  local exam_dir=$4
  local template_dir=$5
  local work_dir=$6

  scp ${exam_dir} $slave:${exam_dir}
  current_dir=$(pwd)
  if (( create == 1 )) ; then
    scp ${TEMPLATE_DIR} $slave:/
  fi

  if [ -d ${work_dir} ]; then
    scp ${work_dir} $slave:${work_dir}
  fi
  parameter=$(echo $parameter | sed "s/$slave//g")
  ssh $slave ${current_dir}/$skript $parameter
}

deployment()
{
  echo "Started with Parameters $1 $2 $3 $4"
  if [ $# == 1 ]; then
    exam=$1
  elif [ $# == 2 ]; then
    begin=$1
    end=$2
  elif [ $# == 3 ]; then
    exam=$1
    begin=$2
    end=$3
  fi

  if [ ! -d ${WORKING_DIR} ] ; then mkdir ${WORKING_DIR}; fi
  work_dir=${WORKING_DIR}/${exam}
  if [ ! -d ${work_dir} ] ; then mkdir ${work_dir}; fi
  exam_qcow=${work_dir}/exam.qcow

  if [ ! -z $slave ]; then
    run_on_slave $slave $skript $parameter ${exam_dir} ${TEMPLATE_DIR} ${work_dir}
    return 0;
  fi


  if (( create == 1 )) ; then
    if [ ! -d ${exam_dir} ] ; then 
      echo "Cannot find directory $1 with exam spec." >&2 ;
      exit 1;
    fi
 
    exam_dir=${EXAM_FS}/${exam}

    kvm_master_dir=${exam_dir}/kvmmaster
    vmimages_dir=${exam_dir}/vmimages
    common_dir=${exam_dir}/COMMON
 
    echo "create ${exam_qcow} from ${exam_dir} and ${TEMPLATE_QCOW_IMG}"

    create_exam_qcow  ${TEMPLATE_QCOW_IMG} \
		${XEN_IMG_NAME} \
		${XEN_DOMAINS} \
		${work_dir} \
		${common_dir} \
		${vmimages_dir} \
		${kvm_master_dir}
  fi
  if (( publish == 1 )); then
    echo "publish ${exam_qcow} to ${pruefling_prefix}$2 - ${pruefling_prefix}$3 in ${KVM_DIR}"
    publish_exam_qcows $begin $end
  fi
  if (( start == 1 )); then
    echo "start ${KVM_DIR}/${pruefling_prefix}$2 - ${KVM_DIR}/${pruefling_prefix}$3"
    start_kvms $begin $end
  fi
}

parameter="$@"
skript="$0"
#Ensure --config is the first option, if present!
if [[ "$1" = --config ]] ; then
   echo "load"
   CONFIG_FILE="$2"
   # load_config is a function that sources the config file
   shift 2
fi

#load config-file
. ${CONFIG_FILE}

while [[ $# > $noargs ]]
do
key="$1"
case $key in
    -e|--examfs)
      EXAMFS="$2"
      shift 2 ;; # past argument
    -w|--workdir)
      WORKING_DIR="$2"
      shift 2 ;; # past argument
    -k|--kvmdir)
      KVM_DIR="$2"
      shift 2 ;; # past argument
    -x|--xendomains)
      XEN_DOMAINS="$2"
      shift 2 ;; # past argument
    -p|--publish)
      publish=1
      if [ $noargs -lt 3 ];then noargs=3;fi
      shift ;; # past argument
    -c|--create)
      create=1
      if [ $noargs -lt 1 ];then noargs=1;fi
      shift ;; # past argument
    -s|--start)
      if [ $noargs -lt 2 ];then noargs=2;fi
      start=1
      shift ;; # past argument
    -P|--prueflingprefix)
      prueflingprefix="$2"
      shift 2;; 
    --slave)
      slave="$2"
      shift 2;;
    -h|--help)
      usage
      exit 1 ;;
    *) # unknown opt
      echo "Invalid option: -$1" >&2; exit 1 ;;
esac
done
if [ "$#" -lt "$noargs" ] ;
then
  usage
  exit 1;
else
    deployment $1 $2 $3 ;
fi
