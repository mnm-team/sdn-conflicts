__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '2.0' - 20201124
use utility to send add_flow event (flowmod) to detector, detector will handle the rest: checking for conflicts and installing rules. the old utility is renamed to pureutility.

__version__ = '1.0' - 2019 or earlier

'''

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

# import plb_config as conf
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

# import topology
import arpcache
import utility_detector as utility
import networkx as nx
import json
import globalconfig

'''
To be run with routing app, since it does not provide routing function for all connection but based on the monitoring information to modify the network behaviour.
'''

class PLB(arpcache.ARPCache, utility.Utility):

    def __init__(self, *args, **kwargs):
        super(PLB, self).__init__(*args, **kwargs)
        print("\tPLB flexible, topology aware")
        config = self.parse_config_plb()
        print("config = %s" % config)
        self.priority = config[0]
        self.blp = config[1]
        # time to calculate bandwidth
        self.bw_time = config[2]
        self.cookie = 0x300
        # when not to consider in load balancing, e.g., port to IDPS server
        self.excluded_ports = {}
        for i,v in self.blp.items():
            self.excluded_ports[i] = []
       
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        # self.past = {self.blp[0]:{}, self.blp[1]:{}}
        self.past = {}
        self.present = {}
        self.bw = {}
        for i,v in self.blp.items():
            self.past[i] = {}
            self.present[i] = {}
            self.bw[i] = {}
        print("past = %s\npresent=%s\nbw=%s" %
              (self.past, self.present, self.bw))

    def parse_config_plb(self):
        priority, blp = globalconfig.parseGlobalConfig("plb")
        # load local config with invariants for each balance point
        # if the balance point is one of the target switches, the invariants are added
        local_config = json.load(open("plb_config_local", "r"))
        for key,value in local_config["switchConfigs"].items():
            hex_int = int(key, 16)
            if hex_int in blp:
                blp[hex_int] = value
        return [priority, blp, local_config["bw_time"]]

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
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
        # update self.present and self.bw from empty, otherwise, they accumulate the old, out-of-date flows
        # update self.past in the end to the current status of the flow tables
        # after self.present and self.bw are done.
        for port in self.bw[dpid]:
            self.present[dpid][port][1] = {}
            self.bw[dpid][port][1] = {}

        for stat in [flow for flow in body]:
            actions = stat.instructions[0].actions  # actions is a list []
            if len(actions) == 1 and actions[0].port in [ofproto_v1_3.OFPP_CONTROLLER, ofproto_v1_3.OFPP_LOCAL, self.excluded_ports]:  # don't have to consider flows for one of these ports only
                # print("continue")
                continue
            curtup = (stat.cookie, stat.priority, str(stat.match),
                      str(stat.instructions[0]))  # curtup = current tuple
            real_curtup = (
                stat.cookie, stat.priority, stat.match, stat.instructions[0])
            # curtup = (stat.cookie,stat.priority) # curtup = current tuple
            for act in actions:
                if hasattr(act, 'port'):
                    if act.port not in self.bw[dpid]:  # bogus flow if after everything converges, e.g., after 2 cycles of self.bw_time
                        continue
                    try:
                        self.present[dpid][act.port][
                            1][curtup] = stat.byte_count
                        self.bw[dpid][act.port][1][real_curtup] = self.calculate_bw(
                            stat.byte_count, self.past[dpid][act.port][1][curtup])
                    except (KeyError, IndexError):
                        print(
                            "no problem, port not in logically physical port, ignore it")
                        if stat.duration_sec != 0:
                            self.bw[dpid][act.port][1][
                                real_curtup] = stat.byte_count / 8.0 / stat.duration_sec
                    try:
                        self.past[dpid][act.port][1][curtup] = stat.byte_count
                    except KeyError:
                        print(
                            "maybe self.past has not yet been initialized with the tuple")

        for port in self.bw[dpid]:
            self.past[dpid][port][1] = self.present[dpid][port][1]

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        print("\n\t PortStat: dpid = %s" % dpid)
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
                if stat.port_no != ofproto_v1_3.OFPP_CONTROLLER and stat.port_no != ofproto_v1_3.OFPP_LOCAL and stat.port_no not in self.excluded_ports[dpid]:
                    try:
                        if len(self.non_interswitch_ports[dpid]) > 0 and stat.port_no in self.non_interswitch_ports[dpid]:
                            continue
                    except KeyError:
                        print("PLB KeyError1")

                    self.present[dpid].setdefault(stat.port_no, [-1, {}])
                    self.bw[dpid].setdefault(stat.port_no, [-1, {}])
                    self.past[dpid].setdefault(stat.port_no, [-1, {}])
                    try:
                        self.present[dpid][stat.port_no][0] = stat.tx_bytes
                        if self.past[dpid][stat.port_no][0] == -1:
                            self.bw[dpid][stat.port_no][
                                0] = stat.tx_bytes / 8.0 / stat.duration_sec
                        else:
                            self.bw[dpid][stat.port_no][0] = self.calculate_bw(
                                self.present[dpid][stat.port_no][0], self.past[dpid][stat.port_no][0])
                        if self.bw[dpid][stat.port_no][0] >= self.blp[dpid]["bw_threshold"]:  # balance path if threshold is exceeded
                            print("bw_threshold is exceeded!port= %s, all_flows= %s" %
                                  (stat.port_no, self.bw[dpid][stat.port_no]))
                            self.balance_path_load(
                                ev.msg.datapath, stat.port_no)
                    except KeyError:
                        print("PLB KeyError2!!!")
                    except IndexError:
                        print("PLB IndexError1!")
                    # initialize the whole structure of self.present here.
                    self.past[dpid][stat.port_no][0] = stat.tx_bytes

    def mac_format(self, mac_string):
        return ':'.join('%02x' % ord(b) for b in mac_string)

    def int2ip(self, addr):
        return socket.inet_ntoa(struct.pack("!I", addr))

    def calculate_bw(self, byte_new, byte_old):  # in Mbps
        return (byte_new - byte_old) * 8.0 / self.bw_time / 1000.0 / 1000.0

    def balance_path_load(self, datapath, port):
        '''
        This port of dpid is overloaded, extract the largest flow and divert it in another direction
        (port) if it does not make that port overloaded
        '''
        dpid = datapath.id
        if len(self.bw[dpid][port][1]) == 1:  # there is only one flow, ignore
            print("there is only one flow, ignore")
            return

        sorted_flow = sorted(self.bw[dpid][port][
                             1].items(), key=lambda kv: kv[1], reverse=True)
        # return value are a list of tuples of (key,value) of original dictionary
        # extract the destination, maybe from action setField or from match of
        # destination Field.
        elp_flow = sorted_flow[0]  # elephant flow
        print("Elephant flow = %s" % str(elp_flow))
        dest_list = self.get_destination(
            elp_flow[0][2], elp_flow[0][3].actions)
        print("dest list = %s" % dest_list)

        '''
        check all paths from dpid to dest, if a path entails the outport different the current port, consider it if that port bw is small and will not be overloaded after switching this flow to that port.
        '''
        # extract target in dpid from dest_list
        target_dpid = None
        if dest_list[1] != None:
            target_dpid = self.arp_cache_db[dest_list[1]]['dpid']
        else:
            for tmp_ip in self.arp_cache_db:
                if self.arp_cache_db[tmp_ip]['mac'] == dest_list[0]:
                    target_dpid = self.arp_cache_db[tmp_ip]['dpid']
                    break
        print("target dpid = %s" % target_dpid)

        for path in sorted(nx.all_simple_paths(self.net, dpid, target_dpid), key=lambda x: len(x)):
            # path is sorted by its length, i.e., the number of traversed nodes
            print(path)
            next_node = path[path.index(dpid) + 1]
            out_port = self.get_out_port_for_link(dpid, next_node)
            if out_port == port:
                print("continue")
                continue  # move to the next path since this path has the same out_port
            if self.bw[dpid][out_port][0] + elp_flow[1] < self.blp[dpid]["bw_threshold"]:  # bw of the new port = current bw of that port + bw of the moved flow
                # move the current elephant flow to this path by changing the
                # current port to the new port
                actions = elp_flow[0][3].actions
                new_actions = []
                print("old actions = %s" % actions)
                for act in actions:
                    if hasattr(act, 'port'):
                        act.port = out_port  # change current port to out_port for the elp_flow
                    new_actions.append(act)
                print("new actions = %s" % new_actions)
                # install flow for the current switch having dpid:
                self.add_flow_with_hard_timeout(
                    self.cookie, datapath, self.priority, elp_flow[0][2], new_actions, self.HARD_TIMEOUT)
                print("finish changing the flow: %s to new actions %s" %
                      (str(elp_flow[0]), new_actions))
                break

    def get_destination(self, match, action):
        dest_list = [None, None]
            #return dest_list including either [eth_dst, ipv4_dst or ipv6_dst]
        for act in action:
            if hasattr(act, 'field'):
                if isinstance(act.field, ofproto_v1_3_parser.MTEthDst):
                    dest_list[0] = self.mac_format(act.field.value)
                    print("detect an eth_dst: %s" % dest_list[0])
                elif isinstance(act.field, ofproto_v1_3_parser.MTIPV4Dst):
                    dest_list[1] = self.int2ip(act.field.value)
                    print("detect an ipv4_dst: %s" % dest_list[1])
        if dest_list[0] != None or dest_list[1] != None:
            return dest_list
        try:
            eth_dst = match['eth_dst']
            dest_list[0] = eth_dst
        except KeyError:
            # print("get dest: PLB KeyError 1")
            pass
        try:
            ipv4_dst = match['ipv4_dst']
            dest_list[1] = ipv4_dst
        except KeyError:
            # print("get dest: PLB KeyError 2")
            pass

        return dest_list
