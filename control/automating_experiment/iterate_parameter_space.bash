#!/bin/bash
# this script should always be run from the automating_experiment directory!
# $1 is a path to a directory containing parameter space json files based on YANG model for parameter space

app_config_dir="auto_configs"

# remove directory for app configs to avoid any errors with remnant files
if [ -d "$app_config_dir" ]
then
  rm -r "$app_config_dir"
fi

for f in $1/*
do
  echo "Generating configs for $f"
  mkdir "$app_config_dir"
  cp $f parameter_space.json
  python3 app_config_generator.py "parameter_space.json" "$app_config_dir" "parameter_space.bash"
  scp "$app_config_dir"/* con0:massive
  rm -r "$app_config_dir"
  bash read_parameter_space.bash
done
