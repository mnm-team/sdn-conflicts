#!/bin/bash

NUMSW=$(sed '6q;d' automating_experiment/parameter_space.bash)
NUMEP=$(sed '7q;d' automating_experiment/parameter_space.bash)

bash config_testbed.bash $NUMSW $NUMEP
cd automating_experiment
# start experiment in tmux session and keep session open until it is closed by user
tmux new -d 'bash read_parameter_space.bash; $SHELL'
