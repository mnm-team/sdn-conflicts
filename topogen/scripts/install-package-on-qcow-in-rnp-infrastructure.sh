groupsvon=$1
groupsbis=$2
package=$3
domain=rnp.lab.nm.ifi.lmu.de


if [ $# != 3 ]; then
  echo "use me as follows:"
  echo "$0 <groups_von> <groups_bis> <package>"
  exit 1
fi;

echo "running apt-get install <package> on gruppe<von-bis>.$domain"


for i in `seq -w $groupsvon $groupsbis`; do
#	login=root@gruppe$i.$domain
	login=root@rnp_kletzander

	ssh -X $login apt-get -y update
	ssh -X $login apt-get -y install $package
	ssh -X $login apt-get -y clean

done;
