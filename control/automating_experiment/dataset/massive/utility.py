__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '1.0'

'''

'''
Provide the basic utitity for other apps
'''

# Handy function that lists all attributes in the given object
def ls(obj):
    print("\n".join([x for x in dir(obj) if x[0] != "_"]))

def add_flow(cookie, datapath, priority, match, actions, buffer_id=None):
    ofproto=datapath.ofproto
    parser = datapath.ofproto_parser
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    if buffer_id:
        mod = parser.OFPFlowMod(cookie=cookie,datapath=datapath, buffer_id=buffer_id,
                priority=priority, match=match, instructions=inst)
    else:
        mod=parser.OFPFlowMod(cookie=cookie,datapath=datapath, priority=priority,
                match=match, instructions=inst)
    datapath.send_msg(mod)

#    def add_flow_with_hard_timeout(self, datapath, priority, match, actions, buffer_id=None, hard_timeout):
def add_flow_with_hard_timeout(cookie, datapath, priority, match, actions, hard_timeout):
    ofproto=datapath.ofproto
    parser = datapath.ofproto_parser
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    #if buffer_id:
    #    mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, buffer_id=buffer_id,
    #            priority=priority, match=match, instructions=inst)
    #else:
    mod=parser.OFPFlowMod(cookie=cookie, datapath=datapath, hard_timeout=hard_timeout, priority=priority,
                match=match, instructions=inst)
    datapath.send_msg(mod)

def add_flow_with_idle_timeout(cookie, datapath, priority, match, actions, idle_timeout):
    ofproto=datapath.ofproto
    parser = datapath.ofproto_parser
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    #if buffer_id:
    #    mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, buffer_id=buffer_id,
    #            priority=priority, match=match, instructions=inst)
    #else:
    mod=parser.OFPFlowMod(cookie=cookie, datapath=datapath, idle_timeout=idle_timeout, priority=priority,
                match=match, instructions=inst)
    datapath.send_msg(mod)
