__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
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

import arpcache
import utility

'''
To run this, you need to install the "networkx" python packet: pip install networkx.
Then at the controller: ryu-manager --observe-links appsuite.py
and connect your infrastructure to the controller.

This app can be executed together with the existing gui_topology app:
    ryu-manager --observe-links app/gui_topology/gui_topology.py routing.py
and based on the web browser, the rules in each switch, their connections, ports can be observed.

'''

class Routing(arpcache.ARPCache):#ARPcache already inherits Topology
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Routing, self).__init__(*args, **kwargs)
        print("\tbasic routing for ICMP/TCP/UDP based on SPF")#shortest path first
        self.count = 1 # to count the number of switch entrance from event switch_enter
        self.cookie = 0x100
        self.HARD_TIMEOUT = 3000 # amount of time (in second) a rule exists in the switch if hard_timeout is set for that rule.
        config = self.parse_config()
        print("config = %s"%config)
        self.priority = config[0]
        #self.excluded_info = {0x0000000000000007:['192.168.1.3']}#to let this app work well with SBEpLB, but not really a good solution
        #self.excluded_info = {}
        self.ei = config[1]
        print("self.excluded_info = %s"%self.ei)


    def parse_config(self):
        priority = None
        ei = [[],[],[],[]]#ei = excluded_info, ei[0]=[dpid for eplb], ei[1] = [proxy_server's IP for eplb], ei[2] = [dpid for pplb], ei[3] = [list of src IPs the pplb concerns]
        with open("routing_config_global") as globalfile: 
        # exemplary input file:
        #2 #priority
        #all #target switches
        #1 #app config
            i = 1
            for line in globalfile:
                line = line.strip()# preprocess line 
                #print("line = %s"%line)
                if i == 1: # first line, priority
                    priority = int(line.split()[0])
                if i == 2: # second line, target switches, for routing it is all switches
                    pass
                if i == 3: # third line, app config (see the parameter space)
                    appconfig = int(line.split()[0])
                    #print("bw_time=%s"%bw_time)
                    break
                i += 1

        with open("routing_excluded_info") as infile: 
        # exemplary input file:
        #7 #target switches, first two lines target eplb
        #192.168.1.3 00:16:3e:00:00:43 #proxy server of eplb
        #0x0000000000000005 0x0000000000000006 #datapath id, lines 3 and 4 target pplb
        #192.168.1.3 00:16:3e:00:00:43 192.168.1.4 00:16:3e:00:00:44 #servers whose traffic will be balanced on as many paths as possible.
            i = 1
            for line in infile:
                line = line.strip()# preprocess line 
                #print("line = %s"%line)
                if (line==""):
                    print("empty line!")
                    i+=1
                    continue
                if i == 1: # first line, list of dpid for eplb
                    dpid_str = line.split()
                    for dpid in dpid_str:
                        if dpid[0] == '#': # a comment
                            break
                        hex_int = int(dpid,16) 
                        ei[0].append(hex_int)
                        #print("blp = %s"%blp) 
                if i == 2: # second line, proxy server of eplb in format "IP MAC"
                    string = line.split()
                    ei[1].append(string[0])
                if i == 3: # third line, list of dpid for pplb
                    dpid_str = line.split()
                    for dpid in dpid_str:
                        if dpid[0] == '#': # a comment
                            break
                        hex_int = int(dpid,16) 
                        ei[2].append(hex_int)
                if i == 4: # fourth line, list of sources the pplb concerns while performing path balancing 
                    string = line.split()
                    index = 0
                    while index<len(string) and string[index][0] != '#':
                        ei[3].append((string[index],string[index+1]))
                        index += 2
                    break
                i += 1

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
            #ignore lldp packet
            return

	#print("routing packet in handler")

        eth_dst = eth.dst
        eth_src = eth.src
        dpid = datapath.id
        print("\nRouting - packet in dpid: %s, src: %s, dst: %s, in_port: %s" %(dpid, eth_src, eth_dst, in_port) )
        
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip = pkt.get_protocols(ipv4.ipv4)[0]
            print("ip = "),
            print(ip)
            ip_src = ip.src
            ip_dst = ip.dst
            #TODO install a path from source to dst here if there is no exception from shortest path realization, otherwise, install a rule at the switch to drop this for a timeout to save the controller's resource.
            #if eth_src == self.arp_cache_db[ip_src]['mac'] and eth_dst == self.arp_cache_db[ip_dst]['mac']:
            if ip.proto != in_proto.IPPROTO_TCP and ip.proto != in_proto.IPPROTO_UDP and ip.proto != in_proto.IPPROTO_ICMP:#only handle TCP/UDP/ICMP packets
                return

            #if dpid in self.excluded_info and ip_dst in self.excluded_info[dpid] and ip.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP] :
            if dpid in self.ei[0] and ip_dst in self.ei[1] and ip.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP] :
                print("is excluded for routing (target eplb), no more processing")
                return
            if dpid in self.ei[2] and (ip_src,eth_src) in self.ei[3] and ip.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP] :
                print("is excluded for routing (target pplb), no more processing")
                return
            if ip_src in self.arp_cache_db and ip_dst in self.arp_cache_db and eth_src == self.arp_cache_db[ip_src]['mac'] and eth_dst == self.arp_cache_db[ip_dst]['mac']:
                print("receive an ip packet with mac src and dst in arp_cache_db, install rule on switch if there is no exception for shortest path, otherwise, drop this message for a predefined timeout")
                try:
                    #path = nx.shortest_path(self.net, self.arp_cache_db[ip_src]['dpid'], self.arp_cache_db[ip_dst]['dpid']) #version 3.0 and prior: don't care the asked switch but the whole path from src to dst
		    path = nx.shortest_path(self.net, self.arp_cache_db[ip_src]['dpid'], self.arp_cache_db[ip_dst]['dpid'])
		    if dpid in path:
		       print("path = %s" %path)
	               #self.add_path_flow_layer4(supposed_shortest_path, eth_src, eth_dst,ip.proto) #this shadows the SBEpLB app. so install in each node instead.
                       if dpid != path[len(path)-1]:#last node should be treated specially, since it connects to an end-point, not another switch
                           print("install rules on node %s" % (dpid) )
                           next_node = path[path.index(dpid)+1]#remember, node and next_node are dpid
                           out_port = self.net[dpid][next_node]['port']
                           if (out_port == in_port):
                               out_port = self.choose_alternative_outport(dpid, self.arp_cache_db[ip_dst]['dpid'], out_port)
                           node_action = [parser.OFPActionOutput(out_port)]

                           data = msg.data
                           out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=node_action,data=data)
                           datapath.send_msg(out)

                           node_match = parser.OFPMatch(in_port=in_port,eth_type=ether_types.ETH_TYPE_IP,ip_proto=ip.proto,eth_src=eth_src, eth_dst=eth_dst)
                           utility.add_flow_with_hard_timeout(self.cookie, datapath, self.priority, node_match, node_action, self.HARD_TIMEOUT) #since path may change, so install rule on the switch with hard_timeout.
                       else:#last node
                           print("install rules on last node of the path, node %s" %(dpid))
                           out_port = None
                           for i in self.arp_cache_db:
                               if self.arp_cache_db[i]['mac'] == eth_dst:
                                   out_port = self.arp_cache_db[i]['port']
                                   break
                           action = [parser.OFPActionOutput(out_port)]

                           data = msg.data
                           out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=action,data=data)
                           datapath.send_msg(out)

                           match = parser.OFPMatch(in_port=in_port,eth_type=ether_types.ETH_TYPE_IP,ip_proto=ip.proto,eth_dst=eth_dst)
                           utility.add_flow_with_hard_timeout(self.cookie, datapath,self.priority,match,action,self.HARD_TIMEOUT)
                    else:#the asking switch is not on the path, install a rule with a matching on destination only
                       print("node %s not in shortest path from src to dst"%dpid)
                       path = nx.shortest_path(self.net, dpid,self.arp_cache_db[ip_dst]['dpid'])
                       print("path=%s"%path)
                       if dpid != path[len(path)-1]:#last node should be treated specially, since it connects to an end-point, not another switch
                           print("install rules on node %s" % (dpid) )
                           next_node = path[path.index(dpid)+1]#remember, node and next_node are dpid
                           out_port = self.net[dpid][next_node]['port']
                           if (out_port == in_port):
                               out_port = self.choose_alternative_outport(dpid, self.arp_cache_db[ip_dst]['dpid'], out_port)
                           node_action = [parser.OFPActionOutput(out_port)]

                           data = msg.data
                           out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=node_action,data=data)
                           datapath.send_msg(out)

                           node_match = parser.OFPMatch(in_port=in_port,eth_type=ether_types.ETH_TYPE_IP,ip_proto=ip.proto,eth_src=eth_src, eth_dst=eth_dst)
                           utility.add_flow_with_hard_timeout(self.cookie, datapath, self.priority, node_match, node_action, self.HARD_TIMEOUT) #since path may change, so install rule on the switch with hard_timeout.
                       else:#last node
                           print("install rules on last node of the path, node %s" %(dpid))
                           out_port = None
                           for i in self.arp_cache_db:
                               if self.arp_cache_db[i]['mac'] == eth_dst:
                                   out_port = self.arp_cache_db[i]['port']
                                   break
                           action = [parser.OFPActionOutput(out_port)]

                           data = msg.data
                           out = parser.OFPPacketOut(datapath=datapath,buffer_id=datapath.ofproto.OFP_NO_BUFFER,in_port=datapath.ofproto.OFPP_CONTROLLER,actions=action,data=data)
                           datapath.send_msg(out)

                           match = parser.OFPMatch(in_port=in_port,eth_type=ether_types.ETH_TYPE_IP,ip_proto=ip.proto,eth_dst=eth_dst)
                           utility.add_flow_with_hard_timeout(self.cookie, datapath,self.priority,match,action,self.HARD_TIMEOUT)
                        
                except nx.NetworkXNoPath:
                    print("There is no path, install a drop rule to stop this switch from bother the controller for a while ")
                    match = parser.OFPMatch(in_port=in_port,eth_src=eth_src, eth_dst=eth_dst, eth_type=ether_types.ETH_TYPE_IP, ip_proto=ip.proto)
                    action = [] #empty action means drop
                    '''install drop rule for this packet for 10 seconds at the asking switch'''
                    utility.add_flow_with_hard_timeout(self.cookie, datapath, self.priority, match, action, 10)#timeout = 10s

            #else: #should this app actively detect the mapping between ip and mac, so the controller receive an ip packet whose information is not in arp_cache_db, if it does not actively perform discovery (do shorcut flood), it will continuously receive this message until an arp_request comes. But if it does the shortcut flood every time such an ip packet comes, it may overwhelm the end-points, there may be weird ip packet with destination is not within this sdn network, so better not do active discovery.
            else:#this else is different from version 4.0
                    print("actively detect destination by sending shortcut ARP request")

                    arp_req = packet.Packet()
                    arp_req.add_protocol(ethernet.ethernet(
                        ethertype=ether_types.ETH_TYPE_ARP, dst='ff:ff:ff:ff:ff:ff', src=eth_src))
                    arp_req.add_protocol(arp.arp(
                        opcode = arp.ARP_REQUEST, src_mac=eth_src, dst_mac='00:00:00:00:00:00',
                        src_ip=ip_src, dst_ip=ip_dst))
                    arp_req.serialize()

                    for fdpid in self.non_interswitch_ports:#flood datapath id --> fdpid
		    	fdatapath = self.datapathmap[fdpid]
                        fdata = arp_req.data
                        fparser = fdatapath.ofproto_parser
                        fofproto = fdatapath.ofproto
                        factions = [fparser.OFPActionOutput(i) for i in list(self.non_interswitch_ports[fdpid])]
                        fout = fparser.OFPPacketOut(datapath=fdatapath, buffer_id=fofproto.OFP_NO_BUFFER,in_port=fofproto.OFPP_CONTROLLER, actions=factions, data=fdata)
                        fdatapath.send_msg(fout)

    def choose_alternative_outport(self, dpid, target_dpid, port):
        '''
        the port (output port chosen by shortest path first algorithm from dpid to target) is the same as the in_port of the packet in the packet-in event from the device dpid, so have to choose an alternative output port
        '''
        for path in sorted(nx.all_simple_paths(self.net, dpid,target_dpid), key = lambda x: len(x)):
            #path is sorted by its length, i.e., the number of traversed nodes
            print(path)
            next_node = path[path.index(dpid)+1]
            out_port = self.net[dpid][next_node]['port']
            if out_port == port:
                continue # move to the next path since this path has the same out_port 
            else:
                break
        if (out_port == port):
            self.logger.error("ERROR: outport is always equal to in_port! Traffic loop occurs likely! dpid = %s, port = %s",dpid,port)
        return out_port

