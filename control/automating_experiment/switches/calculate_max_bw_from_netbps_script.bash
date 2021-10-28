#!/bin/bash
# to calculate max bw from an structured input file
# run this by: bash <thisfilename> <inputfile>
#sample input file (from the command: tcpdump -ieth1 -l -e | ./netbps > input.txt
#16:13:29       2.26 Mbps
#16:13:34      29.53 Mbps
#16:13:39      29.43 Mbps 

awk 'BEGIN {max=0}
{
#print $2
#print max
if (max < $2) max=$2
}
END {print max}
' $1

# an alternative script:
# awk '{print $2 | "sort" }' router7_eth3_190821_0413_.txt | tail -1
