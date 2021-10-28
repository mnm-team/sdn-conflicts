#!/bin/bash
# $1 is the number of switches
# $2 is the number of end-points (PCs)

. ./collectdata_config.bash

#stop the controller
#sleep 12 #wait for more than 2*TIMEOUT_DC, (in this case 2*5s), just in case, if the detector needs to build the rule graph, detect conflicts from the last round of rule deployment, and output the results in the detector_log when dc_flag = 0. This process takes at least 2*TIMEOUT_DC
echo "stop controller"
ssh -n con0 "pkill ryu-manager"
#clean the flows tables of all switches
echo "clean flow and group tables of all switches"
#ssh con0 "sh -c 'ryu-manager $RYU/app/cuong/delete_all_flow_and_group_tables_v1_0.py &' > /dev/null 2>&1"
#echo $APPDIR/$CLEARSWITCH_APP
#ssh -n con0 "sh -c 'ryu-manager $APPDIR/$CLEARSWITCH_APP  &' > /dev/null 2>&1"
ssh -n con0 "sh -c 'cd $APPDIR; timeout 10 ryu-manager $CLEARSWITCH_APP > clean.txt 2>&1'"
#wait for ~10s to clean all route from switches, then stop the controller
echo "stop tcpdump"
for i in $(seq 1 $1); do echo -n "router$i "; ssh -n router$i "pkill tcpdump" ; done 

#can do something in the meantime like flushing arp cache from all pc:
echo -e "\ncleaning arp cache of PCs:"
for i in $(seq 1 $2)
do
echo -n "pc$i "
ssh -n pc$i "sh -c 'pkill iperf; pkill nc; ip n f all'"
ssh -n pc$i "sh -c 'pkill iperf; pkill nc; ip n f all'" #sometimes need to kill iperf twice so that it really stops, seems like it has recovery mechanism against the first kill :)
done
sleep 2
#sometimes need to kill iperf twice so that it really stops, seems like it has recovery mechanism against the first kill :)
echo -e "\ntry again in stopping iperf, nc, sometimes it needs another try to be able to stop them."
for i in $(seq 1 $2)
do
echo -n "pc$i "
ssh -n pc$i "sh -c 'pkill iperf; pkill nc; ip n f all'" 
done
#sleep 5 #to be sure, sleep 5 seconds before stopping the controller
echo -e "\nstop controller"
ssh -n con0 "pkill ryu-manager"
#[ $# -gt 0 ] && numsw=$1 || numsw=10
#ssh -n con0 "cat $APPDIR/clean.txt" | grep "count = $numsw" 
ssh -n con0 "cat $APPDIR/clean.txt" | grep "count = $1" 
if [ $? -ne 0 ]; then
  echo "some OpenFlow switch stops working, try automatic recovery solution!" | tee -a conflict.txt
  ssh -n con0 "cat $APPDIR/clean.txt" | tail -1
  #for (( i=1; i<=$numsw; i++ )); do
  for (( i=1; i<=$1; i++ )); do
    ssh -n router$i "service openvswitch-switch restart"
  done
  ssh -n con0 "sh -c 'pkill ryu-manager; cd $APPDIR; timeout 10 ryu-manager $CLEARSWITCH_APP > clean.txt 2>&1'"
  sleep 15 #to be sure, sleep 10 seconds before stopping the controller
  ssh -n con0 "pkill ryu-manager"
  #ssh -n con0 "cat $APPDIR/clean.txt" | grep "count = $numsw" || (echo "some OpenFlow switch stops working, please check manually, program stops now due to a fatal network defect!" | tee -a conflict.txt && ssh -n con0 "cat $APPDIR/clean.txt" | tail -1 && exit 11)
  ssh -n con0 "cat $APPDIR/clean.txt" | grep "count = $1" || (echo "some OpenFlow switch stops working, please check manually, program stops now due to a fatal network defect!" | tee -a conflict.txt && ssh -n con0 "cat $APPDIR/clean.txt" | tail -1 && exit 11)
fi

