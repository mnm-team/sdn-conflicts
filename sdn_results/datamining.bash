usage(){
echo "count the number of point from all_config file, passed via the first argument"
echo "Usage: bash datamining.bash <all_config file>"
}

[ $# -ne 1 ] && usage && exit 1

numpoint=$(grep point $1 | tail -1 | cut -d' ' -f2)
#echo $numpoint
[[ "$numpoint" == "" ]] && numpoint=0
echo $numpoint

