#!/bin/bash
[ $# -ne 1 ] && echo "enter a file name to read data from" && exit 1
[ ! -f "$1" ] && echo "file $1 does not exist" && exit 2
echo $1
while IFS= read -r LINE
do 
#echo $LINE
[[ $LINE == *"comment"* || -z $LINE  || $LINE == "#"* ]] && continue #don't curl comment lines or empty lines
[[ $LINE == *"===end==="* ]] && break #end of files
#echo $LINE
curl -X POST -d "$LINE" http://localhost:8080/utility/addrule
done < $1

# or using cat as follows:	
#cat rest_rules.json | while read LINE; do curl -X POST -d "$LINE" http://localhost:8080/utility/addrule; done
