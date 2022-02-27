'''
python file that contains functions used for MEADcast packet creation and operations by both the sender and the controller


'''

import socket
import struct
import array
from struct import *
import threading
import random
import string
import itertools

#class for the MC packet data and functions
class mcdata(object):
    def __init__(self, etherframe, ipv6, hbh, mc, udp, payload):
        self.etherframe = etherframe
        self.ipv6 = ipv6
        self.hbh = hbh
        self.mc = mc
        self.udp = udp
        self.payload = payload

    def getetherframe(self):
        return self.etherframe

    def getipv6(self):
        return self.ipv6

    def gethbh(self):
        return self.hbh

    def getmc(self):
        return self.mc

    def getudp(self):
        return self.udp

    def getpayload(self):
        return self.payload

#class for the ether frame data and functions
class etherframedata(object):
    def __init__(self, desti, source, type):
        self.desti = desti
        self.source = source
        self.type = type

    def getetherdesti(self):
        return self.desti

    def getethersource(self):
        return self.source

    def getethertype(self):
        return self.type

#class for ipv6 header data and functions
class ipv6data(object):
    def __init__(self, ipv6ver, ipv6tc, ipv6fl, ipv6pll, ipv6nh, ipv6hl, ipv6source, ipv6desti):
        self.ipv6ver = ipv6ver
        self.ipv6tc = ipv6tc
        self.ipv6fl = ipv6fl
        self.ipv6pll = ipv6pll
        self.ipv6nh = ipv6nh
        self.ipv6hl = ipv6hl
        self.ipv6source = ipv6source
        self.ipv6desti = ipv6desti

    def getipv6ver(self):
        return self.ipv6ver

    def getipv6tc(self):
        return self.ipv6tc

    def getipv6fl(self):
        return self.ipv6fl

    def getipv6pll(self):
        return self.ipv6pll

    def getipv6nh(self):
        return self.ipv6nh

    def getipv6hl(self):
        return self.ipv6hl

    def getipv6source(self):
        return self.ipv6source

    def getipv6desti(self):
        return self.ipv6desti

#class for hop-by-hop extension header data and functions
class hbhdata(object):
    def __init__(self, hbhnh, hbhextln, hbhpadopt, hbhdatalen):
        self.hbhnh = hbhnh
        self.hbhextlen = hbhextln
        self.hbhpadopt = hbhpadopt
        self.hbhdatalen = hbhdatalen

    def gethbhnh(self):
        return self.hbhnh

    def gethbhextlen(self):
        return self.hbhextlen

    def gethbhpadopt(self):
        return self.hbhpadopt

    def gethbhdatalen(self):
        return self.hbhdatalen

#class for MEADcast extension header data and functions
class mcheaderdata(object):
    def __init__(self, mcnh, mchdrextlen, mcroutetype, mcnumdesti, mcdisco, mcrecovery, mchc, mcbitmap, mcrouterbitmap,
                 mcdestinationlist, mcportlist):
        self.mcnh = mcnh
        self.mchdrextlen = mchdrextlen
        self.mcroutetype = mcroutetype
        self.mcnumdesti = mcnumdesti
        self.mcdisco = mcdisco
        self.mcrecovery = mcrecovery
        self.mchc = mchc
        self.mcbitmap = mcbitmap
        self.mcrouterbitmap = mcrouterbitmap
        self.mcdestinationlist = mcdestinationlist
        self.mcportlist = mcportlist

    def getmcnh(self):
        return self.mcnh

    def getmchdrextlen(self):
        return self.mchdrextlen

    def getmcroutetype(self):
        return self.mcroutetype

    def getmcnumdesti(self):
        return self.mcnumdesti

    def getmcdisco(self):
        return self.mcdisco

    def getmcrecovery(self):
        return self.mcrecovery

    def getmchc(self):
        return self.mchc

    def getmcbitmap(self):
        return self.mcbitmap

    def getmcrouterbitmap(self):
        return self.mcrouterbitmap

    def getmcdestinationlist(self):
        return self.mcdestinationlist

    def getmcportlist(self):
        return self.mcportlist

#class for UDP header data and functions
class udpdata(object):
    def __init__(self, sourceport, destiport, length, checksum):
        self.sp = sourceport
        self.dp = destiport
        self.len = length
        self.cs = checksum

    def getudpsourceport(self):
        return self.sp

    def getudpdestiport(self):
        return self.dp

    def getudplen(self):
        return self.len

    def getudpchecksum(self):
        return self.cs


