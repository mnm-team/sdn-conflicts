'''
UDP file sender, sends out a file to 2 4 6 or 9 receivers on port 5006
'''

'''
to test:
start ndp.py every topology:
    ryu-manager ndp.py --observe-links
    
    or  
    
start simple_switch_13.py in any topology without loops with:
    ryu-manager simple_switch_13.py --observe-links
    
    
start udp_file_receiver5006.py on any receiver with:
    python udp_file_receiver5006.py
    
start udp_file_sender.py on pc1 with:
    python udp_file_sender.py arg1 arg2
        where arg1 is the amount of receivers you want to send to (in this case 2, 4, 6 or 9 depending on topology)
              arg2 is the file you want to send (here for example 1MB.txt)
    python udp_file_sender.py 4 1MB.txt
    


start simple
'''
from socket import *
import sys
import time

s = socket(AF_INET6,SOCK_DGRAM)
buf =1024

count = 0
####################################################
# all ip addresses and mac addresses of topology 1 #
####################################################

topo1_pc1 = ["2001:db8::1701", "00:16:3e:00:17:01"]  # pc1
topo1_pc2 = ["2001:db8::2801", "00:16:3e:00:28:01"]  # pc2
topo1_pc3 = ["2001:db8::3801", "00:16:3e:00:38:01"]  # pc3
topo1_pc4 = ["2001:db8::4901", "00:16:3e:00:49:01"]  # pc4
topo1_pc5 = ["2001:db8::5901", "00:16:3e:00:59:01"]  # pc5

####################################################
# all ip addresses and mac addresses of topology 2 #
####################################################

topo2_pc1 = ["fc00::1", "00:16:3e:00:00:41"]  # pc1
topo2_pc2 = ["fc00::2", "00:16:3e:00:00:42"]  # pc2
topo2_pc3 = ["fc00::3", "00:16:3e:00:00:43"]  # pc3
topo2_pc4 = ["fc00::4", "00:16:3e:00:00:44"]  # pc4
topo2_pc5 = ["fc00::5", "00:16:3e:00:00:45"]  # pc5
topo2_pc6 = ["fc00::6", "00:16:3e:00:00:46"]  # pc6
topo2_pc7 = ["fc00::7", "00:16:3e:00:00:47"]  # pc7
topo2_pc8 = ["fc00::8", "00:16:3e:00:00:48"]  # pc8
topo2_pc9 = ["fc00::9", "00:16:3e:00:00:49"]  # pc9
topo2_pc10 = ["fc00::10", "00:16:3e:00:00:4a"]  # pc10

####################################################
# the two experiment setups that were used to test #
# MEADcast in SDN, four and nine receivers         #
####################################################

# topology on 10.152.209.195 with 4 receivers
topo1_fourrecv = [topo1_pc2, topo1_pc3, topo1_pc4, topo1_pc5]

# topology on 10.152.209.195 with 2 receivers
topo1_tworecv = [topo1_pc2, topo1_pc3]

# topology on 10.152.209.195 with 9 receivers
topo2_ninerecv = [topo2_pc2, topo2_pc3, topo2_pc4, topo2_pc5, topo2_pc6, topo2_pc7, topo2_pc8, topo2_pc9, topo2_pc10]

# topology on 10.152.209.195 with 6 receivers
topo2_sixrecv = [topo2_pc2, topo2_pc3, topo2_pc4, topo2_pc5, topo2_pc6, topo2_pc7]

#function to send a file to an IP address with udp destination port 5005
def send_unicast(ip,filename,count,delay):
    host =ip
    #port = 5005
    port = 5006
    addr = (host, port)
    file_name = filename

    #opens the file in read and bytemode
    f = open(file_name, "rb")

    #reads the first 1024 bytes into the data buffer
    data = f.read(buf)

    # s.sendto(file_name,addr)
    # s.sendto(data,addr)
    #while the data buffer is not empty send the data to the IP
    while (data):
        s.sendto(data, addr)
        print count," sending ..."
        count = count+1

        #read the next 1024 bytes
        data = f.read(buf)

        time.sleep(delay)

    return count
    #s.close()
    f.close()

#sends the data to an entire list of receivers
def send_to_topology(topo,file,delay):
    current_count = 0
    for x in range(len(topo)):
        print topo[x]
        current_count = send_unicast(topo[x][0],file,current_count,delay)




file_name=sys.argv[2]
delay = sys.argv[3]
delay = float(delay)


if sys.argv[1] == "2":
    print "minh topology detected, send unicast to 2 destinations"
    current_count = send_to_topology(topo1_tworecv,file_name,delay)
    print "total amount of packets sent: ", current_count
    s.close()

if sys.argv[1] == "4":
    print "minh topology detected, send unicast to 4 destinations"
    current_count = send_to_topology(topo1_fourrecv,file_name,delay)
    print "total amount of packets sent: ", current_count
    s.close()

if sys.argv[1] == "6":
    print "cuong topology detected, send unicast to 6 destinations"
    current_count = send_to_topology(topo2_sixrecv,file_name,delay)
    print "total amount of packets sent: ", current_count
    s.close()

if sys.argv[1] == "9":
    print "cuong topology detected, send unicast to 9 destinations"
    current_count = send_to_topology(topo2_ninerecv,file_name,delay)
    print "total amount of packets sent: ", current_count
    s.close()

