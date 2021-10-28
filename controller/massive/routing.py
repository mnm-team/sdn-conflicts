__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '5.0' - 20210614
Adapt to the use of MultiDiGraph of networkx library to encode network topo which allows parallel edges between two vertices.

__version__ = '4.0' - 20201124
Use utility to send add_flow event (FlowMod) to detector, detector will handle the rest: checking for conflicts and installing rules. The old utility is renamed to pureutility.


__version__ = '3.0' - 20201118
Matching based on layer 3, ip_src and ip_dst instead of matching based on layer 2 (MAC address), in order to facilitate the comparison of rules for conflict detection.

__version__ = '2.0' - 20200718

Routing rules are deployed taking in_port into acount.
    + When choosing out_port, it must be different from the in_port. This case can happen when routing app works with other control apps and provide them the routing functions. By comparing in_port and out_port, traffic looping probability is reduced --> less bugs or anomalies. The other path will then be chosen if in_port == out_port, which is not necessarily the shortest path to the destination. Note that, path is not always from end-point to end-point, but can also be from a switch to other switch or to an end-point, the routing app is also responsible for such request.
    + The match field of a rule installed by the routing app always includes the in_port if it is determinable (and seems like it always is, since a packet-in event should always contain the in_port information.)


__version__ = '1.0' - 2019 or earlier

Install flow entries to control ICMP, TCP, UDP traffic explicitly (specifying traffic type in the flow entry) on demand, i.e., when such traffic arises from dataplane and based on shortest path first algorithm of NetworkX library.

Applicable for IPv4, not yet IPv6
'''

from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.lib.packet import in_proto
from ryu.lib.packet import ipv4

import networkx as nx

import logging
import arpcache
import utility_detector as utility
import globalconfig

'''
To run this, you need to install the "networkx" python packet: pip install networkx.
Then at the controller: ryu-manager --observe-links routing.py
and connect your infrastructure to the controller.

This app can be executed together with the existing gui_topology app:
    ryu-manager --observe-links app/gui_topology/gui_topology.py routing.py
and based on the web browser, the rules in each switch, their connections, ports can be observed.