########################################
# functions related to packet crafting #
########################################


#checksum calculation function used for udp
if pack("H", 1) == b"\x00\x01":  # big endian
    def checksum(pkt):
        if len(pkt) % 2 == 1:  # if size of pkt is not a multiple of 16
            pkt += b"\0"  # padding with zero to have a multiple of 16 size
        s = sum(array.array("H", pkt))  # s may has more than 16 bit if there 's a carry > 0
        s = (s >> 16) + (s & 0xffff)  # make s 16 bit by adding carry to the first 16 bit
        s += s >> 16  # plus carry again if the previous sum is still more than 16 bit.
        s = ~s  # 1 complement of s.
        return s & 0xffff  # make s 16 bit.
else:
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += b"\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return (((s >> 8) & 0xff) | s << 8) & 0xffff


# function that checks if a given packet is a MEADcast packet or not
def mcpacketchecker(packet):
    ismcheader = 0
    # parses ipv6 header (0:14 is the ether frame, so we can ignore that
    ip_header = packet[0 + 14:14 + 40]
    # unpacks the IPv6 header into its individual header fields
    ipv6header = struct.unpack("!IHBB16s16s", ip_header)

    #looks at the NEXT HEADER field and checks if it's 00 (for hop by hop)
    ip_nh = ipv6header[2]

    if ip_nh == 0:

        # if a HBH header exists then unpack it
        hbh_header = packet[54:62]
        hbhheader = struct.unpack("!BBBBI", hbh_header)

        # check the next headerfield of the HBH header is 43, the next header can be assumed to be a MEADcast header
        # 43 stands for experimental routing header

        hbh_nextheader = hbhheader[0]
        #print hbhheader[0]
        if hbh_nextheader == 43:
            #return 1 if true, 0 if not
            ismcheader = 1

    return ismcheader

# helper functions to parse data from the MEADcast header
def parse_mc_data_nexthdr(header, amount):
    bitmap = header[0]
    return bitmap


def parse_mc_data_hdrextlen(header, amount):
    bitmap = header[1]
    return bitmap


def parse_mc_data_routetype(header, amount):
    bitmap = header[2]
    return bitmap


def parse_mc_data_numdesti(header, amount):
    bitmap = header[3]
    return bitmap


def parse_mc_data_drhcres(header, amount):
    bitmap = header[4]
    return bitmap


def parse_mc_data_bitmap(header, amount):
    bitmap = header[5]
    return bitmap


def parse_mc_data_routerbitmap(header, amount):
    routerbitmap = header[6]
    return routerbitmap


# helper function that returns a list of IP when given the HEADER and the amount of destinations encoded in it
def parse_mc_data_ip(header, amount):
    len = 6 + (amount * 2) + 1
    iplist = []
    for i in range(7, 7 + amount):
        iplist.append(socket.inet_ntop(socket.AF_INET6, header[i]))

    return iplist

# helper function that returns a list of UDP destination ports when given the MC header and the amount of destinations
# encoded in it
def parse_mc_data_port(header, amount):
    len = 6 + (amount * 2) + 1
    portlist = []
    for i in range(7 + amount, len):
        portlist.append(header[i])
    return portlist


# function used to calculate the length of the MEADcast header, based on the amount of IP addresses encoded
def calc_MCH_len(amountofip):
    # fix: nh, hdrextlen, type, #desti, DRHC add 1 ea, reserved adds 3, both routerbitmap add 8 ea
    # 1+1+1+1+1+3+8+8 = 24
    # each ip adds 16
    # each port adds 2
    # pad until amount%4 = 0
    len_of_header = 24 + (16 * amountofip) + (2 * amountofip)
    # print len_of_header
    if len_of_header % 8 == 1:
        len_of_header = len_of_header + 7
    if len_of_header % 8 == 2:
        len_of_header = len_of_header + 6
    if len_of_header % 8 == 3:
        len_of_header = len_of_header + 5
    if len_of_header % 8 == 4:
        len_of_header = len_of_header + 4
    if len_of_header % 8 == 5:
        len_of_header = len_of_header + 3
    if len_of_header % 8 == 6:
        len_of_header = len_of_header + 2
    if len_of_header % 8 == 7:
        len_of_header = len_of_header + 1

    return len_of_header

