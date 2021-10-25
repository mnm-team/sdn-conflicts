All of the below was tested on python version Python 3.7.3, but may work for any version 3.5 and above.
The file scripts/constants_build_env.sh needs to be adapted and needs to also include:
SDN_TMP_DIR=$TMP_DIR"/sdntmp"
TAR_DIR=$RNP"/tars/sdn"
TAR_BINARY="/bin/tar"
# TODO add steps for ssh config and constants_build_env in topogen/scripts

### You can eiter deploy an SDN experiment in a local topology with the Xen hypervisor (Linux kernel version 4.9.0-13-amd64) or in an encapsulated topology via VirtualBox (Version 5.2.42 or later)
### Depending on your preference choose one of the following steps
1a. ./sdn_xen_installs
1b. ./sdn_virtualbox_installs

### Steps to set up the pyang model and corresponding python module in topogen/autogen ###
1.  go to topogen/autogen.
2.  Adapt constants_generate_spec.py according to your setup and filesystem.
2.  Execute setup_pyang_module_v2 from there which will generate a python module based on the sdn_testbed_spec_v2.yang model definition (or use the existing sdn_testbed_spec_v2.py python module).

### Steps to generate a SDN topology definition with an existing sdn_testbed_spec_v2.py python module ###
1.  Check the topogen/autogen/sample_topology.py file and adapt or implement your own topology accordingly. The apps, traffic profiles, transport types, nodes and their config and edges between nodes are specified here.
2.  Run python sample_topology.py or other created topology python scripts from the folder autogen to create a json file, the location of the file will be shown.
3.  Run python generate_sdn_spec.py [filepath], where [filepath] is the location of the created json file. This will generate a timestamped spec folder in topogen/specs.
# TODO add steps from thesis here

# TODO remove below steps
5.  To build and deploy the vm images locally, as well as configure all started xen vms, write the parameter_space.sh for an experiment automatically and finally start an experiment cd to topogen/scripts and execute one of the following commands:
# sudo ./deploy_sdn_conflicts_experiment.sh ../specs/[created_spec_folder] 
to deploy the experiment locally
# sudo ./deploy_sdn_conflicts_experiment.sh ../specs/[created_spec_folder] [remote] [path/to/.ssh/config] [path/to/.ssh/id_rsa] 
to deploy the experiment on a remote machine, where [remote] is a host configured in an ssh config file, with a path to the config file and the private key to use (to avoid using root key files and configs when using sudo)
