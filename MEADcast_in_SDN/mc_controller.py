'''
__author__ = 'Cuong Ngoc Tran'
__author__ = 'Minh Duc Nguyen'
'''

'''
NDP part by Cuong, MEADcast part by Minh
TODO: 
'''
"add the shortest path as rules to switches from ndp.py"

'''
Bug: 
    MEADcast packet ipv6 header can't get parsed by the ryu packet handler, ignore the error messages in the console

'''
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ipv6
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import in_proto
from ryu.lib.packet import lldp
from ryu.lib.packet import ipv6
from ryu.lib.packet import icmpv6

from ryu.topology import event

import networkx as nx
import mc_functions as mc
import socket
from scapy import all as sp
import time

'''
To run:
    ryu-manager --observe-links mc_controller.py

To test:
    on pc1: python mc_file_sender.py 
    on PC1: ping PC2
    on PC2: run     
        python udp_ipv6_server.py
'''


# own queue class, not much different from the python one - it adds at the front of the list and pops the last entry in the list
class Queue:
    def __init__(self):
        self.items = []

    # checks if queue is empty
    def isEmpty(self):
        return self.items == []

    # add an entry to the TOP of the list, so whenever a new entry comes in the one at the bottom will always be the oldest
    def queue(self, entry):
        self.items.insert(0, entry)

    # uses list function to pop the lowest entry of the queue
    def pop(self):
        temp_value = self.items[-1]
        self.items.pop()
        return temp_value

    #
    def size(self):
        return len(self.items)

    def printq(self):
        for items in self.items:
            print items

    #


