__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '1.0'

'''
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER

from ryu.topology import event

import networkx as nx
#import utility as ut
import utility

'''
This app builds the topology based on LLDP (observe-links option of ryu-manager) and encodes that in networkx DiGraph (directed graph).
Aims at providing the basic reference for other apps that require routing function, or need to be aware of the network topology.
Also the common add_path_flow_xxx that requires the prior knowledge of topology
'''

class Topology(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Topology, self).__init__(*args, **kwargs)
        print(" \t Topology class")
        self.count = 1 # to count the number of switch entrance from event switch_enter
        self.cookie = 0x10 #cookie to identify a rule installed by which app.

        ''' Shortest path first routing/switching '''
        self.net = nx.DiGraph()

        #a dictionary data structure: {SW_datapath_id, set([all switch ports])}
        self.all_switch_ports = {} # \\XXX not optimized because this includes the DOWN ports, which should be seperated from the LIVE ports.
        #a dictionary data structure: {SW_datapath_id, set([non inter-switch ports])}
        self.non_interswitch_ports = {}
        #a dictionary data structure: {SW_datapath_id, set([inter-switch ports])}
        self.interswitch_ports = {}

	#a dictionary data structure: {dpid: datapath}
	self.datapathmap = {}


# Handy function that lists all attributes in the given object

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def topology_switch_features_handler(self, ev):
	print("\nTopology switch features handler")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()

        '''add default rule, "forward to controller" to the switch '''
        print("Add default rule, \"forward to controller\" in switch:"),
        print(datapath.id)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        utility.add_flow(self.cookie, datapath, 0, match, actions)
	self.datapathmap[datapath.id] = datapath

    @set_ev_cls(event.EventSwitchEnter)
    def topology_handler_switch_enter(self, ev):
        print(" " + str(self.count) + " -- Switch: "),
	self.logger.info("switch is entering")
        print(ev.switch)
        dpid = ev.switch.dp.id
        print("ev.switch.dp.id="),
        print(dpid)

        self.all_switch_ports.setdefault(dpid,set())

        print("ev.switch.ports = %s"% ev.switch.ports)
        for port in ev.switch.ports:
            self.all_switch_ports[dpid].add(port.port_no)
        print("self.all_switch_ports = "),
        print(self.all_switch_ports)
        self.count += 1
    
    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def topology_handler_switch_leave(self, ev):
        dpid = ev.switch.dp.id
	print("switch is leaving!")
        self.logger.info("Not tracking Switche %s anymore, switch %s leaved.", dpid, dpid)
        #delete the corresponding entries in arp_cache_db and all_interswitch_ports, interswitch_ports and non_interswitch_ports
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
    def topology_handler_link_add(self, ev):
        self.logger.info("link is added")
        print(ev)
#        self.ls(ev.link)
        self.interswitch_ports.setdefault(ev.link.src.dpid,set())
        self.interswitch_ports[ev.link.src.dpid].add(ev.link.src.port_no)
        self.non_interswitch_ports.setdefault(ev.link.src.dpid,set())
        self.non_interswitch_ports[ev.link.src.dpid] = self.all_switch_ports[ev.link.src.dpid]-self.interswitch_ports[ev.link.src.dpid]
        self.net.add_edges_from([(ev.link.src.dpid, ev.link.dst.dpid, {'port':ev.link.src.port_no})])
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        print("self.non_interswitch_ports = %s" %self.non_interswitch_ports)
        print("self.interswitch_ports = %s" %self.interswitch_ports)

    @set_ev_cls(event.EventLinkDelete, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def appsuite_handler_link_delete(self, ev):
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
            #datapath = api.get_datapath(self, ev.link.src.dpid) from appsuite_v1_0
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


    def add_path_flow_layer4(self, path, src_mac, dst_mac, ipproto):#ip_proto should be TCP/UDP
        '''This function is customized to install flow entries matching only ARP/ICMP packets '''
        for node in path:
            if node != path[len(path)-1]:#don't install rules on last node, it already has rule from itself to end-point
                print("install rules on node %s" % (node) )
                next_node = path[path.index(node)+1]#remember, node and next_node are dpid
                out_port = self.net[node][next_node]['port']
                #node_datapath = api.get_datapath(self, node) from appsuite_v1_0
		node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                #node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                #node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                #node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=ipproto,eth_src=src_mac, eth_dst=dst_mac)
                utility.add_flow_with_hard_timeout(self.cookie, node_datapath, 1, node_match, node_action, self.HARD_TIMEOUT) #since path may change, so install rule on the switch with hard_timeout.
            else:
                print("install rules on last node of the path, node %s" %(node))
                out_port = None
                for ip in self.arp_cache_db:
                    if self.arp_cache_db[ip]['mac'] == dst_mac:
                        out_port = self.arp_cache_db[ip]['port']
                        break
                datapath = self.datapathmap[node]
                parser = datapath.ofproto_parser
                action = [parser.OFPActionOutput(out_port)]
                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=ipproto,eth_src=src_mac,eth_dst=dst_mac)
                utility.add_flow_with_hard_timeout(self.cookie, datapath,1,match,action,self.HARD_TIMEOUT)

    def add_path_flow_layer4_with_timeout(self, path, dst_mac, ipproto, timeout):
        '''This function is customized to install flow entries matching layer 4 packets(TCP/UDP) '''
        for node in path:
            if node != path[len(path)-1]:#don't install rules on last node, it already has rule from itself to end-point
                print("install rules on node %s" % (node) )
                next_node = path[path.index(node)+1]#remember, node and next_node are dpid
                out_port = self.net[node][next_node]['port']
                #node_datapath = api.get_datapath(self, node) from appsuite_v1_0
		node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                #node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                #node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                #node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP,eth_dst=dst_mac)
                utility.add_flow_with_hard_timeout(self.cookie, node_datapath, 1, node_match, node_action, timeout) #since path may change, so install rule on the switch with hard_timeout.
                node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=ipproto,eth_dst=dst_mac)
                utility.add_flow_with_hard_timeout(self.cookie, node_datapath, 1, node_match, node_action, timeout) #since path may change, so install rule on the switch with hard_timeout.

#    def add_path_flow_with_timeout(self, path, cookie, priority, match, action, timeout):
#        '''  not yet finish '''
#        for node in path:
#            if node != path[len(path)-1]:#don't install rules on last node, it already has rule from itself to end-point
#                print("install rules on node %s" % (node) )
#                next_node = path[path.index(node)+1]#remember, node and next_node are dpid
#                out_port = self.net[node][next_node]['port']
#                #node_datapath = api.get_datapath(self, node) from appsuite_v1_0
#		node_datapath = self.datapathmap[node]
#                node_parser = node_datapath.ofproto_parser
#                #node_proto = node_datapath.ofproto
#                node_action = [node_parser.OFPActionOutput(out_port)]
#                #node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
#                #node_datapath.send_msg(node_out)
#                node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP,eth_dst=dst_mac)
#                utility.add_flow_with_hard_timeout(self.cookie, node_datapath, 1, node_match, node_action, timeout) #since path may change, so install rule on the switch with hard_timeout.
#                node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=ipproto,eth_dst=dst_mac)
#                utility.add_flow_with_hard_timeout(self.cookie, node_datapath, 1, node_match, node_action, timeout) #since path may change, so install rule on the switch with hard_timeout.