'''


class Routing(arpcache.ARPCache, utility.Utility):  # ARPcache already inherits Topology, Utility sends add_flow event to detector
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Routing, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.DEBUG)
        print("\tbasic routing for ICMP/TCP/UDP based on SPF")
              #shortest path first
        self.count = 1  # to count the number of switch entrance from event switch_enter
        self.cookie = 0x100
        self.HARD_TIMEOUT = 3000  # amount of time (in second) a rule exists in the switch if hard_timeout is set for that rule.
        config = self.parse_config()
        print("config = %s" % config)
        self.priority = config[0]
        self.ei = config[1]
        print("self.excluded_info = %s" % self.ei)

    def parse_config(self):
        priority = None
        ei = [{}, [], {}, [], {}, [], {}, {}, []]
        priority, blp = globalconfig.parseGlobalConfig("routing")
        running_apps = open("routing_excluded_info", "r").readlines() # we expect applist to be in one line
        if len(running_apps):
            running_apps = running_apps[0]
        else:
            running_apps = ""
    
        if "eplb" in running_apps:
            try:
                # get global configs for apps, only need their balance points and priority is ignored
                eplb_priority, eplb_blp =  globalconfig.parseGlobalConfig("eplb")
                # get local config for eplb and add all (ip,mac) tuples of proxy servers
                eplb_local_config = globalconfig.localConfigEPLB()
                eplb_proxies = []
                for proxy_touple,servers in eplb_local_config:
                    eplb_proxies.append(proxy_touple)
                ei[0] = eplb_blp
                ei[1] = eplb_proxies
            except Exception:
                print("No config for eplb or error while trying to load")

        if "pplb4s" in running_apps:
            try:
                pplb4s_priority, pplb4s_blp =  globalconfig.parseGlobalConfig("pplb4s")
                # get local config of pplb4s, servers list contains (ip,mac) tuples
                pplb4s_local_config = json.load(open("pplb4s_config_local","r"))
                ei[3] = globalconfig.localConfigPPLB4s()
                ei[2] = pplb4s_blp
            except Exception:
                print("No config for pplb4s or error while trying to load")

        if "pplb4d" in running_apps:
            try:
                pplb4d_priority, pplb4d_blp =  globalconfig.parseGlobalConfig("pplb4d")
                # get local config of pplb4d, servers list contains (ip,mac) tuples
                pplb4d_local_config = json.load(open("pplb4d_config_local","r"))
                ei[5] = globalconfig.localConfigPPLB4d()
                ei[4] = pplb4d_blp
            except Exception:
                print("No config for pplb4d or error while trying to load")

        if "pe" in running_apps:
            try:
                pe_priority, pe_blp =  globalconfig.parseGlobalConfig("pe")
                pe_blp = globalconfig.localConfigPE(pe_blp)
                ei[6] = pe_blp
            except Exception:
                print("No config for pe or error while trying to load")

        if "hs" in running_apps:
            try:
                hs_priority, hs_blp =  globalconfig.parseGlobalConfig("hs")
                hosts_config = globalconfig.localConfigHS()
                config_list = []
                for k,v in hosts_config:
                    config_list.append(k)
                ei[8] = config_list
                ei[7] = hs_blp
            except Exception:
                print("No config for hs or error while trying to load")

        return [priority, ei]

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def routing_packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        eth_dst = eth.dst
        eth_src = eth.src
        dpid = datapath.id

        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip = pkt.get_protocols(ipv4.ipv4)[0]
            ip_src = ip.src
            ip_dst = ip.dst
            # TODO install a path from source to dst here if there is no exception from shortest path realization, otherwise, install a rule at the switch to drop this for a timeout to save the controller's resource.
            if ip.proto != in_proto.IPPROTO_TCP and ip.proto != in_proto.IPPROTO_UDP and ip.proto != in_proto.IPPROTO_ICMP:  # only handle TCP/UDP/ICMP packets
                return

            if dpid in self.ei[0] and (ip_dst, eth_dst) in self.ei[1] and ip.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]:
                self.logger.debug("is excluded for routing (target eplb), no more processing")
                return
            if dpid in self.ei[2] and (ip_src, eth_src) in self.ei[3] and ip.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]:
                self.logger.debug("is excluded for routing (target pplb4s), no more processing")
                return
            if dpid in self.ei[4] and (ip_dst, eth_dst) in self.ei[5] and ip.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]:
                self.logger.debug("is excluded for routing (target pplb4d), no more processing")
                return
            if dpid in self.ei[6] and (not len(self.ei[6][dpid]["protos"]) or ip.proto in self.ei[6][dpid]["protos"]):
                # if the protos list of the Path Enforcer is empty it will handle all ip traffic
                self.logger.debug("is excluded for routing (target pe), no more processing")
                return
            if dpid in self.ei[7] and ip_dst in self.ei[8] and ip.proto in [in_proto.IPPROTO_UDP, in_proto.IPPROTO_TCP]:
                self.logger.debug("is excluded for routing (target hs), no more processing")
                return
            if ip_src in self.arp_cache_db and ip_dst in self.arp_cache_db and eth_src == self.arp_cache_db[ip_src]['mac'] and eth_dst == self.arp_cache_db[ip_dst]['mac']:
                self.logger.debug(
                    "receive an ip packet with mac src and dst in arp_cache_db, install rule on switch if there is no exception for shortest path, otherwise, drop this message for a predefined timeout")
                try:
                    # from src to dst
                    path = nx.shortest_path(self.net, self.arp_cache_db[
                                            ip_src]['dpid'], self.arp_cache_db[ip_dst]['dpid'])
                    if dpid in path:
                        # eth_src, eth_dst,ip.proto) #this shadows the SBEpLB
                        # app. so install in each node instead.
                        if dpid != path[len(path) - 1]:  # last node should be treated specially, since it connects to an end-point, not another switch
                            self.logger.debug("install rules on node %s", dpid)
                            next_node = path[
                                path.index(dpid) + 1]  # remember, node and next_node are dpid
                            out_port = self.get_out_port_for_link(dpid,next_node)
                            if (out_port == in_port):
                                out_port = self.choose_alternative_outport(
                                    dpid, self.arp_cache_db[ip_dst]['dpid'], out_port)
                            node_action = [parser.OFPActionOutput(out_port)]

                            data = msg.data
                            out = parser.OFPPacketOut(
                                datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER, in_port=datapath.ofproto.OFPP_CONTROLLER, actions=node_action, data=data)
                            datapath.send_msg(out)

                            node_match = parser.OFPMatch(
                                in_port=in_port, eth_type=ether_types.ETH_TYPE_IP, ip_proto=ip.proto, ipv4_src=ip_src, ipv4_dst=ip_dst) 
                            self.add_flow_with_hard_timeout(
                                self.cookie, datapath, self.priority, node_match, node_action, self.HARD_TIMEOUT)  # since path may change, so install rule on the switch with hard_timeout.
                        else:  # last node
                            self.logger.debug(
                                "install rules on last node of the path, node %s", dpid)
                            out_port = None
                            for i in self.arp_cache_db:
                                if self.arp_cache_db[i]['mac'] == eth_dst:
                                    out_port = self.arp_cache_db[i]['port']
                                    break
                            action = [parser.OFPActionOutput(out_port)]

                            data = msg.data
                            out = parser.OFPPacketOut(
                                datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER, in_port=datapath.ofproto.OFPP_CONTROLLER, actions=action, data=data)
                            datapath.send_msg(out)

                            match = parser.OFPMatch(
                                in_port=in_port, eth_type=ether_types.ETH_TYPE_IP, ip_proto=ip.proto,  ipv4_dst=ip_dst) 
                            self.add_flow_with_hard_timeout(
                                self.cookie, datapath, self.priority, match, action, self.HARD_TIMEOUT)
                    else:  # the asking switch is not on the path, install a rule with a matching on destination only
                        path = nx.shortest_path(
                            self.net, dpid, self.arp_cache_db[ip_dst]['dpid'])
                        self.logger.debug("path=%s" % path)
                        if dpid != path[len(path) - 1]:  # last node should be treated specially, since it connects to an end-point, not another switch
                            self.logger.debug("install rules on node %s", dpid)
                            next_node = path[
                                path.index(dpid) + 1]  # remember, node and next_node are dpid
                            out_port = self.get_out_port_for_link(dpid, next_node)
                            if (out_port == in_port):
                                out_port = self.choose_alternative_outport(
                                    dpid, self.arp_cache_db[ip_dst]['dpid'], out_port)
                            node_action = [parser.OFPActionOutput(out_port)]

                            data = msg.data
                            out = parser.OFPPacketOut(
                                datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER, in_port=datapath.ofproto.OFPP_CONTROLLER, actions=node_action, data=data)
                            datapath.send_msg(out)

                            node_match = parser.OFPMatch(
                                in_port=in_port, eth_type=ether_types.ETH_TYPE_IP, ip_proto=ip.proto, ipv4_src=ip_src, ipv4_dst=ip_dst) 
                            self.add_flow_with_hard_timeout(
                                self.cookie, datapath, self.priority, node_match, node_action, self.HARD_TIMEOUT)  # since path may change, so install rule on the switch with hard_timeout.
                        else:  # last node
                            self.logger.debug(
                                "install rules on last node of the path, node %s", dpid)
                            out_port = None
                            for i in self.arp_cache_db:
                                if self.arp_cache_db[i]['mac'] == eth_dst:
                                    out_port = self.arp_cache_db[i]['port']
                                    break
                            action = [parser.OFPActionOutput(out_port)]

                            data = msg.data
                            out = parser.OFPPacketOut(
                                datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER, in_port=datapath.ofproto.OFPP_CONTROLLER, actions=action, data=data)
                            datapath.send_msg(out)

                            match = parser.OFPMatch(
                                in_port=in_port, eth_type=ether_types.ETH_TYPE_IP, ip_proto=ip.proto, ipv4_dst=ip_dst) 
                            self.add_flow_with_hard_timeout(
                                self.cookie, datapath, self.priority, match, action, self.HARD_TIMEOUT)

                except nx.NetworkXNoPath:
                    self.logger.debug(
                        "There is no path, install a drop rule to stop this switch from bother the controller for a while ")
                    match = parser.OFPMatch(
                        in_port=in_port, ipv4_src=ip_src, ipv4_dst=ip_dst, eth_type=ether_types.ETH_TYPE_IP, ip_proto=ip.proto)
                    action = []  # empty action means drop
                    '''install drop rule for this packet for 10 seconds at the asking switch'''
                    self.add_flow_with_hard_timeout(
                        self.cookie, datapath, self.priority, match, action, 10)  # timeout = 10s

            # else: #should this app actively detect the mapping between ip and
            # mac, so the controller receive an ip packet whose information is
            # not in arp_cache_db, if it does not actively perform discovery
            # (do shorcut flood), it will continuously receive this message
            # until an arp_request comes. But if it does the shortcut flood
            # every time such an ip packet comes, it may overwhelm the
            # end-points, there may be weird ip packet with destination is not
            # within this sdn network, so better not do active discovery.
            else:  # this else is different from version 4.0
                self.logger.debug(
                    "actively detect destination by sending shortcut ARP request")

                arp_req = packet.Packet()
                arp_req.add_protocol(ethernet.ethernet(
                    ethertype=ether_types.ETH_TYPE_ARP, dst='ff:ff:ff:ff:ff:ff', src=eth_src))
                arp_req.add_protocol(arp.arp(
                    opcode=arp.ARP_REQUEST, src_mac=eth_src, dst_mac='00:00:00:00:00:00',
                    src_ip=ip_src, dst_ip=ip_dst))
                arp_req.serialize()

                for fdpid in self.non_interswitch_ports:  # flood datapath id --> fdpid
                    fdatapath = self.datapathmap[fdpid]
                    fdata = arp_req.data
                    fparser = fdatapath.ofproto_parser
                    fofproto = fdatapath.ofproto
                    factions = [fparser.OFPActionOutput(i)
                                for i in list(self.non_interswitch_ports[fdpid])]
                    fout = fparser.OFPPacketOut(
                        datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER, in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                    fdatapath.send_msg(fout)
