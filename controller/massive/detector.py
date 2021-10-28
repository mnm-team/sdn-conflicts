# Copyright (C) 2021 Cuong Tran - cuongtran@mnm-team.org
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
__author__ = 'Cuong Tran'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '5.1' - 20210718
Parse hc_input from routing_excluded_info file to be compatible with the massive test, using json and functions from global.

__version__ = '5.0' - 20210614
Adapt to the use of MultiDiGraph of networkx library to encode network topo which allows parallel edges between two vertices.

__version__ = '4.5' - 20200610
implementing detection of hidden conflict class "Event Suppression by Local Handling". As discussed with V. Danciu, the other classes "Event Suppression by Changes to Paths" and "Action Suppresion by Packet Modification" are prohibitively expensive to implement, so I don't implement them here.

__version__ = '4.4' - 20200601
implementing removing rules caused by a new rule having the same priority, same match but different action (correlation local conflict). Not yet implementing removing rules in the same manner as for adding rules, eg., via the rest request, remove some rule explicitly, this event is notified to the detector which removes this rule from the rule graph, create links for rules that were shadowed or redundant be the rule to be removed ..., this can simply be implemented by adding these redundant/shadowed rules to the self.tbar as rules in this list will be processed immediately after the removing rules in self.tbrr list (Consider to be in todo list)

__version__ = '4.3' - 20200528
reform self.tbpr2rg in the dictionary of two categories: new rules to be added, existing rules to be deleted. Rules to be modified is considered in the category of new rules to be added into the rule graph as they are treated in the same manner. First process the rules to be deleted, then rules to be added.


__version__ = '4.2' - 20200527
half-done of version 4.1
not yet implemented deleting rules from the rule graph

__version__ = '4.1' - 20200517
implement to_be_processed_rules for building rule graph self.tbpr4rg and update the rule graph with rules from this "database", instead of only building rule graph from devices directly connected to the end-points as in the previous versions.
TODO:
    For each edge, only store the unique paths and not the path which is a sub-path of another, each unique path comes with a matchmap and priority as in previous versions. Besides, the combined matchmap and the priority associated with the two rules forming an edge are always in the path list of that edge, although it is obviously the subpath of all other paths in this list; this information is important in reasoning a path for new traffic that is not matched by any existing (long) paths in the path list; the reason for this case can be that the rule graph is not yet completely built, so not all rules have been covered.
Path matchmap is a cumulative combination of matchmaps of all rules in the path. We do not store the paths and path matchmaps that are subset of the others as this is expensive when there are a lot of paths traversing through an edge, entailings the need to maintain much more cumulative matchmaps than the number of unique paths for a single edge. Instead, we just maintain the different paths traversing the same edge such that none of them is a subset of another. 

NOTE: We don't implement this, please ignore this line, it was just an idea and is replaced by the above one. If a loop or drop is found, we trace the path and calculate the cumulative matchmaps to see if that path is valid. Note that, even though the rule graph may show a lot of paths from a source to a destination, some of them may not be effective since there is no such traffic satisfies all rules in that path, e.g., consider a path X: rule1 -> rule 2 -> rule 3, in which rule 1 targets traffic destined to A and B, rule 2 targets traffic destined to B and C, rule 3 for traffic to C and D; obviously, there is connection between each rule pair: (1,2) and (2,3), but there is no connection between rules 1 and 3, and thus this path is not valid as there is no traffic satisfying it.

    in adding a new rule, check if there are rules connecting to it from its preceding hops, and update matchmap, maybe remove the existing matchmap that is a subset of the newly created matchmap, think about this.



__version__ = '4.0' - 20200507
Based on version 2.1, implement hidden conflict detection without relying on fake events which poison control applications' states, instead relying on the input from control applications.
The rule graph building used in distributed conflict detection needs to be fixed, before can be useful for both distributed and hidden conflict detection.


__version__ = '2.1' - 20201209
Encode the rule chain from one switch to the subsequent overlapping rules in other switches to the destination (based on match and outport) in a Directed Graph using networkx python library.
Status:
Local conflict: done!
Distributed conflict: not yet comprehensive, check for loop, for drop, not yet for rule transformation to bypass firewall (consider if it is really a conflict, how to detect that, besides, how to detect if a firewall is somewhere there since we consider all control apps as black boxes). Besides, the check for loop are also not yet comprehensive, check in conflict7_by_traffic_looping and analyse the result to see what is still missing, typically not all rule chain are shown in the result, so not yet comprehensive.

__version__ = '2.0' - 20201207
Encoding local conflicts's patterns directly by number, e.g., (1,2,1)...

__version__ = '1.1' - 20201205

Detecting distributed conflicts (DC): DC cannot be detected while some rules are being installed, as the installation process may not yet finish: rules are deployed here and there in different switches (sw), so if we conclude during the rule deployment process, for instance, that a rule in this switch forwarding its matching traffic to the next sw but there is no corresponding rule in that next sw to handle this traffic, that statement tends to be one-sided, it is likely there will be the counterpart rule in the next sw to be installed, moreover, if a sw has no rule to handle that traffic, it will ask the control plane for instruction, and there may be rules coming therefrom.
So, we detect distributed conflicts when there is "relaxed", i.e., when there is no new rule comming from the control plane. In this implementation, we wait for a pre-defined period (5 seconds) after the last rule was installed, then we perform the distributed conflict detection.



__version__ = '1.0' - 20201123

Get MsgFlowMod event from the other apps, but not from basic rules from topology.py (add table-miss flow entry), from arpcache.py adding arp rules. Typically, detector just install ip rules (including icmp, tcp, udp).
MsgFlowMod event contains all the fields of a flow entry (rule) to be installed in the data plane.
The detector checks the match and actions (from instructions field) of the MsgFlowMod event for conflicts and installs rules in the data plane. In other words, the detector intercepts all add_flow events from other control apps (except for topoloyg, arpcache as said), checks conflicts and decides to install the rule or not.

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
import flowmod_class
import networkx as nx
from ryu.lib import hub
import utility
import logging
from log import Log, LogLevel
import json
import os
import globalconfig
import datetime
import time

'''

This app is to be run with other apps, e.g., to run with routing.py, eplb.py and pplb4s.py:
    ryu-manager --observe-links routing.py eplb.py pplb4s.py detector.py

'''

TIMEOUT_DC = 10 #timeout for distributed conflicts
TIMEOUT_HC = 10 #timeout for hidden conflicts

class POLICY:
    EARLIER_WIN = 1 # If two rules have the same priority and match the same packet, the rules installed earlier in the rule table dominates, this is true for OpenFlow switch based on Open vSwitch v2.6.2
    LATER_WIN = 2