# just a helper function that adds a latter to a given string x amount of times
def add_to_letter_tostring(string, letter, amount):
    for i in range(0, amount):
        string = string + letter
        # print string

    return string

# creates a corresponding unstruck string to unpack a MEADcast packet, since the packet size is not fixed and dependent
# on the amount of IPs encoded in the header
def create_unstruck_string(amountofip):
    startstring = "!BBBBIqq"
    # print amountofip
    # print (amountofip * 16 + amountofip * 2)
    amountofbuffers = 8 - ((amountofip * 16 + amountofip * 2) % 8)
    # print amountofbuffers
    # print "amount of buffers in struct", amountofbuffers
    startstring = add_to_letter_tostring(startstring, "16s", amountofip)
    startstring = add_to_letter_tostring(startstring, "H", amountofip)
    if amountofbuffers != 8:
        startstring = add_to_letter_tostring(startstring, "x", amountofbuffers)
    # print "String used to unpack MC package: ", startstring
    # print ""
    return startstring


# creates a MAC address from a string by adding a ":" every 2 characters
def createmacaddfromstring(string):
    macaddr = ""
    for x in range(len(string)):
        if x % 2 == 0:
            if x == 0:
                macaddr = macaddr + string[x]
            else:
                macaddr = macaddr + ":"
                macaddr = macaddr + string[x]


        else:
            macaddr = macaddr + string[x]

    return macaddr

# helper function that converts an INT consisting of 0 and 1 into a list of 0 and 1
# 100100 turns into [1,0,0,1,0,0]
def convertinttoINTLIST(int):
    newlist = []
    for x in range(len(str(int))):
        if str(int)[x] == "1":
            newlist.append(1)
        else:
            newlist.append(0)
    return newlist

# converts a list of ints into a string
# [1,0,0,1,0,0] turns into "100100"
def convertINTLISTtostring(list):
    newstring = ""
    for x in range(len(list)):
        newstring = newstring + str(list[x])

    return newstring


# creates the ether frame for the packet
def make_ether_header(source, desti):
    sourceadd = source.replace(':', '').decode('hex')
    destination = desti.replace(':', '').decode('hex')
    protocol = 0x86DD
    packet = struct.pack("!6s6sH", destination, sourceadd, protocol)
    return packet

# creates a Hop-by-Hop extension header
def make_hbh_header(nex, hdrlen, padopt, optdatalen):
    hbh_nextheader = nex
    hbh_headerextlength = 0
    hbh_padoption = padopt
    hbh_optdatalen = optdatalen
    hbh_pad = 0
    hbh_header = pack("!BBBBI", hbh_nextheader, hbh_headerextlength, hbh_padoption, hbh_optdatalen, hbh_pad)
    return hbh_header


# creates a UDP header
def make_udp_header(udp_source, udp_dest, len, check):
    udp_source = udp_source  # 16 bit udp source port
    udp_dest = udp_dest  # 16 bit udp destination port
    udp_length = len  # 16 bit length, which is the length of udp header + data (->minimal 8), will be recalculated later.
    udp_check = check  # 16 bit udp checksum, will be recalculated later.
    udp_header = pack('!HHHH', udp_source, udp_dest, udp_length, udp_check)
    return udp_header

# function that creates a pseudo header and calculates the necessary UDP checksum based on that + the payload
def calc_checksumudp(message, senderport, destiport, senderip, destiip):
    udp_length = 8 + len(message)
    udp_header = make_udp_header(senderport, destiport, udp_length, 0)
    udp_length = len(udp_header) + len(message)  # 32 bit for checksum calculation
    placeholder = 0  # 24 bit zero
    protocol = socket.IPPROTO_UDP  # 8 bit
    placeholder_protocol = placeholder + protocol
    pship = pack('!16s16sII', senderip, destiip, udp_length, placeholder_protocol)
    psh = pship + udp_header
    psh = psh + udp_header + message

    checksumvalue = checksum(psh)

    return checksumvalue

# helper function that adds a new IP address to the MEADcast extension header
def add_ip_add_to_header(package, ipadd):
    new_package_len = len(package)
    formatbyte = "!%ss16s" % new_package_len
    new_package = pack(formatbyte, package, ipadd)
    return new_package

