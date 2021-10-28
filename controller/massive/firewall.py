import threading
import concurrent.futures
import re
import enum
import json
import time
import random
from log import Log, LogLevel
from http_app import HttpApp, HttpAppError, HttpAction
import globalconfig


class TopoEvent(enum.Enum):
    Firewall = "firewall(s)"


def _json_pretty(json_ugly):
    return json.dumps(json_ugly, indent=2)


def _int_id_to_hex(id_int):
    return "%016x" % int(id_int)


def _hex_id_to_int(id_hex):
    return int(id_hex, 16)


def _str_hex_id_to_int(str_hex_id):
    return int(str_hex_id, 16)


class FirewallMonitor:
    """AppMonitor runs a thread that continuously requests information
    on topology, firewalls and net loads of a RYU server. The monitoring thread has
    several states that enable it to make decisions autonomously for
    blocking/redirecting traffic that is causing high net loads.
    Flows with a predefined priority will not be blocked/redirected.
    For a maximum load limit traffic will be blocked and notifications will
    be sent to an admin. Critical changes in the topology will trigger
    also trigger notifications.
    """
    def __init__(self, log_level=LogLevel.Info):

        params = {
        	  "rest_server_port": 8080,
	          "rest_server_host": "0.0.0.0",
	          "logger_file": "/tmp/ryu_fw_log"
        }
        self.firewall_switches = {}
        self.monitor_freq = None
        self.url_ports = "/stats/port/" # need to add dpid / [port]
        self.url_firewalls = "/stats/switches"
        self.url_flow_stats = "/stats/flow/"  # need to add datapath id
        self.url_rules = "/utility/addrule" 
        self.load_scale = 10 ** (-6)  # ryu loads are bytes and we want MB
        self.max_cache_timeouts = 100000
        self.f_bytes_key = "byte_count"
        self.p_bytes_key = "tx_bytes"
        self.ts_key = "timestamp"
        self.bw_key = "bandwidth"
        self.f_stats_key = "flow_stats"
        self.p_stats_key = "port_stats"
        self.f_timeouts_key = "flow_timeouts" # TODO check if we need to use cap for times i.e. 0 at some point to block permanently
        self.s_id_key = "switch_id"
        self.s_config_key = "config"
        self.prio_key = "priority"
        self.match_key = "match"
        self.port_key = "port_no"
        self.actions_key = "actions"
        self.cookie = 0x880
        self.hard_timeout = 5 # 5 seconds
        self.exp_timeout = 2 # 2 seconds
        self.max_exponent = 10
        self.out_port_pattern = re.compile("OUTPUT:[0-9]+")
        self.log_level = log_level

        # utilities
        self.http_app = HttpApp(params)
        self.logger = Log(params)
        self.monitor_thread = None
        self.http_error_count = 0
        self.run = True

        self._load_config() # initialize global and local config
        self._start_monitor()  # starts a new thread

  
    def _load_config(self):
        # ignore priority since we set priority based on the given flows
        priority, target_switches = globalconfig.parseGlobalConfig("fw")
        local_config = json.load(open("fw_config_local", "r"))
        self.monitor_freq = local_config["bw_time"]
        for dpid, switchConfig in local_config["switchConfigs"].items():
            if int(dpid) not in target_switches:
                self.logger.write(self,self.log_level, "Ignoring local config for dpid {}".format(dpid))
            else:
                # initialize all config fields and structures for caching data
                self.firewall_switches[int(dpid)] = {
                        self.s_config_key: switchConfig, 
                        self.p_stats_key:{}, 
                        self.f_stats_key:{},
                        self.f_timeouts_key:{}}


    def _start_monitor(self):
        self.monitor_thread = threading.Thread(target=self._start_monitor_cycle, args=())
        self.monitor_thread.start()
        self.logger.write(self,self.log_level, "Monitor Starting")
        return


    def _stop(self):
        if not self.run:
            return self.logger.write(self,LogLevel.Crit, "Tried to stop firewall but no thread is running!")
        self.run = False
        response = "Stopped monitor mode and not getting any firewall info anymore!"
        self.logger.write(self,LogLevel.Warn, response)
        return


    def _get_firewalls(self):
        """Get status/number of switches which are configured as firewalls,
        process results and return a list.
        """
        fws = self.http_app.conn(HttpAction.GET, self.url_firewalls)
        fws = list(filter(
                    (lambda v: v in self.firewall_switches), fws))
        self._handle_topology_response(len(fws) - len(self.firewall_switches), TopoEvent.Firewall)
        return fws


    def _start_monitor_cycle(self):
        """Method that is started in monitoring thread.
        Administers data structures to buffer information on the monitored topology for
        comparison with following cycles. If the http connection to a RYU rest webserver
        causes to many errors the loop is stopped and the action is logged, 
        since the monitoring features is not active anymore.
        """
        current_firewalls = None
        while self.run:
            time.sleep(self.monitor_freq)  # wait and start new monitor cycle
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:

                    # create own threads for all http calls that are uncorrelated
                    firewalls = executor.submit(self._get_firewalls)
                    concurrent.futures.wait([firewalls],
                                            return_when=concurrent.futures.FIRST_EXCEPTION)

                    # get result or propagate exception
                    current_firewalls = list(
                        map(lambda fw: str(fw),firewalls.result()))

                futures = []
                # get port stats for firewall nodes
                if len(current_firewalls) > 0:
                    try:
                        with concurrent.futures.ThreadPoolExecutor(
                                max_workers=len(self.firewall_switches)) as executor:

                            # get port stats for all firewalls concurrently
                            for value in current_firewalls:
                                str_val = str(value)
                                future = executor.submit(
                                        self.http_app.conn, HttpAction.GET, self.url_ports + str_val)
                                futures.append(future)

                            concurrent.futures.wait(
                                    futures, return_when=concurrent.futures.FIRST_EXCEPTION)

                        # process requested port stats and determine net loads
                        for switch_future in futures:
                            switch_stat = switch_future.result()
                            str_val = next(iter(switch_stat))  # get first key in dict
                            dpid = int(str_val)
                            if dpid in self.firewall_switches:
                                updated_loads = {}
                                fw_switch = self.firewall_switches[dpid]
                                for port_stats in switch_stat[str_val]:
                                    port_no = port_stats[self.port_key]
                                    # only process non-reserved ports
                                    if isinstance(port_no, int):
                                        byte_count = port_stats[self.p_bytes_key]
                                        timestamp = time.time()
                                        bandwidth = 0
                                        if port_no in fw_switch[self.p_stats_key]:
                                            cached_stats = fw_switch[self.p_stats_key][port_no]
                                            bandwidth = (byte_count - cached_stats[self.p_bytes_key])
                                            interval = timestamp - cached_stats[self.ts_key]
                                            # convert to MB/s
                                            bandwidth = (bandwidth * self.load_scale) / interval
                                         
                                        updated_loads[port_no] = {
                                                self.p_bytes_key: byte_count, 
                                                self.ts_key: timestamp, 
                                                self.bw_key: bandwidth}

                                # update cached port stats for firewall switch
                                fw_switch[self.p_stats_key] = updated_loads

                    except HttpAppError as e:
                        self._handle_http_error(e)

            except HttpAppError as e:
                self._handle_http_error(e)
            
            self._handle_updated_loads()
            self.logger.write(self,self.log_level, "Sleeping before next monitor cycle")


    def _handle_http_error(self, e):
        self.http_error_count += 1
        message = "An error occurred in http connection to RYU Manager - {}".format(e)
        log_level = LogLevel.Warn

        if self.http_error_count > 100:
            log_level = LogLevel.Crit
            message = """Stopping monitor due to consistent errors with http connection.
                      Immediate action is required!
                      """
            self._stop()

        self.logger.write(self,log_level, message)


    def _handle_topology_response(self, num_changes, topo_event):
        """Processes topology information and compares them to buffered
        information in order to determine if any nodes or links in the
        topology were added or removed. If nodes/links are removed a mail
        notification is sent to an admin.
        """
        log_level = LogLevel.Info
        message = ""
        if num_changes < 0:
            log_level = LogLevel.Crit
            message = "{} {} are now down!".format(num_changes * (-1), topo_event.value)
        elif num_changes > 0:
            message = "{} has registered {} new {}!".format(type(self).__name__, num_changes, topo_event.value)
        else:
            return  # do nothing since number has not changed

        self.logger.write(self,log_level, message)


    def _handle_updated_loads(self):
        """Method to check aggregate net loads passing
        through a switch. If a load exceeds a configured
        threshold the detailed stats for all flows in a firewall
        switch are requested, sorted, filtered and the flow causing
        the most amount of traffic is blocked. When a load limit for
        early alerts is reached a mail notification is sent to an admin
        with the list of largest flows for inspection. If any autonomous
        mode is enabled the early alert limit will instead block or redirect
        the largest flow without sending a message.
        """
        log_level = LogLevel.Info
        message = ""
        fw_switches = self.firewall_switches
        futures = []
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(fw_switches)) as executor:
                for dpid in fw_switches:
                    future = executor.submit(self.http_app.conn, HttpAction.GET, self.url_flow_stats + str(dpid))
                    futures.append(future)
                # this will raise an error, terminate the method and propagate the exception to caller
                concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_EXCEPTION)

            
            for flow_stats in futures:
                result = flow_stats.result()  # this will be a dict with one entry
                str_dpid = next(iter(result))  # get key from http response body
                dpid = int(str_dpid)
                fw_switch = fw_switches[dpid]
                flows = result[str_dpid]  # get flows from key
                port_stats = fw_switch[self.p_stats_key]
                cached_loads = fw_switch[self.f_stats_key]         
                flow_timeouts = fw_switch[self.f_timeouts_key]
                updated_loads = {}
                for flow_stat in flows:
                    # only process if last action is output port to other node, i.e. a number
                    out_port_action = flow_stat[self.actions_key][-1:]
                    if len(out_port_action):
                      out_port_action = out_port_action[0]
                    else:
                       out_port_action = "DROP"
                    if re.fullmatch(self.out_port_pattern, out_port_action) != None:
                        out_port = int(re.split(":", out_port_action)[1])
                        match = flow_stat[self.match_key]
                        hashable_match = str(match)
                        byte_count = flow_stat[self.f_bytes_key]
                        priority = flow_stat[self.prio_key]
                        timestamp = time.time()
                        bandwidth = 0
                        # update if flow was already seen
                        if out_port in cached_loads and hashable_match in cached_loads[out_port]["stats"]:
                            cached_stats = cached_loads[out_port]["stats"][hashable_match]
                            bandwidth = (byte_count - cached_stats[self.f_bytes_key])
                            interval = timestamp - cached_stats[self.ts_key]
                            # convert to MB/s
                            bandwidth = (bandwidth * self.load_scale) / interval
                           
                            # block flow if it exceeds the per flow threshold 
                            if bandwidth > fw_switch[self.s_config_key]["bw_flow_threshold"]:
                                exponent = 1
                                
                                if out_port not in flow_timeouts:
                                    flow_timeouts[out_port] = {}
                                    flow_timeouts[out_port][hashable_match] = exponent
                                elif hashable_match in flow_timeouts[out_port]:
                                    exponent += flow_timeouts[out_port][hashable_match]
                                
                                flow_timeouts[out_port][hashable_match] = min(self.max_exponent,exponent)
                                try:
                                  timeout = self.exp_timeout**flow_timeouts[out_port][hashable_match]
                                  text = "Blocking elephant flow: {} with timeout {}!"
                                  text = text.format(_json_pretty(match), str(timeout))
                                  self.logger.write(self,self.log_level, text)
                                  self._block_flow(dpid, priority, timeout, match)
                                  # decrement bandwidth count by bandwidth of blocked flow
                                  port_stats[out_port][self.bw_key] -= bandwidth
    
                                except HttpAppError as e:
                                    self._handle_http_error(e)
                                
                        
                        # need to initialize data structures for first flow on port
                        if out_port not in updated_loads:
                            updated_loads[out_port] = {"matches":[], "stats":{}}
                        
                        # add match to array for random choice if port is congested
                        updated_loads[out_port]["matches"].append(hashable_match)
                        # add flow stats for caching or dropping if port is congested
                        updated_loads[out_port]["stats"][hashable_match] = {
                                self.f_bytes_key: byte_count, 
                                self.ts_key: timestamp,
                                self.prio_key: priority,
                                self.bw_key: bandwidth,
                                self.match_key: flow_stat[self.match_key]}
                        
                # at some point we need to flush the remembered exponential timeouts
                if len(flow_timeouts) > self.max_cache_timeouts:
                    flow_timeouts = {}

                for port, port_stat in port_stats.items():
                    if isinstance(port,int) and port in updated_loads:
                        port_loads = updated_loads[port]
                        while port_stat[self.bw_key] > fw_switch[self.s_config_key]["bw_port_threshold"]:
                            try:
                              elem = random.randint(0, len(port_loads["matches"])-1)
                              hashable_match = port_loads["matches"].pop(elem)
                              block_flow = port_loads["stats"][hashable_match]
                              # don't blow flows that haven't been seen twice by firewall
                              if block_flow[self.bw_key] > 0:
                                  text = "Blocking random flow: {} with timeout {}!"
                                  text = text.format(_json_pretty(match), str(self.hard_timeout))
                                  self.logger.write(self,self.log_level, text)
                                  try:
                                      self._block_flow(
                                          dpid, 
                                          block_flow[self.prio_key], 
                                          self.hard_timeout, 
                                          block_flow[self.match_key])
                                  except HttpAppError as e:
                                        self._handle_http_error(e)
                                        break

                                  # decrement bandwidth count by bandwidth of blocked flow
                                  port_stat[self.bw_key] -= block_flow[self.bw_key]
                                  del port_loads["stats"][hashable_match]
        
                            except Exception as e:
                                self.logger.write(self,LogLevel.Warn, "Could not find flow to block!")
                                self.logger.write(self,LogLevel.Debug, "Could not find flow to block!")
                                break
                       
                        port_loads["matches"] = [] # clear the matches list for next cycle

                # update cached flow stats for firewall switch
                fw_switch[self.f_stats_key] = updated_loads #

        except HttpAppError as e:
            self._handle_http_error(e)

        #self.logger.write(self,LogLevel.Debug, self.firewall_switches)

    def _block_flow(self, dpid, priority, timeout, match):
        # TODO might need to check for max prio
        block_flow = {
          "dpid":dpid,"priority":priority + 1,"hard_timeout":timeout,"match":match,"cookie":self.cookie, "actions":[]}

        # send HTTP request to set rule via detector
        self.http_app.conn(HttpAction.POST, self.url_rules, json.dumps(block_flow))


if __name__ == "__main__":
       fw = FirewallMonitor(LogLevel.Debug)
