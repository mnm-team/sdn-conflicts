groupsvon=$1
groupsbis=$2
tarpath=$3
xenname=$4
xenip=$5
tarname=$(basename $tarpath)
domain=rnp.lab.nm.ifi.lmu.de
echo $tarname
for i in `seq -w $groupsvon $groupsbis`; do
	login=root@gruppe$i.$domain
#	login=root@rnp_janus
	scp $tarpath $login:/$tarname
	echo "ssh $login scp /$tarname $xenip:/$tarname"
	ssh $login scp -o StrictHostKeyChecking=no /$tarname $xenip:/$tarname
	echo "ssh $login \"ssh -o StrictHostKeyChecking=no $xenip \"cd /; tar -xf /$tarname; rm /$tarname\"\""
	ssh $login "ssh -o StrictHostKeyChecking=no $xenip \"cd /; tar -xf /$tarname; rm /$tarname\""
	ssh $login "xl reboot $xenname"
	ssh $login "rm /$tarname"
done;
