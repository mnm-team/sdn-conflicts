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

from operator import attrgetter
from ryu.base import app_manager

#import plb_config as conf
import struct
import socket

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub


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

#import topology
import arpcache
import utility
import networkx as nx

'''
To be run with routing app, since it does not provide routing function for all connection but based on the monitoring information to modify the network behaviour.
'''

#class PLB(app_manager.RyuApp):
#class PLB(topology.Topology):
class PLB(arpcache.ARPCache):

    def __init__(self, *args, **kwargs):
        super(PLB, self).__init__(*args, **kwargs)
        print("\tPLB flexible, topology aware")
        config = self.parse_config_plb()
        print("config = %s"%config)
        self.priority = config[0]
        self.blp = config[1]
        #self.blp =[0x0000000000000007, 0x0000000000000001] #blp = balance_point
        #self.observed_port = 2
        #self.bw_time = 5 #time to calculate bandwidth
        self.bw_time = config[2]
        #self.bw_threshold = 25 #Mbps
        self.bw_threshold = config[3]

        self.cookie = 0x300
        #self.excluded_ports={self.blp[0]:[], self.blp[1]:[]} #port to exclude when considering load balancing, e.g., port to IDPS server
        self.excluded_ports = {}
        for i in self.blp:
            self.excluded_ports[i] = []
        #print("self.excluded_ports =%s"%self.excluded_ports)

        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        #self.past = {self.blp[0]:{}, self.blp[1]:{}}
        self.past = {}
        self.present = {}
        self.bw = {}
        for i in self.blp:
            self.past[i] = {}
            self.present[i] = {}
            self.bw[i] = {}
        print("past = %s\npresent=%s\nbw=%s"%(self.past,self.present,self.bw))

        #self.present = {self.blp[0]:{}, self.blp[1]:{}}
        #self.present = {dpid1:{port1:[tx_byte,{(flow0_cookie,priority,match,action):flow0_bytecount,(flow1_cookie,priority,match,action):flow1_bytecout,...}], port2:[tx_byte,{}...]}, dpid2:{port1:[tx_byte,{}], port2:[tx_byte,{}]...]}}
        #self.bw = {self.blp[0]:{}, self.blp[1]:{}}
        #self.bw={dpid1:{port1:[port1 bw,{(flow0_cookie,priority,match,action):flow0_bw, (flow1_match,...):flow1_bw}], port2:[port2 bw,{tuple1:bw,tutple2:bw,...}]},dpid2:{}}

    def parse_config_plb(self):
        # exemplary input file:
        # 2 #priority, although it's not really used in this app, but that's for a consistent template
        # 0x0000000000000007 0x0000000000000001 #balance point
        # 5   #time to calculate bw
        # 25  #bw_threshold in Mbps
        priority = None
        blp = []
        bw_time = None
        bw_threshold = None
        with open("plb_config_global") as globalfile: 
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
                if i == 3: # third line, app config (see the parameter space)
                    appconfig = int(line.split()[0])
                    #print("bw_time=%s"%bw_time)
                    break
                i += 1
        with open("plb_config_local") as localfile: 
            i = 1
            for line in localfile:
                line = line.strip()# preprocess line 
                if i == 1: # third line, bw_time
                    bw_time = int(line.split()[0])
                    #print("bw_time=%s"%bw_time)
                if i == 2: # fourth line, threshold
                    bw_threshold = int(line.split()[0])
                    #print("bw_threshold=%s"%bw_threshold)
                    break # only need to process first 2 lines
                i += 1
        return [priority, blp, bw_time, bw_threshold]

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        #print("Debug: EventOFPStateChange")
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                if dp.id in self.blp:
                   self._request_stats(dp)
            hub.sleep(self.bw_time)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id

        #print("\n\t FlowStat: dpid = %s"%dpid)

        #update self.present and self.bw from empty, otherwise, they accumulate the old, out-of-date flows
        #update self.past in the end to the current status of the flow tables after self.present and self.bw are done.
        for port in self.bw[dpid]:
            self.present[dpid][port][1] = {}
            self.bw[dpid][port][1] = {}

        #print("FlowStatsReply:\n\tbw=%s\n\tpresent=%s\n\tpast=%s"%(self.bw,self.present,self.past))

        for stat in [flow for flow in body]:
            actions = stat.instructions[0].actions #actions is a list []
            #print("len(actions)=%s"%len(actions))
            if len(actions) == 1 and actions[0].port in [ofproto_v1_3.OFPP_CONTROLLER, ofproto_v1_3.OFPP_LOCAL, self.excluded_ports]: #don't have to consider flows for one of these ports only
                #print("continue")
                continue
            #if actions[len(actions)-1] not in [ofproto_v1_3.OFPP_CONTROLLER, ofproto_v1_3.OFPP_LOCAL]:
            #print("\nstat=%s"%stat)
            curtup = (stat.cookie,stat.priority,str(stat.match),str(stat.instructions[0])) # curtup = current tuple
            real_curtup=(stat.cookie,stat.priority,stat.match,stat.instructions[0])
            #curtup = (stat.cookie,stat.priority) # curtup = current tuple
            for act in actions:
                if hasattr(act, 'port'):
                    #print("port = %s"%act.port)
                    if act.port not in self.bw[dpid]:#bogus flow if after everything converges, e.g., after 2 cycles of self.bw_time
                        #print("port not in 'logical physical' port list, bogus flow")
                        continue
                    try:
                        self.present[dpid][act.port][1][curtup] = stat.byte_count
                        #print(curtup)
                        #print("past curtup = %s"%self.past[dpid][act.port][1])
                        #remember: self.present = {dpid1:{port1:[txbyte,{(flow1_match, action,...):bytecount, ...}...]...}...}
                        #print(self.past[dpid][act.port][1])
                        self.bw[dpid][act.port][1][real_curtup] = self.calculate_bw(stat.byte_count,self.past[dpid][act.port][1][curtup])
                    except (KeyError, IndexError):
                        print("no problem, port not in logically physical port, ignore it")
                        if stat.duration_sec != 0:
                            self.bw[dpid][act.port][1][real_curtup] = stat.byte_count/8.0/stat.duration_sec
                    #except IndexError:
                    #    self.present[dpid][act.port].
                    try:
                        self.past[dpid][act.port][1][curtup] = stat.byte_count
                    except KeyError:
                        print("maybe self.past has not yet been initialized with the tuple")

