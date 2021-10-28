. ./collectdata_config.bash

string=$(ssh -n con0 "sh -c 'grep -o -e "192\.168\.1\.[1-9]*" $APPDIR/hs_config_local'")
str=($string)
hs_server="null"
for (( i=0; i<${#str[@]}; i++ ))
do
  if [[ $hs_server = "null" ]]; then
    hs_server=${str[$i]}
  elif [[ $(echo $hs_server | grep -c ${str[$i]}) -ne 0 ]]; then
    hs_server=$hs_server
  else
    hs_server="$hs_server ${str[$i]}"
  fi
done
echo $hs_server