class Detector(arpcache.ARPCache):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Detector, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.INFO)      
        self.app_cookies = json.load(open("app_cookie","r"))
        # log messages with LogLevel.Crit, LogLevel.Warn or LogLevel.Info 
        # will be written to a file with this path
        try:
            detector_log_fn = open("detector_log_filename","r").readline().strip() #the content of the file detector_log_filename is controlled by outer machine in massive run
        except FileNotFoundError:
            detector_log_fn = "detector_log"
        detector_log_fn = "./"+detector_log_fn
        print("detector_log_fn = "+detector_log_fn)
        fileLoggerParams = {
            "logger_file": str(os.path.abspath(detector_log_fn))
            #"logger_file": str(os.path.abspath("./detector_log"))
        }

        self.fileLogger = Log(fileLoggerParams)
        # this suppresses any prints to stdout
        # set to LogLevel.Debug for normal behavior
        # or use a specific LogLevel per log write
        #self.log_level = LogLevel.Debug
        self.log_level = LogLevel.Quiet

        self.fileLogger.write(self, LogLevel.Debug, "Conflict Detector started.")
        self.write_to_log = 1 #1: write to log, 0: don't write as that info is already written to log
        self.cookie = 0x7
        self.ft = {} #flow tables (ft) of all switches in the data plane, current version only stores ip traffic including tcp and udp. Other traffic including arp, icmp is excluded.
        # self.ft = {dpid1: {table0_id: {1:(flow0_cookie,priority,match,action,next_hop,matchmap,actmap),2:(flow1_cookie,pri,m,a,nh,mm,am),...}, table1_id: {1:(flow0_cookie,pri,match,action,next_hop,matchmap,am),2:(flow1_c,p,m,a,nh,mm,am)},...}, dpid2:{}, dpid3:{}, ...} # actmap containing the additional saving of outport_set (actmap[4] = outport_set) is to improve the performance when comparing rules, so we don't have to infer the outport from the actions again which we've done when the rule has just arrived. The advantage of using set against list is that we can add value in any order, it facilitates the comparison independent of the order in which each value was added (unlike list)
        # the next_hop list can be i) empty( []) which means: the traffic matching that rule is dropped, or ii) [-2]: that rule forwards matching traffic to an invalid, non-existent port, the output is neither a sw or an ep, or iii) [dpid1, dpid2,...]: the normal case where traffic is forwarded to other switches, or iv) ['host':ip address]: matching traffic goes to an end-point.
        self.policy = POLICY.EARLIER_WIN #this policy applies for OVS-based OpenFlow switches, (tested with version 2.6.2)
        self.rules_pointing_to_dpid = {} # {dpid1:[r11, r12, ...r1n], dpid2: [r21, r22, ...r2n], ...}, r11, r12, ...r1n have their next hop as dpid1. A rule may have multiple next hops, therefore, r11 can be the same as r21. Each rule eg. r11 is a vertex in the form (dpid, table id, rule number) as in self.ft

        self.PASSIVE_ACTIVE = 0 # 0: passive, 1: active. In the passive mode,the detector alerts the presence of conflicts but still let the incoming rule install in the data plane. It prevents the rule installation in case of conflicts in active mode.
        cp = self.parse_conflict_pattern() #cp: conflict patterns, an array, cp=[local_conflict_patterns, distributed_conflict_patterns]
        self.lcp = cp[0] # local conflict patterns lc=[(class0, pattern0, effect0),(class1,pattern1, effect1),...]
        #self.lc = cp[0] # local conflict patterns lc=[(class0, pattern0, effect0),(class1,pattern1, effect1),...]
        self.dcp = cp[1] # distributed conflict patterns, dc =[(class0, pattern0, effect0),(),...]
        self.fileLogger.write(self, self.log_level,"local conflict patterns:")
        for i in self.lcp:
            self.fileLogger.write(self, self.log_level,i)
        self.hci, self.app_input = self.parse_app_input() #hidden conflict input hci = {'eplb': [1024, [7], [-1], 2048, [6], ['192.168.1.1'], ['192.168.1.3','192.168.1.4'], [-1], [-1], [-1], [-1]], 'routing': [256, [], [-1], 2048, [0], [-1], [-1], [-1], [-1], [-1], [-1]], 'sampleapp': [4096, [5, 6], [3], 2048, [6, 17], ['192.168.1.1', '192.168.1.2'], ['192.168.1.3', '192.168.1.4'], [12345, 12346], [80], [12345, 12346], [5001, 53]]}, index: 0: cookie, 1: target switch, 2: in_port, 3: eth_type, 4: ip_proto, 5: ipv4_src, 6: ipv4_dst, 7: tcp_src, 8:tcp_dst, 9:udp_src, 10:udp_dst
        # app_input = {app_cookie:[targetSwitches]} any apps missing in app_input are assumed to have no or all target switches and are ignored in distributed conflicts
        self.fileLogger.write(self, self.log_level,"input for hidden conflicts: {}".format(self.hci))
        self.rule_num = {} # rule number, to store the numerical order of the rules in the flow table of self.ft. This information is useful to identify a rule when needed, e.g., in case of showing conflicting rules.
        #self.rule_num = {dpid1:{table0_id:0, table1_id:0, table2_id:0...}, dpid2:{table0_id:0, table1_id:0,...}...}
        self.lc_cfl_rules = {} # local conflicting rules self.lc_cfl_rules = {dpid1:{table_id1:{rule number x1:[(rule number y1,conflict class,(priority relationship, match relationship, action relationship)), (rule number z1,cfl class, (prirel,matrel,actrel)),...], rule number x2:[(rule number y2,cfl class,(prirel,matrel,actrel)), (rule number t1,cfl class,(prirel,matrel,actrel)),...],...}, table_id2:{}...}...,dpid2:{table_id1:{}...}...} 
        #In case of passive mode, the detector installs all the rules despite the conflicts detected, all these conflicts are stored in this dictionary data structure. In active mode, this dictionary will be empty since no conflicting rule gets installed.
        self.dt_cfl_rules = {"loops":[], "drop":[], "black-hole":[], "multi-transform":[], "injection":[], "bypass":[], "incomplete-transform":[], "occlusion":[]} # distributed conflicting rules self.dt_cfl_rules = {1:[], 2:[], 3: []}, self.dt_cfl_rules[1] = [(path1,matchmap1),(path2, matchmap2)], [1] is for traffic loop, [2] is for deliberate drop/black-hole(only if packets where coming from other dpid, else drop is considered valid and not a dist conflict), [3] is for accidental drop/black-hole (kinds of a bug, or a mistake while adding a new rule, e.g., by an admin) , [4] is for rule transformation to bypass firewall. 5 is for multi-transform, 6 for injection, 7 for bypass, 8 for incomplete transform, 9 for occlusion
        # path = rule_chain, e.G., ((1,0,1),(2,0,3)) where possible

        self.rg = nx.DiGraph() #rule graph: the path of rules in different switches from source to destination or to a loop or to a black-hole (drop). Each vertex is a tuple of (dpid,tableid,rule_num), as we know in OpenFlow1.3, each rule has output to the next flow table or to the other sw, we consider a single flow table in this version so it is the next sw or the end-point, a rule may have empty action meaning drop, an action of forwarding traffic to an invalid port (e.g., non-existent port) also means drop. We encode the explicit valid drop as a vertex of (dpid,tableid,-1) and the edge from the rule causing this drop as (dpid,tableid,rule_num)-->(dpid,tableid,-1), the drop by invalid port as (dpid,tableid,-2), the endpoint as (0,'ip of ep'). In addition, there may be the case that rule r in sw i has its next hop as sw j, but there is no rule matching that traffic of rule r in sw j, we encode that case temporarily (sw j, 0, -3), however, we need to double-check if such a traffic comes to sw j, will there be instruction from the control plane as sw j will ask the controller when it doesn't know how to handle a packet. (dpid, tid, -4) represents loop.
        #We can use the function in_edges of the graph to trace the preceding vertex of the current vertex, so we can trace to the source dpid by using the direction "back" and see the traffic path of e.g., a rule dropping packets or a loop.

        self.tbar = [] #to be added rules to rule graph. It is a list whose element is also a list of the format: [dpid,table_id, rule, processed_flag], rule corresponds to the rule number in self.ft, processed flag is either 0 (already processed) or 1 (not yet processed). self.tbar= [[1,0,1,1],[1,0,2,0],[3,0,5,1]...]
        self.tbrr = [] #to be removed rules from rule graph. This list has the same format as self.tbar above.
        # a rule r that is overriden by a new rule nr is implemented by adding r in self.tbrr and processing it first, then adding nr in self.tbar.
        # the modified rules are not yet implemented in this version, at least up to 5.0, but is recommended to be treated in the same way as the overriden rules. This way of implementation has the advantage that we can based on the rule number (its order in self.ft) to identify which rule is newer, in in Open vSwitch implementation for OpenFlow, it is determinable which rule takes effect in case more than a rule of the same priority can handle the same packet, here the newer rule wins.

        self.timeout_dc = TIMEOUT_DC #timeout in second since the last rule was deployed, then performing the distributed conflicts detection. This timeout is to ensure that all rules pertaining to the reaction of a new flow were already deployed on all relevant sw. The detection of DC needs sufficient and correct information distributed on different sw.
        self.dc_flag = 0 #if flag is set (=1), perform detecting distributed conflicts.
        #self.detect_distributed_conflicts_thread = hub.spawn(self._detect_distributed_conflicts)
        self.update_rule_graph_thread = hub.spawn(self._update_rule_graph)
        self.hc_cfl_rules = {1:{}, 2:{}, 3:{}} #hidden conflicting rules, 1: Event Suppression by Local Handling, 2: Event Suppression by Changes to Paths, 3: Action Suppression by Packet Modification. self.hc_cfl_rules[1] = {app1:[((dpid,table id,rule1),[matchmap1 in list form]),((dpid2,tid2,rule2),[matchmap2 in list form]),...], app2:[((rule1),[matchmap1]),((rule2),[matchmap2]),...],...}, each tuple (dpid, table id, rule) is a rule, where rule corresponds to the number stored in self.ft, a rule may be broad and cover several interested traffic of a control app, these overlaps are reflected by the matchmap in list format [matchmap]. The 2nd and 3rd hidden conflict classes have not been attacked in this version v4_4

    def parse_app_input(self):
        app,app_input = {},{} #app dictionary: app = {"app1":[cookie, [target switches],[in_port],eth_type,[ip_proto],[ipv4_src],[ipv4_dst],[tcp_src],[tcp_dst],[udp_src],[udp_dst]], "app2":[...], "app3":[...],...}
        running_apps = open("routing_excluded_info","r").readlines()
        if len(running_apps):
            running_apps = running_apps[0]
        else:
            running_apps = ""
            return app

        if "eplb" in running_apps:
            an = "eplb" # app name
            app[an]=[self.app_cookies[an],["all"],[-1],2048,[0],[-1],[-1],[-1],[-1],[-1],[-1]]
            try:
                # get global configs for apps, only need their balance points and priority is ignored
                eplb_priority, eplb_blp =  globalconfig.parseGlobalConfig("eplb")
                # get local config for eplb and add all (ip,mac) tuples of proxy servers
                eplb_local_config = globalconfig.localConfigEPLB()
                eplb_proxies = []
                for key,value in eplb_local_config.items():
                    eplb_proxies.append(key[0])
                targetSwitches = list(eplb_blp.keys())
                app[an][1] = targetSwitches
                app_input[self.app_cookies[an]] = targetSwitches
                app[an][4] = [6, 17]  # ip_proto
                app[an][6] = eplb_proxies  # ipv4_dst
            except Exception:
                print("No config for eplb or error while trying to load")

        if "pplb4s" in running_apps:
            an = "pplb4s" # app name
            app_input[an] = ["all"]
            app[an]=[self.app_cookies[an],["all"],[-1],2048,[0],[-1],[-1],[-1],[-1],[-1],[-1]]
            try:
                pplb4s_priority, pplb4s_blp =  globalconfig.parseGlobalConfig("pplb4s")
                # get local config of pplb4s, servers list contains (ip,mac) tuples
                pplb4s_local_config = globalconfig.localConfigPPLB4s()
                targetSwitches = list(pplb4s_blp.keys())
                app[an][1] = targetSwitches
                app_input[self.app_cookies[an]] = targetSwitches
                app[an][4] = [6, 17]  # ip_proto
                app[an][5] = [] # ipv4_src
                for server in pplb4s_local_config["servers"]:
                    app[an][5].append(server[0])
            except Exception:
                print("No config for pplb4s or error while trying to load")

        if "pplb4d" in running_apps:
            an = "pplb4d" # app name
            app[an]=[self.app_cookies[an],["all"],[-1],2048,[0],[-1],[-1],[-1],[-1],[-1],[-1]]
            try:
                pplb4d_priority, pplb4d_blp =  globalconfig.parseGlobalConfig("pplb4d")
                # get local config of pplb4s, servers list contains (ip,mac) tuples
                pplb4d_local_config = globalconfig.localConfigPPLB4d()
                targetSwitches = list(pplb4d_blp.keys())
                app[an][1] = targetSwitches
                app_input[self.app_cookies[an]] = targetSwitches
                app[an][4] = [6, 17]  # ip_proto
                app[an][6] = [] # ipv4_dst
                for server in pplb4d_local_config["servers"]:
                    app[an][6].append(server[0])
            except Exception:
                print("No config for pplb4d or error while trying to load")

        if "hs" in running_apps:
            an = "hs" # app name
            app[an]=[self.app_cookies[an],["all"],[-1],2048,[0],[-1],[-1],[-1],[-1],[-1],[-1]]
            try:
                hs_priority, hs_blp =  globalconfig.parseGlobalConfig("hs")
                hosts_config = globalconfig.localConfigHS()
                config_list = []
                for k,v in hosts_config:
                    config_list.append(k)
                targetSwitches = list(hs_blp.keys())
                app[an][1] = targetSwitches
                app_input[self.app_cookies[an]] = targetSwitches
                app[an][4] = [6, 17]  # ip_proto
                app[an][6] = config_list # ipv4_dst
            except Exception:
                print("No config for hs or error while trying to load")

        # parse pe config for dist conflict input
        # temporarily do not check hidden conflicts (hc) for pe, as all rules in its target switches other than its rules are sources of first class hc (event suppression by local handling)
        if "pe" in running_apps:
            an = "pe" # app name
            app_input[self.app_cookies[an]] = ["all"]
            try:
                pe_priority, pe_blp =  globalconfig.parseGlobalConfig("pe")
                app_input[self.app_cookies[an]] = list(pe_blp.keys()) # target switch
            except Exception:
                print("No config for pe or error while trying to load")

        # use only for dist conf input
        # white space is necessary to discern between eplb and plb
        if " plb" in running_apps:
            an = "plb" # app name
            try:
                plb_priority, plb_blp =  globalconfig.parseGlobalConfig("plb")
                app_input[self.app_cookies[an]] = list(plb_blp.keys()) # target switch
            except Exception:
                print("No config for plb or error while trying to load")

        # use only for dist conf input
        if "fw" in running_apps:
            an = "fw" # app name
            try:
                fw_priority, fw_blp =  globalconfig.parseGlobalConfig("fw")
                app_input[self.app_cookies[an]] = list(fw_blp.keys()) # target switch
            except Exception:
                print("No config for fw or error while trying to load")

        return app, app_input


    def parse_conflict_pattern(self):
        lc = [] # local conflict
        dc = [] # distributed conflict
        tmparlc = [] #temp array for local conflicts, tmparlc=[class, pattern, effect]
        prev_line = "" # previous line
        with open("conflict_pattern.spec") as cp:
            for line in cp:
                if (len(tmparlc) == 3): #[class, pattern, effect]
                    if "local" in tmparlc[0]:
                      lc.append(tuple(tmparlc))
                    elif "distributed" in tmparlc[0]:
                       dc.append(tuple(tmparlc))
                    else:
                      print("Failed to determine conflict type for conflict pattern:")
                      print(tmparlc)

                    tmparlc = []
                line = line.strip() #remove white-space from both ends of the string 'line'
                if (line == "#===end===#"): #end of file, stop further read
                    break
 
                # extract local and distributed conflict patterns
                if (line.startswith("class")): #e.g., line="class Shadowing (local conflicts):"
                    tmparlc.append(line.rstrip(':')) #get the conflict class name, tmparlc[0] = class
                if (line.startswith("pattern") or line.startswith("effect")):
                    prev_line = line
                    continue
                if (line.startswith('#')): #comment, skip and don't update prev_line
                   continue
                if (len(line) == 0):
                    tmparlc = []
                    prev_line = line
                    continue
                if (prev_line.startswith("pattern")): #extract pattern of current class
                    pattern_list = line.split() # get an array of patterns, each is a string. e.g., ['(1,2,1)', '(1,1,1)']
                    for ptnstr in pattern_list:#pattern string, e.g., '(1,2,3)'
                        tmplist = []
                        for i in ptnstr:
                            if (i.isdigit()):
                                tmplist.append(int(i))
                        if (len(tmparlc) == 1):
                            tmparlc.append([tuple(tmplist)])
                        else: #len(tmparlc) == 2
                            tmparlc[1].append(tuple(tmplist))

                if (prev_line.startswith("effect")):
                    tmparlc.append(line) #tmparlc[2] = effect
                prev_line = line

        return[lc,dc]


    def _get_all_simple_paths_from_matchmap(self,matchmap, dpid=None):
        """returns a path generator based on the current net from source to
        destination endpoint, with optional start from a specific dpid.
        """
        ip_src = matchmap[3]
        ip_dst = matchmap[4]
              
        src_dpid, dst_dpid = None, None
        if ip_src in self.arp_cache_db:
            src_dpid = self.arp_cache_db[ip_src]['dpid']
        if ip_dst in self.arp_cache_db:
             dst_dpid = self.arp_cache_db[ip_dst]['dpid']

        # get path to destination starting from specific dpid
        if not dpid == None: 
            src_dpid = dpid

        # do some sanity checks in case the matchmap contains wildcards
        if (src_dpid == None or dst_dpid == None) or (src_dpid == dst_dpid):
            # we really cannot do any sane check for partial paths or without info on target switches
            return None

        # get all paths from src to dst
        return nx.all_simple_paths(self.net, src_dpid, dst_dpid)


    def _get_target_switches(self,appCookie):
        tSwitches = []
        cookie_str = hex(appCookie)
        if cookie_str in self.app_input:
            tSwitches = self.app_input[cookie_str]
        else:
             self.fileLogger.write(self, LogLevel.Debug,"No/all target switches for app {}".format(cookie_str))
        return tSwitches

    
    def _reverse_transform_pattern(self,actmap,matchmap):
        """Reverses a actmap tuple that does not contain any output actions.
        Length of actmap and matchmap has to be 6 for this to work.
        """
        actmap = list(actmap)
        matchmap = list(matchmap)
        # use only the relevant fields in matchmap
        matchmap = matchmap[3:]
        # just a sanity check in case something changes with actmap/matchmap implementation
        if len(actmap) != 6 or len(matchmap) != 6:
            self.fileLogger.write(self, LogLevel.Debug,"Actmap/Matchmap has unexpected length. Cannot reverse!")
            return (-1,-1,-1,-1,-1,-1)

        out_map = [-1,-1,-1,-1,-1,-1]
        for i,v in enumerate(actmap):
            if v != -1:
                out_map[i] = matchmap[i]
        reverse_map = list([out_map[1],out_map[0],out_map[3],out_map[2],out_map[5],out_map[4]])
        return tuple(reverse_map)

    def _has_set_field_actions(self, actions):
        for act in actions:
            if isinstance(act, ofproto_v1_3_parser.OFPActionSetField):
                return True
        return False


    def _handle_dc_occlusion(self, vertex_app, vertex, actmap, matchmap):
        # this only works if actmap and matchmap have size of 6 
        # and the order of their properties correspond
        # e.g. the first element for both is the ip_src
        dpid, table_id, rule_id = vertex
        interests = []
        mmap = matchmap[3:]
        # ignore outport in actmap
        transform_map = actmap[:-1]
        # for any setField operation in actmap retrieve corresponding value from matchmap
        # only do this for fields that transform destination header fields
        for i,act in enumerate(transform_map):
            # TODO workaround to only consider destination transforms
            # uneven elements in actmap are destination transforms
            # this is not future proof
            if (act != -1) and (i%2 == 1):
                interests.append(mmap[i])

        if not len(interests):
            return

        # check which apps are interested in the same endpoints
        check_apps = []
        for app,value in self.hci.items():
            endpoints = value[6]
            appCookie = int(value[0],16)
            # do not check against interests of same app
            if vertex_app == appCookie:
                continue
            for i in interests:
                relations = utility.compare_ip_hc(i,endpoints)
                if relations[0] != 0:
                  check_apps.append(appCookie)

        # get path to destination starting from current dpid
        paths = self._get_all_simple_paths_from_matchmap(matchmap, dpid)
        
        # sanity check
        if paths == None or not len(check_apps):
            return

        for appCookie in check_apps:
            tSwitches = self._get_target_switches(appCookie)
            for tSwitch in tSwitches:
                for path in paths:
                    if tSwitch in path:
                        self.fileLogger.write(self, LogLevel.Debug,"Dist Occlusion conflict:\nRule {}\nMatchmap {}\nby app {}\n with app {} on target switch {}".format((dpid, table_id, rule_id),matchmap,vertex_app,appCookie,tSwitch))
                        self.fileLogger.write(self, LogLevel.Crit,"Dist Occlusion conflict:\nRule {}\nMatchmap {}\nby app {}\n with app {} on target switch {}".format((dpid, table_id, rule_id),matchmap,vertex_app,appCookie,tSwitch))
                        self.dt_cfl_rules["occlusion"].append(([(dpid,table_id,rule_id),(tSwitch,-1,-1)],(matchmap,(vertex_app,appCookie))))
                        break


    def _handle_dc_multi_transform(self,prev_vertex,vertex,app,visited=None):
        """Checks any in_edges of a vertex in the rule graph for multi transform conflicts
        and injection conflicts. If two distinct apps transform packets on a flow path we 
        are encountering a multi transform conflict. If an app unintentionally routes packets
        to a policy of another app that transforms packets, we are encountering an injection 
        conflict. Apps that are deployed on all switches are exempt from determining the patterns.
        Recursively checks any paths leading back from a starting rule.
        """

        # in case of a loop we need some way of breaking the recursion in this algorithm
        # to avoid runtime errors
        if visited and prev_vertex == vertex:
            self.fileLogger.write(self, LogLevel.Debug,"Stopping recursion for multi-transform check since there probably is a loop")
            return

        for in_vertex in self.rg.in_edges(prev_vertex):
                in_vertex = in_vertex[0]
                in_rule = self.ft[in_vertex[0]][in_vertex[1]][in_vertex[2]]
                in_app = in_rule[0]
                # ignore rules by same app or routing/arpcache app
                omit_apps = [self.app_cookies["arpcache"], self.app_cookies["routing"], hex(app)]
                if hex(in_app) in omit_apps:
                    # skip current vertex and check next
                    self._handle_dc_multi_transform(in_vertex,vertex,app,True)
                    continue

                # we have to compare the output matchmap and original matchmap to check if
                # rules in rule graph are really related
                actions = in_rule[3]
                in_matchmap = in_rule[5]
                in_actmap = in_rule[6]
                rule = self.ft[vertex[0]][vertex[1]][vertex[2]]
                matchmap = rule[5]
                transformed_matchmap = utility.combine_matchmap_and_actmap(in_matchmap, in_actmap)
                relation = utility.compare_match_interflowtable(transformed_matchmap, matchmap)
                # for any relation other than [0,*] rules should handle the same packets
                if self._has_set_field_actions(actions) and relation[0]:
                    collision_elem = (in_vertex, in_rule)
                    start_elem = (vertex,rule)
                    self.fileLogger.write(self, LogLevel.Debug,"Dist Multi-Transform conflict:\n{}".format((collision_elem, start_elem)))
                    self.fileLogger.write(self, LogLevel.Crit,"Dist Multi-Transform conflict:\n{}".format((collision_elem, start_elem)))
                    self.dt_cfl_rules["multi-transform"].append(([collision_elem[0],start_elem[0]], (collision_elem[1],start_elem[1])))
                else:
                    self._handle_dc_multi_transform(in_vertex,vertex,app,True)


    def _handle_dc_injection(self,prev_vertex,vertex,app,visited=None):
        """Checks any in_edges of a vertex in the rule graph for injection conflicts. 
        If an app routes packets to a policy of another app that transforms packets and the are
        multiple paths to the destination, we are encountering an injection  conflict. 
        Apps that are deployed on all switches are exempt from determining the patterns.
        Recursively checks any paths leading back from a starting rule with transform actions.
        """
        # in case of a loop we need some way of breaking the recursion in this algorithm
        # to avoid runtime errors
        if visited and prev_vertex == vertex:
            self.fileLogger.write(self, LogLevel.Debug,"Stopping recursion for injection check since there probably is a loop")
            return

        tSwitches = self._get_target_switches(app)
        rule = self.ft[vertex[0]][vertex[1]][vertex[2]]
        matchmap = rule[5]
        paths = self._get_all_simple_paths_from_matchmap(matchmap)
        for in_vertex in self.rg.in_edges(prev_vertex):
                in_vertex = in_vertex[0]
                in_rule = self.ft[in_vertex[0]][in_vertex[1]][in_vertex[2]]
                in_app = in_rule[0]
                # ignore rules by same app or routing/arpcache app
                omit_apps = [self.app_cookies["arpcache"], self.app_cookies["routing"], hex(app)]
                if hex(in_app) in omit_apps:
                    # skip current vertex and check next
                    self._handle_dc_injection(in_vertex,vertex,app,True)
                    continue

                # we have to compare the matchmaps to check if
                # rules in rule graph are really related
                in_actions = in_rule[3]
                in_matchmap = in_rule[5]
                relation = utility.compare_match_interflowtable(in_matchmap, matchmap)
                # ignore rules with transform actions since these are detected by check
                # for multi-transform conflicts
                # any relation other than 0 means rules are connected
                if not self._has_set_field_actions(in_actions) and relation[0]:
                    try:
                        num_paths = 0
                        inject_app_is_in_all_paths = 0
                        app_is_in_all_paths = 0
                        inTSwitches = self._get_target_switches(in_app)
                        if len(inTSwitches):  
                            for p in paths:
                                for t in inTSwitches:
                                    if t in p:
                                        inject_app_is_in_all_paths += 1
                                        break
                                for t in tSwitches:
                                    if t in p:
                                        app_is_in_all_paths += 1
                                        break
                                num_paths += 1
                                # early stop condition
                                if num_paths > inject_app_is_in_all_paths:
                                    break
                        if num_paths > 1 and num_paths == inject_app_is_in_all_paths and num_paths > app_is_in_all_paths:
                            collision_elem = (in_vertex,in_rule)
                            start_elem = (vertex,rule)
                            inject_path = (collision_elem, start_elem)
                            self.fileLogger.write(self, LogLevel.Debug,"Dist Injection conflict:\n{}".format(inject_path))
                            self.fileLogger.write(self, LogLevel.Crit,"Dist Injection conflict:\n{}".format(inject_path))
                            self.dt_cfl_rules["injection"].append(([collision_elem[0],start_elem[0]], (collision_elem[1],start_elem[1])))
                    except Exception as e:
                        self.fileLogger.write(self, LogLevel.Debug,"{}".format(e))
                        self.fileLogger.write(self, LogLevel.Debug,"Failed to test for injection conflict.")
                self._handle_dc_injection(in_vertex,vertex,app,True)


    def _handle_dc_bypass(self, vertex_app, vertex, matchmap):
        """Check for any rules that circumvent target switches or rules
        of other apps. Bypass conflicts only depend on target switches
        and are only checked once.
        """
        appCookie = vertex_app
        dpid,table_id,rule_id = vertex
        tSwitches = self._get_target_switches(appCookie)
        paths = self._get_all_simple_paths_from_matchmap(matchmap)

        # don't do anything if path generator could not be created or there are no target switches or if there are no transform actions
        if paths == None or len(tSwitches) == 0:
            self.fileLogger.write(self, LogLevel.Debug,"Avoiding detection of bypass for candidate absent from rule graph or candidates with missing info on target switches")
            return

        # get all paths from src to dst
        coveredPaths = 0
        num_paths = 0
        for path in paths:
            num_paths += 1
            for tSwitch in tSwitches:
                if tSwitch in path:
                    coveredPaths += 1
                    break

        path_diff = num_paths - coveredPaths
        # check if we have an uncovered path or a target switch on a covered path without a matching reverse transform
        if path_diff > 0:
            self.fileLogger.write(self, LogLevel.Debug,
              "Dist bypass conflicts:\nCandidate rule {}\n by app {}\ncan get bypassed on {} paths.".format(vertex,vertex_app, path_diff))
            self.fileLogger.write(self, LogLevel.Crit,
              "Dist bypass conflicts:\nCandidate rule {}\n by app {}\ncan get bypassed on {} paths.".format(vertex,vertex_app, path_diff))
            self.dt_cfl_rules["bypass"].append(([dpid,table_id,rule_id],(matchmap,path_diff)))


    def _update_rule_graph(self):
        while (True):
            self.fileLogger.write(self, self.log_level,"self.dc_flag = {}".format(self.dc_flag))
            #====================================
            #check for node with next hop = -2, we assume next hop = -2 means it is intended 
            #to an end-point or a wrong output port. As the end-points can be not yet completely discovered and are not present in self.arp_cache_db, this needs to be checked and updated once the end-point has been discovered.
            sv = set() #set of vertices
            se = set() #set of edges
            lr = [] #list of rules
            for v in self.rg.nodes(): #vertex
                if (len(v) == 3 and v[2] == -2):# e.g.,v == (3,0,-2)
                    print(v)
                    for ie in self.rg.in_edges(v):#in_edges, e.g., ie == ((3,0,1),(3,0,-2))
                        rule = ie[0] # e.g., rule = (3,0,1)
                        outport = self.ft[rule[0]][rule[1]][rule[2]][6][6] # outport = set([a,b,c])
                        for port in outport:
                            for i in self.arp_cache_db:
                                if (self.arp_cache_db[i]['dpid'] == rule[0] and self.arp_cache_db[i]['port'] == port):
                                    self.ft[rule[0]][rule[1]][rule[2]][4].remove(-2) #update next hop of rule
                                    self.ft[rule[0]][rule[1]][rule[2]][4].append("host:"+i)
                                    lr.append(rule)
                                    sv.add(v)
                                    se.add(ie)
                                    #self.rg.remove_node(v), if we remove v here, we might encounter an Error: RuntimeError: dictionary changes size during iteration, since we are looping through v, so add it to a set and remove it outside of the for loop, as in the next line
            for e in se:
                self.rg.remove_edge(*e)
            for v in sv:
                if (self.rg.in_degree(v) == 0): 
                    self.rg.remove_node(v)
            for rule in lr:
                self.fileLogger.write(self, self.log_level,"call _add_rule_to_rule_graph now after removing nodes of (x,x,-2)")
                self._add_rule_to_rule_graph(rule[0],rule[1],rule[2])
                #update self.dt_cfl_rules["black-hole"]
                pmt = [] #path match tuple to be removed from self.dt_cfl_rules["black-hole"]
                for (p,m) in self.dt_cfl_rules["black-hole"]:
                    if (rule == list(p).pop()):# compare rule with the last rule of path p
                        pmt.append((p,m))
                #remove from self.dt_cfl_rules["black-hole"] the tuple (p,m) as it is no more a conflict/problem.
                for (p,m) in pmt:
                    self.dt_cfl_rules["black-hole"].remove((p,m))
                
            while (True):
                if (self.timeout_dc > 0):
                    self.timeout_dc -= 1
                    hub.sleep(1)
                else:
                    self.timeout_dc = TIMEOUT_DC
                    break
            if (self.dc_flag == 0):
                if self.write_to_log == 0:
                    continue
                #hub.sleep(self.timeout_dc)
                #now, self.write_to_log == 1
                self.fileLogger.write(self, LogLevel.Crit,"\n\n\n{}".format(datetime.datetime.now()))
                self.fileLogger.write(self, LogLevel.Crit,"\nnumber of edges in rule graph = {}".format(self.rg.number_of_edges()))
                for e in self.rg.edges():
                    self.fileLogger.write(self, LogLevel.Crit,"\n{} {}".format(e,self.rg.get_edge_data(*e)))
                self.fileLogger.write(self, LogLevel.Crit,"\n\nself.ft = ")
                for i in self.ft:
                    self.fileLogger.write(self, LogLevel.Crit,"\n{}:{}".format(i,self.ft[i]))
                self.fileLogger.write(self, LogLevel.Crit,"\nNumber of rules: {}".format(utility.count_rules(self.ft)))
                self.fileLogger.write(self, LogLevel.Crit,"\n\nself.lc_cfl_rules = ")
                for i in self.lc_cfl_rules:
                    self.fileLogger.write(self, LogLevel.Crit,"\n{}:{}".format(i,self.lc_cfl_rules[i]))
                self.fileLogger.write(self, LogLevel.Crit,"\nNumber of local conflicts by dpid: {}".format(utility.count_local_conflicts(self.lc_cfl_rules,"dpid")))
                self.fileLogger.write(self, LogLevel.Crit,"\nNumber of local conflicts by class: {}".format(utility.count_local_conflicts(self.lc_cfl_rules,"class")))

                self.fileLogger.write(self, LogLevel.Crit,"\n\nself.hc_cfl_rules = ")
                for i in self.hc_cfl_rules:
                    self.fileLogger.write(self, LogLevel.Crit,"\n{}:{}".format(i,self.hc_cfl_rules[i]))
                self.fileLogger.write(self, LogLevel.Crit,"\nNumber of rules causing hidden conflicts by control app: {}".format(utility.count_hidden_conflicts(self.hc_cfl_rules)))
                self.fileLogger.write(self, LogLevel.Crit,"\n\nself.dt_cfl_rules = ")
                for k,v in self.dt_cfl_rules.items():
                    self.fileLogger.write(self, LogLevel.Crit,"\n{}:{}".format(k,v))
                self.fileLogger.write(self, LogLevel.Crit,"\nNumber of distributed conflicts by class: {}".format(utility.count_distributed_conflicts(self.dt_cfl_rules)))
                self.write_to_log = 0 #reset, so the same info just written to log won't be written again.

                continue
            # now self.dc_flag == 1
            self.write_to_log = 1
            self.fileLogger.write(self, self.log_level,"Performing detection of distributed conflicts now") 
            self.fileLogger.write(self, self.log_level,"self.tbrr = {}".format(self.tbrr))
            self.fileLogger.write(self, self.log_level,"self.tbar = {}".format(self.tbar))

            self.fileLogger.write(self, LogLevel.Crit,"\n\n\n{}".format(datetime.datetime.now()))
            self.fileLogger.write(self, LogLevel.Crit,"\nNumber of existing rules: {}".format(utility.count_rules(self.ft)))
            self.fileLogger.write(self, LogLevel.Crit,"\nnumber of edges in rule graph = {}".format(self.rg.number_of_edges()))
            self.fileLogger.write(self, LogLevel.Crit,"\nnumber of rules to be removed = {}".format(len(self.tbrr)))
            self.fileLogger.write(self, LogLevel.Crit,"\nnumber of rules to be added = {}".format(len(self.tbar)))
             #first process rules to be removed
            len_tbrr = len(self.tbrr)
            tdr = [] #time difference for removed rules
            for i in range(len(self.tbrr)):
                (dpid,tid,r,s) = self.tbrr[i] #dpid, table id, rule, state
                if (s==1):#not yet processed, else s==0
                    self.tbrr[i][3] = 0 # reset processed flag to 0
                    self.fileLogger.write(self, self.log_level,"call _remove_rule_from_rule_graph now, vertex ({},{},{})".format(dpid,tid,r))
                    t1 = time.time()
                    self._remove_rule_from_rule_graph(dpid,tid,r)
                    t2 = time.time()
                    tdr.append(t2 - t1) #time difference
                    self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) in removing rule ({},{},{}) from the rule graph = {}".format(dpid,tid,r,tdr[-1]*1000))

            self.tbrr = [] #reset the whole self.tbrr after processing all rules.

            len_tbar = len(self.tbar)
            tda = [] #time difference for added rules
            for i in range(len(self.tbar)):
                (dpid,tid,r,s) = self.tbar[i]
                continue_flag = 0
                try:
                    for con in self.lc_cfl_rules[dpid][tid][r]:
                        if (con[2] in [(2,1,1),(2,3,1),(0,1,1)]): #shadowing2, correlation4 to be compatible with OpenFlow13 where the new rule of pattern (0,1,1) overrides the existing rule in the same flow table
                            self.fileLogger.write(self, self.log_level,"rule ({},0,{}) is shadowed by rule ({},0,{}), ignore this rule in checking distributed conflicts".format(dpid,r,dpid,con[0]))
                            continue_flag = 1
                            break
                except KeyError:
                    pass
                if (continue_flag == 1): #rule r is shadowed by another rule, ignore it
                    continue
                t1 = time.time()
                self._check_hidden_conflict_eslh(dpid,tid,r) #eslh: event suppression by local handling = hidden conflicts class 1
                t2 = time.time()
                td = t2 - t1 #time difference
                self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) in checking hidden conflicts for rule ({},{},{}) = {}".format(dpid,tid,r,td*1000))
                if (s==1):#not yet processed
                    self.tbar[i][3] = 0 #reset
                    #now, check the path that this rule will lead to, to see if there is loop or drop
                    self.fileLogger.write(self, self.log_level,"call _add_rule_to_rule_graph now, target rule: ({},{},{})".format(dpid,tid,r))
                    t1 = time.time()
                    self._add_rule_to_rule_graph(dpid, tid, r)
                    t2 = time.time()
                    tda.append(t2 - t1) #time difference
                    self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) in adding rule ({},{},{}) to the rule graph = {}".format
