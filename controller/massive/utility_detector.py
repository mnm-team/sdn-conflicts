__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '2.0' 
20201123

send the event of flow to be installed in the data plane to the conflict detector.
The conflict detector will examine the rule against the existing rules of the data plane 
to check for conflicts.


__version__ = '1.0'
before 202005

Provide the basic utitity for other apps
'''

from ryu.ofproto import ofproto_v1_3
from ryu.base import app_manager

import flowmod_class
import utility

# Handy function that lists all attributes in the given object


def ls(obj):
    print("\n".join([x for x in dir(obj) if x[0] != "_"]))


class Utility(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _EVENTS = [flowmod_class.MsgFlowMod]
    """
    A list of event classes which this RyuApp subclass would generate.
    This should be specified if and only if event classes are defined in a different python module from the RyuApp subclass is.
    Source: ryu/base/app_manager.py
    """
    def __init__(self, *args, **kwargs):
        super(Utility, self).__init__(*args, **kwargs)
        self.DETECTOR_ACTIVE = True

    def add_flow(cookie, datapath, priority, match, actions, buffer_id=None):
        utility.add_flow(cookie, datapath, priority, match, actions, buffer_id=None)

        if self.DETECTOR_ACTIVE:
          self.send_event_to_observers(flowmod_class.MsgFlowMod(datapath=datapath, cookie=cookie, cookie_mask=0x0, table_id=0, command=ofproto_v1_3.OFPFC_ADD, idle_timeout=0,hard_timeout=0,priority=priority,buffer_id=ofproto_v1_3.OFP_NO_BUFFER, out_port=0, out_group=0, flags=0,match=match,actions=actions))
          #self.logger.info("Send event add_flow")

    
    def add_flow_with_hard_timeout(self, cookie, datapath, priority, match, actions, hard_timeout):
        utility.add_flow_with_hard_timeout(cookie, datapath, priority, match, actions, hard_timeout)

        if self.DETECTOR_ACTIVE:
          self.send_event_to_observers(flowmod_class.MsgFlowMod(datapath=datapath, cookie=cookie, cookie_mask=0x0, table_id=0, command=ofproto_v1_3.OFPFC_ADD, idle_timeout=0,hard_timeout=hard_timeout,priority=priority,buffer_id=ofproto_v1_3.OFP_NO_BUFFER, out_port=0, out_group=0, flags=0,match=match,actions=actions))
          #self.logger.info("Send event add_flow_with_hard_timeout")
    
    def add_flow_with_idle_timeout(self, cookie, datapath, priority, match, actions, idle_timeout):
        utility.add_flow_with_idle_timeout(cookie, datapath, priority, match, actions, idle_timeout)

        if self.DETECTOR_ACTIVE:
          self.send_event_to_observers(flowmod_class.MsgFlowMod(datapath=datapath, cookie=cookie, cookie_mask=0x0, table_id=0, command=ofproto_v1_3.OFPFC_ADD, idle_timeout=idle_timeout,hard_timeout=0,priority=priority,buffer_id=ofproto_v1_3.OFP_NO_BUFFER, out_port=0, out_group=0, flags=0,match=match,actions=actions))
          #self.logger.info("Send event add_flow_with_idle_timeout")
        

    def add_flow_full_fields(self, datapath, cookie, cookie_mask, table_id, command, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, actions):
        utility.add_flow_full_fields(datapath, cookie, cookie_mask, table_id, command, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, actions)

        if self.DETECTOR_ACTIVE:
          self.send_event_to_observers(flowmod_class.MsgFlowMod(datapath=datapath, cookie=cookie, cookie_mask=cookie_mask, table_id=table_id, command=command, idle_timeout=idle_timeout,hard_timeout=hard_timeout,priority=priority,buffer_id=buffer_id, out_port=out_port, out_group=out_group, flags=flags,match=match,actions=actions))
          #self.logger.info("Send event add_flow_full_fields")
