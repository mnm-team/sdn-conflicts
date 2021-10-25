groups=$1
tarpath=$2
tarname=$(basename $tarpath)
domain=rnp.lab.nm.ifi.lmu.de
echo $tarname
for i in `seq -w 1 $groups`; do
	login=root@gruppe$i.$domain
#	login=root@rnp_kletzander
	echo "scp $tarpath $login:/$tarname"
	scp $tarpath $login:/$tarname
	echo "ssh $login \"cd /; tar -xf /$tarname; rm /$tarname\"\""
	ssh $login "cd /; tar -xf /$tarname; rm /$tarname"
done;
