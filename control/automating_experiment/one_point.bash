#version 2: read file from the dataset
# version 1: read file via ssh to the target router, not from the dataset - 202007

#!/bin/bash
#note: bash has to support array, in order to run this code, bash_version 2.x onwards does.

# The first 8 lines of the <all_config> config file, which is dataset/$1/all_config, is the configuration for the experiment, and the control app name must be **EXACTLY** present in this file.

usage(){
echo "To reconstruct the experiment setting of a single point and run experiment for that point"
#version 1: echo "Usage: bash one_point.bash <all_config file> <point number>"
echo "Usage: bash one_point.bash <experiment round id> <point number>"
echo "e.g., bash one_point.bash 200818_160647 1"
}

all_config="dataset/$1/all_config"

[ $# -ne 2 ] && usage && exit 1
[ ! -f $all_config ] && echo "File $all_config does not exist! Exit now" && exit 1
grep "point $2" $all_config
[ $? -ne 0 ] && echo "There is no point $2 in $all_config file, exit" && exit 1

. ./collectdata_config.bash

#switch the massive directory in the controller to the state logged by the gitcommitid in all_config
gitcommitid=$(grep gitcommitid $all_config | cut -d'=' -f2)
ssh -n con0 "sh -c 'cd $APPDIR; git log | grep $gitcommitid'"
[ $? -ne 0 ] && echo "There is no state corresponding to the gitcommitid shown in all_config, exit now!" && exit 1
ssh -n con0 "sh -c 'cd $APPDIR; git checkout $gitcommitid'"


next=$(($2+1))
sed -n "/^point $2/,/^point $next/p;/^point $next/q" $all_config > tmp.txt

cat tmp.txt

app_str="" #app string
conf_str="" # config string
pri_str="" # priority string
ts_str="null" # target switch string
while IFS= read -r line; do
  if [[ $line == "point"*  ]]; then
    continue
  fi
  app_str="$app_str $(echo $line | cut -d':' -f1)"
  conf_str="$conf_str $(echo $line | cut -d':' -f2)"
  pri_str="$pri_str $(echo $line | cut -d':' -f3)"
  if [[ $ts_str == "null" ]]; then
    ts_str=$(echo $line | cut -d':' -f4)
  else
    ts_str="$ts_str:$(echo $line | cut -d':' -f4)"
  fi
done < tmp.txt
#echo $app_str
#echo $conf_str
#echo $pri_str
#echo $ts_str

i=1
while IFS= read -r line
do
  if [ -z "$line" ]; then
      break
  fi
  if [ $i -eq 3 ]; then #process TRANS, transport type
	trans=($line)
  fi
  if [ $i -eq 5 ]; then #process EPTRAFPROF
	trafprof=($line)
  fi
  if [ $i -eq 6 ]; then #process NUMSW
	numsw=$line
	echo "number of switches = $numsw"
  fi
  if [ $i -eq 7 ]; then #process NUMEP
	numep=$line
	echo "number of end-points = $numep"
  fi
  if [ $i -eq 8 ]; then #process EPCOMBI
	IFS=':' read -ra comb <<< $line
  fi
  let i=$i+1 #or i=$(( $i+1 )) or let i++
done < $all_config

#clean the environment for experiment
bash collectdata_stop_and_clean.bash $numsw $numep

apps=($app_str)
conf=($conf_str)
pri=($pri_str)
IFS=':' read -ra ts <<< $ts_str

for (( i=0; i<${#apps[@]}; i++ )); do
  echo ${apps[$i]}
  file=${apps[$i]}_config_global
  echo "${pri[$i]} #priority" > $file
  echo "${ts[$i]} #target switches" >> $file
  echo "${conf[$i]} #app config" >> $file
  echo >> $file
  echo "[global] #generated by the script from outer machine" >> $file
  #echo "content of $file"
  #cat $file

  scp $file con0:$APPDIR #con0 is the hostname of the controller0
  # adapt the local config file of the control app (CA): each CA has in *massive* directory of con0 the local1/2/3... file, choose one to be the *local*.
  ssh -n con0 "sh -c 'cd $APPDIR; cp ${apps[$i]}_config_local${conf[$i]} ${apps[$i]}_config_local'"
done 

#echo "list_app = $list_app"
bash collectdata_controller.bash ${apps[*]}
[ $? -eq 11 ] && echo "Controller is not running, please check! Terminate!" && exit 1
#bash collectdata_dataplane.bash 0 "${comb[0]}" "${comb[1]}"
bash collectdata_dataplane_single.bash "point$2" "${comb[0]}" "${comb[1]}" $numsw
#bash collectdata_stop_and_clean.bash $numsw $numep

#retore the massive directory of the controller back to the latest state.
ssh -n con0 "sh -c 'cd $APPDIR; git checkout master'"
