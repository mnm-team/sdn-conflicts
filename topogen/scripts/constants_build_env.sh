#!/bin/bash
# Defines paths, binaries etc. of the build environment

# Paths
RNP=$(dirname $(echo $PWD)) # same as ../ and absolute
TMP_DIR="/tmp"
SDN_TMP_DIR=$TMP_DIR"/sdntmp"
MAC_FILE="${TMP_DIR}/macfile"
TAR_DIR=$RNP"/tars/sdn"
TAR_BINARY="/bin/tar"
