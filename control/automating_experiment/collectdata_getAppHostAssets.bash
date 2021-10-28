. ./collectdata_config.bash

string=$(ssh -n con0 "sh -c 'grep -o -e "192\.168\.1\.[1-9]*" $APPDIR/$1_config_local'")
str=($string)
servers="null"
for (( i=0; i<${#str[@]}; i++ ))
do
  if [[ $servers = "null" ]]; then
    servers=${str[$i]}
  elif [[ $(echo $servers | grep -c ${str[$i]}) -ne 0 ]]; then
    servers=$servers
  else
    servers="$servers ${str[$i]}"
  fi
done
echo $servers
