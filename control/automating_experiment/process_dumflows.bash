#version 2: read file from the dataset
# version 1: read file via ssh to the target router, not from the dataset - 202007

#!/bin/bash
# input $1 = <point number>, $2 = <target router>
# e.g., bash <this file name> 15 7
# Implicit input: router*_dumpflows_*
# output: dumpflow_merge and dumpflow_single, used for comparing the expected output and observed output. Still, just a text comparison.

#locate the point in all_config file
# version 1: [ $# -ne 2 ] && echo -e "please input exactly 2 numbers including the point and router in concern! E.g.: \n bash <thisfilename> <point> <router>" && exit 1
[ $# -ne 3 ] && echo -e "please input exactly 3 arguments including the point and router in concern and the experiment round ID! i.e.: bash <thisfilename> <point> <router> <experiment round id> \n E.g.: bash process_dumpflows.bash 2 7 200818_160647" && exit 1

re='^[0-9]+$'
if ! [[ $1 =~ $re && $2 =~ $re ]] ; then
   echo "error: Not a number" >&2; exit 1
fi

[ ! -d dataset/$3 ] && echo "There is no directory dataset/$3!" && exit 1
configfile=dataset/$3/all_config
tmpfile=tmpprocessdumpflow
next=$(($1+1))
grep -n "\<point $1\>" $configfile >/dev/null && point=$(grep -n "\<point $1\>" $configfile | cut -d: -f1)
[ $? -ne 0 ] && echo "point $1 does not exist in $configfile, exit" && exit 1
grep -n "\<point $next\>" $configfile >/dev/null && npoint=$(grep -n "\<point $next\>" $configfile | cut -d: -f1) #npoint = next point
[ $? -ne 0 ] && echo "You are lucky! given point is last point" && npoint="null"
#echo $point
#echo $npoint
# extract the content of the point from the all_config file
[[ $npoint != "null" ]] && (let point++; let npoint--; sed -n "$point,$npoint p" $configfile>$tmpfile)
#[[ $npoint != "null" ]] && (let point++; let npoint--; sed -n "$point,$npoint p" $configfile | cut -d: -f1,2)
[[ $npoint = "null" ]] && (let point++; sed -n "$point,$ p" $configfile > $tmpfile)
#[[ $npoint = "null" ]] && (let point++; sed -n "$point,$ p" $configfile | cut -d: -f1,2)
i=0
while IFS= read -r line
do
  IFS=':' read -ra part <<< $line
  app[$i]=${part[0]}
  conf[$i]=${part[1]}
  pri[$i]=${part[2]}
  cookie[$i]=$(grep -w ${app[$i]} app_cookie.txt | awk '{print $2}')
  let i++
done < $tmpfile

for ((i=0;i<${#app[@]};i++));do
  echo ${app[$i]}: ${conf[$i]}: ${pri[$i]}: ${cookie[$i]}
done

for (( i=0;i<${#app[@]};i++ )); do
  echo ${app[$i]} ${conf[$i]}
  dumpflowfile[$i]=router"$2"_dumpflows_"${app[$i]}"_"${conf[$i]}"
  #version 1: scp router$2:${dumpflowfile[$i]} .
  tar -zxvf dataset/$3/router${2}_dumpflows.tar.gz ${dumpflowfile[$i]}
done

for (( i=0;i<${#app[@]};i++ )); do
  awk '!/arp|icmp|OFPST/ && !/priority=0/ && !/priority=65535/ { if ($6 ~ /timeout/) {print $1" "$7" "$8} else {print $1" "$6" "$7" "$8} }' ${dumpflowfile[$i]} > tmp$i
  tmpfilelist="$tmpfilelist tmp$i"
done
sort $tmpfilelist | uniq | sed -e '/^\s\+$/d' > dumpflow_merge
for ((i=0;i<${#app[@]};i++));do
  sed -i -e "s/cookie=${cookie[$i]}, priority=[0-9]\+\(.\+\)/cookie=${cookie[$i]}, priority=${pri[$i]}\1/g" dumpflow_merge
done
echo "Successful! Result is stored in dumpflow_merge"

dumpflowpoint=router"$2"_dumpflows_"$1"
# version 1: scp router$2:$dumpflowpoint .
tar -zxvf dataset/$3/router${2}_dumpflows.tar.gz $dumpflowpoint
awk '!/arp|icmp|OFPST/ && !/priority=0/ && !/priority=65535/ { if ($6 ~ /timeout/) {print $1" "$7" "$8} else {print $1" "$6" "$7" "$8} }' $dumpflowpoint > tmppoint
sort tmppoint | sed -e '/^\s\+$/d' > dumpflow_single
echo "Successful! Result is stored in dumpflow_single"


#clean
rm $tmpfile tmppoint
rm $dumpflowpoint
for (( i=0;i<${#app[@]};i++ )); do
  rm tmp$i
  rm ${dumpflowfile[$i]}
done