(dpid,tid,r,tda[-1]*1000))
                    # check if actmap is longer than 2, i.e. it contains transform rules, and check for transform conflicts
                    # only do this if the vertex was actually added
                    rule_entry = self.ft[dpid][tid][r]
                    vertex_actions = rule_entry[3]
                    vertex_actmap = rule_entry[6]
                    vertex_matchmap = rule_entry[5]
                    vertex_app = rule_entry[0]
                    vertex = (dpid, tid, r)
                    if vertex in self.rg and self._has_set_field_actions(vertex_actions):
                        t1 = time.time()
                        # backward oriented concerning rule graph
                        self._handle_dc_multi_transform(vertex,vertex,vertex_app)
                        t2 = time.time()
                        time_delta = (t2 - t1)
                        self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) for multi-transform conflict check: {}".format(time_delta*1000))
                        t1 = time.time()

                        # forward oriented concerning rule graph and other apps interests
                        self._handle_dc_occlusion(vertex_app, vertex, vertex_actmap, vertex_matchmap)
                        t2 = time.time()
                        time_delta = (t2 - t1)
                        self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) for occlusion conflict check: {}".format(time_delta*1000))
                        t1 = time.time()
                        # based on examination of alternate routes
                        self._handle_dc_bypass(vertex_app, vertex, vertex_matchmap)
                        t2 = time.time()
                        time_delta = (t2 - t1)
                        self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) for bypass conflict check: {}".format(time_delta*1000))
                    
                    # TODO this is a test with the injection algorithm that is oblivious of packet transformations
                    # This might be a simple heuristic to acutally detect invariant contention conflicts
                    # but since apps in SDN are supposed to work together, this will result in a lot of false positives
                    # to reinstate the intended behavior, below block needs to be indented in above if clause
                    # ignore rules by same app or routing/arpcache app
                    omit_apps = [self.app_cookies["arpcache"], self.app_cookies["routing"]]
                    if hex(vertex_app) not in omit_apps:
                        # we always check for injection conflicts since this does not have to be transformation related 
                        t1 = time.time()
                        # backward oriented concerning rule graph
                        self._handle_dc_injection(vertex,vertex,vertex_app)
                        t2 = time.time()
                        time_delta = (t2 - t1)
                        self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) for injection conflict check: {}".format(time_delta*1000))
                        t1 = time.time()


            self.tbar = [] #reset after processing all rules
            self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) after this round of updating the rule graph = {}".format(sum(tdr)*1000+sum(tda)*1000))
            atdr = 0 #avarage of time difference of removed rules
            count_tdr = 0
            if len(tdr) > 10:
                count_tdr = 10
                stdr = 0 #sum of time difference of removed rules
                for i in range(10):
                    stdr += tdr[i]
                atdr = 1.0*stdr/10
            elif len(tdr) > 0:
                count_tdr = len(tdr)
                atdr = 1.0*sum(tdr)/len(tdr)
            self.fileLogger.write(self, LogLevel.Crit,"\nAverage time difference (ms) in removing {} rules from rule graph = {}".format(count_tdr,atdr*1000))
            atda = 0 #avarage of time difference of added rules
            count_tda = 0
            if len(tda) > 10:
                count_tda = 10
                stda = 0 #sum of time difference of added rules
                for i in range(10):
                    stda += tda[i]
                atda = 1.0*stda/10
            elif len(tda) > 0:
                count_tda = len(tda)
                atda = 1.0*sum(tda)/len(tda)
            self.fileLogger.write(self, LogLevel.Crit,"\nAvarage time difference (ms) in adding {} rules to rule graph = {}".format(count_tda,atda*1000))


            #check vertices of pattern (x,x,-3) (head-ends of wavering edges) to see if there are new rule now, if yes, remove these vertices. Remember, the (x,x,-3) means there is no matching rule for a certain matchmap in the last time, but it may change if the switch has asked the controller and got new rules matching that matchmap.
            sv = set() #set of vertices
            se = set() #set of edges
            for v in self.rg.nodes(): #vertex
                if (len(v) == 3 and v[2] == -3):# e.g.,v == (7,0,-3)
                    print(v)
                    for ie in self.rg.in_edges(v):#in_edges, e.g., ie == ((1,0,1),(7,0,-3))
                        for oe in self.rg.out_edges(ie[0]):#out_edges,e.g. oe = ((1,0,1),(7,0,-3)) or ((1,0,1),(7,0,5))
                            if ( oe[1][0:2] == v[0:2] and oe[1][2] != -3 ):
                                sv.add(v) 
                                se.add(ie)
                                #self.rg.remove_node(v), if we remove v here, we might encounter an Error: RuntimeError: dictionary changes size during iteration, since we are looping through v, so add it to a set and remove it outside of the for loop, as in the next line
            for e in se:
                self.rg.remove_edge(*e)
            for v in sv:
                if (self.rg.in_degree(v) == 0): 
                    self.rg.remove_node(v)

            self.fileLogger.write(self, self.log_level,"After looping, number of nodes = {}, self.rg.nodes() = {}".format(self.rg.number_of_nodes(),self.rg.nodes()))
            self.fileLogger.write(self, self.log_level,"number of edges = {}".format(self.rg.number_of_edges()))
            for e in self.rg.edges():
                self.fileLogger.write(self, self.log_level,"{} {}".format(e,self.rg.get_edge_data(*e)))

            self.dc_flag = 0
            continue

    def _check_hidden_conflict_eslh(self,dpid,tid,r): #eslh: event suppression by local handling = hidden conflicts class 1
        # loop through each hc input to check for overlap of this rule (dpid,tid,r) with the interested traffic of the corresponding control app. If the cookie is the same, skip it as this rule is installed by that app, otherwise, log it in the hc database.
        #self.ft = {1: {0: {1: (256, 1, OFPMatch(oxm_fields={'ipv4_dst': '192.168.1.3', 'in_port': 1, 'ipv4_src': '192.168.1.1', 'ip_proto': 6, 'eth_type': 2048}), [OFPActionOutput(len=16,max_len=65509,port=3,type=0)], [7], (1, 2048, 6, '192.168.1.1', '192.168.1.3', -1, -1, -1, -1), (-1, -1, -1, -1, {3}))}}},
        #self.ft = {dpid1: {table0_id: {1:(flow0_cookie,priority,match,action,next_hop,matchmap,actmap)
        #hidden conflict input hci = {'eplb': [1024, [7], [-1], 2048, [6], ['192.168.1.1'], ['192.168.1.3','192.168.1.4'], [-1], [-1], [-1], [-1]], 'routing': [256, [], [-1], 2048, [0], [-1], [-1], [-1], [-1], [-1], [-1]], 'sampleapp': [4096, [5, 6], [3], 2048, [6, 17], ['192.168.1.1', '192.168.1.2'], ['192.168.1.3', '192.168.1.4'], [12345, 12346], [80], [12345, 12346], [5001, 53]]}, index: 0: cookie, 1: target switch, 2: in_port, 3: eth_type, 4: ip_proto, 5: ipv4_src, 6: ipv4_dst, 7: tcp_src, 8:tcp_dst, 9:udp_src, 10:udp_dst
        #self.hc_cfl_rules = {1:{}, 2:{}, 3:{}} #hidden conflicting rules, 1: Event Suppression by Local Handling, 2: Event Suppression by Changes to Paths, 3: Action Suppression by Packet Modification. self.hc_cfl_rules[1] = {app1:[((dpid,table id,rule1),[matchmap1 in list form]),((dpid2,tid2,rule2),[matchmap2 in list form]),...], app2:[((rule1),[matchmap1]),((rule2),[matchmap2]),...],...}, each tuple (dpid, table id, rule) is a rule, where rule corresponds to the number stored in self.ft, a rule may be broad and cover several interested traffic of a control app, these overlaps are reflected by the matchmap in list format [matchmap]. The 2nd and 3rd hidden conflict classes have not been attacked in this version v4_4
        break_flag = 0
        for app in self.hci:
            if (dpid not in self.hci[app][1]):#app[1]: target switch
                continue
            if (self.hci[app][0] == self.ft[dpid][tid][r][0]):#app[0]: cookie, rule r is installed by app, ignore
                continue
            if (self.hci[app][1][0] == "all"):#app[1]: target switch, currently, don't check hidden conflicts for apps installing rules on all switches, e.g., routing
                continue
            re = utility.compare_match_hc(self.ft[dpid][tid][r][5],self.hci[app][2:]) #re: result = intersection between r and interested traffic of app.
            self.fileLogger.write(self, self.log_level,"check hc: re = {}".format(re))
            if (re == [0,-2]):# interested traffic of app and rule r are disjoint
                continue
            self.hc_cfl_rules[1].setdefault(app,[])
            self.hc_cfl_rules[1][app].append(((dpid,tid,r),re))


    def _remove_rule_from_rule_graph(self, dpid, tid, r):
        #remove vertex (dpid,tid,r) from rule graph and all the related paths
        #add rules that are shadowed or made redundant by rule (dpid,tid,r) and not a node of the rule graph, to self.tbar, so that they will be added to the rule graph
       
        # or consider, if there is no other rules, add a wavering edge to the vertices connect to this vertex.
        # for ier in self.rg.in_edges((dpid,tid,r)): #ier in_edge of rule r
        #     if (self.rg.out_degree(ier[0]) == 1):
        #         self.fileLogger.write(self, self.log_level,"Adding a temporary wavering edge to the vertex %s",ier[0])
        #         #this wavering edge should be removed right before the next distributed conflict detection is performed, since there may be new rules matching rule ir
        #         self.rg.add_edges_from([(ier[0],(ier[0][0],ier[0][1],-3))])
        # need matchmap
        #         self.rg[(ch,0,ir)][(nh,0,-3)][path] = (matchmap, -1) #-1 means don't care for priority

        for oer in self.rg.out_edges((dpid,tid,r)): #oer out edge of rule r
            #if (oer[1][0] ==0 or oer[1][-1] < 0):# oer[1] is the vertex at the end of oer. If index 0 is 0, this vertex is an end-point, the path stops there. Index -1 is the last element of the vertex, the problematic vertex has this value less than 0, eg. -3: wavering edge, -4, loop, -1: deliberate drop, -2: accidental drop.  
            #   return
            self.fileLogger.write(self, self.log_level,"call remove_rule_from_rule_graph v=({}), iv=({},{},{})".format(oer[1],dpid,tid,r))
            self.remove_rule_from_rule_graph(oer[1],(dpid,tid,r))

        try:
            self.rg.remove_node((dpid,tid,r))
        except nx.exception.NetworkXError:
            self.fileLogger.write(self, self.log_level,"Node ({},{},{}) is not in the rule graph".format(dpid,tid,r))


        #remove rule r from self.ft, self.rules_pointing_to_dpid, self.lc_cfl_rules, self.dt_cfl_rules, self.rg and self.tbar
        for nh in self.ft[dpid][tid][r][4]: # the index 4 points to the next_hop list of the rule
            if (nh != -2 and not self._is_endpoint(nh)):
                self.rules_pointing_to_dpid[nh].remove((dpid,tid,r))
                self.fileLogger.write(self, self.log_level,"self.rules_pointing_to_dpid = {}".format(self.rules_pointing_to_dpid))

        #remove rule r from data record/structure... of the local conflicts.
        if (dpid in self.lc_cfl_rules and r in self.lc_cfl_rules[dpid][tid]):#eg. self.lc_cfl_rules = {4: {0: {2: [(1, 'class Overlap (local conflicts)', (0, 4, 0))]}}, 5: {0: {2: [(1, 'class Overlap (local conflicts)', (0, 4, 0))]}}}
            self.lc_cfl_rules[dpid][tid].pop(r)
            for (i,j) in self.lc_cfl_rules[dpid][tid].items():
                for k in j:
                    if (k[0] == r):
                        self.lc_cfl_rules[dpid][tid][i].remove(k)
            self.fileLogger.write(self, self.log_level,"self.lc_cft_rules = {}".format(self.lc_cfl_rules))

        #remove rule r from data record/structure... of the distributed conflicts.
        for k,v in self.dt_cfl_rules.items(): #eg. self.dt_cfl_rules = {1: [(((4, 0, 1), (5, 0, 1), (6, 0, 2), (4, 0, 1), (4, 0, -4)), (-1, 2048, 0, '192.168.1.1', '192.168.1.3', -1, 80, -1, -1))], 2: [], 3: [], 4: []}
            tbr = set() #to be removed
            for (p,m) in self.dt_cfl_rules[k]:
                if ((dpid,tid,r) in p):
                    tbr.add((p,m))
            for j in tbr:
                self.dt_cfl_rules[k].remove(j)

        #remove rule r from data record/structure... of the hidden conflicts.
        #self.hc_cfl_rules = {1: {'sampleapp': [((5, 0, 1), [[3], 2048, [6, 17], ['192.168.1.1'], ['192.168.1.3', '192.168.1.4'], [12345, 12346], [80], [12345, 12346], [5001, 53]]), ((5, 0, 2), [[3], 2048, [6, 17], ['192.168.1.2'], ['192.168.1.3'], [12345, 12346], [80], [12345, 12346], [5001, 53]])]}, 2: {}, 3: {}}
        for (app,rl) in self.hc_cfl_rules[1].items():#rl: rule list
            for rule in rl:
                if (rule[0] == (dpid,tid,r)):
                    self.hc_cfl_rules[1][app].remove(rule)

        #remove rule r from data record/structure... of the hidden conflicts.
        if ([dpid,tid,r,1] in self.tbar):
            self.fileLogger.write(self, self.log_level,"Remove [{},{},{},1] out of the self.tbar".format(dpid,tid,r))
            self.tbar.remove([dpid,tid,r,1])

        self.ft[dpid][tid].pop(r)
        self.fileLogger.write(self, self.log_level,"After removing rule ({},{},{}), self.ft = {}".format(dpid,tid,r,self.ft))
        
    def remove_rule_from_rule_graph(self, v, iv):#v is vertex behind input vertex iv
        self.fileLogger.write(self, self.log_level,"in remove_rule: v={}, iv={}".format(v,iv))
        if (self.rg.out_degree(v) == 0):
            return
        for oev in self.rg.out_edges(v):#oev: out_edge of vertex v
            self.fileLogger.write(self, self.log_level,"oev={}, list of paths = {}".format(oev, self.rg[oev[0]][oev[1]].keys()))
            sp = set() #set of paths
            count = 0 #count the number of paths in oev containing v
            for p in self.rg[oev[0]][oev[1]].keys():
                if (iv in p):
                    self.fileLogger.write(self, self.log_level,"iv={} in p={}".format(iv, p))
                    count += 1
                    sp.add(p)
            #if (count == 0): #there is no paths of oev containing v, stop here
            #    return
            #else:
            if (count > 0):
                for p in sp:
                    self.rg[oev[0]][oev[1]].pop(p)
                self.remove_rule_from_rule_graph(oev[1],iv)


    def _is_endpoint(self,next_hop):
        # switch nodes are ints, endpoints ip addresses
        return isinstance(next_hop, str)


    def _check_next_hop_and_add_rule(self, dpid, table_id, rule_id, matchmap, path):
        #TODO we may have to probe for hidden conflict if there will be rules installed
        #in the next hop on active traffic?, 
        #and besides, if all next hops nh are not in self.ft, add this to the list of wavering nodes.
        next_hop_list = self.ft[dpid][table_id][rule_id][4]
        # if next_hop_list is empty this is a drop action
        if not len(next_hop_list):
            self.add_rule_to_rule_graph(rule_id,dpid,None,matchmap,path)
            return
        # if it is not a drop action check if connected rule is already in ft
        for next_hop in next_hop_list:
            if (next_hop != -2 and not self._is_endpoint(next_hop) and next_hop not in self.ft):
                self.fileLogger.write(self, self.log_level,"next hop is not yet in the rule database self.ft, rule in the next hop may be installed on active traffic")
                continue
            self.fileLogger.write(self, self.log_level,"rule {} in sw {}, nh={}".format(rule_id,dpid,next_hop))
            self.add_rule_to_rule_graph(rule_id,dpid,next_hop,matchmap,path)


    def _add_rule_to_rule_graph(self, dpid, tid, r):
        if (dpid not in self.rules_pointing_to_dpid or len(self.rules_pointing_to_dpid[dpid]) == 0):
            self._check_next_hop_and_add_rule(dpid, tid, r, self.ft[dpid][tid][r][5], ((dpid,tid,r),))
        else:
            count_v = 0 # number of vertex v connecting to rule r, direction is from v to r.
            for v in self.rules_pointing_to_dpid[dpid]:
                continue_flag = 0
                try:
                    for con in self.lc_cfl_rules[v[0]][v[1]][v[2]]:
                        if (con[2] in [(2,1,1),(2,3,1),(0,1,1)]): 
                            #shadowing2, correlation4 to be compatible with 
                            #OpenFlow13 where the new rule of pattern (0,1,1) 
                            #overrides the existing rule in the same flow table
                            self.fileLogger.write(self, self.log_level,"rule {} in table 0 of sw {} is shadowed by rule {}, ignore this rule in checking distributed conflicts".format(v[2],v[0],con[0]))
                            continue_flag = 1
                            break
                except KeyError:
                    pass

                if (continue_flag == 1): 
                    #rule v is shadowed by another rule, ignore it
                    continue

                #check if rule at vertex v has connection with rule (dpid,tid,r)
                #adapt matchmap of rule v for compare_match_interflowtable
                matchmap_v = utility.combine_matchmap_and_actmap(self.ft[v[0]][v[1]][v[2]][5],self.ft[v[0]][v[1]][v[2]][6])                
                #first compare the in_port of rule r (if any) and out_port of rule v, 
                #if in_port of rule r does not correspond to out_port of v, 
                #these 2 rules are disjoint.
                in_port_r = self.ft[dpid][tid][r][5][0]
                if (not self._check_inport(in_port_r,dpid,v[0])): #adapt to the use of MultiDiGraph
                    continue
          
                matchmap_r = self.ft[dpid][tid][r][5]
                # re = [match relationship, intersection of matchmap_v and matchmap_r]
                re_v = utility.compare_match_interflowtable(matchmap_v, matchmap_r) 
                self.fileLogger.write(self, self.log_level,"in _add_rule_to_rule_graph: rule v ({},{},{}) relationship re=%s with the new rule r ({},{},{})".format(v[0],v[1],v[2],re_v, dpid,tid,r))

                if (re_v[0] == 0 ): # 0 means disjoint
                    continue

                """now there is intersection between v and rule r, add an edge between v and r, 
                and loop through all the in_edges to v to have its paths, extend these paths to r, 
                then call the add_rule_to_rule_graph function with the just obtained input.
                """

                count_v += 1

                """new: check if v is already in self.rg. If yes, take the in_edge of v and append 
                its to r and call add_rule_to_rule_graph from r

                else: this means v is also a new rule and should be within self.tbar, 
                set the processed flag of the corresponding element of v in self.tbar to 0, 
                add an edge from v to r (this also has the effect of adding both v and r 
                to the rule graph), then call _add_rule_to_rule_graph (this function) recursively.
                """
                try:
                    index = self.tbar.index([v[0],v[1],v[2],1])
                except ValueError:
                    if v not in self.rg.nodes():
                        self.rg.add_node(v)
                        self.fileLogger.write(self, self.log_level,"just added node v={} to rg".format(v))
                if (v in self.rg.nodes()):
                    #1. add an edge from v to r:
                    self.rg.add_edges_from([(v,(dpid,tid,r),{(v,(dpid,tid,r)):(re_v[1],self.ft[dpid][tid][r][1])})])
                    #2. get in_edges to vertex v to consider its path and matchmap
                    #2.1 if in_degree of v is 0:
                    if (len(self.rg.in_edges(v)) == 0):
                        self._check_next_hop_and_add_rule(dpid, tid, r, re_v[1], (v,(dpid,tid,r)))
                    
                    #2.2 if there are some edges to v, extract its path, 
                    #matchmap and update rule graph in the direction to the new rule (dpid,tid,r)
                    else:
                        count_path = 0 # count the number of paths that has connection to rule r
                        in_edge_v = list(self.rg.in_edges(v))
                        for ie_v in in_edge_v:
                            """this way can help avoiding the runtime error: "dictionary changed size during iteration" 
                            if edges to v are added or removed, though this solution may be not good.

                            first remove the redundant paths of each ie_v, such a path contains more than two vertices, 
                            is a subset of another path while having the same matchmap as that other path, it is 
                            redundant since it contributes less value than the other path during the growth of the 
                            path to detect problems (eg. loop, drop). The paths of two vertices must be retained 
                            for inferring traffic path in case the other paths do not match.
                            """
                            l_rp = [] #list of redundant paths to be removed
                            l_lp = [] #list of long paths, ie, paths spanning more than 2 vertices
                            self.fileLogger.write(self, self.log_level,"self.rg.in_edge = {}".format(self.rg[ie_v[0]][ie_v[1]]))
                            sp_check = 0
                            #short path = path containing 2 vertices, 
                            #0 means sp matchmap is unique, 1 means its matchmap 
                            #is the same as one of the longer path, in that case, 
                            #we do not concerning it in growing path for other connected vertices.
                            for p in self.rg[ie_v[0]][ie_v[1]].keys(): 
                                if (len(p) == 2):
                                    spmm=self.rg[ie_v[0]][ie_v[1]][p][0] # short path matchmap ,sp = short path = path containing 2 vertices
                                if (len(p) > 2):
                                    l_lp.append(p)
                            self.fileLogger.write(self, self.log_level,"l_lp = {}".format(l_lp))
                            if (len(l_lp)>0):
                                for i in range(len(l_lp)):
                                    p1 = l_lp[i]
                                    s_p1 = set(p1)
                                    if (sp_check == 0):
                                        if (spmm == self.rg[ie_v[0]][ie_v[1]][p1][0]):
                                            sp_check = 1
                                    for j in range(len(l_lp)):
                                        if (i==j):
                                            continue
                                        p2 =l_lp[j]
                                        s_p2 = set(p2)
                                        if(s_p1.issubset(s_p2)):
                                            #comparing matchmap of these paths
                                            if (self.rg[ie_v[0]][ie_v[1]][p1][0] == self.rg[ie_v[0]][ie_v[1]][p2][0]): 
                                                l_rp.append(p1)
                                                break
                                for rp in l_rp: #redundant path
                                    self.fileLogger.write(self, self.log_level,"rp = {}".format(rp))
                                    self.rg[ie_v[0]][ie_v[1]].pop(rp) #remove redundant paths out of rule graph

                            for path in self.rg[ie_v[0]][ie_v[1]]:
                                #ie_v[1] == v, each edge has its attribute stored in the 
                                #dictionary data structure of path as key and (matchmap, priority) as value.
                                if (len(path) == 2 and sp_check == 1):
                                    #this short path has the same matchmap as one 
                                    #of the longer path, we don't consider it in growing paths for rule graph.
                                    continue
                                if (path[-1][-1] == -4): 
                                    #loop, don't consider adding rule to a path containing loop
                                    continue

                                pmm = self.rg[ie_v[0]][ie_v[1]][path][0] #path matchmap
                                #check if this path matchmap pmm intersects with the matchmap of r. 
                                #Note that, even though rule v alone has a connection to r, 
                                #it is not sure if the matchmap of a path to v connects with r 
                                #due to the combined effect of rules during the path growth.
                                rule_matchmap = self.ft[dpid][tid][r][5]
                                # re = [match relationship, intersection of pmm and rule_matchmap]
                                re = utility.compare_match_interflowtable(pmm, rule_matchmap)
                                if (re[0] == 0 ): # 0 means disjoint
                                    continue
                                if((dpid,tid,r) in path):
                                    self._handle_dt_loop(v[0],v[1],v[2],dpid,tid,r,path,re[1])
                                    continue
                                count_path += 1
                                # append the new rule (dpid,tid,r) to the path and update this path 
                                # to the edge from v to r, then call the add_rule_to_rule_graph 
                                # recursively to update the subsequent rules connected to r
                                tmp_path = list(path) #originally, path is a tuple
                                tmp_path.append((dpid,tid,r))
                                tmp_path = tuple(tmp_path)
                                self.rg[v][(dpid,tid,r)][tmp_path] = (re[1],self.ft[dpid][tid][r][1]) # [1] is priority of rule
                                self._check_next_hop_and_add_rule(dpid, tid, r, re[1], tmp_path)

                        if (count_path == 0):
                            # There is no path of existing in_edges connecting to this new rule r, 
                            # call add_rule starting from rule v connected to it
                            self._check_next_hop_and_add_rule(dpid, tid, r, re_v[1], (v,(dpid,tid,r)))
                else:
                    self.fileLogger.write(self, self.log_level,"index of v in self.tbar = {}".format(index))
                    self.tbar[index][3] = 0 #reset processed flag to 0
                    #1. add an edge from v to r:
                    self.rg.add_edges_from([(v,(dpid,tid,r),{(v,(dpid,tid,r)):(re_v[1],self.ft[dpid][tid][r][1])})])
                    self.fileLogger.write(self, self.log_level,"call _add_rule_to_rule_graph for the father vertex ({},{},{}) of vertex ({},{},{})".format(v[0],v[1],v[2],dpid,tid,r))
                    self._add_rule_to_rule_graph(v[0],v[1],v[2])

            if (count_v == 0):
                #there is no rule v that connects to rule r
                self.fileLogger.write(self, self.log_level,"There is no rule connected to this new rule, consider it a new root connected to other rules")
                self._check_next_hop_and_add_rule(dpid, tid, r, self.ft[dpid][tid][r][5], ((dpid,tid,r),))


    def add_rule_to_rule_graph(self,ir,ch,nh,matchmap,path):        
        """input rule denoted by its number in self.ft[dpid][table_id], 
        current hop (dpid), next hop (dpid or host), see description of next hop in self.ft, 
        matchmap is initally the matchmap of the input rule ir, at each next step, 
        matchmap is the intersection of ir and the rule in the next hop that intersects with it. 
        Path is a tuple of vertices, e.g., ((1,0,1),(2,0,4)), a path formed by rule chain is unique 
        and becomes a key of the edge dictionary. 
        self.rg.[vertex1][vertex2] = {path:(matchmap, priority of rule in the next hop)}, 
        the priority of rule is important when considering matching a concrete packet, 
        e.g., a packet can match 2 rules in the next_hop due to the generalization conflict, 
        then the rule of higher pri will be chosen.
        """       
        if (path[-1][-1] == -4): 
            #loop, don't consider adding rule to a path containing loop
            return

        if (nh == None): 
            #if the next_hop field in self.ft is empty([]), i.e., explicit drop
            self._handle_dt_drop(path,matchmap)
            return self.rg.add_edges_from([((ch,0,ir),(ch,0,-1),{path:(matchmap,-1)})]) #priority in this case = -1, meaning don't care

        if (nh == -2): # -2 means invalid output
            self.dt_cfl_rules["black-hole"].append((path,matchmap)) #[3] is for accidental drop
            return self.rg.add_edges_from([((ch,0,ir),(ch,0,-2),{path:(matchmap,-1)})]) #again, priority = -1, don't care

        if self._is_endpoint(nh):
            ip = nh.split(':')[1]
            tmp_path1 = list(path) #originally, path is a tuple
            tmp_path1.append((0,ip))
            tmp_path1 = tuple(tmp_path1)
            self.rg.add_edges_from([((ch,0,ir),(0,ip),{tmp_path1:(matchmap,-1)})])
            if (((ch,0,ir),(0,ip)) not in self.rg[(ch,0,ir)][(0,ip)]):
                self.rg.add_edges_from([((ch,0,ir),(0,ip),{((ch,0,ir),(0,ip)):(self.ft[ch][0][ir][5],-1)})])
            return

        """check for loop, stop if there's a loop, else the path would grow forever
        Check exactly the rule in the next hop, ie. (nh,0,num) is in the path, not only the datapath
        as a rule can connect to a newer rule in the next hop, eg., because of next hop value like 
        in the conflict7_by_traffic_looping directory.
        """
        #adapt matchmap for compare_match_interflowtable, to check for direct connection of rule ir with a rule in the next hop
        matchmap_ir = utility.combine_matchmap_and_actmap(self.ft[ch][0][ir][5],self.ft[ch][0][ir][6])
        #adapt matchmap for compare_match_interflowtable, to check for connection of the input path with a rule in the next hop
        matchmap = utility.combine_matchmap_and_actmap(matchmap,self.ft[ch][0][ir][6])
        num_matching_rule = 0 # check the number of rules overlapping/intersecting the rule ir in the nh
        for num, rule in self.ft[nh][0].items():
            # TODO we currently just consider table 0
            #check if rule num is active, i.e., it is not shadowed by some other rules in the nh
            continue_flag = 0
            try:
                for con in self.lc_cfl_rules[nh][0][num]:
                    if (con[2] in [(2,1,1),(2,3,1),(0,1,1)]): #shadowing2, correlation4
                        self.fileLogger.write(self, self.log_level,"rule {} in table 0 of sw {} is shadowed by rule {}, ignore this rule in checking distributed conflicts".format(num,nh,con[0]))
                        continue_flag = 1
                        break
            except KeyError:
                pass

            if (continue_flag == 1): 
                # this rule is shadowed by other rules, it won't get effective, ignore it
                continue

            #first compare the in_port of rule in next hop (if any) and 
            #out_port of rule in current hop, if in_port of nh rule does 
            #not correspond to out_port of ch rule, these 2 rules are disjoint.
            rule_matchmap = rule[5]
            in_port_nh = rule_matchmap[0] #in_port of rule in nh
            if (not self._check_inport(in_port_nh,nh,ch)): #adapt to the use of MultiDiGraph
                continue 

            #check for direct connection between ir and (nh,0,num), add a direct link if there is a connection but not yet existent
            re = utility.compare_match_interflowtable(matchmap_ir, rule_matchmap) # re = [match relationship, intersection of ir and rule]
            if (re[0] == 0): # 0 means disjoint
                #if there is no direct connection --> 
                #there is certainly no connection of the input path with narrower matchmap 
                # with this rule either--> skip this rule and check the next one
                continue            
            # add a direct connection between 2 vertices
            self.rg.add_edges_from([((ch,0,ir),(nh,0,num),{((ch,0,ir),(nh,0,num)):(re[1],self.ft[nh][0][num][1])})])
            #check for connection of the path and input rule to this rule (nh,0,num)
            re = utility.compare_match_interflowtable(matchmap, rule_matchmap) # [match relationship, intersection of ir and rule]
            self.fileLogger.write(self, self.log_level,"in build_rule_graph: rule {} in sw {},re={}".format(num,nh,re))
            if (re[0] == 0): # 0 means disjoint
                continue
            num_matching_rule += 1
            #now there is intersection betwenn the cumulative matchmap of the path to ir and rule (nh,0,num), 
            #check if rule num causes a loop
            if ((nh,0,num) in path):
                self.fileLogger.write(self, LogLevel.Debug,"Distributed Conflict! Loop detected!")
                self.fileLogger.write(self, self.log_level,"vertex = ({},0,{}), path = {}".format(nh,num, path))
                """now, there's a loop, either update this rule with the path to the rule graph 
                and the distributed conflict database self.dt_cfl_rules if the path and the 
                rule are new or cover an existing path in the dc database; or ignore this path 
                and the rule if it is covered by one of the existing.
                """
                self._handle_dt_loop(ch,0,ir,nh,0,num,path,re[1])
                continue

            # Now, there is a connection of the rule (nh,0,num) with the input rule ir and it causes no loop, add it to the rule graph
            self.fileLogger.write(self, self.log_level,"add an edge to self.rg from ({},0,{}) to ({},0,{})".format(ch,ir,nh,num))
            self.rg.add_edges_from([((ch,0,ir),(nh,0,num))])
            tmp_path3 = list(path) #originally, path is a tuple
            tmp_path3.append((nh,0,num))
            tmp_path3 = tuple(tmp_path3)
            self.rg[(ch,0,ir)][(nh,0,num)][tmp_path3] = (re[1],self.ft[nh][0][num][1]) #self.ft[nh][0][num][1] is priority of rule self.ft[nh][0][num]
            nnh = None # next switches the rule points to
            next_hop_list = rule[4]
            for nnh in next_hop_list:
                if (nnh not in self.ft):
                    #TODO We may have to probe for hidden conflict if there will be 
                    #rules installed in the next hop on active traffic?, 
                    #and besides, if all next hops nh are not in self.ft, 
                    #add this to the list of wavering nodes.
                    self.fileLogger.write(self, self.log_level,"next next hop nnh is not yet in the rule database self.ft, rule in the next next hop may be installed on active traffic")
                    continue
                self.add_rule_to_rule_graph(num,nh,nnh,re[1],tmp_path3)
            if (nnh == None):
                self.add_rule_to_rule_graph(num,nh,nnh,re[1],tmp_path3)
        # Now, all rules in the next hop have been processed
        if (num_matching_rule == 0): 
            """there is no rule in nh matching rule ir, all traffic matching rule ir may be dropped, 
            although this needs to be checked. By default, a sw doesn't know how to handle some 
            traffic will ask the controller for instructions.
            """
            self.fileLogger.write(self, self.log_level,"Adding a temporary wavering edge")
            #this wavering edge should be removed right before the next distributed conflict detection is performed, 
            #since there may be new rules matching rule ir
            self.rg.add_edges_from([((ch,0,ir),(nh,0,-3))])
            self.rg[(ch,0,ir)][(nh,0,-3)][path] = (matchmap, -1) #-1 means don't care for priority
            # TODO this rule is candidate for hidden conflicts, add it to hidden conflicts' candidate rule/traffic

    def _handle_dt_drop(self,path,matchmap):
        # do not consider any rules that have no in edge
        # rules that prevent packets from entering the topology are not distributed conflicts
        # rules that drop traffic coming from within the topology indicate a Spuriousness conflict
        if len(path) < 2:
            self.fileLogger.write(self, LogLevel.Debug,"\nDistributed Conflict\nDrop ignored since it is not considered as spurious: Path{}\nMatchmap:{}".format(path,matchmap))
            return
        check_path = 0
        for (p,m) in self.dt_cfl_rules["drop"]:
            if (path[0] in p or p[0] in path):# if true, probably path is a subset of p or vice versa, or they are the same
                self.fileLogger.write(self, self.log_level,"path = {}, p = {}".format(path,p))
                if (len(path) <= len(p)):
                    index = p.index(path[0])
                    if (p[index:index+len(path)] == path):
                        self.fileLogger.write(self, self.log_level,"path is a subset of p existent in dt_cfl_rules[2], ignore it")
                        check_path = 1
                        break
                else:
                    index = path.index(p[0])
                    if (path[index:index+len(p)] == p):
                        self.fileLogger.write(self, self.log_level,"path is a superset of p existent in dt_cfl_rules[2], remove p, add path to dt_cfl_rules[2]")
                        check_path = 2
                        break
        self.fileLogger.write(self, self.log_level,"check_path = {}".format(check_path))
        if (check_path == 1): #tmp_path is a repetition in dt_cfl_rules, do nothing
            pass
        elif (check_path == 2):
            self.dt_cfl_rules["drop"].remove((p,m))
        if (check_path in [0, 2]):#check_path == 0 means the path is new to the dc drop database
            if (path,matchmap) not in self.dt_cfl_rules["drop"]:
                self.dt_cfl_rules["drop"].append((path,matchmap)) #[2] is for deliberate drop
                self.fileLogger.write(self, LogLevel.Crit,"\nDistributed Conflict\nDrop:{}\nMatchmap:{}".format(path,matchmap))

    def _handle_dt_loop(self,ch,ctid,cr,nh,ntid,nr,path,matchmap): 
        """current hop, current table id, current rule, next hop, next tid, next rule, path 
        containing the vertex (ch,ctid,cr) and the next hop vertex (nh,ntid,nr) cause a loop in path, 
        matchmap is the intersection of the path matchmap and the rule (nh,ntid,nr)
        """
        tmp_path = list(path) #originally, path is a tuple
        tmp_path.append((nh,ntid,nr)) #Append again to see exactly which rule repeats in the loop.
        check_path = 0
        tmp_edges=set()
        tmp_vertices = set()
        #check if (nh,0,num) is a node in some existing path in self.dt_cfl_rules
        self.fileLogger.write(self, self.log_level,"(nh,ntid,nr) = ({},{},{}),tmp_path[0] = {}".format(nh,ntid,nr,tmp_path[0]))
        for (p,m) in self.dt_cfl_rules["loops"]:
            if ((nh,ntid,nr) in p and tmp_path[0] in p):# if true, probably p is a subset of tmp_path2 or vice versa, or they are the same
                self.fileLogger.write(self, self.log_level,"tmp_path = {}, p = {}".format(tmp_path,p))
                if (len(tmp_path) <= len(p)):
                    index = p.index(tmp_path[0])
                    if (p[index:index+len(tmp_path)] == tuple(tmp_path) and matchmap == m):
                        self.fileLogger.write(self, self.log_level,"path is a subset of p existent in dt_cfl_rules, ignore it")
                        check_path = 1
                        break
                else:
                    index = tmp_path.index(p[0])
                    if (tuple(tmp_path[index:index+len(p)]) == p and matchmap == m):
                        self.fileLogger.write(self, self.log_level,"path is a superset of p existent in dt_cfl_rules, remove p, add path to dt_cfl_rules")
                        check_path = 2
                        tmp_edges.add(p[-2:])
                        tmp_vertices.add(p[-1]) # remove the last element, which is (dpid,0,-4), so the comparison between 2 sets set_tmp_path2 and set_p is relevant.
                        break
        self.fileLogger.write(self, self.log_level,"check_path = {}".format(check_path))
        tmp_path.append((nh,ntid,-4)) #-4 means loop in path (distributed conflicts)
        tmp_path = tuple(tmp_path)
        #add a direct edge
        self.rg[(ch,ctid,cr)][(nh,ntid,nr)][tmp_path] = (matchmap,self.ft[nh][ntid][nr][1]) # [1] is priority of rule
        if (check_path == 1): 
            #tmp_path is a repetition in dt_cfl_rules, do nothing
            pass
        elif (check_path == 2):
            self.dt_cfl_rules["loops"].remove((p,m))
            self.fileLogger.write(self, self.log_level,"removing edges: {}".format(tmp_edges))
            # remove from the self.rg the last node of p, ie, (dpid, 0, -4) 
            # as this path is a redundant repetition of tmp_path2
            for e in tmp_edges:
                if (e in self.rg.edges()):
                    self.rg.remove_edge(e[0],e[1])
            self.fileLogger.write(self, self.log_level,"possibly removing vertices: {}".format(tmp_vertices))
            for v in tmp_vertices:
                if (self.rg.in_degree(v) == 0):
                    self.rg.remove_node(v)
        if (check_path in [0, 2]):#check_path == 0 means the tmp_path2 is new to the dc database
            #add to self.dt_cfl_rules[1] (tmp_path2,matchmap) and to the rule gragh the relevant edge
            if ((tmp_path,matchmap) not in self.dt_cfl_rules["loops"]):
                self.dt_cfl_rules["loops"].append((tmp_path,matchmap))
                self.fileLogger.write(self, LogLevel.Crit,"\nDistributed Conflict\nLoop:{}\nMatchmap:{}".format(tmp_path,matchmap))
            self.rg.add_edges_from([((nh,ntid,nr),(nh,ntid,-4),{tmp_path:(matchmap,-1)})])

    def _check_inport(self, in_port, src, dst): 
        """given a switch A with dpid src, switch B with dpid dst, 
        check if switch A connects to switch B using the port in_port
        return False: no, True: yes
        """
        if (in_port == -1):
            return True
        for va in self.net[src][dst].values():
            if (va['port'][0] == in_port):
                return True
        return False

    @set_ev_cls(flowmod_class.MsgFlowMod)
    def _flowmod_handler(self, ev):
        self.fileLogger.write(self, self.log_level, "receive a FlowMod message")
        self.dc_flag = 0
        self.timeout_dc = TIMEOUT_DC
        self.fileLogger.write(self, self.log_level,"reassign, self.dc_flag = {}".format(self.dc_flag))
        datapath = ev.datapath
        dpid = datapath.id
        self.fileLogger.write(self, self.log_level, "datapath {}, id {}".format(datapath,dpid))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.fileLogger.write(self, self.log_level,"priority={}".format(ev.priority))
        self.fileLogger.write(self, self.log_level,"match={}".format(ev.match))
        self.fileLogger.write(self, self.log_level,"actions={}".format(ev.actions))

        # parse the FlowMod elements
        cookie = ev.cookie
        cookie_mask = ev.cookie_mask
        table_id = ev.table_id
        command = ev.command
        idle_timeout = ev.idle_timeout
        hard_timeout = ev.hard_timeout
        priority = ev.priority
        buffer_id = ev.buffer_id
        out_port = ev.out_port
        out_group = ev.out_group
        flags = ev.flags
        match = ev.match
        actions = ev.actions

        #if not IP traffic in general, or not TCP/UDP traffic, just install rule and exit
        #The excluded traffic include layer2 traffic (e.g., VLAN), ICMP traffic
        # not yet consider IPv6 traffic
        eth_type = -1
        ip_proto = 0 # = in_proto.IPPROTO_IP
        time_now = datetime.datetime.now()
        t_before = time.time()
        try:
            eth_type = match['eth_type']
        except KeyError: 
            # not IP traffic. In OpenFlow, we always need to specify the field eth_type in order 
            # to install the layer 3 related rules, including IP
            # just install rules and exit
            return 1
        if (eth_type != 2048):
            # eth_type of IP is 2048 or 0x0800
            return 2
        # now we know that the match is for IP traffic
        try: 
            ip_proto = match['ip_proto']
        except KeyError:
            pass
        if (ip_proto not in [in_proto.IPPROTO_IP, in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]):
            return 3

        """Now the traffic is either general IP, or TCP or UDP (ip_proto = 0, 6, 17 respectively), eth_type=2048
        We assume that the match field always has correct ip addresses. If the original match doesn't cover 
        ip addresses but MAC addresses only, these MAC addresses are converted to their corresponding IP addresses in the match.
        
        Calculate rule map = matchmap, priority, action, for rule comparison, rule map is also stored in self.ft
        matchmap = in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst
        if a field is missing, its value is -1
        to this point, we have already eth_type=2048, ip_proto = 0 or 6 or 17
        """
        try: 
            in_port = match['in_port']
        except KeyError:
            in_port = -1 # or wildcard, which means any port
        try:
            ipv4_src = match['ipv4_src']
        except KeyError:
            ipv4_src = -1 # or wildcard, which means any ip address
        try:
            ipv4_dst = match['ipv4_dst']
        except KeyError:
            ipv4_dst = -1 # or wildcard, which means any ip address
        try:
            tcp_src = match['tcp_src']
        except KeyError:
            tcp_src = -1 # depends on ip_proto, if ip_proto=6, it means any port, else, it is irrelevant
        try:
            tcp_dst = match['tcp_dst']
        except KeyError:
            tcp_dst = -1 # depends on ip_proto, if ip_proto=6, it means any port, else, it is irrelevant
        try:
            udp_src = match['udp_src']
        except KeyError:
            udp_src = -1 # depends on ip_proto, if ip_proto=6, it means any port, else, it is irrelevant
        try:
            udp_dst = match['udp_dst']
        except KeyError:
            udp_dst = -1 # depends on ip_proto, if ip_proto=6, it means any port, else, it is irrelevant

        """convert MAC address to ip_address using ARP_cache, some control app installs rule based 
        on MAC (layer 2) for source and destination, while we consider ip (layer 3).
        """
        try:
            eth_src = match['eth_src']
        except KeyError:
            eth_src = -1
        try:
            eth_dst = match['eth_dst']
        except KeyError:
            eth_dst = -1
        if (ipv4_src == -1 and eth_src != -1):
            for ip in self.arp_cache_db:
                if (eth_src == self.arp_cache_db[ip]['mac']):
                    ipv4_src = ip
                    break
        if (ipv4_dst == -1 and eth_dst != -1):
            for ip in self.arp_cache_db:
                if (eth_dst == self.arp_cache_db[ip]['mac']):
                    ipv4_dst = ip
                    break

        matchmap = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
        
        next_hop = [] #from dpid and out_port in the actions, we can infer the next hop(s)
        outport = set() # the advantage of set is that we can add value in any order, it facilitates the comparison independent of the order in which each value was added (unlike list)
        sf_ipv4_src = -1 #setField in actions
        sf_ipv4_dst = -1 #setField in actions
        sf_tcp_src = -1 #setField tcp source port
        sf_tcp_dst = -1 #setField tcp destination port.
        sf_udp_src = -1 #setField udp source port
        sf_udp_dst = -1 #setField udp destination port.

        for act in actions:
            if hasattr(act, 'port'):
                outport.add(act.port) # here also store outport to controller and to LOCAL
                for i in self.net[dpid]:
                    for va in self.net[dpid][i].values():#adapt to the use of MultiDiGraph
                        if (va['port'][0] == act.port):
                            next_hop.append(i)
                            break
                if (len(next_hop) == 0 and act.port not in [ofproto_v1_3.OFPP_CONTROLLER, ofproto_v1_3.OFPP_LOCAL]): #next hop is an end-point
                    for i in self.arp_cache_db:
                        if (self.arp_cache_db[i]['dpid'] == dpid and self.arp_cache_db[i]['port'] == act.port):
                            next_hop.append("host:"+i)
                    if (len(next_hop) == 0):
                        """After the for loop, len(next_hop) is still 0 --> 
                        the outport forwards the matching traffic to an invalid port, 
                        not to the other switch nor to an end-point. Any matching traffic will 
                        be dropped here, as if a black-hole. This can be a bug or a conflict 
                        which is up to the sense of the analyst, anyway, this needs to be logged, 
                        we put this in self.rg (rule graph)
                        """
                        next_hop.append(-2) # -2 means invalid output, also causes packet drop/black-hole
                        log_message = "ERROR (possibly)! Incoming rule has invalid output, all of its matching traffic can be dropped!"
                        self.fileLogger.write(self, LogLevel.Debug,log_message)

            if hasattr(act, 'key'): #action has setField
                if (act.key == "ipv4_src"):
                    sf_ipv4_src = act.value
                if (act.key == "ipv4_dst"):
                    sf_ipv4_dst = act.value
                if (act.key == "tcp_src"):
                    sf_tcp_src = act.value
                if (act.key == "tcp_dst"):
                    sf_tcp_dst = act.value
                if (act.key == "udp_src"):
                    sf_udp_src = act.value
                if (act.key == "udp_dst"):
                    sf_udp_dst = act.value
        actmap = (sf_ipv4_src,sf_ipv4_dst,sf_tcp_src,sf_tcp_dst,sf_udp_src,sf_udp_dst,outport)

        #Detect conflict
        conflict = [] # contains local and distributed conflicts
        # check local conflicts:
        update_ft_flag = 1 # flag triggering the update of self.ft, 0: don't update.
        try:
            for num, rule in self.ft[dpid][table_id].items():
                if (update_ft_flag == 0):
                    conflict = [] #clear conflict list so this rule will not be updated in self.lc_cfl_rules
                    break
                compared_matches = utility.compare_match(matchmap, rule[5])
                matrel = compared_matches[0]
                self.fileLogger.write(self, LogLevel.Debug,"intersection between 2 matchmap\nm1 = {}\nm2={}\nre={}".format(matchmap,rule[5],compared_matches))
                self.fileLogger.write(self, self.log_level,"matrel = {}".format(matrel))
                if (matrel != 0): # 0 = disjoint
                    if (priority == rule[1]):
                        prirel = 0 #priority relationship
                    elif (priority < rule[1]):
                        prirel = 1
                    else:
                        prirel = 2
                    if (actmap == rule[6]): #rule[6] = actmap
                        actrel = 0 # action relationship
                    else:
                        actrel = 1 
                    for conpat in self.lcp: #conflict pattern, e.g., ('class Shadowing1 (local conflicts)',[(1,2,1),(1,1,1),'its effect'])
                        if ((prirel,matrel,actrel) in conpat[1]):
                            self.fileLogger.write(self, LogLevel.Debug,"Conflict! {}, {}".format(conpat[0],conpat[2]))
                            if ((prirel,matrel,actrel) in [(0,1,0),(1,1,0)]):
                                self.fileLogger.write(self, self.log_level,"redundant rule, pattern ({},{},{}) (belonging to a part of the redundancy local conflict class that should be ignored), ignore!".format(prirel,matrel,actrel))
                                update_ft_flag = 0
                                conflict = [] #clear conflict list so this rule will not be updated in self.lc_cfl_rules
                                break
                            conflict.append((conpat[0],(prirel,matrel,actrel),conpat[2], num)) #e.g., (class,(1,2,1),effect, 3)
                            self.fileLogger.write(self, LogLevel.Crit,"\nLocal Conflict - {}\n:Priority Relationship Pattern:{}\nMatchmap Relationship Pattern:{}\nAction Relationship Pattern:{}".format(conpat[0], prirel, matrel, actrel, conpat[2]))
                            self.fileLogger.write(self, LogLevel.Crit,"\nMatchmap 1:{}".format(matchmap))
                            self.fileLogger.write(self, LogLevel.Crit,"\nMatchmap 2:{}".format(rule))
                            #each pattern in self.lcp is unique, 
                            #if (prirel,matrel,actrel) matches a pattern already, it won't match the other patterns, 
                            #so break the for loop to save some calculation time.
                            break

        except KeyError:
            # self.ft[dpid][table_id] is empty, simply store this rule in self.ft and install it in data plane.
            pass

        """and store flow tables of each switch, if detector is passive, store first, detect after, 
        else detect first, may not store if do not install the rule

        self.ft = {dpid1: {table0_id: [(flow0_cookie,priority,match,action,next_hop,matchmap),
          (flow1_cookie,pri,m,a,nh,mm),...], table1_id: [(flow0_cookie,pri,match,action,next_hop,matchmap),
          (flow1_c,p,m,a,nh,mm)],...}, dpid2:{}, dpid3:{}, ...}
        """
        if (len(conflict) > 0 ):
            self.fileLogger.write(self, LogLevel.Debug,"conflicts detected: {}".format(conflict))
            # write detected conflicts and their origin to log file
            self.lc_cfl_rules.setdefault(dpid,{})
            self.lc_cfl_rules[dpid].setdefault(table_id,{})
            self.lc_cfl_rules[dpid][table_id].setdefault(self.rule_num[dpid][table_id],[])
            for con in conflict:
                if (con[1] in [(2,1,1),(2,3,1),(2,2,1),(2,4,1),(0,1,1),(2,1,0),(2,3,0),(2,2,0),(2,4,0)]):
                    """shadowing2, generalization2, correlation2 where new rule has higher priority 
                    than existing rule conflicting with it. Correlation4 (0,1,1) is also included 
                    here to be compatible with OpenFlow13, where new rule will override the existing 
                    rule having the same priority and match but different action. Also adding the redundancy 
                    and overlap patterns where new rule has higher priority, which cause the existing (older) 
                    rule to be (partially) deactivated.
                    """
                    self.lc_cfl_rules[dpid][table_id].setdefault(con[3],[])
                    self.lc_cfl_rules[dpid][table_id][con[3]].append((self.rule_num[dpid][table_id],con[0],con[1]))
                    if (con[1] == (0,1,1)): 
                        #correlation4 (0,1,1), new rule will override the existing rule having 
                        #the same priority and match but different action. ie, the existing will be deleted, 
                        self.tbrr.append([dpid,table_id,con[3],1])
                        self.fileLogger.write(self, self.log_level,"self.tbrr = {}".format(self.tbrr))
                else:
                    self.lc_cfl_rules[dpid][table_id][self.rule_num[dpid][table_id]].append((con[3],con[0],con[1]))
            self.fileLogger.write(self, self.log_level,"self.lc_cfl_rules = {}".format(self.lc_cfl_rules))


        t_after = time.time()
        td = t_after - t_before #time difference
        if (update_ft_flag == 1):
            self.fileLogger.write(self, LogLevel.Crit,"\n\n{}".format(time_now))
            self.fileLogger.write(self, LogLevel.Crit,"\nNew rule is coming, number of existing rules: {}".format(utility.count_rules(self.ft)))
            if (dpid in self.ft):
                self.ft[dpid].setdefault(table_id,{})
                self.rule_num[dpid].setdefault(table_id, 1)
                self.ft[dpid][table_id][self.rule_num[dpid][table_id]] = (cookie,priority,match,actions,next_hop,matchmap,actmap)
                self.tbar.append([dpid,table_id,self.rule_num[dpid][table_id],1])
                for i in next_hop:
                    if i in self.rules_pointing_to_dpid:
                        self.rules_pointing_to_dpid[i].append((dpid, table_id, self.rule_num[dpid][table_id]))
                    else:
                        self.rules_pointing_to_dpid[i] = [(dpid, table_id, self.rule_num[dpid][table_id])]
                self.rule_num[dpid][table_id] += 1
            else:
                self.rule_num[dpid] = {table_id:1}
                self.ft[dpid] = {table_id:{self.rule_num[dpid][table_id]:(cookie,priority,match,actions,next_hop,matchmap,actmap)}}
                self.tbar.append([dpid,table_id,self.rule_num[dpid][table_id],1])
                for i in next_hop:
                    if i in self.rules_pointing_to_dpid:
                        self.rules_pointing_to_dpid[i].append((dpid, table_id, self.rule_num[dpid][table_id]))
                    else:
                        self.rules_pointing_to_dpid[i] = [(dpid, table_id, self.rule_num[dpid][table_id])]
                self.rule_num[dpid][table_id] += 1

            self.fileLogger.write(self, LogLevel.Crit,"\nTime difference (ms) in checking local conflicts and adding new rule ({},{},{}) to the rule database = {}".format(dpid,table_id,self.rule_num[dpid][table_id]-1,td*1000))

        self.fileLogger.write(self, LogLevel.Debug,"Detector's just installed a rule in switch {}".format(datapath.id))
        #set this flag, so the thread _detect_distributed_conflicts/_update_rule_graph 
        #will perform detecting distributed conflicts if after self.timeout_dc period, 
        #there is no new rule arriving that clear this self.dc_flag.
        self.dc_flag = 1
