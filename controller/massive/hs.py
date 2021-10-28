# Copyright (C) 2021 Nicholas Reyes - nicholasreyes@hotmail.de
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
__author__ = 'Nicholas Reyes'
__email__ = 'nicholasreyes@hotmail.de'
__licence__ = 'GPL2.0'

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import in_proto
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3_parser

import arpcache
import utility_detector as utility
import networkx as nx
from ryu.lib import hub
import logging
import json
import globalconfig

'''
The use case for this app is that a host ip that is black-listed in certain systems or countries
can be reached by appearing to communicate with a frontend host, that shadows the black-listed 
backend host.
This app needs to be deployed to one or multiple switches, such that forward and backward flows will
always pass it/them. In other words, the forward and backward flow to the frontend and from the 
backend host need to pass one of the target switches.

__version__ = '1.0'
App prototype for a SDN implementation similar to the concept of domain shadowing.

Applicable for IPv4, not yet IPv6

To run this app:
ryu-manager --observe-links host_shadower.py routing.py
'''

class HostShadower(arpcache.ARPCache, utility.Utility):

    def __init__(self, *args, **kwargs):
        super(HostShadower, self).__init__(*args, **kwargs)
        self.COMPLETE_SWITCH_COVERAGE = True
        self.logger.setLevel(logging.INFO)
        self.logger.info("Host shadowing app, topology aware")
        config = self.parse_config()
        print("config = %s" % config)
        self.priority = config[0]
        # datapath ids
        self.blp = config[1]
        self.hosts_config = config[2]
        self.shadowed_flows = {}
        self.cookie = 0x440
        self.IDLE_TIMEOUT = 1800  # if a flow is idle for 10s, remove it since it is very specific
        self.discoverserver_thread = hub.spawn(self.discover_server)


    def parse_config(self):
        priority, blp = globalconfig.parseGlobalConfig("hs")
        # load local config and covert to dict with (proxy_mac,proxy_ip) as keys
        hosts_config = globalconfig.localConfigHS()
        return [priority, blp, hosts_config]


    def discover_server(self):
        '''
        Wait for the topology information to be collected by topology app.
        We only need the info for the shadower machine, since the original
        host will never be addressed by this app.
        '''
        hub.sleep(10)
        for frontend,backend in self.hosts_config.items():
            self.discover_arpmapping(backend[0])


    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def flow_removed_handler(self, evt):
        msg = evt.msg
        match = msg.match
        try:
            # we only need to handle removal of own flow insertions
            if not match.cookie == self.cookie:
                return

            eth_dst = match.eth_dst
            eth_src = match.eth_src
            ip_src = match.ip_src
            ip_dst = match.ip_dst

            if "tcp_src" in match or "udp_src" in match:
                # we have a forward flow
                port_key = None
                if "tcp_src" in match:
                    port_key = "tcp_src"
                else:
                    port_key = "udp_src"
                
                # shadowed_flows is based on backend addresses
                # but forward flow matches will always contain frontend addresses
                # so we need to get the right tuple from config
                backend = self.hosts_config[(ip_dst,eth_dst)]
                hashable_entry = str((ip_src, eth_src, match[port_key], backend[0], backend[1]))
                del self.shadowed_flows[hashable_entry]
                self.logger.debug("HostShadower, removing entry: {}".format(hashable_entry))

            elif "tcp_dst" in match or "udp_dst" in match:
                # we have a backward flow
                port_key = None
                if "tcp_dst" in match:
                    port_key = "tcp_dst"
                else:
                    port_key = "udp_dst"
           
                # for backward flows the match should be based on backend addresses
                # the same as shadowed_flows
                hashable_entry = str((ip_dst, eth_dst, match[port_key], ip_src, eth_src))
                del self.shadowed_flows[hashable_entry]
                self.logger.debug("HostShadower, removing entry: {}".format(hashable_entry))

            else:
                self.logger.debug("Error HostShadower, didn't remove entry for match: {}"
                                    .format(match))
        
        except Exception as e:
            self.logger.debug("Error something went wrong in HostShadower while removing entry: {}"
                                .format(e))


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        m_len = ev.msg.msg_len  
        t_len = ev.msg.total_len
        if m_len < t_len:
            self.logger.debug("packet truncated: only %s of %s bytes", m_len, t_len)

        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        eth_type = eth.ethertype

        # only handle ip packets
        # ignore if dpid is not a target switch
        if (not eth_type == ether_types.ETH_TYPE_IP) or (dpid not in self.blp):
            return
        
        # only handle tcp,udp packets       
        ip = pkt.get_protocols(ipv4.ipv4)[0]
        if (ip.proto not in [in_proto.IPPROTO_TCP,in_proto.IPPROTO_UDP]):
            return

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        eth_dst = eth.dst
        eth_src = eth.src
        ip_src = ip.src
        ip_dst = ip.dst
        
        # get the info to remember shadowed forward flows
        # or to lookup handled flows for handling reverse flows
        src_port = None
        dst_port = None
        session_proto = None
        match = None
        reverse_match = None
        actions = None
        reverse_actions = None

        # handle packets to frontend servers going through the target switches
        # insert reverse rule for packets coming back from the backend host
        if (ip_dst,eth_dst) in self.hosts_config:
            if ip.proto == in_proto.IPPROTO_TCP:
                tcp_header = pkt.get_protocols(tcp.tcp)[0]
                src_port = tcp_header.src_port
                dst_port = tcp_header.dst_port
                session_proto = 'tcp'
            elif ip.proto == in_proto.IPPROTO_UDP:
                udp_header = pkt.get_protocols(udp.udp)[0]
                src_port = udp_header.src_port
                dst_port = udp_header.dst_port
                session_proto = 'udp'        

            backend_s = self.hosts_config[(ip_dst,eth_dst)]
            log_msg = "\n HostShadower redirecting traffic for frontend: {},{} to backend: {},{}"
            self.logger.info(log_msg.format(ip_dst, eth_dst, backend_s[0],backend_s[1]))

            # get outport for switch connected to backend host on current switch
            b_ip_dst, b_eth_dst = backend_s[0], backend_s[1]
            path = nx.shortest_path(self.net, dpid, self.arp_cache_db[b_ip_dst]['dpid'])
            out_port = None
            try:
                next_node = path[path.index(dpid) + 1]
                out_port = self.get_out_port_for_link(dpid, next_node)
                if (out_port == in_port):
                    out_port = self.choose_alternative_outport(
                        dpid, self.arp_cache_db[b_ip_dst]['dpid'], out_port)
            except IndexError:
                self.logger.error("IndexError: last node on the path to destination")
                out_port = self.arp_cache_db[b_ip_dst]['port']
            
            # check if flow was already handled
            hashable_match = str((session_proto, ip_src, eth_src, src_port, ip_dst, eth_dst))
            if hashable_match in self.shadowed_flows:
                return
 
            # remember flow to handle multiple packet-ins for the same flow
            # value really doesn't matter as long as we have a hashable key
            self.shadowed_flows[str((session_proto, ip_src, eth_src, src_port, ip_dst, eth_dst))] = True 

            # Need to be session aware when sending to shadowing host to ensure
            # that we can identify the flow upon removal, since shadowed_flows
            # is based on client socket port number
            if session_proto == 'tcp':
                match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype, 
                            ipv4_src=ip_src, ipv4_dst=ip_dst, ip_proto=ip.proto, 
                            tcp_src=src_port)
                reverse_match = parser.OFPMatch(eth_type=eth.ethertype, 
                                    ipv4_dst=ip_src, ipv4_src=b_ip_dst, ip_proto=ip.proto, 
                                    tcp_dst=src_port)
            elif session_proto == 'udp':
                match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype, 
                            ipv4_src=ip_src, ipv4_dst=ip_dst, ip_proto=ip.proto, 
                            udp_src=src_port)
                reverse_match = parser.OFPMatch(eth_type=eth.ethertype, 
                                    ipv4_dst=ip_src, ipv4_src=b_ip_dst, ip_proto=ip.proto, 
                                    udp_dst=src_port)

            # overwrite dst fields with data of backend host to send traffic there
            actions = [parser.OFPActionSetField(eth_dst=b_eth_dst), parser.OFPActionSetField(
                ipv4_dst=b_ip_dst), parser.OFPActionOutput(out_port)]
            
            # we don't care about the in_port here since this is not a flow with packet-in event
            reverse_actions = [parser.OFPActionSetField(eth_src=eth_dst), 
                                parser.OFPActionSetField(ipv4_src=ip_dst), 
                                parser.OFPActionOutput(in_port)]

        else:
            # this is traffic that does not concern host shadower and is routed out to the 
            # next switch or host
            self.logger.info("HostShadower: no host shadowing, normal routing.")
            return
        
        if actions == None or match == None or reverse_actions == None or reverse_match == None:
            log_msg = "Error in HostShadower: match and/or actions are None!"
            self.logger.info(log_msg)
            return

        log_msg = "HS: install {} rule at sw {}, priority: {}, match: {}, action: {}"

        # add flow in switch for backwards rewrites from backend host
        self.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, reverse_match, 
                                              reverse_actions, self.IDLE_TIMEOUT)

        if self.COMPLETE_SWITCH_COVERAGE:
          self.logger.info("HS installing backward transform on all target switches")
          for alt_dpid in self.blp:
            if not alt_dpid == dpid:
              path = nx.shortest_path(self.net, alt_dpid, self.arp_cache_db[ip_src]['dpid'])
              next_node = path[path.index(alt_dpid) + 1]
              out_port = self.get_out_port_for_link(alt_dpid, next_node)
              alt_datapath = self.datapathmap[alt_dpid]
              alt_parser = alt_datapath.ofproto_parser
              if session_proto == 'tcp':
                alt_reverse_match = alt_parser.OFPMatch(eth_type=eth.ethertype, 
                                  ipv4_dst=ip_src, ipv4_src=b_ip_dst, ip_proto=ip.proto, 
                                  tcp_dst=src_port)
              elif session_proto == 'udp':
                 alt_reverse_match = alt_parser.OFPMatch(eth_type=eth.ethertype, 
                                  ipv4_dst=ip_src, ipv4_src=b_ip_dst, ip_proto=ip.proto, 
                                  udp_dst=src_port)
              alt_reverse_actions = [alt_parser.OFPActionSetField(eth_src=eth_dst), 
                                  alt_parser.OFPActionSetField(ipv4_src=ip_dst), 
                                  alt_parser.OFPActionOutput(out_port)]
              # add flow in other target switches for backwards rewrites from backend host
              self.add_flow_with_idle_timeout(self.cookie, alt_datapath, self.priority, alt_reverse_match, 
                                                alt_reverse_actions, self.IDLE_TIMEOUT)
        else:
          self.logger.info("HS not installing backward transform on all target switches")


        self.logger.info(log_msg.format("backward", 
                              datapath.id, self.priority, reverse_match, reverse_actions))

        # add flow in switch for forward rewrites to backend host
        self.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match, actions, 
                                          self.IDLE_TIMEOUT)
        self.logger.info(log_msg.format("forward", datapath.id, self.priority, match, actions))
       
        # send packet-out after installing the rule
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                    in_port=datapath.ofproto.OFPP_CONTROLLER, actions=actions, data=msg.data)
        
        datapath.send_msg(out)
