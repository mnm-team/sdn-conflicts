. ./collectdata_config.bash

string=$(ssh -n con0 "sh -c 'grep -v ":" $APPDIR/pe_config_local'")
string=$(echo "$string" | grep -o -e "\"[0-9]*\"")
string=$(echo "$string" | sed "s/\"//g")
echo "$string"
