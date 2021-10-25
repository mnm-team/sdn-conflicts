# Collection of helper functions related to .tar files containing configuration files


###################################
# $1 = <tar_filename>
# $2 = <config root>
#
# Requires $TAR_DIR and $TAR_BINARY to be set
###################################
apply_tar ()
{
	cd $2
	$TAR_BINARY -xf $TAR_DIR/$1
}


