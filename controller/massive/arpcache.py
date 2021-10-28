__author__ = 'Cuong Tran'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '2.0' 20210614
Adapt version 1.0 to the use of MultiDiGraph network topo of networkx library. Version 1.0 used DiGraph to encode networks that does not allow parallel edges between two vertices.


__version__ = '1.0' 2018...

Build ARP cache (simple, no timeout to update ARP and assuming that there's no ARP spoofing attack)
and install route, flows for arp messages.

'''

from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp

from ryu.topology import event

import networkx as nx

import topology
import utility

'''
To run this, you need to install the "networkx" python packet: pip install networkx.
Then at the controller: ryu-manager --observe-links arpcache.py
and connect your infrastructure to the controller.

This app can be executed together with the existing gui_topology app:
    ryu-manager --observe-links app/gui_topology/gui_topology.py appsuite.py
and based on the web browser, the rules in each switch, their connections, ports can be observed.

'''


class ARPCache(topology.Topology):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ARPCache, self).__init__(*args, **kwargs)
        print(" \tARP cache")
        self.count = 1  # to count the number of switch entrance from event switch_enter
        self.cookie = 0x11
        self.HARD_TIMEOUT = 3000  # amount of time (in second) a rule exists in the switch if hard_timeout is set for that rule.
        self.controller_mac = '00:16:3e:00:00:01'
        self.controller_ip = '192.168.0.253'

        ''' Cache ARP'''
        # a dictionary data structure: IP, MAC, SW datapath_id, port
        #{IP:{'mac':'x', 'dpid':y, 'port':z}}
        self.arp_cache_db = {}

    @set_ev_cls(event.EventSwitchLeave, [MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def arp_handler_switch_leave(self, ev):
        dpid = ev.switch.dp.id
        # delete the corresponding entries in arp_cache_db and
        # all_interswitch_ports, interswitch_ports and non_interswitch_ports
        for i in self.arp_cache_db:
            # print(self.arp_cache_db[i]['dpid'])
            if self.arp_cache_db[i]['dpid'] == dpid:
                print("delete switch %s out of arp_cache_db" % dpid)
                del self.arp_cache_db[i]
                break
        print("self.arp_cache_db = ", end='')
        print(self.arp_cache_db)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def arp_packet_in_handler(self, ev):
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

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            # arp_cache application comes here:
            arp_msg = pkt.get_protocols(arp.arp)[0]
            self.logger.debug("arp_msg =\n %s", arp_msg)
            try:
                if in_port not in self.non_interswitch_ports[dpid]:  # only cache host's info from switch directly connected to the host.
                    pass
               # return
                if in_port in self.non_interswitch_ports[dpid] and arp_msg.src_ip not in self.arp_cache_db:  # cache it and only cache host's info from switch directly connected to the host.

                    self.arp_cache_db.setdefault(arp_msg.src_ip, {})
                    self.arp_cache_db[arp_msg.src_ip]['mac'] = arp_msg.src_mac
                    self.arp_cache_db[arp_msg.src_ip]['dpid'] = dpid
                    self.arp_cache_db[arp_msg.src_ip]['port'] = in_port
                    self.logger.debug("arp_cache_db =\n %s", self.arp_cache_db)
                    # install forwarding rule for the asked switch. Note that,
                    # with this approach, only switches who connect directly to
                    # end-hosts will send ARP packet-in, the core switches (do
                    # not connect to any host) never send ARP packet-in to
                    # controller. Unlike normal simple_switch_13.py app where
                    # all switches can ask controller things related to ARP,
                    # however, this normal app assumes the network topology as
                    # a tree, no loop there, which makes it weak. If there is a
                    # loop, the line: self.mac_to_port[dpid][src] = in_port
                    # will need to update repeatedly and may render this value
                    # wrong.
                    actions = [parser.OFPActionOutput(in_port)]
                    match = parser.OFPMatch(
                        eth_type=ether_types.ETH_TYPE_ARP, eth_dst=arp_msg.src_mac)
                    utility.add_flow(0x11, datapath, 1, match, actions)
                    # new 20210615: to address the problem of 2 or more hosts attached to the same switch that could not "talk" with each other due to no ARP response relayed to the controller and the arp_cache_db is not updated, thus the routing app does not know how to route traffic between these two hosts. The current solution is to add a rule to this switch to forward arp response to the controller in a short timeout.
                    actions = [parser.OFPActionOutput(in_port),parser.OFPActionOutput(ofproto_v1_3.OFPP_CONTROLLER)]
                    match = parser.OFPMatch(
                        eth_type=ether_types.ETH_TYPE_ARP, eth_dst=arp_msg.src_mac)
                    utility.add_flow_with_hard_timeout(0x11, datapath, 2, match, actions,5)
            except KeyError:
                self.logger.debug("ARP_cache: KeyError!")

            if arp_msg.opcode == 1 and arp_msg.dst_ip not in self.arp_cache_db:  # do shortcut FLOOD
                self.logger.debug("ARP REQUEST, dst ip not in arp cache")
                if in_port not in self.non_interswitch_ports[dpid]:  # install a temporary drop rule on that switch for 5s
                    match = parser.OFPMatch(
                        eth_src=eth_src, arp_tpa=arp_msg.dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                    action = []  # empty action means drop
                    '''install drop rule for this packet for 5 seconds at the asking switch'''
                    utility.add_flow_with_hard_timeout(
                        0x11, datapath, 1, match, action, 5)  # timeout = 5s
                        #self.cookie, datapath, 1, match, action, 5)  # timeout = 5s
                    self.logger.debug("install drop rule for ARP_REQUEST at switch %s for 5s", dpid)
                    return

                for fdpid in self.non_interswitch_ports:  # flood datapath id --> fdpid
                    if fdpid != dpid:  # XXX wrong! if 2 hosts connect to a switch having dpid, add else:
                        fdatapath = self.datapathmap[fdpid]
                        fdata = msg.data
                        fparser = fdatapath.ofproto_parser
                        fofproto = fdatapath.ofproto
                        factions = [fparser.OFPActionOutput(i)
                                    for i in list(self.non_interswitch_ports[fdpid])]
                        fout = fparser.OFPPacketOut(
                            datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER, in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                        fdatapath.send_msg(fout)
                    else:  # XXX added to control the wrong case from if
                        factions = None
                        for i in list(self.non_interswitch_ports[dpid]):
                            if i != in_port:  # do not forward to in_port
                                factions = [parser.OFPActionOutput(i)]
                        # print("factions = %s, dpid = %s" % (factions, dpid))
                        if factions != None:
                            fdata = None
                            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                                fdata = msg.data
                            fout = parser.OFPPacketOut(
                                datapath=datapath, buffer_id=msg.buffer_id, in_port=ofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                            datapath.send_msg(fout)

            if arp_msg.opcode == 1 and arp_msg.dst_ip in self.arp_cache_db:
                # or arp_msg.opcode == arp.ARP_REQUEST
                # send packet out: an ARP response, set field accordingly
                # install a path from src to dst and vice versa.
                self.logger.debug("ARP REQUEST, dst ip in arp cache")
                if arp_msg.src_ip == self.controller_ip:
                    self.logger.debug("request from controller, ignore")
                    return #ignore, ottherwise there's a bug arisen in the next line
                if dpid == self.arp_cache_db[arp_msg.src_ip]['dpid']:  # there are cases arp_request are sent from switch other than the responsible switch: since sender sends several arp requests, the first is answered and rules are install on switches on the path, while the subsequent arp requests are based on that installed path and reach the next switch, causing such arp request to be sent from not responsible switch.
                    try:
                        path = nx.shortest_path(
                            self.net, dpid, self.arp_cache_db[arp_msg.dst_ip]['dpid'])
                        self.logger.debug("path from source ip %s to dest ip %s is %s", 
                            arp_msg.src_ip, arp_msg.dst_ip, path)
                        # so there is a path from src to dst.
                        # build ARP REPLY :
                        # ref:https://sourceforge.net/p/ryu/mailman/message/33076908/
                        arp_reply = packet.Packet()
                        arp_reply.add_protocol(ethernet.ethernet(
                            ethertype=eth.ethertype, dst=eth_src, src=self.arp_cache_db[arp_msg.dst_ip]['mac']))
                        arp_reply.add_protocol(arp.arp(
                            opcode=arp.ARP_REPLY, src_mac=self.arp_cache_db[
                                arp_msg.dst_ip]['mac'], dst_mac=eth_src,
                            src_ip=arp_msg.dst_ip, dst_ip=arp_msg.src_ip))
                        arp_reply.serialize()

                        actions = [parser.OFPActionOutput(in_port)]
                        out = parser.OFPPacketOut(
                            datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER,
                            actions=actions, data=arp_reply.data)
                        datapath.send_msg(out)
                        # install path from source to dest and vice versa
                        for node in path:
                            if node != path[len(path) - 1]:  # don't install rules on last node, it already has rule from itself to end-point
                                self.logger.debug("install rules on node %s" % (node))
                                next_node = path[
                                    path.index(node) + 1]  # remember, node and next_node are dpid
                                #out_port = self.net[node][next_node]['port']
                                out_port = self.get_out_port_for_link(node, next_node)
                                # node_datapath = api.get_datapath(self, node)
                                # from appsuite_v1_0
                                node_datapath = self.datapathmap[node]
                                node_parser = node_datapath.ofproto_parser
                                # node_proto = node_datapath.ofproto
                                node_action = [
                                    node_parser.OFPActionOutput(out_port)]
                                # node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                                # node_datapath.send_msg(node_out)
                                node_match = parser.OFPMatch(
                                    eth_type=ether_types.ETH_TYPE_ARP, eth_src=eth_src, eth_dst=self.arp_cache_db[arp_msg.dst_ip]['mac'])
                                utility.add_flow_with_hard_timeout(
                                    0x11, node_datapath, 1, node_match, node_action, self.HARD_TIMEOUT)
                                    #self.cookie, node_datapath, 1, node_match, node_action, self.HARD_TIMEOUT)
                                # node_match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=in_proto.IPPROTO_ICMP, eth_src=eth_src, eth_dst=self.arp_cache_db[arp_msg.dst_ip]['mac'])
                                # self.add_flow_with_hard_timeout(self.cookie,
                                # node_datapath, 1, node_match, node_action,
                                # self.HARD_TIMEOUT)

                        path = nx.shortest_path(
                            self.net, self.arp_cache_db[arp_msg.dst_ip]['dpid'], dpid)
                        self.logger.debug("path from source ip %s to dest ip %s is %s",
                            arp_msg.dst_ip, arp_msg.src_ip, path)
                        # self.add_path_flow(path, eth_dst, eth_src)#remember
                        # eth_src = arp_msg.src_mac #from v3.0 and prior,
                        # causing possibly the rule with mac address
                        # ff:ff:ff:ff:ff:ff in flow table
                        self.add_path_flow(path, self.arp_cache_db[arp_msg.dst_ip][
                                           'mac'], eth_src)  # remember eth_src = arp_msg.src_mac
                    except nx.NetworkXNoPath:
                        self.logger.debug("There is no path, install a drop rule for 5s to relieve the controller a little bit")
                        match = parser.OFPMatch(
                            eth_src=eth_src, arp_tpa=arp_msg.dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                        action = []  # empty action means drop
                        '''install drop rule for this packet for 10 seconds at the asking switch'''
                        utility.add_flow_with_hard_timeout(
                            0x11, datapath, 1, match, action, 5)  # timeout = 5s
                            #self.cookie, datapath, 1, match, action, 5)  # timeout = 5s
                else:
                    # such case occurs when appsuite (this application) works
                    # together with other application (like
                    # simple_switch_snort) when a message without a matching
                    # rule in a switch will be flooded.
                    path = nx.shortest_path(
                        self.net, dpid, self.arp_cache_db[arp_msg.dst_ip]['dpid'])
                    self.logger.debug("asking switch is somewhere else on the network, path from %s to %s is: %s",
                          dpid, arp_msg.dst_ip, path)
                    self.add_path_flow_with_timeout(
                        path, arp_msg.dst_mac, 5)  # timeout is 5s
                    return
                    # drop this request since it is from the asking switch that
                    # is not related, by installing drop rule for 5s
                    match = parser.OFPMatch(
                        eth_src=eth_src, arp_tpa=arp_msg.dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                    action = []  # empty action means drop
                    '''install drop rule for this packet for 5 seconds at the asking switch'''
                    utility.add_flow_with_hard_timeout(
                        0x11, datapath, 1, match, action, 5)  # timeout = 5s
                        #self.cookie, datapath, 1, match, action, 5)  # timeout = 5s
                    self.logger.debug("install drop rule for ARP_REQUEST at switch %s for 5s", dpid)

            if arp_msg.opcode == 2 and arp_msg.dst_ip == self.controller_ip:
                self.logger.debug("dst ip = controller IP, a case for active arpcache discovery!")
                return

            if arp_msg.opcode == 2 and arp_msg.dst_ip in self.arp_cache_db:
                # or arp_msg.opcode == arp.ARP_REPLY
                # install a path from src to dst and vice versa, the response
                # will follow the installed path to reach the requested
                # end-point.
                self.logger.debug("ARP RESPONSE")
                try:
                    if arp_msg.src_ip in self.arp_cache_db and arp_msg.dst_ip in self.arp_cache_db:
                        supposed_shortest_path = nx.shortest_path(self.net, self.arp_cache_db[
                                                                  arp_msg.src_ip]['dpid'], self.arp_cache_db[arp_msg.dst_ip]['dpid'])
                        if dpid in supposed_shortest_path:
                            self.logger.debug("path from %s to %s is: %s",
                                arp_msg.src_ip, arp_msg.dst_ip, supposed_shortest_path)
                            self.add_path_flow(
                                supposed_shortest_path, arp_msg.src_mac, arp_msg.dst_mac)
                            path = nx.shortest_path(self.net, self.arp_cache_db[
                                                    arp_msg.dst_ip]['dpid'], self.arp_cache_db[arp_msg.src_ip]['dpid'])
                            self.add_path_flow(
                                path, arp_msg.dst_mac, arp_msg.src_mac)
                    else:  # such case occurs when appsuite (this application) works together with other application (like simple_switch_snort) when a message without a matching rule in a switch will be flooded.
                        path = nx.shortest_path(
                            self.net, dpid, self.arp_cache_db[arp_msg.dst_ip]['dpid'])
                        self.logger.debug("dpid not in shortest path, path from %s to %s is: %s",
                            dpid, arp_msg.dst_ip, path)
                        self.add_path_flow_with_timeout(
                            path, arp_msg.dst_mac, 5)  # timeout is 5s
                except nx.NetworkXNoPath:
                    self.logger.debug("There is no path")

            if arp_msg.opcode == 2 and arp_msg.dst_ip not in self.arp_cache_db:
                # this case cannot happen
                self.logger.debug("ARP RESPONSE! Kernel panic!!!")
                match = parser.OFPMatch(
                    eth_src=eth_src, arp_tpa=arp_msg.dst_ip, eth_type=ether_types.ETH_TYPE_ARP)
                action = []  # empty action means drop
                '''install drop rule for this packet for 5 seconds at the asking switch'''
                utility.add_flow_with_hard_timeout(
                    0x11, datapath, 1, match, action, 5)  # timeout = 5s
                    #self.cookie, datapath, 1, match, action, 5)  # timeout = 5s
                self.logger.debug("install drop rule for ARP_REQUEST at switch %s for 5s", dpid)

    def add_path_flow(self, path, src_mac, dst_mac):
        '''This function is customized to install flow entries matching only ARP/ICMP packets '''
        for node in path:
            if node != path[len(path) - 1]:  # don't install rules on last node, it already has rule from itself to end-point
                self.logger.debug("ARPCache: install rules on node %s", node)
                next_node = path[
                    path.index(node) + 1]  # remember, node and next_node are dpid
                #out_port = self.net[node][next_node]['port']
                #out_port = self.net[node][next_node][0]['port'][0] #adapt to mutlidigraph network
                out_port = self.get_out_port_for_link(node, next_node)
                # node_datapath = api.get_datapath(self, node) from
                # appsuite_v1_0
                node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                # node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                # node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                # node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_ARP, eth_src=src_mac, eth_dst=dst_mac)
                utility.add_flow_with_hard_timeout(
                    0x11, node_datapath, 1, node_match, node_action, self.HARD_TIMEOUT)
                    #self.cookie, node_datapath, 1, node_match, node_action, self.HARD_TIMEOUT)
                                                   #since path may change, so install rule on the switch with hard_timeout.
                # node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=in_proto.IPPROTO_ICMP,eth_src=src_mac, eth_dst=dst_mac)
                # self.add_flow_with_hard_timeout(self.cookie, node_datapath,
                # 1, node_match, node_action, self.HARD_TIMEOUT) #since path
                # may change, so install rule on the switch with hard_timeout.

    def add_path_flow_with_timeout(self, path, dst_mac, timeout):
        '''This function is customized to install flow entries matching only ARP/ICMP packets '''
        for node in path:
            if node != path[len(path) - 1]:  # don't install rules on last node, it already has rule from itself to end-point
                self.logger.debug("install rules on node %s",node)
                next_node = path[
                    path.index(node) + 1]  # remember, node and next_node are dpid
                out_port = self.get_out_port_for_link(node, next_node)
                # node_datapath = api.get_datapath(self, node) from
                # appsuite_v1_0
                node_datapath = self.datapathmap[node]
                node_parser = node_datapath.ofproto_parser
                # node_proto = node_datapath.ofproto
                node_action = [node_parser.OFPActionOutput(out_port)]
                # node_out = node_parser.OFPPacketOut(datapath=node_datapath, buffer_id=node_proto.OFP_NO_BUFFER, in_port=node_proto.OFPP_CONTROLLER, actions=node_action,data=None)
                # node_datapath.send_msg(node_out)
                node_match = node_parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_ARP, eth_dst=dst_mac)
                utility.add_flow_with_hard_timeout(
                    0x11, node_datapath, 1, node_match, node_action, timeout)
                    #self.cookie, node_datapath, 1, node_match, node_action, timeout)
                                                   #since path may change, so install rule on the switch with hard_timeout.
                # node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=in_proto.IPPROTO_ICMP,eth_dst=dst_mac)
                # self.add_flow_with_hard_timeout(self.cookie, node_datapath,
                # 1, node_match, node_action, timeout) #since path may change,
                # so install rule on the switch with hard_timeout.

    def discover_arpmapping(self, ip):
        self.logger.debug("ARPCache: actively discover destination ARP mapping using controller info as source!")
        arp_req = packet.Packet()
        arp_req.add_protocol(ethernet.ethernet(
            ethertype=ether_types.ETH_TYPE_ARP, dst='ff:ff:ff:ff:ff:ff', src=self.controller_mac))
        arp_req.add_protocol(arp.arp(
            opcode=arp.ARP_REQUEST, src_mac=self.controller_mac, dst_mac='00:00:00:00:00:00',
            src_ip=self.controller_ip, dst_ip=ip))
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
