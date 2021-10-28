#!/bin/bash

# this file is for the inside machines (PC / routers)
# can pass one argument or two argument or no argument at all
# $1 first argument is the signal
# $2 second argument is the timestamp
# to run this:
# bash tcpdump.sh signal
# e.g. bash tcpdump.sh PLB_alone
# or bash tcpdump.sh appsuite_multipath_conflict

timestamp=$(date +"%y%m%d_%H%M")
if [ $# -gt 1 ]
then timestamp=$2
fi
echo $timestamp

#list_interface=$(tcpdump -D | grep -v eth0| grep eth | cut -c3-6| xargs) #--> wrong if there is eth10, eth11...
list_interface=$(tcpdump -D | grep -v eth0 | grep eth | sed --expression='s/^[0-9]\+.//g' | cut -c1-5 | xargs) #correct until eth99
echo $list_interface
for eth in $list_interface
do
 echo $eth
 #tcpdump -i$eth not ether proto 0x88cc -l -e | ./netbps > $(hostname)_$eth\_$timestamp\_$1.txt &
 tcpdump -i$eth not ether proto 0x88cc -l -e | ./netbps > $(hostname)_$eth\_$1.txt &
 #tcpdump -i$eth not ether proto 0x88cc -w $(hostname)_$eth\_$timestamp\_$1.pcap &
done
echo done

#tcpdump -ieth2 not ether proto 0x88cc -w $(hostname)_eth2\_$(date +"%y%m%d_%H%M").pcap &
#tcpdump -ieth3 not ether proto 0x88cc -w $(hostname)_eth3\_$(date +"%y%m%d_%H%M").pcap &
#tcpdump -ieth4 not ether proto 0x88cc -w $(hostname)_eth4\_$(date +"%y%m%d_%H%M").pcap &
