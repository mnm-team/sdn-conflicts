# bash <this file name> <total number of point from all_config> <conflict file>
# e.g. bash <this file name> 3 conflict.txt
numcon=0 #number of conflict
[[ "$1" -eq "" ]] && last=1 || last=$1
#echo "last = $last"
for i in $(seq 1 $1); do
 #echo $i
 grep "point = $i" $2 > /dev/null 2>&1
 [ $? -eq 0 ] && numcon=$(( $numcon+1))
done
echo $numcon
