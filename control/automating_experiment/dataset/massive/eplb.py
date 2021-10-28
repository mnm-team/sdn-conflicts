# Copyright (C) 2018 Cuong Tran - cuongtran@mnm-team.org
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
__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '2.0' - 20200731
Store the information of port combination for the flows that were already handled in the SBEpLB and treat the packets of these flows consistently, only install rule for the first packet of this flow, subsequent packets arrive in packet-in event as a result of race condition will be ignored at the controller (or in packet-in event handling of SBEpLB).

__version__ = '1.0' - 2019 or earlier
Not yet dealt with race condition:
    Session-based EpLB wants to balance layer 4 traffic based on the combination of layer 4 (TCP/UDP) src and dst port to different replicas which are represented by an address. E.g., first TCP traffic flow to 192.168.1.3 will arrive at 192.168.1.3, second TCP traffic flow to 192.168.1.3 will arrive at 192.168.1.4...
    Due to race condition, the excessive load caused by iperf induces the unexpected behaviour of the EpLB. Specifically, a bunch of packets come to the switch, which has no existing corresponding flow entry to handle them and has to send them to the controller to ask for instruction, so the first packet coming at the controller produces a rule to be installed in the switch, saying "forward the packet to the first replica", the second packet coming to the controller produces another rule: "forward to the second replica" and so on.
    For this test: see conflict8_race_condition directory.
    At controller: ryu-manager --observe-links eplb.py routing.py
    At pc3 and 4: iperf -s -u
    At pc1: iperf -c 192.168.1.3 -u -b 20m -t 5


Applicable for IPv4, not yet IPv6
'''

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
import utility
import networkx as nx
from ryu.lib import hub
import logging

'''
The routing app has actively discover the destination information for ARPCache: e.g., ARP entry for an IPv4. That feature will be reused in this SBEpLB --> run with routing app.

Note: SBEpLB needs to know the position of the balancing servers (destinations) beforehand, i.e., which switch (dpid) is responsible for these servers, these entries need to be available in the ARPCache, so it will ask the ARPCache to actively discover these immediately when it starts.

Balance all layer4 traffic (UDP,TCP) with session-information-awareness to the specified server at the balance point.

To run this app:
    ryu-manager --observe-links eplb.py routing.py