#        print("FlowStatsReply:\n\tFinally: bw=%s"%(self.bw))
        for port in self.bw[dpid]:
            self.past[dpid][port][1] = self.present[dpid][port][1]
        #print("\n\tupdated past=%s"%self.past)


    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        print("\n\t PortStat: dpid = %s"%dpid)
        if ev.msg.datapath.id in self.blp:
            self.logger.info('datapath         port     '
                         'rx-pkts  rx-bytes rx-error '
                         'tx-pkts  tx-bytes tx-error')
            self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- --------')
            for stat in sorted(body, key=attrgetter('port_no')):
                self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)
                #print("port_no = %s, port controller=%s"%(stat.port_no, ofproto_v1_3.OFPP_CONTROLLER))
                if stat.port_no != ofproto_v1_3.OFPP_CONTROLLER and stat.port_no != ofproto_v1_3.OFPP_LOCAL and stat.port_no not in self.excluded_ports[dpid]:
                    try:
                        if len(self.non_interswitch_ports[dpid])>0 and stat.port_no in self.non_interswitch_ports[dpid]:
                            continue
                    except KeyError:
                        print("PLB KeyError1")

                    self.present[dpid].setdefault(stat.port_no,[-1,{}])
                    self.bw[dpid].setdefault(stat.port_no,[-1,{}])
                    self.past[dpid].setdefault(stat.port_no,[-1,{}])
                    #print("assign tx_bytes for self.present")
                    try: 
                        self.present[dpid][stat.port_no][0] = stat.tx_bytes
                        #print("come here 1")
                        if self.past[dpid][stat.port_no][0] == -1:
                        #    print("come here 2")
                            self.bw[dpid][stat.port_no][0] = stat.tx_bytes/8.0/stat.duration_sec
                        else:
                        #    print("come here 3")
                            self.bw[dpid][stat.port_no][0] = self.calculate_bw(self.present[dpid][stat.port_no][0], self.past[dpid][stat.port_no][0])
                        if self.bw[dpid][stat.port_no][0] >= self.bw_threshold:#balance path if threshold is exceeded
                            print("bw_threshold is exceeded!port= %s, all_flows= %s"%(stat.port_no,self.bw[dpid][stat.port_no]))
                        #    print("come here 4")
                            #self.balance_path_load(dpid,stat.port_no)
                            self.balance_path_load(ev.msg.datapath,stat.port_no)
                    except KeyError:
                        print("PLB KeyError2!!!")
                    except IndexError:
                        print("PLB IndexError1!")
                    #print("assign tx_bytes for self.past")
                    #self.past[dpid][stat.port_no]=[stat.tx_bytes,{}] # initialize the whole structure of self.present here.
                    self.past[dpid][stat.port_no][0]=stat.tx_bytes 
            #print("PortStat:\n\tpresent = %s\n\tbw = %s"%(self.present, self.bw))