# helper function that adds a new destination UDP port to the MEADcast extension header
def add_port_to_header(package, port):
    new_package_len = len(package)
    formatbyte = "!%ssH" % new_package_len
    new_package = pack(formatbyte, package, port)
    return new_package

# helper function that adds padding to the MEADcast extension header
def add_padding_to_header(package):
    new_package_len = len(package)
    formatbyte = "!%ss1x" % new_package_len
    new_package = pack(formatbyte, package)
    # print "adding pad"
    return new_package

# function that creates the MEADcast extension header
# it has the discovery bit, response bit, number of destinations, hopcount, intended destination of the sender and port, the destination list, the destination bitmap, router bitmap and port list
#and returns a MEADcast header
# numdesti obsolete since the number of destinations will be calculated based on the ... number of destinations TODO: remove
# intendeddestinationofsen and port are obsolete and not used. TODO: delete from header and adjust code in all applications that use this function
def make_mc_header3(discobit, responsebit, numdesti, hopcounts, intendeddestiofsen,
                    port, destinationlist, bitmaplist, routerlist,
                    destinationportlist):  # example for 1 destination with fixed values

    #MEADcast next header, hardcoded to UDP (17)
    mmc_nxthdr = 17
    mmc_routetype = 253  # experimental
    mmc_numberdest = len(destinationlist)
    mmc_discoverybit = discobit  # 1 if related to discovery phase
    mmc_response = responsebit  # 0 means request, 1 means response
    mmc_hopcount = hopcounts
    mmc_reserved = 0

    # creates the MEADcast bitmap in a roundabout way, it's an INT in the end
    mmc_bitmap1 = int(convertINTLISTtostring(bitmaplist))
    # print mmc_bitmap1,"bitmap"
    # creates the router bitmap
    mmc_routertag_bitmap1 = int(convertINTLISTtostring(routerlist))
    # print mmc_routertag_bitmap1,"routerbitmap"
    # uncomment to see if headerlen calc work with max ip and ports, divide with 8 at the end
    # destinationportlist = [1,2,3,4,5,6,7,8,9,10,1,2,3,4,5,6,7,8,9,10,1,2,3,4,5,6,7,8,9,10,1,2,3,4,5,6,7,8,9,10,1,2,3,4
    # ,5,6,7,8,9,10,1,2,3,4,5,6,7,8,9,10,1,2,3,4]
    # destinationlist = ["::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1",
    # "::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1",
    # "::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1",
    # "::1","::1","::1","::1","::1","::1","::1","::1","::1","::1","::1"]
    mmc_desti = socket.inet_pton(socket.AF_INET6, intendeddestiofsen)  #
    mmc_port = port
    mmc_padding = 0  # since only 1 destination and 1 port we need 1 pad

    # section that calculates the amount of padding needed later the MEADcast

    if len(destinationportlist) % 4 == 0:
        portlength = len(destinationportlist) / 4
        # print portlength,"portoctets"
    if len(destinationportlist) % 4 == 1:
        portlength = (len(destinationportlist) + 3) / 4
        # print portlength,"portoctets"
    if len(destinationportlist) % 4 == 2:
        portlength = (len(destinationportlist) + 2) / 4
        # print portlength,"portoctets"
    if len(destinationportlist) % 4 == 3:
        portlength = (len(destinationportlist) + 1) / 4
        # print portlength,"portoctets"

    # calculates the header extension length of the MEADcast header based on the amount of destinations encoded
    mmc_hdrextlen = 1 + 1 + len(destinationlist) * 2 + portlength

    #packs the discovery bit, response bit, hopcount and reserved part into a single format
    #1 bit for the discovery bit, 1 bit for the response bit, 6 bits for the hopcount and the rest for reserved
    mmc_d_r_hc_res = (mmc_discoverybit << 31) + (mmc_response << 30) + (mmc_hopcount << 24) + mmc_reserved

    # print(bin(mmc_d_r_hc_res), "bintest")
    # print("('0b11000000000000000000000000000000 - control")
    # print(mmc_d_r_hc_res, "mmc_d_r_hc_res")

    # creates the fixed part of the MEADcast extension header without the destinations and ports
    mc_header_woiport = pack("!BBBBIqq", mmc_nxthdr, mmc_hdrextlen, mmc_routetype, mmc_numberdest, mmc_d_r_hc_res,
                             mmc_bitmap1, mmc_routertag_bitmap1)
    # print ""
    # print "startlen (withoutip and ports):",len(mc_header_woiport)
    # print ""
    # print "string", str(mc_header_woiport)


    # adds every IP address in the ip destination list given to the extension header, one by one
    for x in range(len(destinationlist)):
        mc_header_woiport = add_ip_add_to_header(mc_header_woiport,
                                                 socket.inet_pton(socket.AF_INET6, destinationlist[x]))
        # print "adding ipadd", destinationlist[x]
        # print("currentlen", len(mc_header_woiport))
        # print "currentlen",len(mc_header_woiport)%8

    # adds every UDP destination port to the extension header, one by one
    for x in range(len(destinationportlist)):
        mc_header_woiport = add_port_to_header(mc_header_woiport, destinationportlist[x])
        # print "adding port", destinationportlist[x]
        # print("currentlen", len(mc_header_woiport))
        # print("currentlen",len(mc_header_woiport)%8)

    # section that adds padding depending on the current length of the packet
    if len(mc_header_woiport) % 8 == 1:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    if len(mc_header_woiport) % 8 == 2:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    if len(mc_header_woiport) % 8 == 3:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    if len(mc_header_woiport) % 8 == 4:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    if len(mc_header_woiport) % 8 == 5:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    if len(mc_header_woiport) % 8 == 6:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    if len(mc_header_woiport) % 8 == 7:
        mc_header_woiport = add_padding_to_header(mc_header_woiport)

    # print "endlen (with ip and ports):",len(mc_header_woiport)
    # print (mc_header_woiport)


    #return the finished packet
    return mc_header_woiport

