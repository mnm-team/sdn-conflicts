. ./collectdata_config.bash
switches=$(ssh -n con0 "sh -c 'grep -c "switchAssets" $APPDIR/$1_config_local'")
app=$(ssh -n con0 "sh -c 'grep -c "appAssets" $APPDIR/$1_config_local'")
if [[ switches -gt 0 ]] || [[ app -gt 0 ]]
then
  echo 1
else
  echo 0
fi
