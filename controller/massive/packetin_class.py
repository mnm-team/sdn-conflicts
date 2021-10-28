#from ryu.ofproto import ofproto_parser
from ryu.ofproto import ofproto_v1_3_parser as parser


class MsgPktIn(parser.OFPPacketIn):
    #def __init__(self, datapath, version, msg_type, msg_len, xid, buf, buffer_id, total_len, reason, table_id, cookie, match, data):
    #def __init__(self, datapath, version, msg_type, msg_len, xid, buffer_id, total_len, reason, table_id, cookie, match, data):
    def __init__(self):
        pass
        #super(MsgPktIn, self).__init__(datapath, buffer_id, total_len, reason, table_id, cookie, match, data)
        #super(parser.OFPPacketIn,self).__init__(datapath)
        
    @classmethod
    #def build_packetin_message(cls, datapath, version, msg_type, msg_len, xid, buf, buffer_id, total_len, reason, table_id, cookie, match, data):
    def build_packetin_message(cls, datapath, version, msg_type, msg_len, xid, buffer_id, total_len, reason, table_id, cookie, match, data):
        #msg = cls(datapath, version, msg_type, msg_len, xid, buffer_id, total_len, reason, table_id, cookie, match, data)
        msg = cls()
        msg.datapath = datapath
        msg.version = version
        msg.msg_type = msg_type
        msg.msg_len = msg_len
        msg.xid = xid
        #msg.buf = buf
        msg.buffer_id = buffer_id
        msg.total_len = total_len
        msg.reason = reason
        msg.table_id = table_id
        msg.cookie = cookie
        msg.match = match
        msg.data = data
        return msg
