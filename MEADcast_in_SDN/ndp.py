__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '1.0'
NDP: Neighbor discovery protocol, "ARP for IPv6"

TODO: 
'''

'''
Bug: 

'''
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import in_proto
from ryu.lib.packet import lldp
from ryu.lib.packet import ipv6
from ryu.lib.packet import icmpv6

from ryu.topology import event

import networkx as nx

from scapy import all as sp

'''
This app can be executed together with the existing gui_topology app:

'''

class ndp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ndp, self).__init__(*args, **kwargs)
        print(" \t Cuong Dai Ca")
        self.count = 1 # to count the number of switch entrance from event switch_enter
        self.HARD_TIMEOUT = 3000 # amount of time (in second) a rule exists in the switch if hard_timeout is set for that rule.

#        self.topology_api_app = data['topology_api_app']
        ''' Shortest path first routing/switching '''
        self.net = nx.DiGraph()

        '''Learning Switch'''
        self.mac_to_port = {}
        
        ''' Cache NDP''' 
        #a dictionary data structure: {SW_datapath_id, set([all switch ports])}
        self.all_switch_ports = {} # \\XXX not optimized because this includes the DOWN ports, which should be seperated from the LIVE ports.
        #a dictionary data structure: {SW_datapath_id, set([non inter-switch ports])}
        self.non_interswitch_ports = {}
        #a dictionary data structure: {SW_datapath_id, set([inter-switch ports])}
        self.interswitch_ports = {}

        #a dictionary data structure: IP, MAC, SW datapath_id, port
        #{IP:{'mac':'x', 'dpid':y, 'port':[a,b,c]}}
        self.ndp_cache_db = {}

	#a dictionary data structure: {dpid: datapath}
	self.datapathmap = {}

# Handy function that lists all attributes in the given object
    def ls(self,obj):
        print("\n".join([x for x in dir(obj) if x[0] != "_"]))

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto=datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                    priority=priority, match=match, instructions=inst)
        else:
            mod=parser.OFPFlowMod(datapath=datapath, priority=priority,
                    match=match, instructions=inst)
        datapath.send_msg(mod)

#    def add_flow_with_hard_timeout(self, datapath, priority, match, actions, buffer_id=None, hard_timeout):
    def add_flow_with_hard_timeout(self, datapath, priority, match, actions, hard_timeout):
        ofproto=datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        #if buffer_id:
        #    mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, buffer_id=buffer_id,
        #            priority=priority, match=match, instructions=inst)
        #else:
        mod=parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, priority=priority,
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

    @set_ev_cls(event.EventSwitchEnter)
    def ndp_handler_switch_enter(self, ev):
        print(" " + str(self.count) + " -- Switch: "),
	self.logger.info("switch is entering")
        print(ev.switch)
        print("ndp_cache_db = %s" %self.ndp_cache_db)
        dpid = ev.switch.dp.id
        print("ev.switch.dp.id="),
        print(dpid)

        self.all_switch_ports.setdefault(dpid,set())

        print("ev.switch.ports = %s"% ev.switch.ports)
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
        self.logger.info("Not tracking Switch %s anymore, switch %s leaved.", dpid, dpid)
        #delete the corresponding entries in ndp_cache_db and all_interswitch_ports, interswitch_ports and non_interswitch_ports
        for i in self.ndp_cache_db:
            #print(self.ndp_cache_db[i]['dpid'])
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
        print("self.non_interswitch_ports = %s" %self.non_interswitch_ports)
        # update self.net: links and nodes:
        self.net.remove_node(dpid)
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())

    #TODO update rules at switch for shortest path switching
    @set_ev_cls(event.EventLinkAdd, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def ndp_handler_link_add(self, ev):
        self.logger.info("link is added")
        print(ev)
#        self.ls(ev.link)
        self.interswitch_ports.setdefault(ev.link.src.dpid,set())
        self.interswitch_ports[ev.link.src.dpid].add(ev.link.src.port_no)
        self.non_interswitch_ports.setdefault(ev.link.src.dpid,set())
        self.non_interswitch_ports[ev.link.src.dpid] = self.all_switch_ports[ev.link.src.dpid]-self.interswitch_ports[ev.link.src.dpid]

#        link = [(ev.link.src.dpid, ev.link.dst.dpid,{'port':link.src.port_no})]
#        self.net.add_edges_from(link)
        self.net.add_edges_from([(ev.link.src.dpid, ev.link.dst.dpid, {'port':ev.link.src.port_no})])
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        print("self.non_interswitch_ports = %s" %self.non_interswitch_ports)
        print("self.interswitch_ports = %s" %self.interswitch_ports)

    @set_ev_cls(event.EventLinkDelete, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def ndp_handler_link_delete(self, ev):
        self.logger.info("link is deleted")
        print(ev)
        try:
            self.net.remove_edge(ev.link.src.dpid, ev.link.dst.dpid)
        except nx.NetworkXError:
            print("there is no such edge in the graph")
        #if ev.link.src.dpid in self.interswitch_ports and 
        try:
            if ev.link.src.port_no in self.interswitch_ports[ev.link.src.dpid]:
                self.interswitch_ports[ev.link.src.dpid].remove(ev.link.src.port_no)
            #if ev.link.src.dpid in self.non_interswitch_ports:
            if ev.link.src.port_no in self.non_interswitch_ports[ev.link.src.dpid]:
                self.non_interswitch_ports[ev.link.src.dpid].remove(ev.link.src.port_no)
        except KeyError:
            print("Keyerror: already deleted.")
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        print("self.non_interswitch_ports = %s" %self.non_interswitch_ports)
        print("self.interswitch_ports = %s" %self.interswitch_ports)

        #update rules at switch for shortest path switching
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
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        
        scapy_pkt = sp.Ether(msg.data)
        #print scapy_pkt.summary()
        #if scapy_pkt.haslayer(sp.Raw):
        #    print scapy_pkt.getlayer(sp.Raw).load
        eth_src = scapy_pkt.getlayer(sp.Ether).src
        eth_dst = scapy_pkt.getlayer(sp.Ether).dst
        #print("mac src = %s, dst = %s"%(eth_src, eth_dst))

        if scapy_pkt.haslayer(sp.IPv6ExtHdrRouting):
            pass

        #return 


        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        eth_dst = eth.dst
        eth_src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

#        self.ndp_cache_db.setdefault()

       #if eth_dst != "01:80:c2:00:00:00": #LLDP messages for topology discover are sent to controller all the time
        if eth_dst == lldp.LLDP_MAC_NEAREST_BRIDGE: #LLDP messages for topology discover are sent to controller all the time
            return
        else:
            #self.logger.info("\npacket in dpid: %s, src: %s, dst: %s, in_port: %s", dpid, eth_src, eth_dst, in_port)
            print("\nndp packet in dpid: %s, src: %s, dst: %s, in_port: %s" %(dpid, eth_src, eth_dst, in_port) )
            print("self.ndp_cache_db = %s" % self.ndp_cache_db)
            scapy_pkt = sp.Ether(msg.data)
            print("SCAPY")
            print scapy_pkt.summary()
            if scapy_pkt.haslayer(sp.Raw):
                print scapy_pkt.getlayer(sp.Raw).load

        # learn a mac address to avoid "shortcut" FLOOD next time.
        self.mac_to_port[dpid][eth_src] = in_port

        if eth_dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][eth_dst]
        else: 
            #do "shortcut" FLOOD here, i.e., flood the packet directly on non_interswitch_ports, omit the rest
            out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]
        data = msg.data
        #data = None
        out = parser.OFPPacketOut(datapath=datapath, buffer_id = msg.buffer_id,
                in_port=in_port, actions=actions, data=data)
        #datapath.send_msg(out)
        #print("send packet_out, out_port = %s" % out_port)
        '''
        The above 2 lines (mainly the first line) will cause the controller to misunderstand the network topology since for each LLDP message sent by controller to discover the network topology, a PacketIn event is generated and caused the controller to send a PacketOut, too many of them together with the LLDP in and out congest the channel between the controller and the switches, many LLDP packets will then be lost, as a result the controller just thinks that a link is down.
        Or no, the link may be actually overloaded since for each LLDP message, the action installed is to flood it. This triggers the event link-down/link-up repeatedly.
        '''

        ip_src = None
        ip_dst = None
        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            ip = pkt.get_protocols(ipv6.ipv6)
            print("ip = "),
            print(ip)
            ip_src = ip[0].src
            ip_dst = ip[0].dst
            print("ip src = %s, ip dst = %s" %(ip_src, ip_dst))
            if ip[0].nxt == in_proto.IPPROTO_ICMPV6:
                print("ICMPv6 packet")
                icmp = pkt.get_protocols(icmpv6.icmpv6)[0]
                print("icmp = %s"%icmp)
                if icmp.type_ == 135:
                    print("NDP Neighbor solicitation")
                    print("requested dst = %s " % icmp.data.dst)
                    if in_port in self.non_interswitch_ports[dpid] and ip_src not in self.ndp_cache_db: #cache it and only cache host's info from switch directly connected to the host.
                        self.ndp_cache_db.setdefault(ip_src,{})
                        self.ndp_cache_db[ip_src]['mac'] = eth_src
                        self.ndp_cache_db[ip_src]['dpid'] = dpid
                        self.ndp_cache_db[ip_src]['port'] = in_port
                        print("ndp_cache_db = %s" % self.ndp_cache_db)
                        #install rules for the switch responsible for a host based on in_port.
                        actions = [parser.OFPActionOutput(in_port)]
                        match = parser.OFPMatch(eth_dst=eth_src)
                        self.add_flow(datapath, 1, match, actions)
                    if icmp.data.dst not in self.ndp_cache_db: #do shorcut FLOOD
                        print("dst ip not in cache")
                        for fdpid in self.non_interswitch_ports:
                            if fdpid != dpid:
                                fdatapath = self.datapathmap[fdpid]
                                fdata = msg.data
                                fparser = fdatapath.ofproto_parser
                                fofproto = fdatapath.ofproto
                                factions = [fparser.OFPActionOutput(i) for i in list(self.non_interswitch_ports[fdpid])]
                                fout = fparser.OFPPacketOut(datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER,in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                                fdatapath.send_msg(fout)
                            else:#
                                factions = None
                                for i in list(self.non_interswitch_ports[dpid]):
                                    if i != in_port:#do not forward to in_port
                                        factions = [parser.OFPActionOutput(i)]
                                        # print("factions = %s, dpid = %s" % (factions, dpid))
                                if factions != None:
                                    fdata = None
                                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                                        fdata = msg.data
                                    fout = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=ofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                                    datapath.send_msg(fout)
                    else:
                        #TODO: build response message (neighbor advertisement) and reply to the asked host.
                        pass

                elif icmp.type_ == 136:
                    print("NDP Neighbor advertisement")
                    if in_port in self.non_interswitch_ports[dpid] and ip_src not in self.ndp_cache_db: #cache it and only cache host's info from switch directly connected to the host.
                        self.ndp_cache_db.setdefault(ip_src,{})
                        self.ndp_cache_db[ip_src]['mac'] = eth_src
                        self.ndp_cache_db[ip_src]['dpid'] = dpid
                        self.ndp_cache_db[ip_src]['port'] = in_port
                        print("ndp_cache_db = %s" % self.ndp_cache_db)
                        #install rules for the switch responsible for a host based on in_port.
                        actions = [parser.OFPActionOutput(in_port)]
                        match = parser.OFPMatch(eth_dst=eth_src)
                        self.add_flow(datapath, 1, match, actions)
                    try:
		        supposed_shortest_path = nx.shortest_path(self.net, self.ndp_cache_db[ip_src]['dpid'], self.ndp_cache_db[ip_dst]['dpid'])
		        if dpid in supposed_shortest_path:
		            print("path from %s to %s is: %s" %(ip_src, ip_dst, supposed_shortest_path))
		            self.add_path_flow(supposed_shortest_path, eth_src, eth_dst)
                            print("install reverse path:")
                            path = nx.shortest_path(self.net, self.ndp_cache_db[ip_dst]['dpid'], self.ndp_cache_db[ip_src]['dpid'])
                       	    self.add_path_flow(path, eth_dst, eth_src)
                    except nx.NetworkXNoPath:
                        print("There is no path")
                    #handle current packet sent to the controller by PacketOut:
                    dest_dpid = self.ndp_cache_db[ip_dst]['dpid']
                    dest_datapath = self.datapathmap[dest_dpid]
                    dest_parser = dest_datapath.ofproto_parser
                    dest_action = [dest_parser.OFPActionOutput(self.ndp_cache_db[ip_dst]['port'])]
                    dest_data = msg.data
                    dest_out = dest_parser.OFPPacketOut(datapath=dest_datapath, buffer_id=dest_datapath.ofproto.OFP_NO_BUFFER, in_port=dest_datapath.ofproto.OFPP_CONTROLLER , actions=dest_action, data=dest_data)
                    dest_datapath.send_msg(dest_out)
                    print("send neighbor advertisement directly to the destination")


    def add_path_flow(self, path, src_mac, dst_mac):
        for node in path:
            if node != path[len(path)-1]:#don't install rules on last node, it already has rule from itself to end-point
                print("install rules on node %s" % (node) )
                next_node = path[path.index(node)+1]#remember, node and next_node are dpid
                out_port = self.net[node][next_node]['port']
		node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                #node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                #node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                #node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
                self.add_flow_with_hard_timeout(node_datapath, 1, node_match, node_action, self.HARD_TIMEOUT) #since path may change, so install rule on the switch with hard_timeout.

    def add_path_flow_with_timeout(self, path, dst_mac, timeout):
        for node in path:
            if node != path[len(path)-1]:#don't install rules on last node, it already has rule from itself to end-point
                print("install rules on node %s" % (node) )
                next_node = path[path.index(node)+1]#remember, node and next_node are dpid
                out_port = self.net[node][next_node]['port']
		node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                #node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                #node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                #node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(eth_dst=dst_mac)
                self.add_flow_with_hard_timeout(node_datapath, 1, node_match, node_action, timeout) #since path may change, so install rule on the switch with hard_timeout.
