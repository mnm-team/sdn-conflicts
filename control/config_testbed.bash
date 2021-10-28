#!/bin/bash

# $1: Number of switches
# $2: Number of end-points

# this script is to run in the parent directory of the automating_experiment directory
# run this script only once for the setting up of the testbed after generating the topology and (make sure) all the PC and Switches are already up (sometime some of them are not automatically brought up, check by xl list). Then run the "read_parameter_space.bash" inside the automating_experiment directory to collect the dataset based on the parameter_space.bash

[ $# -ne 2 ] && echo "please input the number of switches and end-points in the topology" && exit 1

NUMSW=$1
NUMEP=$2

# check if all xen domains are started or wait for /etc/init.d/rnp_vms to finish
NUMS=0
((NUMS+=NUMSW + NUMEP + 1)) # switches, hosts and controller
TIMEOUT=20
STARTED=$(xl list | grep -c -e router* -e pc* -e con*)
until [ "$NUMS" == "$STARTED"  ] || [ $TIMEOUT -eq 0 ]
do
  sleep 1
  let TIMEOUT--
done

################################
# 0. Maybe not necessary, if all necessary software/packages were already installed
################################
#sysctl -w net.ipv4.ip_forward=1
#iptables -t nat -A POSTROUTING -o ens3 -j MASQUERADE

###############################
# TODO check if this works when using last three digits of mac addresses up to 252
# 1. put eth0's ip addresses of all pc, sw in /etc/hosts, so that the outermachine can ssh there by
# hostname, ip address of the controller is always 192.168.0.253 and the entry: 192.168.0.253 con0
# is always there in /etc/hosts
###############################

getLastByte() {
  str=$1
  # get mac and remove double colons
  lastbyte=$(echo $str | cut -c 6-22 | sed 's/://g')
  # use last three digits in mac
  lastbyte=${lastbyte: -3}
  # remove leading zeros
  lastbyte=$(echo $lastbyte | sed 's/^0*//')
  # this is an unsafe way to set IPs so check and warn for debugging purposes
  if [ "$lastbyte" -gt 252 ]; then
    echo "WARNING: cannot set last byte of eth0 IP larger to a value larger than 252!"
  fi
  echo -n $lastbyte
}

echo "generating /etc/hosts..."
echo "192.168.0.253  con0" | tee /etc/hosts
for i in $(seq 1 $NUMEP); do
  str=$(grep vif0 /xen/domains/pc$i/pc$i.cfg)
  lastbyte=$(getLastByte $str)
  #lastbyte=$(echo $str | cut -d' ' -f1 | cut -d':' -f6 | cut -d',' -f1 | sed 's/^0//')
  host="pc"$i
  echo "192.168.0.$lastbyte   $host" | tee -a /etc/hosts
done
for i in $(seq 1 $NUMSW); do
  str=$(grep vif0 /xen/domains/router$i/router$i.cfg)
  lastbyte=$(getLastByte $str)
  host="router"$i
  echo "192.168.0.$lastbyte   $host" | tee -a /etc/hosts
done


###############################
# 2. Add the fingerprints of all innermachines to the .ssh/known_hosts, so the shell script will not be tripped up by the ssh fingerprints, which usually appear for the first time we ssh to a new machine
###############################
echo "Add fingerprints for all machines inside..."
ssh-keyscan -H con0 >> ~/.ssh/known_hosts
for i in $(seq 1 $NUMEP); do
ssh-keyscan -H pc$i >> ~/.ssh/known_hosts
done
for i in $(seq 1 $NUMSW); do
ssh-keyscan -H router$i >> ~/.ssh/known_hosts
done


###############################
# TODO do we need to adapt the mac or only set the IP
# => if yes why does eplb need macs to be adapted?
# 3. config eth1's IP and MAC addresses of all PC
# need to config mac address of eth1 interfaces of all pcs, so that the eplb app can work properly with the predefined MAC address.
# The last byte of eth1's IP and MAC address of each PC and the PC's name correspond: IP-prefix: 192.168.1, MAC-prefix: 00:16:3e:11:11:, e.g., PC5 has eth1's IP 192.168.1.5 and MAC 00:16:3e:11:11:05
###############################
echo "Configure eth1's ip address and mac address of pc..."
bash config_pc.bash $NUMEP


###############################
# 4. Config open-vswitch for all SW, add bridge, add ports to bridge, change the datapath id, connect them to the controller.
# generate dumpflows.sh... in all switches
# put the files that are independent from the switch's name inside all switches in advance (in sample switch image).
# generate the bridge name in each switch to be the same "br" to make it also independent from the switch name, e.g., instead of br1, br2...
# note that current config_ovs.bash only supports a switch of up to 9 interfaces: from eth1 to eth9. it will not work for eth10 and above, you have to modify the config_ovs.bash if it is the case.
###############################
echo "Configure the ovs in switches..."
bash config_ovs.bash $NUMSW


###############################
# 5. Copy app_files from out vm to controller and clone the git repository of in the dataset/massive from the controller:
###############################
echo "Copying current app_files and auto-generated local config files to controller"
mv automating_experiment/app_files automating_experiment/massive
ssh con0 "rm massive/*"
scp -r automating_experiment/massive con0:
ssh con0 "cd massive && git add . && git commit -m 'Inserting current app files from outer vm' && git push"
echo "Clone the massive git-repo from the controller into the dataset"
mkdir -p automating_experiment/dataset
rm -rf automating_experiment/dataset/massive
(cd automating_experiment/dataset; git clone con0:git-repo/massive)