class ndp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ndp, self).__init__(*args, **kwargs)
        self.count = 1  # to count the number of switch entrance from event switch_enter
        self.HARD_TIMEOUT = 3000  # amount of time (in second) a rule exists in the switch if hard_timeout is set for that rule.

        #        self.topology_api_app = data['topology_api_app']
        ''' Shortest path first routing/switching '''
        self.net = nx.DiGraph()

        '''Learning Switch'''
        self.mac_to_port = {}
        self.ip_list = {}
        #ip and mac of controller in topo1
        self.msg_src_ip = '2001:db8::6701'
        self.msg_src_mac = '00:16:3e:00:67:01'
        self.count = 0

        "queue"

        self.q = Queue()

        ''' Cache NDP'''
        # a dictionary data structure: {SW_datapath_id, set([all switch ports])}
        self.all_switch_ports = {}  # \\XXX not optimized because this includes the DOWN ports, which should be seperated from the LIVE ports.
        # a dictionary data structure: {SW_datapath_id, set([non inter-switch ports])}
        self.non_interswitch_ports = {}
        # a dictionary data structure: {SW_datapath_id, set([inter-switch ports])}
        self.interswitch_ports = {}

        # a dictionary data structure: IP, MAC, SW datapath_id, port
        # {IP:{'mac':'x', 'dpid':y, 'port':[a}}
        self.ndp_cache_db = {}

        # a dictionary data structure: {dpid: datapath}
        self.datapathmap = {}

        "response packet dictionary"

        # a dictionary for waiting discovery response packets, basically a waiting list for response packets
        self.responsepacketdict = {}

    # Handy function that lists all attributes in the given object
    def ls(self, obj):
        print("\n".join([x for x in dir(obj) if x[0] != "_"]))

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    #    def add_flow_with_hard_timeout(self, datapath, priority, match, actions, buffer_id=None, hard_timeout):
    def add_flow_with_hard_timeout(self, datapath, priority, match, actions, hard_timeout):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        # if buffer_id:
        #    mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, buffer_id=buffer_id,
        #            priority=priority, match=match, instructions=inst)
        # else:
        mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def ndp_switch_features_handler(self, ev):
        print("\nndp switch features handler")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()

        '''add default rule, "forward to controller" to the switch '''
        print("Add default rule, \"forward to controller\" in switch:"),
        print(datapath.id)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.datapathmap[datapath.id] = datapath

        "adds custom rule for meadcast packets, every packet from the sender with the udp destination port of 5005" \
        "will be handled as a MCpacket"
        matchformc = parser.OFPMatch(eth_type=0x86dd, ip_proto=17, udp_dst=5005)
        actionsmc = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 500, matchformc, actionsmc)
        self.logger.info("attempt: add flow eth_type=86dd,ip_proto=17,udp_port:5005 with priority 500 ")

    @set_ev_cls(event.EventSwitchEnter)
    def ndp_handler_switch_enter(self, ev):
        print(" " + str(self.count) + " -- Switch: "),
        self.logger.info("switch is entering")
        print(ev.switch)
        print("ndp_cache_db = %s" % self.ndp_cache_db)
        dpid = ev.switch.dp.id
        print("ev.switch.dp.id="),
        print(dpid)

        self.all_switch_ports.setdefault(dpid, set())

        print("ev.switch.ports = %s" % ev.switch.ports)
        for port in ev.switch.ports:
            #            print(port)
            self.all_switch_ports[dpid].add(port.port_no)
        #        self.ls(ev.switch.ports)
        print("self.all_switch_ports = "),
        print(self.all_switch_ports)
        self.count += 1

    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def ndp_handler_switch_leave(self, ev):
        dpid = ev.switch.dp.id
        print("switch is leaving!")
        self.logger.info("Not tracking Switche %s anymore, switch %s leaved.", dpid, dpid)
        # delete the corresponding entries in ndp_cache_db and all_interswitch_ports, interswitch_ports and non_interswitch_ports
        for i in self.ndp_cache_db:
            # print(self.ndp_cache_db[i]['dpid'])
            if self.ndp_cache_db[i]['dpid'] == dpid:
                print("delete switch %s out of ndp_cache_db" % dpid)
                del self.ndp_cache_db[i]
                break
        print("self.ndp_cache_db = "),
        print(self.ndp_cache_db)
        del self.all_switch_ports[dpid]
        del self.interswitch_ports[dpid]
        del self.non_interswitch_ports[dpid]
        del self.datapathmap[dpid]
        print("self.non_interswitch_ports = %s" % self.non_interswitch_ports)
        # update self.net: links and nodes:
        self.net.remove_node(dpid)
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())

    # TODO update rules at switch for shortest path switching
    @set_ev_cls(event.EventLinkAdd, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def ndp_handler_link_add(self, ev):
        self.logger.info("link is added")
        print(ev)
        #        self.ls(ev.link)
        self.interswitch_ports.setdefault(ev.link.src.dpid, set())
        self.interswitch_ports[ev.link.src.dpid].add(ev.link.src.port_no)
        self.non_interswitch_ports.setdefault(ev.link.src.dpid, set())
        self.non_interswitch_ports[ev.link.src.dpid] = self.all_switch_ports[ev.link.src.dpid] - self.interswitch_ports[
            ev.link.src.dpid]

        #        link = [(ev.link.src.dpid, ev.link.dst.dpid,{'port':link.src.port_no})]
        #        self.net.add_edges_from(link)
        self.net.add_edges_from([(ev.link.src.dpid, ev.link.dst.dpid, {'port': ev.link.src.port_no})])
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        print("self.non_interswitch_ports = %s" % self.non_interswitch_ports)
        print("self.interswitch_ports = %s" % self.interswitch_ports)

    @set_ev_cls(event.EventLinkDelete, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def ndp_handler_link_delete(self, ev):
        self.logger.info("link is deleted")
        print(ev)
        try:
            self.net.remove_edge(ev.link.src.dpid, ev.link.dst.dpid)
        except nx.NetworkXError:
            print("there is no such edge in the graph")
        # if ev.link.src.dpid in self.interswitch_ports and
        try:
            if ev.link.src.port_no in self.interswitch_ports[ev.link.src.dpid]:
                self.interswitch_ports[ev.link.src.dpid].remove(ev.link.src.port_no)
            # if ev.link.src.dpid in self.non_interswitch_ports:
            if ev.link.src.port_no in self.non_interswitch_ports[ev.link.src.dpid]:
                self.non_interswitch_ports[ev.link.src.dpid].remove(ev.link.src.port_no)
        except KeyError:
            print("Keyerror: already deleted.")
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        print("self.non_interswitch_ports = %s" % self.non_interswitch_ports)
        print("self.interswitch_ports = %s" % self.interswitch_ports)

        # update rules at switch for shortest path switching
        try:
            datapath = self.datapathmap[ev.link.src.dpid]
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch()
            # delete current rules in the switches
            mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE, out_port=ev.link.src.port_no,
                                    out_group=ofproto.OFPG_ANY, match=match)
            print("\nDelete existing rules in switch:"),
            print(ev.link.src.dpid)
            datapath.send_msg(mod)
        except AttributeError:
            print("NoneType: no such datapath")
        except KeyError:
            print("KeyError: no such key in datapathmap")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def ndp_packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)

        msg = ev.msg
        # scapy_pkt = sp.Ether(msg.data)

        datapath = msg.datapath
        in_port = msg.match['in_port']

        # mcpacketchecker is a function that returns 1 if the incoming packet contains a MEADcast header and 0 if it doesn't
        ismcheader = mc.mcpacketchecker(msg.data)

        # if the packet is a MEADcast packet
        if ismcheader == 1:
            # count the number of MEADcast packets that have arrived so far
            self.count = self.count + 1
            print self.count

            ###################################################
            # functions specific to handling MEADcast packets #
            ###################################################

            # function to send a unicast packet (IPV6 and UDP) to a list of receiver specified in the MEADcast packet
            def send_unicast_packet_to_hosts(queueentry):

                "queueentry has the following structure: " \
                "[payload,[[ip,port],[ip,port],....,[ip,port]"
                "[payload,[listofip]]"

                src_mac = '00:16:3e:00:67:01'  # the controller
                src_ip = '2001:db8::6701'  # the controller

                # iterate through the list and send the payload to every receiver
                for x in range(len(queueentry[1])):
                    dst_ip_add = queueentry[1][x][0]
                    dst_ip_port = queueentry[1][x][1]
                    dst_mac = self.ndp_cache_db[dst_ip_add]['mac']

                    # create a UDP packet with scapy
                    pkt_udp = sp.Ether(dst=dst_mac, src=src_mac) / sp.IPv6(src=src_ip, dst=dst_ip_add) / sp.UDP(
                        sport=5005, dport=dst_ip_port) / sp.Raw(
                        load=payload)

                    # parse the necessary data from self.datapathmap so the switch knows which port it has to send
                    # the packet out
                    temp_datapath = self.datapathmap[self.ndp_cache_db[dst_ip_add]['dpid']]
                    temp_port = self.ndp_cache_db[dst_ip_add]['port']
                    temp_data = bytes(pkt_udp)
                    temp_parser = temp_datapath.ofproto_parser
                    temp_ofproto = temp_datapath.ofproto
                    temp_actions = [temp_parser.OFPActionOutput(temp_port)]
                    temp_out = temp_parser.OFPPacketOut(datapath=temp_datapath, buffer_id=temp_ofproto.OFP_NO_BUFFER,
                                                        in_port=temp_ofproto.OFPP_CONTROLLER, actions=temp_actions,
                                                        data=temp_data)
                    temp_datapath.send_msg(temp_out)

            # sends a ICMP NS packet to the specified IP address
            def flood_with_icmp(msg_src_ip, msg_dst_ip):

                if msg_dst_ip not in self.ndp_cache_db:

                    msg_dst_ip_net_format = sp.inet_pton(socket.AF_INET6, msg_dst_ip)
                    msg_dst_ip_mul_net_format = sp.in6_getnsma(msg_dst_ip_net_format)
                    msg_dst_ip_mul_printable = sp.inet_ntop(socket.AF_INET6, msg_dst_ip_mul_net_format)

                    msg_dst_mac = sp.in6_getnsmac(msg_dst_ip_net_format)
                    msg_src_mac = '00:16:3e:00:67:01'
                    ns = sp.Ether(dst=msg_dst_mac, src=msg_src_mac) / sp.IPv6(src=msg_src_ip,
                                                                              dst=msg_dst_ip_mul_printable) / sp.ICMPv6ND_NS(
                        tgt=msg_dst_ip) / sp.ICMPv6NDOptSrcLLAddr(lladdr=msg_src_mac)
                    print ns.summary()
                    # ns.show2()

                    print("Do shortcut flooding")
                    for fdpid in self.non_interswitch_ports:
                        fdatapath = self.datapathmap[fdpid]
                        fdata = bytes(ns)
                        fparser = fdatapath.ofproto_parser
                        fofproto = fdatapath.ofproto
                        factions = [fparser.OFPActionOutput(i) for i in list(self.non_interswitch_ports[fdpid])]
                        fout = fparser.OFPPacketOut(datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER,
                                                    in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                        fdatapath.send_msg(fout)

            # sends ICMP NS packet to specified IP address
            def flood_with_icmp2(msg_src_ip, msg_dst_ip):

                msg_dst_ip_net_format = sp.inet_pton(socket.AF_INET6, msg_dst_ip)
                msg_dst_ip_mul_net_format = sp.in6_getnsma(msg_dst_ip_net_format)
                msg_dst_ip_mul_printable = sp.inet_ntop(socket.AF_INET6, msg_dst_ip_mul_net_format)

                msg_dst_mac = sp.in6_getnsmac(msg_dst_ip_net_format)
                msg_src_mac = '00:16:3e:00:67:01'
                ns = sp.Ether(dst=msg_dst_mac, src=msg_src_mac) / sp.IPv6(src=msg_src_ip,
                                                                          dst=msg_dst_ip_mul_printable) / sp.ICMPv6ND_NS(
                    tgt=msg_dst_ip) / sp.ICMPv6NDOptSrcLLAddr(lladdr=msg_src_mac)
                print ns.summary()
                # ns.show2()

                print("Do shortcut flooding")
                for fdpid in self.non_interswitch_ports:
                    fdatapath = self.datapathmap[fdpid]
                    fdata = bytes(ns)
                    fparser = fdatapath.ofproto_parser
                    fofproto = fdatapath.ofproto
                    factions = [fparser.OFPActionOutput(i) for i in list(self.non_interswitch_ports[fdpid])]
                    fout = fparser.OFPPacketOut(datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER,
                                                in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                    fdatapath.send_msg(fout)

            # same as flood_with_icmp2(), but checks if the ip is in the ndp_cache_db first however and only sends if it is not in there
            def check_and_send_icmp(msg_src_ip, ip_dst):
                if ip_dst not in self.ndp_cache_db:
                    # print "ip_dst not in cache yet"
                    flood_with_icmp(msg_src_ip, ip_dst)
                else:
                    print "is in cache already, not sending another icmp"

            #########################################################
            # unpacks the MEADcast packet into its specific headers #
            #########################################################

            "unpacks that pseudo packet"
            packetdataa = mc.handlemcpacket(msg.data)

            "ethernet frame data"
            ether_frameheader = packetdataa.getetherframe()

            "ipv6 data"
            ipv6dataa = packetdataa.getipv6()

            "hbh data"
            hbhdataa = packetdataa.gethbh()

            "meadcastheader data"
            mcdataa = packetdataa.getmc()

            "udpdata"
            udpdataa = packetdataa.getudp()

            "payload"
            payload = packetdataa.getpayload()

            "ether dst and src"
            dst = mc.createmacaddfromstring(ether_frameheader.getetherdesti())
            src = mc.createmacaddfromstring(ether_frameheader.getethersource())
            dpid = datapath.id



            # checks if the discovery bit is set to 1, if it is then it's a discovery request packet
            if mcdataa.getmcdisco() == 1:

                # parse the ip destionation address (ip_add) and ip source address(ip_src) from the packet
                ip_add = socket.inet_ntop(socket.AF_INET6, ipv6dataa.getipv6desti())
                ip_src = socket.inet_ntop(socket.AF_INET6, ipv6dataa.getipv6source())

                print "\ndiscovery packet discovered! for %s" % ip_add
                # check_and_send_icmp(self.msg_src_ip, ip_add)

                # add the sender to ndp_cache_db
                if in_port in self.non_interswitch_ports[
                    dpid] and ip_src not in self.ndp_cache_db:  # cache it and only cache host's info from switch directly connected to the host.
                    self.ndp_cache_db.setdefault(ip_src, {})
                    self.ndp_cache_db[ip_src]['mac'] = src
                    self.ndp_cache_db[ip_src]['dpid'] = dpid
                    self.ndp_cache_db[ip_src]['port'] = in_port
                    print("ndp_cache_db = %s" % self.ndp_cache_db)

                # parse the ether src and dst macaddress from the packet
                eth_dst = mc.createmacaddfromstring(ether_frameheader.getetherdesti())
                eth_src = mc.createmacaddfromstring(ether_frameheader.getethersource())

                dpid = datapath.id
                self.mac_to_port.setdefault(dpid, {})

                # add the IP address of the destination specified in the discovery request packet to the responsepacket waiting list
                # will only send a response packet if a ICMP NA packet arrives at the controller from that receiver
                self.responsepacketdict.setdefault(ip_add, {})
                self.responsepacketdict[ip_add]["sender"] = ip_src
                self.responsepacketdict[ip_add]["sendermac"] = src

                print "responsepacketdict: ", self.responsepacketdict

                # send icmp out regardless of if the ip add is in the ndp_cache or not
                # useful to update the ndp_cache for when changes occur in the receiverlist on the sender topology viewpoint
                flood_with_icmp2(self.msg_src_ip, ip_add)



            # if the discovery bit is clear, then it is a data delivery packet and will be handled here:
            else:
                print("ndp_cache_db = %s" % self.ndp_cache_db)

                # relevant data for data delivery

                #ip destination list
                rawiplist = mcdataa.getmcdestinationlist()

                # print mcdataa.getmcbitmap()
                # print mcdataa.getmcrouterbitmap()
                # print mcdataa.getmcdestinationlist()
                # print mcdataa.getmcportlist()

                # destination bitmap
                mcbitlist = mcdataa.getmcbitmap()

                # router bitmap
                mcrouterbitmap = mcdataa.getmcrouterbitmap()

                # UDP destination portlist
                mcportbitlist = mcdataa.getmcportlist()

                # add_to_dict2 is a function that adds the lists from above to an ip_list for further processing
                mc.add_to_dict2(self.ip_list, rawiplist, mcrouterbitmap, mcbitlist, mcportbitlist)

                #creates a queue entry with the payload as its key. saves which receivers need to receive that payload
                "temporary data to add to the queue"
                temp_queue_entry = mc.create_payload_ipv6_queue_entry(payload, rawiplist, mcrouterbitmap, mcbitlist,
                                                                      mcportbitlist)

                eth_src = ether_frameheader.getethersource()
                # print "adding the entry twice"

                # adds that queue entry to the actual queue (future work, could be used to resend data to receivers
                # who did not receive the payload)
                self.q.queue(temp_queue_entry)

                # find out macadd, port and responsible switch for each ip addr listed in the mcheader
                for ip in self.ip_list:
                    if ip not in self.ndp_cache_db:
                        check_and_send_icmp(self.msg_src_ip, ip)

                # takes the queue entry and sends the payload to every specified receiver via unicast
                send_unicast_packet_to_hosts(temp_queue_entry)

        # if it's a normal packet:
        if ismcheader == 0:

            pkt = packet.Packet(msg.data)
            eth = pkt.get_protocols(ethernet.ethernet)[0]

            eth_dst = eth.dst
            eth_src = eth.src

            dpid = datapath.id
            self.mac_to_port.setdefault(dpid, {})

            # if eth_dst != "01:80:c2:00:00:00": #LLDP messages for topology discover are sent to controller all the time
            if eth_dst == lldp.LLDP_MAC_NEAREST_BRIDGE:  # LLDP messages for topology discover are sent to controller all the time
                return
            else:
                # self.logger.info("\npacket in dpid: %s, src: %s, dst: %s, in_port: %s", dpid, eth_src, eth_dst, in_port)
                print("\npacket in dpid: %s, src: %s, dst: %s, in_port: %s" % (dpid, eth_src, eth_dst, in_port))
                print("self.ndp_cache_db = %s" % self.ndp_cache_db)
                scapy_pkt = sp.Ether(msg.data)
                # print scapy_pkt.summary()
                if scapy_pkt.haslayer(sp.Raw):
                    # print scapy_pkt.getlayer(sp.Raw).load
                    pass

            # Controller builds Neighbor Solicitation message:
            # destination IPv6 address, PC2: 2001:db8::2801 --> multicast IPv6 address: scapy function: sp.in6_getnsma(ipv6 address)
            # source IPv6 address, controller: 2001:db8::6701
            # MAC src addr, controller: 00:16:3e:00:67:01
            # MAC dest addr, unknown --> built from dest IPv6: 33:33:FF:XX:XX:XX, use scapy function: sp.in6_getnsmac(ipv6 address)


            # function that creates and sends a response packet a specified sender
            def send_response_packet_to_sender(packet, sender_ip):
                dst_ip = sender_ip
                print dst_ip
                temp_datapath = self.datapathmap[self.ndp_cache_db[dst_ip]['dpid']]
                temp_port = self.ndp_cache_db[dst_ip]['port']
                temp_data = bytes(packet)
                temp_parser = temp_datapath.ofproto_parser
                temp_ofproto = temp_datapath.ofproto
                temp_actions = [temp_parser.OFPActionOutput(temp_port)]
                temp_out = temp_parser.OFPPacketOut(datapath=temp_datapath, buffer_id=temp_ofproto.OFP_NO_BUFFER,
                                                    in_port=temp_ofproto.OFPP_CONTROLLER, actions=temp_actions,
                                                    data=temp_data)
                temp_datapath.send_msg(temp_out)
                print "sent"

                return

            def flood_with_icmp(msg_src_ip, msg_dst_ip):

                if msg_dst_ip not in self.ndp_cache_db:

                    msg_dst_ip_net_format = sp.inet_pton(socket.AF_INET6, msg_dst_ip)
                    msg_dst_ip_mul_net_format = sp.in6_getnsma(msg_dst_ip_net_format)
                    msg_dst_ip_mul_printable = sp.inet_ntop(socket.AF_INET6, msg_dst_ip_mul_net_format)

                    msg_dst_mac = sp.in6_getnsmac(msg_dst_ip_net_format)
                    msg_src_mac = '00:16:3e:00:67:01'
                    ns = sp.Ether(dst=msg_dst_mac, src=msg_src_mac) / sp.IPv6(src=msg_src_ip,
                                                                              dst=msg_dst_ip_mul_printable) / sp.ICMPv6ND_NS(
                        tgt=msg_dst_ip) / sp.ICMPv6NDOptSrcLLAddr(lladdr=msg_src_mac)
                    print ns.summary()
                    # ns.show2()

                    print("Do shortcut flooding")
                    for fdpid in self.non_interswitch_ports:
                        fdatapath = self.datapathmap[fdpid]
                        fdata = bytes(ns)
                        fparser = fdatapath.ofproto_parser
                        fofproto = fdatapath.ofproto
                        factions = [fparser.OFPActionOutput(i) for i in list(self.non_interswitch_ports[fdpid])]
                        fout = fparser.OFPPacketOut(datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER,
                                                    in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                        fdatapath.send_msg(fout)

            def check_and_send_icmp(msg_src_ip, ip_dst):
                if ip_dst not in self.ndp_cache_db:
                    print "ip_dst not in cache yet, adding %s to list" % ip_dst
                    flood_with_icmp(msg_src_ip, ip_dst)

            # cache the destination MAC based on the Neighbor Advertisement
            if eth.ethertype == ether_types.ETH_TYPE_IPV6:
                ip = pkt.get_protocols(ipv6.ipv6)[0]
                ip_src = ip.src
                ip_dst = ip.dst
                if ip.nxt == in_proto.IPPROTO_ICMPV6:
                    icmp = pkt.get_protocols(icmpv6.icmpv6)[0]
                    if icmp.type_ == 136:
                        print("NDP Neighbor advertisement")
                        if in_port in self.non_interswitch_ports[
                            dpid] and ip_src not in self.ndp_cache_db:  # cache it and only cache host's info from switch directly connected to the host.
                            self.ndp_cache_db.setdefault(ip_src, {})
                            self.ndp_cache_db[ip_src]['mac'] = eth_src
                            self.ndp_cache_db[ip_src]['dpid'] = dpid
                            self.ndp_cache_db[ip_src]['port'] = in_port
                            print("ndp_cache_db = %s" % self.ndp_cache_db)

                        # checks if there is a sender waiting for a discovery response packet for that inc icmp packet
                        if in_port in self.non_interswitch_ports[dpid] and ip_src in self.responsepacketdict:
                            print "" \
                                  ""
                            print self.responsepacketdict[ip_src][
                                "sender"], " waiting for response packet for: ", ip_src

                            ethernetpacket = mc.make_ether_header("00:16:3e:00:67:01",
                                                                  self.responsepacketdict[ip_src]["sendermac"])
                            r2 = ethernetpacket + mc.create_mc_response_packet("2001:db8::7807",
                                                                               self.responsepacketdict[ip_src][
                                                                                   "sender"], ip_src, 5005,
                                                                               5005, 0)
                            send_response_packet_to_sender(r2, self.responsepacketdict[ip_src]["sender"])

                            # once the discovery response packet has been sent, delete the entry from the responsepacketdict
                            del self.responsepacketdict[ip_src]
                            "print sending response packet to sender"

                            print self.responsepacketdict
                            # just wait a slight time to make sure the sender gets the response packet
                            time.sleep(0.25)

    def add_path_flow(self, path, src_mac, dst_mac):
        for node in path:
            if node != path[
                len(path) - 1]:  # don't install rules on last node, it already has rule from itself to end-point
                print("install rules on node %s" % (node))
                next_node = path[path.index(node) + 1]  # remember, node and next_node are dpid
                out_port = self.net[node][next_node]['port']
                node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                # node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                # node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                # node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
                self.add_flow_with_hard_timeout(node_datapath, 1, node_match, node_action,
                                                self.HARD_TIMEOUT)  # since path may change, so install rule on the switch with hard_timeout.

    def add_path_flow_with_timeout(self, path, dst_mac, timeout):
        for node in path:
            if node != path[
                len(path) - 1]:  # don't install rules on last node, it already has rule from itself to end-point
                print("install rules on node %s" % (node))
                next_node = path[path.index(node) + 1]  # remember, node and next_node are dpid
                out_port = self.net[node][next_node]['port']
                node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                # node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                # node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                # node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(eth_dst=dst_mac)
                self.add_flow_with_hard_timeout(node_datapath, 1, node_match, node_action,
                                                timeout)  # since path may change, so install rule on the switch with hard_timeout.
