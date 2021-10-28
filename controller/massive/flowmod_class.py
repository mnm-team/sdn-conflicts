from ryu.controller import ofp_event, event

class MsgFlowMod(event.EventBase):
    #def __init__(self, datapath, cookie, cookie_mask, table_id, command, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, actions, instructions):
    def __init__(self, datapath, cookie, cookie_mask, table_id, command, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, actions):
        super(MsgFlowMod,self).__init__()
        self.datapath = datapath
        self.cookie = cookie
        self.cookie_mask = cookie_mask
        self.table_id = table_id
        self.command = command
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout
        self.priority = priority
        self.buffer_id = buffer_id
        self.out_port = out_port
        self.out_group = out_group
        self.flags = flags
        self.match = match
        self.actions = actions
        #self.instructions = instructions
