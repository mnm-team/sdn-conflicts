__author__ = 'Duc Minh Nguyen'

import itertools
import os
import socket
import sys
import time

import mc_functions as mc

'''
mc_file_sender : MEADcast file sender
TODO: send variable payload sizes
TODO: send out discovery request packets without etherframe (arp/icmp implementation on controller)
TODO: just combine senddata and senddisco into a threaded application instead of having two instances run at the same time
    one that listens to receivers that want to join the MEADcast session and sends out discovery request packets
    one that listens for discovery response packets and sends the data out based on the topology it creates


to test:

start the MEADcast controller on the controller (if not currently running already)

start on any receiving pc:
    python udp_file_receiver5005.py

start two instances of this application on pc1:
    python mc_file_sender.py senddata 100MB.txt
    python mc_file_sender.py senddisco 4

senddata listens for discovery response packets, builds the topology and sends a 100MB textfile(or any file) to that topology
senddisco sends the discovery request packets for intended receivers, in this case 2,4,6 or 9
    


'''

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


############################################################
# all the necessary functions to create and send MCpackets #
############################################################

# handles incoming MEADcast packets and adds the necessary data to a given list
# in this case hopcount, routerip, receiverip and destinationport of that receiver

def handleresponsepacket(listofip, packet):
    linklist = listofip
    packetdataa = mc.handlemcpacket(packet)
    hopcount = packetdataa.getmc().getmchc()
    routerip = socket.inet_ntop(socket.AF_INET6, packetdataa.getipv6().getipv6source())
    receiverip = packetdataa.getmc().getmcdestinationlist()[0]

    portofreceiver = packetdataa.getudp().getudpdestiport()
    relevantpacketdata = [[hopcount, routerip], [receiverip, portofreceiver]]
    linklist.append(relevantpacketdata)  # eventual linklist

    return linklist



# sortes the list after hopcount
def sortlistafterhopcount(list):
    sortedList = list.sort(key=lambda sortedlist: sortedlist[0], reverse=True)
    return sortedList


# groups all values together for each router and after hopcount
def group_by_hc_router(lista):
    returnlist = []
    list_key = lambda x: x[0]
    for key, group in itertools.groupby(lista, list_key):
        # print key
        tempiplist = []
        groupsave = group
        listgroup = list(group)
        # print len(listgroup)
        for x in range(len(listgroup)):
            # templist = templist.append(listgroup[x])
            # print listgroup[x][1]
            tempiplist.append(listgroup[x][1])
            # print tempiplist
        returnlist.append([key, tempiplist])

    return returnlist

    # print group[x],test

    # print newlist
    # mc.printlist(newlist)


def replace_duplicates_with_router(list, finallist):
    for x in range(len(list)):
        # print list[x][1]

        for y in range(len(finallist)):
            # print "checking: ",list[x][1], "and ", finallist[y][1]
            if list[x][1] == finallist[y][1]:
                # print list[x][1],finallist[y][1]
                if list[x][0][0] == finallist[y][0][0]:
                    # print list[x][0][0],finallist[y][0][0], "same HC"
                    pass
                else:

                    finallist[y][1] = list[x][0]

    return finallist


# removes all duplicate entries from the list
def remove_duplicates(list):
    finallist = []
    for x in range(len(list)):
        if list[x] not in finallist:
            finallist.append(list[x])
    return finallist


# deletes the routers from the list that are not needed
def delete_routers_from_list(list):
    finallist = []
    for x in range(len(list)):
        if isinstance(list[x][1][0], int):
            pass
        else:
            finallist.append(list[x])
    return finallist


def create_topologylist_without_routers(rawlist):
    new_list = list(rawlist)
    # sorting after HC
    sortlistafterhopcount(new_list)

    # creating a list to compare old list against
    comparelist = list(new_list)

    # replace all duplicate destinations with responsible routers from top
    replace_duplicates_with_router(new_list, comparelist)

    new_list_1 = delete_routers_from_list(new_list)
    # removing duplicate routers
    new_list_2 = remove_duplicates(new_list_1)

    # group all entries by HC + router
    new_list_3 = group_by_hc_router(new_list_2)

    return new_list_3


