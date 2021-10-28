__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '2.0' 20210613
Using Multi Directed Graph of networkx library to maintain the network topology. Compared to version 1.0 using (Single) Directed Graph, the use of Multi Directed Graph allows multiple parallel edges to exist between a pair of vertices. In practice, these multiple parallel edges exist to provide redundancy/backup in case one link fails, or to increase bandwidth, or to perform Load Balancing over multiple paths...

__version__ = '1.0' 2018...
Using Directed Graph of networkx library to maintain the network topology.

'''
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER

from ryu.topology import event

import networkx as nx
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
        self.count = 1  # to count the number of switch entrance from event switch_enter
        self.cookie = 0x10  # cookie to identify a rule installed by which app.

        ''' Shortest path first routing/switching '''
        self.net = nx.MultiDiGraph()
        # self.net[vertex1][vertex2] = AtlasView({0: {'port': (srcport1, dstport1)}, 1: {'port': (srcport2, dstport2)}, 2: {'port': (srcport3, dstport3),...}})
        #self.net = nx.DiGraph()

        # a dictionary data structure: {SW_datapath_id, set([all switch ports])}
        self.all_switch_ports = {}
        # XXX not optimized because this includes the DOWN ports, which should be seperated from the LIVE ports.
        # a dictionary data structure: {SW_datapath_id, set([non inter-switch-ports])}
        self.non_interswitch_ports = {}
        # a dictionary data structure: {SW_datapath_id, set([inter-switch-ports])}
        self.interswitch_ports = {}
        # a dictionary data structure: {dpid: datapath}
        self.datapathmap = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def topo_switch_features_handler(self, ev):
        print("\nTopology switch features handler")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()

        '''add default rule, "forward to controller" to the switch '''
        print("Add default rule, \"forward to controller\" in switch: %s"%(datapath.id))
        #print(datapath.id)
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        # utility.add_flow(self.cookie, datapath, 0, match, actions)
        utility.add_flow(0x10, datapath, 0, match, actions)
        #self.add_flow(0x10, datapath, 1, match, actions)
        
        self.datapathmap[datapath.id] = datapath

    @set_ev_cls(event.EventSwitchEnter)
    def topo_switch_enter_handler(self, ev):
        #print(" " + str(self.count) + " -- Switch: "),
        #self.logger.info("switch is entering")
        #print(ev.switch)
        dpid = ev.switch.dp.id
        #print("ev.switch.dp.id=",end='')
        #print(dpid)

        self.all_switch_ports.setdefault(dpid, set())

        #print("ev.switch.ports = %s" % ev.switch.ports)
        for port in ev.switch.ports:
            self.all_switch_ports[dpid].add(port.port_no)
        print("self.all_switch_ports = %s"%self.all_switch_ports)
        #print(self.all_switch_ports)
        self.count += 1

    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def topo_switch_leave_handler(self, ev):
        dpid = ev.switch.dp.id
        print("switch is leaving!")
        self.logger.info(
            "Not tracking Switche %s anymore, switch %s leaved.", dpid, dpid)
        # delete the corresponding entries in arp_cache_db and
        # all_interswitch_ports, interswitch_ports and non_interswitch_ports
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
    def topo_link_add_handler(self, ev):
        #self.logger.info("link is added")
        #print(ev)
        #self.ls(ev.link)
        self.interswitch_ports.setdefault(ev.link.src.dpid, set())
        self.interswitch_ports[ev.link.src.dpid].add(ev.link.src.port_no)
        self.non_interswitch_ports.setdefault(ev.link.src.dpid, set())
        self.non_interswitch_ports[ev.link.src.dpid] = self.all_switch_ports[
            ev.link.src.dpid] - self.interswitch_ports[ev.link.src.dpid]
        self.net.add_edges_from(
            [(ev.link.src.dpid, ev.link.dst.dpid, {'port': (ev.link.src.port_no,ev.link.dst.port_no)})])
        print("self.net.nodes() = %s " % self.net.nodes())
        #print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        #print("self.non_interswitch_ports = %s" % self.non_interswitch_ports)
        #print("self.interswitch_ports = %s" % self.interswitch_ports)

    @set_ev_cls(event.EventLinkDelete, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def topo_link_delete_handler(self, ev):
        self.logger.info("link is deleted")
        print(ev)
        try:
            self.net.remove_edge(ev.link.src.dpid, ev.link.dst.dpid)
        except nx.NetworkXError:
            print("there is no such edge in the graph")
        # if ev.link.src.dpid in self.interswitch_ports and
        try:
            if ev.link.src.port_no in self.interswitch_ports[ev.link.src.dpid]:
                self.interswitch_ports[
                    ev.link.src.dpid].remove(ev.link.src.port_no)
            # if ev.link.src.dpid in self.non_interswitch_ports:
            if ev.link.src.port_no in self.non_interswitch_ports[ev.link.src.dpid]:
                self.non_interswitch_ports[
                    ev.link.src.dpid].remove(ev.link.src.port_no)
        except KeyError:
            print("Keyerror: already deleted.")
        print("self.net.nodes() = %s " % self.net.nodes())
        print("self.net.edges() = %s" % self.net.edges())
        print("Number of edges = %s" % self.net.number_of_edges())
        print("self.non_interswitch_ports = %s" % self.non_interswitch_ports)
        print("self.interswitch_ports = %s" % self.interswitch_ports)

        # TODO update rules at switch for shortest path switching
        try:
            # datapath = api.get_datapath(self, ev.link.src.dpid) from
            datapath = self.datapathmap[ev.link.src.dpid]
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch()
            # delete current rules in the switches
            mod = parser.OFPFlowMod(
                datapath=datapath, command=ofproto.OFPFC_DELETE, out_port=ev.link.src.port_no,
                    out_group=ofproto.OFPG_ANY, match=match)
            print("\nDelete existing rules in switch: %s"%ev.link.src.dpid)
            #print(ev.link.src.dpid)
            datapath.send_msg(mod)
        except AttributeError:
            print("NoneType: no such datapath")
        except KeyError:
            print("KeyError: no such key in datapathmap")


    def get_out_port_for_link(self, dpid, target_dpid):
        out_port = None
        for va in self.net[dpid][target_dpid].values():#value, adapt to the use of MultiDiGraph
            out_port = va['port'][0]
            break
        return out_port


    def choose_alternative_outport(self, dpid, target_dpid, port):
        '''
        the port (output port chosen by shortest path first algorithm from dpid to target) is the same as the in_port of the packet in the packet-in event from the device dpid, so have to choose an alternative output port
        '''
        out_port = -1
        for path in sorted(nx.all_simple_paths(self.net, dpid, target_dpid), key=lambda x: len(x)):
            # path is sorted by its length, i.e., the number of traversed nodes
            print(path)
            next_node = path[path.index(dpid) + 1]
            out_port = self.get_out_port_for_link(dpid, next_node)
            if out_port == port:
                continue  # move to the next path since this path has the same out_port
            else:
                break
        if (out_port == -1 or out_port == port):
            self.logger.error(
                "ERROR: outport is always equal to in_port! Traffic loop occurs likely! dpid = %s, port = %s", dpid, port)
        return out_port