# creates the IPv6 header, it takes the version, traffic class, flowlabel, next header, header length, IP source address, IP destination address and payload length
# and returns the IPv6 header
def make_ipv6headerpll(ver, tc, fl, nh, hl, source, desti, pll):
    rip_ver = ver #version
    rip_tc = tc #traffic class
    rip_fl = fl #flow label
    rip_pl = pll #payloadlength
    rip_nh = nh #nextheader
    rip_hl = hl #headerlength
    rip_saddr = socket.inet_pton(socket.AF_INET6, source) #IP source address
    rip_daddr = socket.inet_pton(socket.AF_INET6, desti) #IP destination address

    rip_ver_tc_fl = (rip_ver << 28) + rip_tc + rip_fl

    ripheader = pack("!IHBB16s16s", rip_ver_tc_fl, rip_pl, rip_nh, rip_hl, rip_saddr, rip_daddr)

    return ripheader


# creates a MEADcast discovery packet, takes the source and destination IP address and UDP ports and returns
# a MEADcast discovery request packet
# most fields are empty as specified by the MEADcast paper
def create_mc_discovery_packet(ip_sourceadd, ipdestiadd, udp_sourceport, udp_destport):
    #technically just a placeholder and not needed, just a dummy so the make_mc_header3 function works
    mc_senderintendedipadd = "::1"
    mc_port = 5005
    #empty iplist
    iplist = []
    #empty portlist
    portmap = []
    #empty destination bitmap
    bitmaplist = [0]
    #empty destination routerbitmap
    routermaplist = [0]

    #the payload field is usually empty, it currently has a message encoded for testing purposes
    message = "THIS IS A DISCOVERY PACKET, IGNORE PAYLOAD"
    udp_length = 8 + len(message)
    # make the hbh header
    hbh_header = make_hbh_header(43, 0, 1, 1)

    # make the udp header
    udp_check = calc_checksumudp(message, udp_sourceport, udp_destport, ip_sourceadd, ipdestiadd)
    udp_header2 = make_udp_header(udp_sourceport, udp_destport, udp_length, udp_check)
    # iprouterbitmaplist = convert_list_to_ipadd_and_routerbitmap(list_of_ips)

    # make the MC header, discovery bit set to 1 and response bit set to 0
    rmc_header = make_mc_header3(1, 0, len(iplist), 0, mc_senderintendedipadd, mc_port,
                                 iplist, bitmaplist, routermaplist, portmap)

    # calculate the IPv6 payload length
    pll = len(rmc_header) + len(hbh_header) + len(udp_header2) + len(message)

    # make the IPv6 header
    ip_headerpll = make_ipv6headerpll(6, 0, 0, 00, 128, ip_sourceadd, ipdestiadd, pll)

    # make the discovery packet
    package = ip_headerpll + hbh_header + rmc_header + udp_header2 + message

    # return the packet
    return package

