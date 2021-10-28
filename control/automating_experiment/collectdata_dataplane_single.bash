#!/bin/bash
# pass application name as argument without the .py extension
# example:
# bash collectdata.bash appsuite_v4_0 ryu_multipath
# $1 is the point number, for app deployment in isolation, $1 is appname_config
# $2 $3 is source group and destination group in traffic generation.
# $4 is the number of switches in the topology
. ./collectdata_config.bash
. ./collectdata_function.bash
CONFLICT_FILE=conflict_single_$1.txt
> $CONFLICT_FILE
#echo "tcpdump at each router"
#timestamp=$(date +"%y%m%d_%I%M")
#for i in {1..10}; do echo router$i; ssh router$i "sh -c 'nohup bash tcpdump_fromoutside.sh $timestamp $applist >/dev/null 2>&1'"; done
#for i in {1..10}; do echo router$i; ssh -n router$i "sh -c 'nohup bash $TCPDUMP_FILE $timestamp $applist >/dev/null 2>&1'"; done
#for i in {1..1}; do echo router$i; ssh -n router$i "sh -c 'nohup bash $TCPDUMP_FILE $timestamp $1 >/dev/null 2>&1'"; done #$1 is the point in parameter space, which stores the configuration of that point.
#for i in {1..10}; do echo -n "router$i "; ssh -n router$i "sh -c 'nohup bash $TCPDUMP_FILE $1 >/dev/null 2>&1'"; done #$1 is the point in parameter space, which stores the configuration of that point.
#for i in $(seq 1 $4); do echo -n "router$i "; ssh -n router$i "sh -c 'nohup bash $TCPDUMP_FILE $1 >/dev/null 2>&1'"; done #$1 is the point in parameter space, which stores the configuration of that point.
#echo

#do ping between end-hosts

# perform traffic generation for all combinations of end-points between source set and destination set with iperf, nc to transfer files, using tcp, udp. Note: this handles only unicast, not multicast.
#trap 'ssh -n ' INT

#starting nc testing
#new approach: that allow concurrent nc test --> each server will have to listen on multiple ports
for src in $2; do
  for dst in $3; do
    for dst1 in $3; do #all dst will listen on port 34$src$dst (so for each round a src connects to a dst via nc, the port at the dst is unique and always available for this connection), so the effect of SBEpLB, that directing a session to another server (which we usually don't know) will cause no problem of a server not listening on a port.
      serport=34$src$dst #server port
      [ $serport -gt 65000 ] && serport=$(alternative_port $serport)
      echo "SERVER: starting nc server at pc$dst1, port $serport"
      ssh -n pc$dst1 "sh -c 'nc -lvp $serport > recv.txt &'"
    done
  done
done
for src in $2; do
  for dst in $3; do
    serport=34$src$dst #server port
    [ $serport -gt 65000 ] && serport=$(alternative_port $serport)
    #tcpdump to get the temporary client port used to connect to server, which will be extracted later in the client.
    ssh -n pc$src "sh -c 'tcpdump -ieth1 tcp port $serport > tmptcpdump.txt 2>&1 &'"
    echo "CLIENT: nc from pc$src to pc$dst"
    ssh -n pc$src "sh -c 'echo -n nc from pc$src to pc$dst > tmpnc$dst; for i in {1..5}; do echo $i; sleep 0.3; done  | nc -w 3 192.168.1.$dst $serport >> tmpnc$dst 2>&1 &'"
    sleep 3 # each run is 3 seconds one after another, seems like this help the result always be consistent, i.e., the 10 times re-run still yields the same output
    #now extract the client port from tcpdump result.
    ssh -n pc$src "sh -c 'pkill -f \"tcpdump -ieth1 tcp port $serport\"'"
    eval portnc$src$dst=$(ssh -n pc$src "sh -c 'grep -m 1 \"192.168.1.$src.\+ >\" tmptcpdump.txt'" | awk '{print $3}' | cut -d'.' -f5)
    #eval tmpportnc=\$portnc$src$dst
    #echo tmpportnc = $tmpportnc
  done
