#!/bin/bash

# if there is no limit specified, this script generate up to 1300 rules

rule_full={"\"dpid\":%s, \"cookie\":\"%s\", \"priority\":%s, \"match\":{\"in_port\":%s, \"eth_type\":2048, \"ipv4_src\":\"%s\", \"ipv4_dst\":\"%s\", \"ip_proto\":%s, \"tcp_src\":%s, \"tcp_dst\":%s}, \"actions\":[{\"type\":\"OUTPUT\", \"port\":%s}]}\n"
rule_ip_src_dst={"\"dpid\":%s, \"cookie\":\"%s\", \"priority\":%s, \"match\":{\"eth_type\":2048, \"ipv4_src\":\"%s\", \"ipv4_dst\":\"%s\"}, \"actions\":[{\"type\":\"OUTPUT\", \"port\":%s}]}\n"
rule_ip_src={"\"dpid\":%s, \"cookie\":\"%s\", \"priority\":%s, \"match\":{\"eth_type\":2048, \"ipv4_src\":\"%s\"}, \"actions\":[{\"type\":\"OUTPUT\", \"port\":%s}]}\n"
rule_ip_dst={"\"dpid\":%s, \"cookie\":\"%s\", \"priority\":%s, \"match\":{\"eth_type\":2048, \"ipv4_dst\":\"%s\"}, \"actions\":[{\"type\":\"OUTPUT\", \"port\":%s}]}\n"
#s=$s_full
rule=$rule_ip_src_dst
#echo $s
#printf "$rule_full" "1" "0x200" "3" "1"  "172.16.1.1/16" "172.17.1.1/16" "6" "2222" "8080" "2"
#printf "$rule_ip_src_dst" "1" "0x200" "3" "172.16.1.1/16" "172.17.1.1/16" "2"
#printf "$rule" "1" "0x200" "3" "172.16.1.1/16" "172.17.1.1/16" "2"

[ $# -eq 1 ] && limit=$1 || limit=1000

count=0
dpid=8 #router8 of topo_mwn has 10 ports
masklim=32 #mask limit: network mask for ip address
reset(){ #reset to the value of $1
       	cookie=$1
       	pri=$1
       	act=1
}
increase(){
	cookie=$(( $cookie+1 ))
	pri=$(( $pri+1 ))
	act=$(( $act+1 ))
}
reset 1

src="10.0.0.1"
dst="10.10.10.10"
rule=$rule_ip_src
for mask in $(seq 8 $masklim); do
	r=$(printf "$rule" "$dpid" "0x$cookie" "$pri" "$src/$mask" "$act")
	echo $r
	count=$(( $count+1 ))
	[ $count -eq $limit ] && echo "{\"comment\":\"Number of rule = $count\"}" && exit 0
	increase
	[ $act -eq 6 ] && act=1
	[ $pri -eq 10 ] && reset 1
done

rule=$rule_ip_dst
for mask in $(seq 8 $masklim); do
	r=$(printf "$rule" "$dpid" "0x$cookie" "$pri" "$dst/$mask" "$act")
	echo $r
	count=$(( $count+1 ))
	[ $count -eq $limit ] && echo "{\"comment\":\"Number of rule = $count\"}" && exit 0
	increase
	[ $act -eq 6 ] && act=1
	[ $pri -eq 10 ] && reset 1
done

rule=$rule_ip_src_dst
for mask1 in $(seq 8 $masklim); do
	for mask2 in $(seq 8 $masklim); do
		r=$(printf "$rule" "$dpid" "0x$cookie" "$pri" "$src/$mask1" "$dst/$mask2" "$act")
		echo $r
	       	count=$(( $count+1 ))
	       	[ $count -eq $limit ] && echo "{\"comment\":\"Number of rule = $count\"}" && exit 0
	       	increase
	        [ $act -eq 6 ] && act=1
	       	[ $pri -eq 20 ] && reset 8
	done
done

src="10.0.0.1"
dst="10.11.11.11"
rule=$rule_ip_src_dst
for mask1 in $(seq 8 $masklim); do
	for mask2 in $(seq 8 $masklim); do
		r=$(printf "$rule" "$dpid" "0x$cookie" "$pri" "$src/$mask1" "$dst/$mask2" "$act")
		echo $r
	       	count=$(( $count+1 ))
	       	[ $count -eq $limit ] && echo "{\"comment\":\"Number of rule = $count\"}" && exit 0
	       	increase
	        [ $act -eq 6 ] && act=1
	       	[ $pri -eq 20 ] && reset 8
	done
done


echo "{\"comment\":\"Number of rule = $count\"}"
