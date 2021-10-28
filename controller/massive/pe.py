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
__version__ = '1.0'
'''

class PathEnforcer(arpcache.ARPCache, utility.Utility):

    def __init__(self, *args, **kwargs):
        super(PathEnforcer, self).__init__(*args, **kwargs)
        self.logger.info("\tPath Enforcer for IP,TCP,UDP protocols, topology aware")
        config = self.parse_config()
        self.logger.info("config = %s" % config)
        self.priority = config[0]
        # blp is map of datapath ids
        # for every blp the mandatory jump destination is added
        # and the protocols to filter the flows that should be sent to 
        # the mandatory jump
        self.blp = config[1]
        self.cookie = 0x990
        self.flows_key = "handled_flows"
        self.protos_key = "protos"
        self.jump_key = "jumps"
        self.IDLE_TIMEOUT = 1800  # if a flow is idle for 1800s, remove it since it is very specific
        # remember handled flows to address multiple packet-ins for same flow
        self.handled_flows = {}
        for blp in self.blp:
            self.blp[blp][self.flows_key] = {}


    def parse_config(self):
        priority, blp = globalconfig.parseGlobalConfig("pe")
        # load local config, contains a list of (ip string,mac string)
        blp = globalconfig.localConfigPE(blp)
        return [priority, blp]


    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def flow_removed_handler(self, evt):
        msg = evt.msg
        dpid = msg.datapath.id
        match = msg.match
        try:
            # we only need to handle removal of own flow insertions
            # and only for target switches
            # other inserted flows in switches will be removed due to idle timeout
            # at some point
            if not match.cookie == self.cookie or dpid not in self.blp:
                return
            
            hashable_match = str(match)
            del self.blp[dpid][self.flows_key][hashable_match]
            log_msg = "PathEnforcer, removing entry: {} in dpid {}"
            self.logger.debug(log_msg.format(hashable_match,dpid))

        except Exception as e:
            self.logger.debug("ERROR: Something went wrong in PathEnforcer while removing entry: {}"
                                .format(e))


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        if dpid not in self.blp:
            return

        blp = self.blp[dpid]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        in_port = msg.match['in_port']

        match = None
        reverseMatch = None # reverse rule needs to be inserted in first switch to prevent a loop
        hashable_match = None
        # only handle IP traffic in general or TCP and UDP
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip = pkt.get_protocols(ipv4.ipv4)[0]
            # an empty protos list means we want to handle all ip traffic and ports don't matter
            if not len(blp[self.protos_key]) or ip.proto in blp[self.protos_key]:
                match = parser.OFPMatch(eth_type=eth.ethertype, ip_proto=ip.proto, ipv4_src=ip.src, ipv4_dst=ip.dst)
                reverse_match = parser.OFPMatch(eth_type=eth.ethertype, ip_proto=ip.proto, ipv4_src=ip.dst, ipv4_dst=ip.src)
                hashable_match = str(match)
            else:
              # no hit on packet or protos, routing should handle this
              return
        else:
            # no IP traffic, so ignore the packet
            return

        if hashable_match not in blp[self.flows_key]:
            self.logger.info("PathEnforcer handling flow: {} on dpid {}"
                                .format(hashable_match,dpid))
            # add handled flow and remember in_port
            blp[self.flows_key][hashable_match] = in_port
            
            # get the mandatory jump nodes for current blp and calculate the path
            # from jump node to jump node to retain the order of the jumps
            dpids = self.blp[dpid][self.jump_key]
            
            # check if this path actually makes sense or if the shortest path 
            # to the destination will route backwards over the jumps
            target_dpid = self.arp_cache_db[ip.dst]['dpid']

            # check if target host is directly connected to the current dpid
            if dpid == target_dpid:
              # don't add a backward flow since it could be routed over jumps
              self.logger.info("PathEnforcer, last node dpid {} to host {}".format(target_dpid, ip.dst))
              out_port = self.arp_cache_db[ip.dst]['port']
              self.add_short_circuit_path(msg, match, out_port)
              return

            # path from last jump switch to target
            check_path = nx.shortest_path(self.net, dpids[len(dpids)-1], target_dpid)
            if dpid in check_path:
              # this path will lead back over the current dpid!
              # if there is a shortest path that leads over dpid
              # there is a risk of conflicts, so don't route over jumps
              # don't add a backward flow since it could be routed over jumps
              self.logger.info("PathEnforcer, jump path not valid to dpid {}".format(target_dpid))
              self.logger.info("PathEnforcer, sending packet to next dpid on path to target")
              path = nx.shortest_path(self.net, dpid, target_dpid)
              next_dpid = path[0]
              if dpid == next_dpid and len(path) > 1:
                next_dpid = path[1]
              out_port = self.get_out_port_for_link(dpid, next_dpid)
              self.add_short_circuit_path(msg, match, out_port)
              return

            self.logger.info("PathEnforcer, trying to find path {}".format(dpids))
            # get path from current dpid to next jump
            path = nx.shortest_path(self.net, dpid, dpids[0])
            for i in range(len(dpids)-1):
              try:
                  # always omit the first element since it is already in path
                  path += nx.shortest_path(self.net, dpids[i], dpids[i+1])[1:]
              except Exception as e:
                  log_msg = "PathEnforcer, exception for path dpid {} to dpid {}:\n{}"
                  self.logger.info(log_msg.format(dpids[0],dpids[len(dpids)-1],e))
                  return

            # check if the path contains any dpid twice
            nodes_map = {}
            for node in path:
              if node in nodes_map:
                self.logger.info("PathEnforcer, path contains duplicate node {}".format(path))
                self.logger.info("PathEnforcer, enforcing path on reverse flow if possible.")
                path = nx.shortest_path(self.net, dpid, target_dpid)
                next_dpid = path[0]
                out_port = self.get_out_port_for_link(dpid, next_dpid)
                self.add_short_circuit_path(msg, match, out_port)
                return
              else:
                nodes_map[node] = True


            # add reverse flow first to prevent installation of looping rule by this app for async packet-in
            reverse_action = [parser.OFPActionOutput(in_port)]
            self.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, reverse_match,
                                              reverse_action, self.IDLE_TIMEOUT)
            try:
                # loop through all nodes in path and install flow
                self.logger.info("chosen_path = %s", path)
                # get out port to next dpid and install flows on all nodes in path
                out_action = self.add_path_flow_with_idle_timeout(path, match, self.IDLE_TIMEOUT, msg.data)
            except UnboundLocalError: 
                # no need to do anything, routing apps should handle installation of rule on last dpid
                return
        
        elif blp[self.flows_key][hashable_match] != in_port:
            self.logger.info("PathEnforcer handling seen flow with unkown in_port: {} on dpid {}"
                                .format(hashable_match,dpid))
            # check if blp is connected directly and get out port
            target_dpid = self.arp_cache_db[ip.dst]['dpid']
            node_datapath = self.datapathmap[target_dpid]
            node_parser = node_datapath.ofproto_parser
            if target_dpid == dpid:
                # get outport to directly connected host
                out_port = self.arp_cache_db[ip.dst]['port']
            else:
                path = nx.shortest_path(self.net, dpid, target_dpid)
                out_port = self.get_out_port_for_link(dpid, path[0])

            # use higher prio for this rule to prevent shadowing
            # include in_port in rule match to prevent generalization           
            out_action = [node_parser.OFPActionOutput(out_port)]
            match['in_port'] = in_port
            self.add_flow_with_idle_timeout(self.cookie, node_datapath, self.priority+1, match, 
                    out_action, self.IDLE_TIMEOUT)

        else:
            self.logger.info("PathEnforcer, flow was already handled: {} on dpid {}"
                                .format(hashable_match, dpid))
            return

        if out_action == None:
          log_msg = "No action for packet out in Path Enforcer. No path found from dpid {} to {}."
          self.logger.info(log_msg.format(dpid, target_dpid))
          return

        # send packet-out after installing the rule
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                    in_port=datapath.ofproto.OFPP_CONTROLLER, actions=out_action, data=msg.data)
        
        datapath.send_msg(out)


    def add_short_circuit_path(self, msg, match, out_port):
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        out_action = [parser.OFPActionOutput(out_port)]
        self.add_flow_with_idle_timeout(self.cookie, datapath, self.priority, match, 
              out_action, self.IDLE_TIMEOUT)
        # send packet-out after installing the rule
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER,
              in_port=datapath.ofproto.OFPP_CONTROLLER, actions=out_action, data=msg.data)
        datapath.send_msg(out)
 

    # this returns the out port to the first element of the path connected to current dpid
    def add_path_flow_with_idle_timeout(self, path, match, timeout, data):
        out_action = None
        for dpid in path:
            if dpid != path[len(path) - 1]:  
                next_dpid = path[path.index(dpid) + 1] 
                out_port = self.get_out_port_for_link(dpid, next_dpid)
                node_datapath = self.datapathmap[dpid]
                node_parser = node_datapath.ofproto_parser
                node_action = [node_parser.OFPActionOutput(out_port)]
                # we return the action for the first node for packet-out event
                if out_action == None:
                    out_action = node_action
                self.add_flow_with_idle_timeout(self.cookie, node_datapath, self.priority, match, 
                    node_action, self.IDLE_TIMEOUT)
        return out_action