'''

class SBEpLB(arpcache.ARPCache):

    def __init__(self, *args, **kwargs):
        super(SBEpLB, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.INFO)
        #print("\tSession-based Endpoint-Load Balancer flexible, topology aware")
        self.logger.info("\tSession-based Endpoint-Load Balancer flexible, topology aware")
        #self.blp =[0x0000000000000007, 0x0000000000000001] #blp = balance_point in datapath id form
        config = self.parse_config()
        print("config = %s"%config)
        #self.priority = 2
        self.priority = config[0]
        #self.blp =[0x0000000000000007] #blp = balance_point in the form of datapath id
        self.blp = config[1]
        #self.proxy_server = ('192.168.1.3','00:16:3e:00:00:43')#the server info exposed to clients
        self.proxy_server = config[2]
        #self.servers = [('192.168.1.3','00:16:3e:00:00:43'),('192.168.1.4','00:16:3e:00:00:44')]#the list of servers actually handle the client traffic, in a round-robin manner
        self.servers = config[3]
        self.cookie = 0x400
        self.index = 0 #to pick the server to handle the incoming session.
        self.IDLE_TIMEOUT = 1800# if a flow is idle for 10s, remove it since it is very specific
        self.discoverserver_thread = hub.spawn(self.discover_server)
        self.handled_flow = {} # store the flows that were already handled, so that only the first packet of each new flow will trigger rule installation in the data plane, and therefore the race condition caused by multiple packet-in events of the same flow can be eliminated.
        #self.handled_flow = {dpid1:[(tcp,src_port1,dst_port1),(udp,src_port2,dst_port2)...], dpid2:[]}
        for i in self.blp:
            self.handled_flow[i] = []
        
    def parse_config(self):
    # 2 #priority
    # 0x0000000000000007 #datapath id
    # 192.168.1.3 00:16:3e:00:00:43 #proxy server
    # 192.168.1.3 00:16:3e:00:00:43 192.168.1.4 00:16:3e:00:00:44 # replicas/servers to balance traffic on.
        priority = None
        blp = []
        proxy_server = None
        servers = []
        with open("eplb_config_global") as globalfile: 
            i = 1
            for line in globalfile:
                line = line.strip()# preprocess line 
                #print("line = %s"%line)
                if i == 1: # first line, priority
                    priority = int(line.split()[0])
                if i == 2: # second line, for balance point, i.e., switch dpid
                    blp_str = line.split()
                    #print(blp_str)
                    for dpid in blp_str:
                        if dpid[0] == '#': # a comment
                            break
                        hex_int = int(dpid,16) 
                        blp.append(hex_int)
                        #print("blp = %s"%blp) 
                if i == 3: # first line, priority
                    appconfig = int(line.split()[0])
                #if i == 3: # third line, proxy server
                #    string = line.split()
                #    proxy_server = (string[0],string[1])
                #if i == 4: # fourth line, replicas/servers
                #    string = line.split()
                #    index = 0
                #    while index<len(string) and string[index][0] != '#':
                #        servers.append((string[index],string[index+1]))
                #        index += 2
                    break #only process first 2 lines, the rest is not necessary
                i += 1
        with open("eplb_config_local") as localfile:
            i = 1
            for line in localfile:
                line = line.strip()# preprocess line 
                if i == 1: # first line, proxy server
                    string = line.split()
                    proxy_server = (string[0],string[1])
                if i == 2: # second line, replicas/servers
                    string = line.split()
                    index = 0
                    while index<len(string) and string[index][0] != '#':
                        servers.append((string[index],string[index+1]))
                        index += 2
                    break #only process first 2 lines, the rest is not necessary
                i += 1
        return [priority, blp, proxy_server, servers]


    def discover_server(self):
        hub.sleep(10)#wait for the topology information to be collected by topology app
        for ser in self.servers:
            self.discover_arpmapping(ser[0])
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def eplb_packet_in_handler(self,ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes", 
                    ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        if dpid not in self.blp:
            return

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            #ignore lldp packet
            return

        eth_dst = eth.dst
        eth_src = eth.src

	#print("SBEpLB packet in handler")
        #print("\nSBEpLB - packet in dpid: %s, src: %s, dst: %s, in_port: %s" %(dpid, eth_src, eth_dst, in_port) )
        self.logger.info("\nSBEpLB - packet in dpid: %s, src: %s, dst: %s, in_port: %s",dpid, eth_src, eth_dst, in_port)

        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip = pkt.get_protocols(ipv4.ipv4)[0]
            print("ip = %s"%ip)
            if ip.proto not in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]:
                return
            ip_src = ip.src
            ip_dst = ip.dst
            if ip_dst != self.proxy_server[0] and eth_dst != self.proxy_server[1]:#only consider traffic to the proxy server
                return
            src_port = None
            dst_port = None
            match = None
            if ip.proto == in_proto.IPPROTO_TCP:
                tcphdr = pkt.get_protocols(tcp.tcp)[0]
                print("tcp header = %s"%tcphdr)
                src_port = tcphdr.src_port
                dst_port = tcphdr.dst_port
                if (('tcp',src_port,dst_port) not in self.handled_flow[dpid]):
                    self.logger.info("new flow, add to handled flow")
                    self.logger.info("self.handled_flow = %s",self.handled_flow)
                    self.handled_flow[dpid].append(('tcp',src_port,dst_port))
                else:
                    self.logger.info("this flow was already handled, exit")
                    self.logger.info("self.handled_flow = %s",self.handled_flow)
                    return
                match = parser.OFPMatch(
                        in_port=in_port,eth_type=eth.ethertype,
                        ipv4_src=ip_src,ipv4_dst=ip_dst,
                        ip_proto=ip.proto,
                        tcp_src=tcphdr.src_port,tcp_dst=tcphdr.dst_port
                        )
                
            if ip.proto == in_proto.IPPROTO_UDP:
                udphdr = pkt.get_protocols(udp.udp)[0]
                print("udp header = %s"%udphdr)
                src_port = udphdr.src_port
                dst_port = udphdr.dst_port
                if (('udp',src_port,dst_port) not in self.handled_flow[dpid]):
                    self.logger.info("new flow, add to handled flow")
                    self.logger.info("self.handled_flow = %s",self.handled_flow)
                    self.handled_flow[dpid].append(('udp',src_port,dst_port))
                else:
                    self.logger.info("this flow was already handled, exit")
                    self.logger.info("self.handled_flow = %s",self.handled_flow)
                    return
                match = parser.OFPMatch(
                        in_port=in_port,eth_type=eth.ethertype,
                        ipv4_src=ip_src,ipv4_dst=ip_dst,
                        ip_proto=ip.proto,
                        udp_src=udphdr.src_port,udp_dst=udphdr.dst_port
                        )
            print("src port = %s, dst port = %s"%(src_port,dst_port))
            #having match, now calculate the action
            if self.servers[self.index][0] == self.proxy_server[0]:
                #install normal rule, without setField 
                path = nx.shortest_path(self.net, dpid, self.arp_cache_db[ip_dst]['dpid'])
                try:
                    next_node = path[path.index(dpid)+1]
                    out_port = self.net[dpid][next_node]['port']
                except IndexError:
                    self.logger.error("IndexError: last node on the path to destination")
                    for i in self.arp_cache_db:
                        if i == ip_dst:
                            out_port = self.arp_cache_db[i]['port']
                            break
                actions = [parser.OFPActionOutput(out_port)]
                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match,actions,self.IDLE_TIMEOUT)
                self.logger.info("install rule at sw %s, priority: %s, match: %s, action: %s", datapath.id,self.priority, match, actions)
                #send packet-out after installing the rule
                out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=actions,data=msg.data)
                datapath.send_msg(out)
                #install rule for reverse path
                if ip.proto == in_proto.IPPROTO_TCP:
                    match = parser.OFPMatch(
                        eth_type=eth.ethertype,
                        ipv4_src=ip_dst,ipv4_dst=ip_src,
                        ip_proto=ip.proto,
                        tcp_src=tcphdr.dst_port,tcp_dst=tcphdr.src_port
                        )
                if ip.proto == in_proto.IPPROTO_UDP:
                    match = parser.OFPMatch(
                        eth_type=eth.ethertype,
                        ipv4_src=ip_dst,ipv4_dst=ip_src,
                        ip_proto=ip.proto,
                        udp_src=udphdr.dst_port,udp_dst=udphdr.src_port
                        )
                path = nx.shortest_path(self.net, dpid, self.arp_cache_db[ip_src]['dpid'])
                try:
                    next_node = path[path.index(dpid)+1]
                    out_port = self.net[dpid][next_node]['port']
                except IndexError:
                    self.logger.error("IndexError: last node on the path to destination")
                    for i in self.arp_cache_db:
                        #if self.arp_cache_db[i]['mac'] == eth_dst:
                        if i == ip_src:
                            out_port = self.arp_cache_db[i]['port']
                            break

                actions = [parser.OFPActionOutput(out_port)]
                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match,actions,self.IDLE_TIMEOUT)
                self.logger.info("install rule at sw %s, priority: %s, match: %s, action: %s", datapath.id,self.priority, match, actions)

            else:
                #add forwarding flow
                ip_dst = self.servers[self.index][0]
                path = nx.shortest_path(self.net, dpid, self.arp_cache_db[ip_dst]['dpid'])
                try:
                    next_node = path[path.index(dpid)+1]
                    out_port = self.net[dpid][next_node]['port']
                except IndexError:
                    self.logger.error("IndexError: last node on the path to destination")
                    for i in self.arp_cache_db:
                        if i == ip_dst:
                            out_port = self.arp_cache_db[i]['port']
                            break
                actions = [parser.OFPActionSetField(eth_dst=self.servers[self.index][1]), parser.OFPActionSetField(ipv4_dst=ip_dst), parser.OFPActionOutput(out_port)]
                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match,actions,self.IDLE_TIMEOUT)
                self.logger.info("install rule at sw %s, priority: %s, match: %s, action: %s", datapath.id,self.priority, match, actions)
                #send packet-out after installing the rule
                out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=actions,data=msg.data)
                datapath.send_msg(out)
                #add reverse flow
                if ip.proto == in_proto.IPPROTO_TCP:
                    match=parser.OFPMatch(#don't know the in_port, so skip that in match
                        eth_type=eth.ethertype,
                        ipv4_src=ip_dst,ipv4_dst=ip_src,#ip_dst was changed above
                        ip_proto=ip.proto,
                        tcp_src=tcphdr.dst_port,tcp_dst=tcphdr.src_port
                        )
                if ip.proto == in_proto.IPPROTO_UDP:
                    match=parser.OFPMatch(#don't know the in_port, so skip that in match
                        eth_type=eth.ethertype,
                        ipv4_src=ip_dst,ipv4_dst=ip_src,#ip_dst was changed above
                        ip_proto=ip.proto,
                        udp_src=udphdr.dst_port,udp_dst=udphdr.src_port
                        )
                path = nx.shortest_path(self.net, dpid, self.arp_cache_db[ip_src]['dpid'])
                try:
                    next_node = path[path.index(dpid)+1]
                    out_port = self.net[dpid][next_node]['port']
                except IndexError:
                    self.logger.error("IndexError: last node on the path to destination")
                    for i in self.arp_cache_db:
                        #if self.arp_cache_db[i]['mac'] == eth_dst:
                        if i == ip_src:
                            out_port = self.arp_cache_db[i]['port']
                            break
                actions = [parser.OFPActionSetField(eth_src=self.proxy_server[1]), parser.OFPActionSetField(ipv4_src=self.proxy_server[0]), parser.OFPActionOutput(out_port)]
                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match,actions,self.IDLE_TIMEOUT)
                self.logger.info("install rule at sw %s, priority: %s, match: %s, action: %s", datapath.id,self.priority, match, actions)

            # calculate index for next server picking
            self.index += 1
            self.index = self.index % len(self.servers)