done
sleep 6
#now check the logfile of nc if there is any problem.
for src in $2; do
  for dst in $3; do
    ssh -n pc$src "sh -c 'grep UNKNOWN tmpnc$dst > /dev/null 2>&1'" 
    [ $? -eq 0 ] && echo "error with nc, point = $1" | tee -a $CONFLICT_FILE
    ssh -n pc$src "sh -c 'grep UNKNOWN tmpnc$dst'" | tee -a $CONFLICT_FILE
  done
done

#start iperf traffic
for src in $2; do
  for dst in $3; do
    ssh -n pc$dst "sh -c 'pgrep -a iperf >/dev/null 2>&1'"
    [ $? -eq 0 ] && echo "iperf already running at pc$dst" && continue #already running, don't have to start iperf server at this end-point
    #echo $dst
    echo "SERVER: starting iperf server at pc$dst"
    #ssh -n pc$dst "sh -c 'pkill iperf; iperf -s -u &' >/dev/null"
    ssh -n pc$dst "sh -c 'iperf -s -u &' >/dev/null"
  done
  for dst in $3; do
    echo "CLIENT: iperf from pc$src to pc$dst"
    #ssh -n pc$src "sh -c 'iperf -c 192.168.1.$dst -u -b 20M -t 20'" 2>&1 | tee temp.txt
    #ssh -n pc$src "sh -c 'iperf -c 192.168.1.$dst -u -b 5m -t 20'" >> temp.txt 2>&1 &
    ssh -n pc$src "sh -c 'echo iperf from pc$src to pc$dst > tmpiperf$dst; iperf -c 192.168.1.$dst -u -b 5m -t 20 >> tmpiperf$dst 2>&1 &'"
    sleep 5
    #grep "WARNING" temp.txt > /dev/null && [ $? -eq 0 ] && (echo "error! iperf from pc$src to pc$dst, point = $1" | tee -a $CONFLICT_FILE) && (grep "WARNING" temp.txt >> $CONFLICT_FILE)
  done
done
sleep 25
#echo $CONFLICT_FILE
#cat temp.txt
#grep "WARNING" temp.txt
#grep "WARNING" temp.txt > /dev/null && [ $? -eq 0 ] && (echo "error with iperf, point = $1" | tee -a $CONFLICT_FILE) && (grep "WARNING" temp.txt >> $CONFLICT_FILE)
# now check the logfile of iperf if there is any problem.
for src in $2; do
  for dst in $3; do
    ssh -n pc$src "sh -c 'grep WARNING tmpiperf$dst > /dev/null 2>&1'" 
    [ $? -eq 0 ] && echo -n "error with iperf, point = $1, " | tee -a $CONFLICT_FILE && ssh -n pc$src "sh -c 'sed -n 1p tmpiperf$dst; grep WARNING tmpiperf$dst'" | tee -a $CONFLICT_FILE
    #extract the port, then replace it in the dumpflow file later, so that the merging and comparing of flow table is more precise.
    eval portiperf$src$dst=$(ssh -n pc$src "sh -c 'grep \"connected with\" tmpiperf$dst'" | awk '{print $6}') 
  done
done

echo "dump flow and group tables into a file"
#timestamp=$(date +"%y%m%d_%I%M")
#for i in {1..10}; do echo router$i; ssh -n router$i "sh -c 'sh $DUMPFLOWS_FILE ; echo " "; sh $DUMPGROUPS_FILE' > router$i\_dumpflows_$timestamp\_$applist\_$desc" ; done
for i in $(seq 1 $4); do echo -n "router$i "; ssh -n router$i "sh -c 'sh $DUMPFLOWS_FILE' > router$i\_dumpflows_single_$1" ; done
#replace the extracted ports above by self-defined port in the $DUMPFLOWS_FILE:
for src in $2; do
  for dst in $3; do
    eval tmpportnc=\$portnc$src$dst
    echo tmpportnc = $tmpportnc
    eval tmpportiperf=\$portiperf$src$dst
    echo tmpportiperf = $tmpportiperf
    for i in $(seq 1 $4); do ssh -n router$i "sh -c 'sed -i \"s/=$tmpportnc/=23$src$dst/g;s/=$tmpportiperf/=56$src$dst/g \" router$i\_dumpflows_single_$1'"; done
    echo "replacing port done!"
  done
done
