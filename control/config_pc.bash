#!/bin/bash
# $1: number of pc

for i in $(seq 1 $1)
do
  echo pc$i
  lastbyte=$(printf "%02d" $i) #to make lastbyte a 2-digit decimal number
  ssh pc$i "ip l s eth1 down"
  ssh pc$i "ip link set dev eth1 address 00:16:3e:11:11:$lastbyte"
  ssh pc$i "ip addr add 192.168.1.$i/24 broadcast 192.168.1.255 dev eth1"
  ssh pc$i "ip l s eth1 up"

  #set also the ip address in the pc's Xen config file, so that the mac address will change accordingly after rebooting, or destroying and re-creating.
  sed -i "s/00:00:[0-9a-zA-Z][0-9a-zA-Z], vifname=pc${i}_vif1/11:11:$lastbyte, vifname=pc${i}_vif1/" /xen/domains/pc$i/pc$i.cfg

  #ssh pc$i exit
  #if [ $? -eq 0 ]
  #then
  #  echo pc$i
  #  ssh pc$i "ip addr add 192.168.1.$i/24 broadcast 192.168.1.255 dev eth1"
  #  ssh pc$i "ip l s eth1 up"
  #fi
done