# function to send a discovery request packet to a list of receivers
def send_discovery_request(sender, list_of_receivers):
    for x in range(len(list_of_receivers)):
        # print sender[0],sender[1]
        disco_mc_header = mc.create_mc_discovery_packet(sender[0], list_of_receivers[x][0], 5005, 5005)
        disco_ether_header = mc.make_ether_header(sender[1], list_of_receivers[x][1])
        disco_packet = disco_ether_header + disco_mc_header
        mc.sendpacketwithether(disco_packet)
        time.sleep(0.20)
        print "discovery request packet sent for %s" % list_of_receivers[x]
        print ""

# deletes entries that are only responsible for 0 or 1 destinations
def delete0or1entrieslist_2(list):
    newlist = []
    for x in range(len(list)):
        if len(list[x][1]) > 1:
            newlist.append(list[x])

    return newlist

# creates the ip destination list from the raw list
def makeipaddrmap2(list):
    ipaddrmap = []
    for x in range(len(list)):
        ipaddrmap.append(list[x][0][1])
        for y in range(len(list[x][1])):
            ipaddrmap.append(list[x][1][y][0])

    return ipaddrmap

# creates the portlist from the raw list
def makeportmap2(list):
    ipaddrmap = []
    for x in range(len(list)):
        ipaddrmap.append(0)
        for y in range(len(list[x][1])):
            ipaddrmap.append(list[x][1][y][1])

    return ipaddrmap

# creates the router bitmap from the raw list
def make_routermap2(list):
    ipaddrmap = []

    # add a 1 for every router
    for x in range(len(list)):
        ipaddrmap.append(1)

        #iterate through each router and add a 0 for every destination it is responsible for
        for y in range(len(list[x][1])):
            ipaddrmap.append(0)

    return ipaddrmap

# same function as make_routermap2()
def makebitmap2(list):
    bitmap = []
    for x in range(len(list)):
        bitmap.append(1)
        for y in range(len(list[x][1])):
            bitmap.append(0)

    # print "bitmapcontrol",bitmap
    return bitmap


################################################################
# main part of this file, sends and receives discovery request #
# response packets and can send data based on the topology     #                                                                                       #
################################################################


filename = ""

if len(sys.argv) == 1:
    print "instructions:"
    print "\nmc_file_sender.py takes two arguments, first argument is either senddisco or senddata"
    print "\nsecond argument depends on the first one, if it was senddisco then you have to pick 2,4,6 or 9 as your second argument" \
          "\npython mc_file_sender.py senddisco 2" \
          "" \
          "\nsends out the discovery request packets for 2 receivers for topology 1" \
          "\npython mc_file_sender.py senddata 100MB.txt" \
          "" \
          "\nwaits few seconds for discovery response packets, generates the topology and then sends the data to that topology" \
          "\n you have to start two instances of mc_file_sender.py, the first one that listens to the response packets and the second one that sends the discovery request packets to the receivers"

if len(sys.argv) == 3:
    print sys.argv
    print sys.argv[1]
    print sys.argv[2]



    if sys.argv[1] == "senddisco":

        # sends the discovery request packets for 4 receivers in topology 1
        if sys.argv[2] == "4":
            print "sending disco for topology for 4pc..\n"
            send_discovery_request(topo1_pc1, topo1_fourrecv)
            print "done"

        # sends the discovery request packets for 9 receivers in topology 2
        if sys.argv[2] == "9":
            print "sending disco for topology for 9pc..\n"
            send_discovery_request(topo2_pc1, topo2_ninerecv)
            print "done"

        # sends the discovery request packets for 2 receivers in topology 1
        if sys.argv[2] == "2":
            print "sending disco for topology for 9pc..\n"
            send_discovery_request(topo1_pc1, topo1_tworecv)
            print "done"

        # sends the discovery request packets for 6 receivers in topology 2
        if sys.argv[2] == "6":
            print "sending disco for topology for 9pc..\n"
            send_discovery_request(topo2_pc1, topo2_sixrecv)
            print "done"