#            print("PortStat:\tbw = %s"%self.bw)


    def mac_format(self, mac_string):
        return ':'.join('%02x' % ord(b) for b in mac_string)

    def int2ip(self, addr):
        return socket.inet_ntoa(struct.pack("!I", addr))
    
    def calculate_bw(self, byte_new, byte_old): # in Mbps
        return (byte_new - byte_old)*8.0/self.bw_time/1000.0/1000.0

    def balance_path_load(self,datapath,port):
        '''
        This port of dpid is overloaded, extract the largest flow and divert it in another direction
        (port) if it does not make that port overloaded
        '''
        dpid = datapath.id
        if len(self.bw[dpid][port][1]) == 1:#there is only one flow, ignore
            print("there is only one flow, ignore")
            return

        sorted_flow = sorted(self.bw[dpid][port][1].items(), key=lambda kv:kv[1], reverse=True)
        #return value are a list of tuples of (key,value) of original dictionary
#        print("sorted_flow = %s"%sorted_flow)
        #extract the destination, maybe from action setField or from match of destination Field.
        elp_flow = sorted_flow[0]#elephant flow
        print("Elephant flow = %s"%str(elp_flow))
        dest_list = self.get_destination(elp_flow[0][2],elp_flow[0][3].actions)
        print("dest list = %s"%dest_list)

        '''
        check all paths from dpid to dest, if a path entails the outport different the current port, consider it if that port bw is small and will not be overloaded after switching this flow to that port.
        '''
        #extract target in dpid from dest_list
        target_dpid = None
        if dest_list[1] != None:
            target_dpid = self.arp_cache_db[dest_list[1]]['dpid']
        else:
            for tmp_ip in self.arp_cache_db:
                if self.arp_cache_db[tmp_ip]['mac'] == dest_list[0]:
                    target_dpid = self.arp_cache_db[tmp_ip]['dpid']
                    break
        print("target dpid = %s"%target_dpid)

        for path in sorted(nx.all_simple_paths(self.net, dpid,target_dpid), key = lambda x: len(x)):
            #path is sorted by its length, i.e., the number of traversed nodes
            print(path)
            next_node = path[path.index(dpid)+1]
            out_port = self.net[dpid][next_node]['port']
            if out_port == port:
                print("continue")
                continue # move to the next path since this path has the same out_port 
            if self.bw[dpid][out_port][0]+elp_flow[1] < self.bw_threshold: #bw of the new port = current bw of that port + bw of the moved flow
                #move the current elephant flow to this path by changing the current port to the new port
                actions = elp_flow[0][3].actions
                new_actions = []
                print("old actions = %s"%actions)
                for act in actions:
                    if hasattr(act, 'port'):
                        act.port = out_port #change current port to out_port for the elp_flow
                    new_actions.append(act)
                print("new actions = %s"%new_actions)
                #install flow for the current switch having dpid:
                #utility.add_flow_with_hard_timeout(elp_flow[0][0],datapath,elp_flow[0][1],elp_flow[0][2],new_actions,self.HARD_TIMEOUT)
                #utility.add_flow_with_hard_timeout(self.cookie,datapath,elp_flow[0][1],elp_flow[0][2],new_actions,self.HARD_TIMEOUT)
                utility.add_flow_with_hard_timeout(self.cookie,datapath,self.priority,elp_flow[0][2],new_actions,self.HARD_TIMEOUT)
                print("finish changing the flow: %s to new actions %s"%(str(elp_flow[0]),new_actions))
                break



    def get_destination(self,match,action):
        dest_list = [None,None] #return dest_list including either [eth_dst, ipv4_dst or ipv6_dst]
        for act in action:
            if hasattr(act,'field'):
                if isinstance(act.field, ofproto_v1_3_parser.MTEthDst):
                    dest_list[0] = self.mac_format(act.field.value)
                    print("detect an eth_dst: %s"%dest_list[0])
                elif isinstance(act.field, ofproto_v1_3_parser.MTIPV4Dst):
                    dest_list[1] = self.int2ip(act.field.value)
                    print("detect an ipv4_dst: %s"%dest_list[1])
                #if isinstance(act.field, ofproto_v1_3_parser.MTIPv6Dst):
        if dest_list[0] != None or dest_list[1] != None:
                    return dest_list
        try:
            eth_dst = match['eth_dst']
            dest_list[0] = eth_dst
        except KeyError:
            #print("get dest: PLB KeyError 1")
            pass
        try:
            ipv4_dst = match['ipv4_dst']
            dest_list[1] = ipv4_dst
        except KeyError:
            #print("get dest: PLB KeyError 2")
            pass

        return dest_list
