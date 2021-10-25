groups=$1
package=$2
xenip=$3
domain=rnp.lab.nm.ifi.lmu.de
echo $tarname
for i in `seq -w 1 $groups`; do
	login=root@gruppe$i.$domain
#	login=root@rnp_janus

	ssh  $login iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
	ssh  $login "ssh -o StrictHostKeyChecking=no $xenip \"ip r add default via 192.168.0.254\""
	ssh  $login "ssh -o StrictHostKeyChecking=no $xenip \"apt-get -y update\""
	ssh  $login "ssh -o StrictHostKeyChecking=no $xenip \"apt-get -y install $package\""
	ssh  $login "ssh -o StrictHostKeyChecking=no $xenip \"apt-get -y clean\""
	ssh  $login "ssh -o StrictHostKeyChecking=no $xenip \"ip r del default\""
	ssh  $login iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

done;
