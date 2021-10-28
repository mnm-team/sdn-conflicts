#!/bin/bash
#APPDIR="/usr/local/lib/python2.7/dist-packages/ryu/app/cuong/massive"
APPDIR="massive"
#echo $APPDIR/cuongdaica
CLEARSWITCH_APP="delete_all_flow_and_group_tables_v2_0.py"
#echo $APPDIR/$CLEARSWITCH_APP

#this file is put in each router, also netbps and calculate_max_bw_from_netbps_script.bash
TCPDUMP_FILE="tcpdump_fromoutside_bwgauge.sh"

#dumpflows and dumpgroups file in all routers/switches
DUMPFLOWS_FILE="dumpflows.sh"
DUMPGROUPS_FILE="dumpgroups.sh"
CONFLICT_FILE="conflict.txt"