# creates a MEADcast data delivery packet, similar create_mc_discovery_packet function, but with the discovery bit set

def create_mc_packet2(ip_sourceadd,
                      ipdestiadd, udp_sourceport, udp_destport,
                      message, iplist, routermaplist, bitmaplist, portmap):
    mc_port = 0
    udp_length = 8 + len(message)
    # make the hbh header
    hbh_header = make_hbh_header(43, 0, 1, 1)

    # make the udp header
    udp_check = calc_checksumudp(message, udp_sourceport, udp_destport, ip_sourceadd, ipdestiadd)
    udp_header2 = make_udp_header(udp_sourceport, udp_destport, udp_length, udp_check)
    # iprouterbitmaplist = convert_list_to_ipadd_and_routerbitmap(list_of_ips)

    rmc_header = make_mc_header3(0, 0, len(iplist), 0, ipdestiadd, mc_port,
                                 iplist, bitmaplist, routermaplist, portmap)

    pll = len(rmc_header) + len(hbh_header) + len(udp_header2) + len(message)
    ip_headerpll = make_ipv6headerpll(6, 0, 0, 00, 128, ip_sourceadd, ipdestiadd, pll)
    package = ip_headerpll + hbh_header + rmc_header + udp_header2 + message
    return package

# creates a MEADcast discovery response packet, similar to create_mc_discovery_packet function, but with response packet set
def create_mc_response_packet(router_ip_add, ip_sourceadd, ipdestiadd, udp_sourceport, udp_destport,
                              hopcount):
    hopcount = hopcount + 1
    message = ""
    mc_senderintendedipadd = "::1"
    mc_port = 0
    iplist = [ipdestiadd]
    portmap = [udp_destport]
    bitmaplist = [0]
    routermaplist = [0]
    udp_length = 8 + len(message)
    # make the hbh header
    hbh_header = make_hbh_header(43, 0, 1, 1)

    # make the udp header
    udp_check = calc_checksumudp(message, udp_sourceport, udp_destport, ip_sourceadd, ipdestiadd)
    udp_header2 = make_udp_header(udp_sourceport, udp_destport, udp_length, udp_check)
    # iprouterbitmaplist = convert_list_to_ipadd_and_routerbitmap(list_of_ips)

    rmc_header = make_mc_header3(1, 1, len(iplist), hopcount, mc_senderintendedipadd, mc_port,
                                 iplist, bitmaplist, routermaplist, portmap)

    pll = len(rmc_header) + len(hbh_header) + len(udp_header2) + len(message)
    ip_headerpll = make_ipv6headerpll(6, 0, 0, 00, 128, router_ip_add, ip_sourceadd, pll)
    package = ip_headerpll + hbh_header + rmc_header + udp_header2 + message
    return package


# function that decomposes a MEADcast packet into all the relevant MC data
# returns a data structure that has the decomponsed packet data saved

