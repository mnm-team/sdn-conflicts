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
version 3.0 - 20200817 - stateful, added self.handled_flow

version 2.0 - 20200716
This app - passive PLB - will install path flow from redirection point (switch, relay point) to the destination. That means: PPLB receives a packet-in event from the sw interested to it containing the source and destination address, PPLB then install the path flow from this sw to the destination based on the path it determines for this packet flow. The simplified view of the topo is: S(ource) - SW - D(estination), from S to SW is responsible by the routing app with shortest path first routing algorithm, from SW to D is responsible by the PPLB with different paths for different packet flows.


version 1.0 - 202004
The routing app has actively discover the destination information for ARPCache: e.g., ARP entry for an IPv4. That feature will be reused in this passive path load balancer (PPLB) --> run with routing app.

Use case: the given servers are broadcasting some live services, which means there may be multiple clients connecting to these servers to download the content, so there may be heavy traffic on the direction from servers to clients, therefore, traffic originating from these servers, upon reaching the balancing points, will be directed on different paths starting from the balancing point if possible to the clients, so that the traffic is distributed on more paths and reduce the possible high load on a particular path.
In other words, from the balancing point's view: last time, I forward traffic from this server on this path, now if possible I will forward its traffic on the other path to the client (even a different client). --> The PPLB tries to route traffic against the criteria: the more paths the traffic of different (TCP/UDP) sessions traverses along, the better for the network as more links will be used and it lowers the chance of a overloaded link whilst others are underutilized.
The PPLB therefore considers the source of the traffic to decide if it should be balanced on different paths, and then the destination to choose the next path different from the previous chosen path if possible.

