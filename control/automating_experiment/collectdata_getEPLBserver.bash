. ./collectdata_config.bash

string=$(ssh -n con0 "sh -c 'grep -o -e "192\.168\.1\.[1-9]*" $APPDIR/eplb_config_local'")
str=($string)
eplb_server="null"
for (( i=0; i<${#str[@]}; i++ ))
do
  if [[ $eplb_server = "null" ]]; then
    eplb_server=${str[$i]}
  elif [[ $(echo $eplb_server | grep -c ${str[$i]}) -ne 0 ]]; then
    eplb_server=$eplb_server
  else
    eplb_server="$eplb_server ${str[$i]}"
  fi
done
echo $eplb_server