def handlemcpacket(packet):

    #parses the data from the ether frame
    ether_frame = packet[0:14]
    # print "ether",ether_frame
    ether_frameheader = struct.unpack("!6s6sH", ether_frame)
    ether_desti = ether_frameheader[0].encode("hex") #destination MAC address
    ether_source = ether_frameheader[1].encode("hex") #source MAC address
    ether_type = ether_frameheader[2] # ether frame type
    # print("Destination MAC: {}".format(ether_desti))
    # print str(ether_source.decode()),"str"
    # print ether_type,"34525 is 86DD (ipv6 ethernet frame type)"

    ## handle ipv6 header
    ip_header = packet[0 + 14:14 + 40]
    ipv6header = struct.unpack("!IHBB16s16s", ip_header)
    a = ipv6header[0]
    ip_ver = a >> 28    # IP version
    ip_tc = (a & 0x0fffffff) >> 20 # traffic class
    ip_fl = (a & 0x000fffff) # flow label
    ip_pl = ipv6header[1] #payload length
    ip_nh = ipv6header[2] #next header
    ip_hl = ipv6header[3] #header length
    ip_saddr = ipv6header[4] #source IP address
    ip_daddr = ipv6header[5] #destination IP address

    # saves the data in a ipv6data class
    ipv6_data = ipv6data(ip_ver, ip_tc, ip_fl, ip_pl, ip_nh, ip_hl, ip_saddr, ip_daddr)

    if ip_nh == 0:

        #handles the Hop-by-Hop header
        hbh_header = packet[54:62]
        # print("hbh", hbh_header)
        hbhheader = struct.unpack("!BBBBI", hbh_header)

        hbh_nextheader = hbhheader[0] #next header
        hbh_headerextlength = hbhheader[1] #header extension length
        hbh_padoption = hbhheader[2] # hbh pad option
        hbh_optdatalen = hbhheader[3] #optional data len

        #saves the data in a hbhdata class
        hbh_data = hbhdata(hbh_nextheader, hbh_headerextlength, hbh_padoption, hbh_optdatalen)

        # print("expected length of mcheader:"), calc_MCH_len(hbh_optdatalen)
        # mch_len= calc_MCH_len(hbh_optdatalen)


        #handles the MEADcast extension header
        if hbh_nextheader == 43:

            #this block calculates the MEADcast extension header length, used to calculate the amount of receivers encoded
            #and when the MEADcast header ends and the UDP header begins


            mc_numdestitemp = packet[62:62 + 4]
            mc_numdestitemptemp = struct.unpack("!BBBB", mc_numdestitemp)
            num4 = mc_numdestitemptemp[3]
            mch_len = calc_MCH_len(num4)

            # parsing MEADcast data
            medcast_header = packet[62:62 + mch_len]

            # creates the string used for unpacking the MEADcast extension header based on the amount of receivers encoded
            unstruckstring = create_unstruck_string(num4)

            # print unstruckstring
            unstruckstring = unstruckstring
            # print num4
            # print len(medcast_header)
            mcheader = struct.unpack(unstruckstring, medcast_header)

            # print_mc_header(mcheader, num4, 8 - (num4 * 16 + num4 * 2 + 24) % 8)
            nextheader = parse_mc_data_nexthdr(mcheader, num4)
            hdrextlen = parse_mc_data_hdrextlen(mcheader, num4)
            routetype = parse_mc_data_routetype(mcheader, num4)
            numdesti = parse_mc_data_numdesti(mcheader, num4)
            mc_drhres = parse_mc_data_drhcres(mcheader, num4)
            bitmap = parse_mc_data_bitmap(mcheader, num4)
            routerbitmap = parse_mc_data_routerbitmap(mcheader, num4)
            iplist = parse_mc_data_ip(mcheader, num4)
            portlist = parse_mc_data_port(mcheader, num4)

            #mask used to only look at the first bit of the D_R_HC pack to unpack the discovery bit
            mc_d_mask = 0b10000000000000000000000000000000
            mc_d = (mc_d_mask & mc_drhres) >> 31
            # mask used to only look at the second bit of the D_R_HC section to unpack the response bit
            mc_r_mask = 0b01000000000000000000000000000000
            mc_r = (mc_r_mask & mc_drhres) >> 30
            # mask used to only look at the 6 bits that make up the hopcount
            mc_hc_mask = 0b00111111000000000000000000000000
            mc_hc = (mc_hc_mask & mc_drhres) >> 24

            #saves all the MEADcast data in the MEADcastdata class
            mc_header_data = mcheaderdata(nextheader, hdrextlen, routetype, numdesti, mc_d, mc_r, mc_hc, bitmap,
                                          routerbitmap, iplist, portlist)

            ## UDP PART
            udp_header = packet[62 + mch_len:62 + mch_len + 8]
            # print("UDPHeader", udp_header)
            # print("udpheaderlen", len(udp_header))
            udpheader = struct.unpack("!HHHH", udp_header)

            udp_port = udpheader[0] #udp source port
            udp_dest = udpheader[1] #udp destination port
            udp_len = udpheader[2] #udp length
            udp_check = udpheader[3] #udp checksum

            # print[udp_port]
            # print[udp_dest]
            # print[udp_len]
            # print[udp_check]

            #saves all the UDP data in the udpdata class
            udp_data = udpdata(udp_port, udp_dest, udp_len, udp_check)

            #every data after the UDP header is the payload and gets parsed here
            payload = packet[62 + mch_len + 8:len(packet)]


            ether_data = etherframedata(ether_desti, ether_source, ether_type)


            #saves all the data in the mcdata class for easier processing
            mc_data = mcdata(ether_data, ipv6_data, hbh_data, mc_header_data, udp_data, payload)

            return mc_data

    return

