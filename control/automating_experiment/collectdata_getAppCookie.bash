. ./collectdata_config.bash
cookie=$(ssh -n con0 "sh -c 'grep "\"cookie\":\\s*\"0x[0-9]*\"" $APPDIR/$1_config_local'")
cookie=$(echo $cookie | grep -o "0x[0-9]*")
echo "$cookie"