Balance all layer4 traffic (UDP,TCP) with session-information-awareness to the specified server at the balance point.
'''

class PPLB(arpcache.ARPCache):

    def __init__(self, *args, **kwargs):
        super(PPLB, self).__init__(*args, **kwargs)
        #self.logger.setLevel(logging.DEBUG)
        self.logger.info("\tPassive Path Load Balancer flexible, topology aware")
        #self.blp =[0x0000000000000007, 0x0000000000000001] #blp = balance_point in datapath id form
        config = self.parse_config()
        self.logger.info("config = %s"%config)
        #self.priority = 2
        self.priority = config[0]
        #self.blp =[0x0000000000000007] #blp = balance_point in the form of datapath id
        self.blp = config[1]
        #self.servers = [('192.168.1.3','00:16:3e:00:00:43'),('192.168.1.4','00:16:3e:00:00:44')]#the list of servers that the PPLB will balance the traffic therefrom
        self.servers = config[2]
        self.ol = {} # outport list
        # self.ol = {dpid1:[port1, port2, port3,...],dpid2:[port1, port2, ...],...}
        for i in self.blp:
            self.ol[i] = []
        self.cookie = 0x700
        self.IDLE_TIMEOUT = 1800# if a flow is idle for 1800s, remove it since it is very specific
        self.version = 2
        self.discoverserver_thread = hub.spawn(self.discover_server)
        self.handled_flow = {} # store the flows that were already handled, so that only the first packet of each new flow will trigger rule installation in the data plane, and therefore the race condition caused by multiple packet-in events of the same flow can be eliminated.
        #self.handled_flow = {dpid1:[(tcp,src_port1,dst_port1),(udp,src_port2,dst_port2)...], dpid2:[]}
        for i in self.blp:
            self.handled_flow[i] = []
        
    def parse_config(self):
    # 2 #priority
    # 0x0000000000000007 #datapath id
    # 192.168.1.3 00:16:3e:00:00:43 192.168.1.4 00:16:3e:00:00:44 # replicas/servers to balance traffic on.
        priority = None
        blp = []
        servers = []
        with open("pplb_config_global") as globalfile: 
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
                if i == 3: # app config
                    appconfig = int(line.split()[0])
                    break
                i += 1

        with open("pplb_config_local") as localfile: 
            i = 1
            for line in localfile:
                line = line.strip()# preprocess line 
                if i == 1: # first line, replicas/servers
                    string = line.split()
                    index = 0
                    while index<len(string) and string[index][0] != '#':
                        servers.append((string[index],string[index+1]))
                        index += 2
                    break
                i += 1
        return [priority, blp, servers]


    def discover_server(self):
        hub.sleep(10)#wait for the topology information to be collected by topology app
        for ser in self.servers:
            self.discover_arpmapping(ser[0])
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def pplb_packet_in_handler(self,ev):
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

	#self.logger.info("\nPPLB packet in handler")

        eth_dst = eth.dst
        eth_src = eth.src
        print("\nPPLB - packet in dpid: %s, src: %s, dst: %s, in_port: %s" %(dpid, eth_src, eth_dst, in_port) )

        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip = pkt.get_protocols(ipv4.ipv4)[0]
            self.logger.info("ip = %s",ip)
            if ip.proto not in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]:
                return
            ip_src = ip.src
            ip_dst = ip.dst
            if ((ip_src, eth_src) not in self.servers): #only consider traffic originating from the specified servers
                return
            src_port = None
            dst_port = None
            match = None
            if ip.proto == in_proto.IPPROTO_TCP:
                tcphdr = pkt.get_protocols(tcp.tcp)[0]
                self.logger.info("tcp header = %s",tcphdr)
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
                # version 1.0 includes in_port in match fields
                if (self.version == 1):
                    match = parser.OFPMatch(
                        in_port=in_port,eth_type=eth.ethertype,
                        ipv4_src=ip_src,ipv4_dst=ip_dst,
                        ip_proto=ip.proto,
                        tcp_src=tcphdr.src_port,tcp_dst=tcphdr.dst_port
                        )
                # version 2.0 removes in_port in match fields to keep it simple for the add_path_flow_with_idle_timeout function
                if (self.version == 2):
                    match = parser.OFPMatch(
                        eth_type=eth.ethertype,
                        ipv4_src=ip_src,ipv4_dst=ip_dst,
                        ip_proto=ip.proto,
                        tcp_src=tcphdr.src_port,tcp_dst=tcphdr.dst_port
                        )
                
            if ip.proto == in_proto.IPPROTO_UDP:
                udphdr = pkt.get_protocols(udp.udp)[0]
                self.logger.info("udp header = %s",udphdr)
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
                # version 1.0 with in_port in match fields
                if (self.version == 1):
                    match = parser.OFPMatch(
                        in_port=in_port,eth_type=eth.ethertype,
                        ipv4_src=ip_src,ipv4_dst=ip_dst,
                        ip_proto=ip.proto,
                        udp_src=udphdr.src_port,udp_dst=udphdr.dst_port
                        )
                # version 2.0 without in_port in match fields to simplify the add_path_flows_with_idle_timeout function
                if (self.version == 2):
                    match = parser.OFPMatch(
                        eth_type=eth.ethertype,
                        ipv4_src=ip_src,ipv4_dst=ip_dst,
                        ip_proto=ip.proto,
                        udp_src=udphdr.src_port,udp_dst=udphdr.dst_port
                        )
            self.logger.info("src port = %s, dst port = %s",src_port,dst_port)
            #having match, now calculate the action
            target_dpid = self.arp_cache_db[ip_dst]['dpid']
            break_flag = False
            if (self.version == 1):
                for path in nx.all_simple_paths(self.net, dpid,target_dpid):
                    self.logger.info("path = %s",path)
                    try:
                        next_node = path[path.index(dpid)+1]
                        out_port = self.net[dpid][next_node]['port']
                    except IndexError:
                        self.logger.error("IndexError: last node on the path to destination")
                        for i in self.arp_cache_db:
                            if i == ip_dst:
                                out_port = self.arp_cache_db[i]['port']
                                break
                        break
                    #now compare the out_port with the outport list self.ol, use it as outport for the current considered flow and add it into self.ol if it is not yet there, else, check the next path.
                    if (out_port == in_port):
                        continue
                    if (out_port not in self.ol[dpid]):
                        self.ol[dpid].append(out_port)
                        break_flag = True
                        break
                    else:
                        continue
                if (break_flag == False): # There is no new out_port, then use the first value of the outport list in self.ol[dpid] as the next outport (round-robin) then make it the last value in this list, so that the next choice of outport for the next flow will not be it. In other words, we turn around the list self.ol[dpid] after choosing its first value as out_port
                    out_port = self.ol[dpid][0]
                    self.ol[dpid].append(self.ol[dpid][0])
                    self.ol[dpid].pop(0)
                self.logger.info("out_port = %s", out_port)
                actions = [parser.OFPActionOutput(out_port)]
                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match,actions,self.IDLE_TIMEOUT)
            if (self.version == 2):
                chosen_path = None
                for path in nx.all_simple_paths(self.net, dpid,target_dpid):
                    self.logger.info("path = %s",path)
                    try:
                        next_node = path[path.index(dpid)+1]
                        out_port = self.net[dpid][next_node]['port']
                    except IndexError:
                        self.logger.error("IndexError: last node on the path to destination")
                        # then install the rule for this switch and done, return!
                        chosen_path = None
                        for i in self.arp_cache_db:
                            if i == ip_dst:
                                out_port = self.arp_cache_db[i]['port']
                                actions = [parser.OFPActionOutput(out_port)]
                                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match,actions,self.IDLE_TIMEOUT)
                                #send packet-out after installing the rule
                                data = msg.data
                                out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=actions,data=data)
                                datapath.send_msg(out)
                                return
                                #break
                        #break
                    #now compare the out_port with the outport list self.ol, use it as outport for the current considered flow and add it into self.ol if it is not yet there, else, check the next path.
                    if (out_port == in_port):
                        continue
                    if (out_port not in self.ol[dpid]):
                        self.ol[dpid].append(out_port)
                        chosen_path = path # out_port is new, choose this path to add path_flow
                        # break_flag = True, this variable is not necessary in version 2.0
                        #TODO install path_flow here and done
                        break
                    else:
                        continue
                if (chosen_path != None): #out_port is new
                    self.logger.info("1 self.ol[dpid]=%s",self.ol[dpid])
                    self.logger.info("chosen_path = %s",chosen_path)
                    self.add_path_flow_with_idle_timeout(chosen_path, match, ip_dst, self.IDLE_TIMEOUT,msg.data)
                    #send packet-out after installing the rule
                    #actions = [parser.OFPActionOutput(out_port)]
                    #data = msg.data
                    #out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=actions,data=data)
                    #datapath.send_msg(out)
                    return
                else: #choose the path with out_port == self.ol[dpid][0] and rotate the self.ol
                    for path in nx.all_simple_paths(self.net, dpid,target_dpid):
                        next_node = path[path.index(dpid)+1]
                        out_port = self.net[dpid][next_node]['port']
                        if (out_port == self.ol[dpid][0]):
                            self.ol[dpid].append(self.ol[dpid][0])
                            self.ol[dpid].pop(0)
                            self.logger.info("2 self.ol[dpid]=%s",self.ol[dpid])
                            self.logger.info("chosen_path = %s",path)
                            self.add_path_flow_with_idle_timeout(path, match, ip_dst, self.IDLE_TIMEOUT,msg.data)
                            #send packet-out after installing the rule
                            #actions = [parser.OFPActionOutput(out_port)]
                            #data = msg.data
                            #out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=actions,data=data)
                            #datapath.send_msg(out)
                            return
                        else:
                            self.logger.info("3 self.ol[dpid]=%s, out_port=%s",self.ol[dpid],out_port)
                        #break
                    #loop through all path and out_port always != self.ol[dpid][0], then choose the last path.
                    self.logger.info("chosen_path = %s",path)
                    self.add_path_flow_with_idle_timeout(path, match, ip_dst, self.IDLE_TIMEOUT,msg.data)
                    #still, rotate the self.ol for next use
                    self.ol[dpid].append(self.ol[dpid][0])
                    self.ol[dpid].pop(0)
                    return


    def add_path_flow_with_idle_timeout(self, path, match, ip_dst, timeout, data):
        '''
        Customized for this app: passive_PLB, match very specific layer 3 and 4 header, e.g., TCP/UDP src and dst port.
        Since the rule is very specific, and idle timeout is added so that it will be removed if it stays idle for this timeout.
        To reduce the complexity, the match is calculated before passing to this function and in_port is not inclusive. Otherwise, individual header fields have to be passive in this function arguments to build the match, in this case, in_port can be inferred based on the self.net graph.
        '''
        for node in path:
            if node != path[len(path)-1]:# each node is a sw with dpid, last node connects to end-point, not to a switch, so the instruction "next_node = path[path.index(node)+1] will cause IndexError
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
                #node_match = node_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=ipproto,eth_src=src_mac, eth_dst=dst_mac)
                utility.add_flow_with_idle_timeout(self.cookie, node_datapath, self.priority, match, node_action, self.IDLE_TIMEOUT)
                #send packet-out
                out = node_parser.OFPPacketOut(datapath=node_datapath,buffer_id=node_datapath.ofproto.OFP_NO_BUFFER,in_port=node_datapath.ofproto.OFPP_CONTROLLER,actions=node_action,data=data)
                node_datapath.send_msg(out)
            else:
                print("install rules on last node of the path, node %s" %(node))
                out_port = None
                for ip in self.arp_cache_db:
                    if (ip == ip_dst):
                        out_port = self.arp_cache_db[ip]['port']
                        break
                datapath = self.datapathmap[node]
                parser = datapath.ofproto_parser
                action = [parser.OFPActionOutput(out_port)]
                #match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ip_proto=ipproto,eth_src=src_mac,eth_dst=dst_mac)
                utility.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match, action, self.IDLE_TIMEOUT)
                out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=action,data=data)
                datapath.send_msg(out)