#######################################
# functions related to packet sending #
#######################################

# simple test function that uses raw socket
def sendpacket(o):
    s = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_RAW)
    s.sendto(o, ("::1", 0))
    # print "len packet",len(o)," prob ",len(o)+14
    # print("packet sent")

# simple function that sends a packet via raw socket to the specified IP address
# o for the packet and i for the IP address
def sendpacketwithip(o, i):
    s = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_RAW)
    s.sendto(o, (i, 0))
    print "packet sent to:", i
    # print "len packet",len(o)," prob ",len(o)+14
    # print("packet sent")

# sends a unicast packet
def sendpacketwithipnoraw(message, udp_ip, udp_port):
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    s.sendto(message, (udp_ip, udp_port))
    print "packet sent to:", udp_ip, udp_port


# sends a packet with ether frame attached via raw socket directly
# this function only works for the endhosts PC1-PC10 on both topologies that have eth1 as their interface that connects them to their router

def sendpacketwithether(ethernet_packet):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    s.bind(("eth1", 0))
    s.send(ethernet_packet)


#################################################
# functions that are specific to the controller #
#################################################
'''
TODO: just add them to the controller application itself instead of having it here
'''

# used to create a temporary data structure in the controller. It takes the payload, IP destination list, router bitmap, destination bitmap and portlist and
# creates a list with the payload as the first value and a list of IP+ports as the second value for the destinations it is responsible for
def create_payload_ipv6_queue_entry(payload,iplist,routerbitmap,bitmap,portmap):
    working_routerbitmap = convertinttoINTLIST(routerbitmap)
    working_bitmap = convertinttoINTLIST(bitmap)
    entry_list = [payload,[]]

    for x in range(len(working_bitmap)):
        if working_routerbitmap[x] == 1:
            #if routerbitmap and bitmap are aligned it means that there are ips coming that we are responsible for those ip
            if working_routerbitmap[x] == working_bitmap[x]:
                # print working_bitmap[x]
                # print "responsible for coming ip"
                responsible_switch = iplist[x]

            #if routerbitmap and bitmap are not aligned it means we found the end of our responsible ip....in theory
            if working_routerbitmap[x] != working_bitmap[x]:
                responsible_switch = ""


        if working_routerbitmap[x] == 0:
            if responsible_switch == "":
                print "ip dealt with already "
            else:
                # print "ip found that is not a router"
                entry_list[1].append([iplist[x],portmap[x]])
                #dict.setdefault(iplist[x], {})
                #dict[iplist[x]]['destination_udpport'] = portmap[x]
    return entry_list


# similar to create_payload_ipv6_queue_entry, but deals with a dictionary instead
def add_to_dict2(dict, iplist, routerbitmap, bitmap, portmap):
    working_routerbitmap = convertinttoINTLIST(routerbitmap)
    working_bitmap = convertinttoINTLIST(bitmap)
    # print working_bitmap
    responsible_switch = ""

    for x in range(len(working_bitmap)):
        if working_routerbitmap[x] == 1:
            #if routerbitmap and bitmap are aligned it means that there are ips coming that we are responsible for those ip
            # router bitmap 100100 and destination bitmap 100100 indicate that both routers (indicated by the 1 on the router bitmap
            # are responsible for two destinations and haven't been dealt with

            # router bitmap 100100 and destinationbitmap 100000 for example indicate that there are two routers responsible for
            # two destinations, but one of them has been dealt with already (the second 1 on the router bitmap)
            if working_routerbitmap[x] == working_bitmap[x]:
                # print working_bitmap[x]
                # print "responsible for coming ip"
                responsible_switch = iplist[x]

            #if routerbitmap and bitmap are not aligned it means we found the end of our responsible ip....in theory

            if working_routerbitmap[x] != working_bitmap[x]:
                responsible_switch = ""


        if working_routerbitmap[x] == 0:
            if responsible_switch == "":
                print "ip dealt with already "
            else:
                # print "ip found that is not a router"
                dict.setdefault(iplist[x], {})
                dict[iplist[x]]['destination_udpport'] = portmap[x]



    return dict
