#!/bin/bash
# $1: number of switch
NUMSW=$1

for i in $(seq 1 $NUMSW)
do
  echo router$i
  ssh router$i "ovs-vsctl add-br br"
  vif_counter=1
  until [ $vif_counter -lt 1 ]
  do
    ssh router$i "ip l | grep eth$vif_counter>/dev/null"
    if [ $? -eq 0 ]
    then
      ssh router$i "ovs-vsctl add-port br eth$vif_counter && ip l s eth$vif_counter up"
      let vif_counter++
    else
      let vif_counter=0
    fi
  done
  ssh router$i "ovs-vsctl set-controller br tcp:192.168.0.253:6653"
  ssh router$i "ovs-vsctl set-fail-mode br secure"
  ssh router$i "ovs-vsctl set Bridge br protocols=OpenFlow13"
  ssh router$i "ovs-vsctl set controller br connection-mode=out-of-band" #to avoid hidden flows of in-band mode, see OVS FAQ
  ssh router$i "ovs-vsctl show"
  dpid=$(printf "%05x" $i) #to make dpid a 5-digit number, and then add to it 11 leading 0 to have the 16-digit dpid
  ssh router$i "ovs-vsctl set bridge br other_config:datapath-id=00000000000$dpid"
  scp automating_experiment/switches/* router$i:
done

