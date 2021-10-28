'''
20201221
Cuong Tran - cuongtran@mnm-team.org
I refered to the ryu/app/simple_switch_rest_13.py, ofctl_rest.py and this link
https://osrg.github.io/ryu-book/en/html/rest_api.html
https://ryu.readthedocs.io/en/latest/app/ofctl_rest.html#add-a-flow-entry
to program and to run this app

To run this app for testing it alone:
    ryu-manager --observe-links utility_rest.py
To run with detector.py:
    ryu-manager --observe-links utility_rest.py detector.py

Then, a rule can be installed by running this in another terminal of the controller con0:
    curl -X POST -d '{"dpid":1,"match":{"in_port":1, "eth_src":"00:00:00:00:00:01"}, "actions":[{"type":"OUTPUT","port":2}]}' http://localhost:8080/utility/addrule
    curl -X POST -d '{"dpid":1,"match":{"in_port":9, "eth_type":2048, "ipv4_src":"192.168.1.1", "ipv4_dst":"192.168.1.3"}, "actions":[{"type":"OUTPUT","port":9}]}' http://localhost:8080/utility/addrule


'''
import json
import utility_detector as utility
from ryu.app.wsgi import Response
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib import ofctl_v1_3 as ofctl
from ryu.lib import ofctl_utils
from ryu.ofproto import ofproto_v1_3

import logging
LOG = logging.getLogger('ryu.lib.ofctl_v1_3')
UTIL = ofctl_utils.OFCtlUtil(ofproto_v1_3)

utility_instance_name = 'utility_api_app'

class UtilityRest13(utility.Utility):

    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(UtilityRest13, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(UtilityController, {utility_instance_name: self})
        self.datapathmap = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        datapath = ev.msg.datapath
        self.datapathmap.update({datapath.id:datapath})
        print("swittch features handler!!")


class UtilityController(ControllerBase):
    
    def __init__(self, req, link, data, **config):
        super(UtilityController, self).__init__(req, link, data, **config)
        self.utility_rest_app = data[utility_instance_name]

    @route('addrule', '/utility/addrule', methods=['POST'], requirements=None)
    def add_rule(self, req, **kwargs):
            ur = self.utility_rest_app # utility_rest
            #print(utility_rest.datapathmap)
            print("req = %s"%req)
            try:
                nr = req.json if req.body else {} #new rule
                print("new rule")
            except ValueError:
                print("Raise status 400")
                raise Response(status=400)
            print(nr)
            try:
                dpid = nr['dpid']
                if dpid not in ur.datapathmap:
                    s = "dpid %s not in datapathmap, exit"%dpid
                    print(s)
                    body = json.dumps(s)
                    return Response(content_type='application/json',body=body)
            except KeyError:
                s = "there is no dpid to install, exit"
                print(s)
                return Response(content_type='application/json',body=json.dumps(s))
            dp = ur.datapathmap[dpid]
            match = ofctl.to_match(dp, nr.get('match',{}))
            print("match = %s"%match)
            actions = []
            for a in nr.get('actions',[]):
                action = ofctl.to_action(dp, a)
                if action is not None:
                    actions.append(action)
            print("actions = %s"%actions)
            cookie = ofctl.str_to_int(nr.get('cookie',0))
            cookie_mask = ofctl.str_to_int(nr.get('cookie_mask',0))
            table_id = UTIL.ofp_table_from_user(nr.get('table_id',0))
            idle_timeout = ofctl.str_to_int(nr.get('idle_timeout',0))
            hard_timeout = ofctl.str_to_int(nr.get('hard_timeout',0))
            priority = ofctl.str_to_int(nr.get('priority',0))
            buffer_id = UTIL.ofp_buffer_from_user(
                nr.get('buffer_id', dp.ofproto.OFP_NO_BUFFER))
            out_port = UTIL.ofp_port_from_user(
                nr.get('out_port', dp.ofproto.OFPP_ANY))
            out_group = UTIL.ofp_group_from_user(
                nr.get('out_group', dp.ofproto.OFPG_ANY))
            flags = ofctl.str_to_int(nr.get('flags', 0))
            ur.add_flow_full_fields(dp, cookie, cookie_mask, table_id, ofproto_v1_3.OFPFC_ADD, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, actions)