if len(sys.argv) == 4:
    print sys.argv
    print sys.argv[1]
    print sys.argv[2]
    delay = sys.argv[3]
    delay = float(delay)

    #if the second first argument is senddata, it will send the file specified in the second argument to the topology
    if sys.argv[1] == "senddata":
        count = 0
        topo_list_tmp = []

        empty = 0
        while empty == 0:
            #
            try:
                s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x86DD))

                # closing the socket after 5 seconds
                s.settimeout(5)
                packet = ""
                packet = s.recvfrom(65565)
                packet = packet[0]

                # function that checks if an incoming packet is a MEADcast packet or not, returns 0 or 1
                ismcheader = mc.mcpacketchecker(packet)
                if ismcheader == 1:
                    count += 1
                    print count
                    handleresponsepacket(topo_list_tmp, packet)
                    print "discovery response packet in"


            except socket.timeout:
                if topo_list_tmp == []:
                    print "still empty, continue"
                else:
                    print topo_list_tmp
                    empty = 1
                    s.close()
                    print "closing socket"

            # sorts the raw list after hopcount
            bitmaplist = create_topologylist_without_routers(topo_list_tmp)

            # print "deletes routers that are responsible for 0 or 1 entries only"
            bitmaplist_without_01_entries = delete0or1entrieslist_2(bitmaplist)

            # print "creating ip map"
            ipmaplist = makeipaddrmap2(bitmaplist_without_01_entries)

            # print "creating portbitmap"
            portmap = makeportmap2(bitmaplist_without_01_entries)

            # print "creating routerbitmap"
            routermaplist = make_routermap2(bitmaplist_without_01_entries)

            # print "creating destinationbitmap"
            bitmaplist = makebitmap2(bitmaplist_without_01_entries)

            #takes the filename from the second argument
            filename = sys.argv[2]

            #buffersize, currently hardcoded (just substract currentpacketsize from maxpacketsize to receive a value that
            #that is not hardcoded and depends on number of receivers
            buffer = 1024

            #opens the file in read and byte mode
            file = open(filename, "rb")

            #reads the first 1024 bytes into the data
            data = file.read(buffer)
            count = 0
            print ipmaplist
            print routermaplist
            print bitmaplist
            print portmap

        #as long as the data buffer is not empty (when the file is fully read) it will keep doing this:
        while (data):

            # depending on length of ipmaplist we can determine which topology and sender we're in.
            # TODO: just change hardcoded values to ip and mac of sender
            if len(ipmaplist) > 5:
                print "cuong"
                # creates the etherframe
                ethernetpacket = mc.make_ether_header("00:16:3e:00:00:41", "00:16:3e:00:00:42")
                # creates the mc packet
                ether_testpacket5 = mc.create_mc_packet2("fc00::1", "fc00::2", 5005, 5005, data, ipmaplist,
                                                         routermaplist, bitmaplist, portmap)
            else:
                print "minh"
                ethernetpacket = mc.make_ether_header("00:16:3e:00:17:01", "00:16:3e:00:28:01")
                ether_testpacket5 = mc.create_mc_packet2("2001:db8::1701", "2001:db8::2801", 5005, 5005, data,
                                                         ipmaplist,
                                                         routermaplist, bitmaplist, portmap)

            #combines both etherframe and mc packet
            test_packet5 = ethernetpacket + ether_testpacket5

            #sends the packet out
            mc.sendpacketwithether(test_packet5)

            #prints the current #1 of packet sent, the current length of the payload and the overall length of the packet
            print "sending ...", count, len(data), len(test_packet5)

            #after application is done sending the first 1024 bytes it reads the next 1024 bytes into the buffer
            data = file.read(buffer)
            count = count + 1

            # the value to throttle the speed at which the sender sends out the packets, it's needed because the link
            # between controller and switches can't keep up with too much traffic

            time.sleep(delay)

        #print final size of the file for comparison with the receivers
        fsize = os.stat(filename)
        print('size:' + fsize.st_size.__str__())
        print

    if sys.argv[1] != "senddisco" and sys.argv[1] != "senddata":
        print "first combination = senddisco + (2,4,6,9) and second one is senddata + filename"
