__author__ = 'Cuong Dai Ca'
__email__ = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

'''
__version__ = '3.0'
20210608, added compare_match_hc function to compare the matchmap of a rule with the interested traffic of a control application to detect hidden conflicts of the 
first class "Event Suppression by Local Handling"

__version__ = '2.1' 
20201210, added intersection (overlap) result while comparing match fields of 2 rules. The intersection serves as input for the distributed conflict detection.

__version__ = '2.0' 
20201130, added compare match function for conflict detector


__version__ = '1.0'
2019 or earlier

'''

'''
Provide the basic utitity for other apps
'''


from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import in_proto
import ipaddress
import socket
import struct

# Handy function that lists all attributes in the given object
def ls(obj):
    print("\n".join([x for x in dir(obj) if x[0] != "_"]))


def add_flow(cookie, datapath, priority, match, actions, buffer_id=None):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    if buffer_id:
        mod = parser.OFPFlowMod(
            cookie=cookie, datapath=datapath, buffer_id=buffer_id,
                priority=priority, match=match, instructions=inst)
    else:
        mod = parser.OFPFlowMod(
            cookie=cookie, datapath=datapath, priority=priority,
                               match=match, instructions=inst)
    datapath.send_msg(mod)

# def add_flow_with_hard_timeout(self, datapath, priority, match, actions,
# buffer_id=None, hard_timeout):


def add_flow_with_hard_timeout(cookie, datapath, priority, match, actions, hard_timeout):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    # if buffer_id:
    #    mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, buffer_id=buffer_id,
    #            priority=priority, match=match, instructions=inst)
    # else:
    mod = parser.OFPFlowMod(
        cookie=cookie, datapath=datapath, hard_timeout=hard_timeout, priority=priority,
                match=match, instructions=inst)
    datapath.send_msg(mod)


def add_flow_with_idle_timeout(cookie, datapath, priority, match, actions, idle_timeout):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    # if buffer_id:
    #    mod = parser.OFPFlowMod(datapath=datapath, hard_timeout=hard_timeout, buffer_id=buffer_id,
    #            priority=priority, match=match, instructions=inst)
    # else:
    mod = parser.OFPFlowMod(
        cookie=cookie, datapath=datapath, idle_timeout=idle_timeout, priority=priority,
                match=match, instructions=inst)
    datapath.send_msg(mod)

#def add_flow_full_fields(datapath, cookie, cookie_mask, table_id, command, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, instructions):
def add_flow_full_fields(datapath, cookie, cookie_mask, table_id, command, idle_timeout, hard_timeout, priority, buffer_id, out_port, out_group, flags, match, actions):
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
    mod = parser.OFPFlowMod(
            datapath=datapath, cookie=cookie, cookie_mask=cookie_mask,table_id=table_id,
            command=command, idle_timeout=idle_timeout, hard_timeout=hard_timeout,
            priority=priority, buffer_id=buffer_id, out_port=out_port, out_group=out_group,
            flags=flags, match=match, instructions=instructions)
    datapath.send_msg(mod)

#def compare_match(match1, match2):
#    '''
#    match1 and match2 only cover ip traffic for tcp, udp, do not cover other traffic including arp, icmp
#    return match1 subset/superset/overlap/disjoint match2
#    '''
#def compare_match(matchmap1, matchmap2):
def compare_match(m1, m2): 
    '''
    This function compares two matchmap within a single flow table.
                     (   0        1          2         3         4        5        6        7        8   )
    m1 = matchmap1 = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
    m2 = matchmap2 = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
                 1   (   2        2048      6         .1.2       -1       1234      -1      -1      -1   )
                 2   (   -1       2048      6        -1         .1.3       -1      5678     -1      -1   )
                 3   (   2        2048      0         .1.2       .1.3       1234    -1      -1      -1   )
                 4   (   -1       2048      6        -1         -1         -1      5678     -1      -1   )

    matchmap1 and matchmap2 (also, match1 and match2) only cover general ip traffic, traffic for tcp, udp, do not cover other traffic including arp, icmp
    matchmap1: a new rule to be installed, matchmap2 belongs to the existing rule in the data plane
    eth_type (m[1]) is present only for the sake of completion, we don't consider it here since its value is always 2048 for IP traffic.
    return: overlap pattern of match1 and match2:
    + 0 (disjoint)
    + 1 (equal)
    + 2 (subsetof)
    + 3 (supersetof)
    + 4 (overlap (not subsetof and not supersetof and intersection is not empty))
    should also return the difference, to be used in probing hidden conflicts
    rule:
    + X . X = X
    + disjoint . X = disjoint ( 0 . X = 0 )
    + X . equal = X ( X . 1 = X )
    + subsetof . supersetof = overlap (2 . 3 = 4)
    + if X != disjoint then X . overlap = overlap (X . 4 = 4, if X != 0 )

    Use ipaddress library to compare ip addresses: https://docs.python.org/3/library/ipaddress.html
    functions: overlaps(other), address_exclude(network)
    
    ip_proto has different encoding (don't use -1 for wildcard but 0), has to be considered separately

    The second value of the output is the intersection between matchmap1 and matchmap2, which is also a matchmap stored in a tuple (), if they are disjoint, the second value is -2, i.e., the returned value is the list [0,-2]
    '''
    if (m1 == m2):
        return [1,m1] # "equal"
    l = [[],[]] #list
    #res = [-1,-3] #result
    res = None #result
    for i in range(0,9):# since matchmap is a tuple of 9 elements
        if (len(l[1]) == 1):
            l[1].append(m1[1]) # add ip_proto 
        if (i == 1): # eth_type, ignore
            continue
        if (i == 2):# ip_proto
            res = compare_ipproto(m1[i],m2[i])
            if (res == [0,-2]):
                return [0,-2]
            l[0].append(res[0])
            l[1].append(res[1])
            continue
        if (i in [3,4]):# ip
            res = compare_ip(m1[i],m2[i])
            if (res == [0,-2]):
                return [0,-2]
            l[0].append(res[0])
            l[1].append(res[1])
            continue
        res = compare_xy(m1[i],m2[i])
        if (res == [0,-2]):
            return [0,-2]
        l[0].append(res[0])
        l[1].append(res[1])
    #print("compare_match l[i] = %s"%l)
    # now, m1 and m2 are not disjoint, determine if the relationship is equal, supersetof, subsetof or overlap
    fin = l[0][0] #final result
    for i in l[0][1:]:
        fin = multiply_relationship(fin,i)
        if (fin == 4):
            return [4,tuple(l[1])]
    return [fin,tuple(l[1])]

def combine_matchmap_and_actmap(m, a): 
    '''
    This function combine matchmap and actmap of a rule, mainly used for comparing rules in two different flow table (see function compare_match_interflowtable). The matchmap is adapted to the actmap, since the matchmap can be changed due to the setField action in the actmap. 
                   (   0        1          2         3         4        5        6        7        8   )
    m = matchmap = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
    a = actmap =   (ipv4_src, ipv4_dst, l4_src,   l4_dst,   outport_set) #we don't need to consider outport_set here, but still it is a part of the actmap

    return: a new matchmap, which is the combination of matchmap m and actmap a
    '''
    if (a[:4] == (-1,-1,-1,-1) ): #there is no setField in actmap a
        return m
    #print("modify matchmap for compare_match_interflowtable")
    #print("orininally, m=%s",m)
    l = list(m)
    if (a[0] != -1):
        l[3] = a[0]
    if (a[1] != -1):
        l[4] = a[1]
    if (a[2:4] != (-1,-1) ):
        if (m[2] == 6): #TCP
            if (a[2] != -1):
                l[5] = a[2]
            if (a[3] != -1):
                l[6] = a[3]
        if (m[2] == 17): #UDP
            if (a[2] != -1):
                l[7] = a[2]
            if (a[3] != -1):
                l[8] = a[3]
        else: #should never happen in OpenFlow 13, though we still provide a backup
            print("Error! There is no tcp or udp setField for ip_proto = %s!",m1[2])
            return -1
    #print("after modifying, m=%s",tuple(l))
    return tuple(l)

def compare_match_interflowtable(m1, m2): 
    '''
    This function compares two matchmap in two different flow table, the in_ports between two rules need to be check before using the network topology data (self.net), so the in_port doesn't make sense anymore and needs not be considered here in this function, in this implementation, we consider the in_port values between 2 rules are the same and are a wildcard value of -1. Apart from the difference in the in_port, this function is similar to the compare_match(m1,m2) above.
                     (   0        1          2         3         4        5        6        7        8   )
    m1 = matchmap1 = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
    m2 = matchmap2 = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
                 1   (   2        2048      6         .1.2       -1       1234      -1      -1      -1   )
                 2   (   -1       2048      6        -1         .1.3       -1      5678     -1      -1   )

    return: overlap pattern of match1 and match2:
    + 0 (disjoint)
    + 1 (equal)
    + 2 (subsetof)
    + 3 (supersetof)
    + 4 (overlap (not subsetof and not supersetof and intersection is not empty))
    rule:
    + X . X = X
    + disjoint . X = disjoint ( 0 . X = 0 )
    + X . equal = X ( X . 1 = X )
    + subsetof . supersetof = overlap (2 . 3 = 4)
    + if X != disjoint then X . overlap = overlap (X . 4 = 4, if X != 0 )

    The second value of the output is the intersection between matchmap1 and matchmap2, which is also a matchmap stored in a tuple (), if they are disjoint, the second value is -2, i.e., the returned value is the list [0,-2]
    If there is overlap between the two matches m1 and m2, the in_port in their intersection is set to -1, ie, we don't consider in_port in comparing match spaces of rules in different rule tables (or flow tables).
    '''

    if (m1[1:] == m2[1:]): #ignore in_port
        tmp=list(m1)
        tmp[0] = -1 #set in_port to -1, ie any value. We don't consider in_port in interflowtable comparison of match
        return [1,tuple(tmp)] # "equal"
    l = [[],[-1,m1[1]]] #list
    #res = [-1,-3] #result
    res = None #result
    for i in range(0,9):# since matchmap is a tuple of 9 elements
        #if (len(l[1]) == 1):
        #    l[1].append(m1[1]) # add ip_proto 
        if (i ==0 or i == 1): # in_port or eth_type, ignore
            continue
        if (i == 2):# ip_proto
            res = compare_ipproto(m1[i],m2[i])
            if (res == [0,-2]):
                return [0,-2]
            l[0].append(res[0])
            l[1].append(res[1])
            continue
        if (i in [3,4]):# ip
            res = compare_ip(m1[i],m2[i])
            if (res == [0,-2]):
                return [0,-2]
            l[0].append(res[0])
            l[1].append(res[1])
            continue
        res = compare_xy(m1[i],m2[i])
        if (res == [0,-2]):
            return [0,-2]
        l[0].append(res[0])
        l[1].append(res[1])
    #print("compare_match l[i] = %s"%l)
    # now, m1 and m2 are not disjoint, determine if the relationship is equal, supersetof, subsetof or overlap
    fin = l[0][0] #final result
    for i in l[0][1:]:
        fin = multiply_relationship(fin,i)
        if (fin == 4):
            return [4,tuple(l[1])]
    return [fin,tuple(l[1])]

def compare_match_hc(m, t):  #hc: hidden conflicts
    '''
    This function determines the intersection between m - the matchmap of a rule with t - the interested traffic of a control application specified for hidden conflict detection. While each field of m is according to OpenFlow 1.3 a single field, e.g., the field for TCP source port cannot be both 80, 81, 82, but can only be a single value as one of those, or unspecified (wildcard), the field of t can be complex in that it can cover multiple values for a field. In fact, we implement each field of t as a python list.
                             (   0        1          2         3         4        5        6        7        8   )
    m = matchmap           = (in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst)
    t = interested traffic = [in_port, eth_type, ip_proto, ipv4_src, ipv4_dst, tcp_src, tcp_dst, udp_src, udp_dst]
                         1   (   2        2048      6         .1.2       -1       1234      -1     -1      -1   )
                         2   [ [1,2,3]    2048     [0]   [1.1, 1.2] [1.3,1.4] [1234,1235]  [-1]   [-1]   [80,5001] ]


    return: intersection between m and t. We just need to determine if m and t overlap each other, or if they are disjoint. If they are not disjoint, we need to show their intersection in the form of matchmap so that we can show the influenced traffic, we don't need to tell if one is equal, subset, superset of the other or if they are intersecting.
    + 0 (disjoint)
    + 1 (overlap (can be subsetof or supersetof or intersecting))

    The second value of the output is the intersection between m and t, which has the same form as t, ie, a list of lists. If they are disjoint, the second value is -2, i.e., the returned value is the list [0,-2]
    '''
    l = [[],2048,[],[],[],[],[],[],[]] #list
    res = None #result
    for i in range(0,9):# since matchmap is a tuple of 9 elements
        if (i == 1): # eth_type, ignore
            continue
        if (i in [3,4]):# ip_src, ip_dst
            res = compare_ip_hc(m[i],t[i])
            if (res == [0,-2]):
                return [0,-2]
            l[i] = res
            continue

        if (i == 2):# ip_proto
            res = compare_xy_hc(m[i],t[i],0)
        else: # i in [0,5,6,7,8] in_port, tcp_src/dst, udp_src/dst
            res = compare_xy_hc(m[i],t[i],-1)
        if (res == [0,-2]):
            return [0,-2]
        l[i] = res
    #print("compare_match hc, l = %s"%l)
    return l

def compare_ip_hc(ip, ipl): #ip and ip list. compare ip for hidden conflict.
    '''
    the ipaddress library support the function: subnet_of and supernet_of from python 3.7. It is safe to implement this function so that earlier python version can also compare the ip addresses. Here, we are using python 3.5
    ip and ipl is/contains ipv4/ipv6 addresses or ipv4/ipv6 range, e.g., 192.168.1.1 (the same as 192.168.1.1/32) or 192.168.1.0/24. The input string without the network mask indicates the network mask of /32. 
    output: [intersection of ip and ipl] or [0,-2] if they are disjoint. There can be the case where ip is broader than ipl or these two actually intersect each other, eg. ip = 192.168.1.4/30, ipl = ['192.168.1.5','192.168.1.6','192.168.1.9'], in this case, ip contains 4 ip addresses from 192.168.1.4-> 192.168.1.7, and the intersection is ['192.168.1.5','192.168.1.6'].
    Note that, a wildcard (*) for IP address/network is denoted as -1 in the match implementation. Otherwise, it is a valid IP address/network
    '''
    if (ip == -1):
        return ipl
    if (ipl[0] == -1):
        return [ip]
    # Now, both ip and ipl[0] are not -1
    ipm = ipaddress.ip_network(ip) #ipm: ip from Matchmap m
    res = [] #result
    for i in ipl:
        ipt = ipaddress.ip_network(i) #ipt: ip from interested Traffic t of a control app
        if (not ipm.overlaps(ipt)):
            continue
        try:
            l=list(ipm.address_exclude(ipt))
            if (len(l) == 0): #ipm == ipt
                #res.append[ip]
                return [ip]
            else:
                res.append(i) # ipm is superset of ipt
        except ValueError:
            return [ip] # ipm is subset of ipt
    if (len(res)==0):
        return [0,-2]
    else:
        return res

def compare_xy_hc(x,y,w):#x: a single number in the matchmap of a rule, y: a list representing interested traffic of a control app, w: wildcard value, for ip_proto, w=0, for other fields eg. tcp_src, in_port, w=-1
    # return a list, being [intersection of x, y], or [0,-2] if x and y are disjoint 
    if (x == w):
        return y
    if (y[0] == w): #x != w
        return [x]
    if (x in y):
        return [x]
    return [0,-2]
    
def multiply_relationship(x,y):
    '''
    x, y values are in:
    + 0 (disjoint)
    + 1 (equal)
    + 2 (subsetof)
    + 3 (supersetof)
    + 4 (overlap (not subsetof and not supersetof and intersection is not empty))

    Multiplying rule:
    + X . X = X
    + disjoint . X = disjoint ( 0 . X = 0 )
    + X . equal = X ( X . 1 = X )
    + subsetof . supersetof = overlap (2 . 3 = 4)
    + if X != disjoint then X . overlap = overlap (X . 4 = 4, if X != 0 )

    output: multiplying value of x . y
    '''
    if (x == y): # X . X = X
        return x
    if (0 in [x,y]): # 0 . X = 0, does not happen here since we exclude it in the input when calling this function
        return 0
    if (1 in [x,y]): # X . 1 = X
        if (x != 1):
            return x
        else:
            return y
    if (2 in [x,y] or 3 in [x,y] or 4 in [x,y]): # (x,y) == (2,3) or (3,2) since we exclude in the above cases: x==y, 0 or 1 not in [x,y], 
        return 4


def compare_xy(x,y):
    '''
    input x, y: -1 or a certain natural number, -1 denote a wildcard value (*)
    output: disjoint, equal, subsetof, supersetof in the first value of the array, second value is the intersection between x and y, if they are disjoint, second value is -2.
    '''
    if (x == y):
        return [1,x] # "equal"
    if ( -1 not in [x,y] and x != y ):
        return [0,-2] # "disjoint"
    if (x==-1):
        return [3,y] # "supersetof"
    if (y==-1):
        return [2,x] # "subsetof"

def compare_ipproto(x,y):
    '''
    input x, y: 0 or a certain natural number, 0 denote a wildcard value (*)
    output: disjoint, equal, subsetof, supersetof and the intersection (second value) in an array, if the first value is disjoint, the second value is -1, i.e., the return array = [0,-2]
    '''
    if (x == y):
        return [1,x] # "equal"
    if ( 0 not in [x,y] and x != y ):
        return [0,-2] # "disjoint"
    if (x==0):
        return [3,y] # "supersetof"
    if (y==0):
        return [2,x] # "subsetof"

def compare_ip(ip_1, ip_2):
    '''
    the ipaddress library support the function: subnet_of and supernet_of from python 3.7. It is safe to implement this function so that earlier python version can also compare the ip addresses. Here, we are using python 3.5
    ip1 and ip2 are ipv4/ipv6 addresses or ipv4/ipv6 range, e.g., 192.168.1.1 (the same as 192.168.1.1/32) or 192.168.1.0/24. The input string without the network mask indicates the network mask of /32. 

    output: relationship of ip1 to ip2: disjoint, equal, subsetof or supersetof, overlap (overlap means not subsetof and not supersetof but their intersection is not empty. Actually, for two any given ip addresses, there are never the overlap relationship between them. The output also contains the intersection of the two ip addresses in the second value of the array. If ip_1 and ip_2 are disjoint, the second value is -2.
    Note that, a wildcard (*) for IP address/network is denoted as -1 in the match implementation. Otherwise, it is a valid IP address/network
    '''
    if (ip_1 == ip_2):
        return [1,ip_1] #"equal"
    if (ip_1 == -1 and ip_2 != -1):
        return [3,ip_2] #"supersetof"
    if (ip_1 != -1 and ip_2 == -1):
        return [2,ip_1] #"subsetof"
    # Now, both ip_1 and ip_2 are not -1
    ip1 = ipaddress.ip_network(ip_1)
    ip2 = ipaddress.ip_network(ip_2)
    if (not ip1.overlaps(ip2)):
        return [0,-2] #"disjoint"
    try:
        l=list(ip1.address_exclude(ip2))
        if (len(l) == 0):
            return [1,ip_1] #"equal"
        else:
            return [3,ip_2] #"supersetof"
    except ValueError:
        return [2,ip_1] #"subsetof"



def mac_format(self, mac_string):
    return ':'.join('%02x' % ord(b) for b in mac_string)

def int2ip(self, addr):
    return socket.inet_ntoa(struct.pack("!I", addr))

def count_rules(rt):#rule tables
    c = 0 # count = sum of all numbers of rules in each switch (dpid)
    cr = {} # count rule
    for dpid in rt:
        cr[dpid] = len(rt[dpid][0])
    for dpid in cr:
        c += cr[dpid]
    return [c,cr]

def count_local_conflicts(lc,opt):
    #lc = local conflict database from the detector, ie. self.lc_cft_rules
    #opt = option, one can ask to show the number of conflicts based on dpid or based on classes.
    #opt = "dpid" or "class"
    if opt not in ["dpid","class"]:
        opt = "dpid"
    clc = {} #count local conflict
    for dpid in lc:
        clc[dpid] = {}
        for r,lt in lc[dpid][0].items(): #r = rule, lt = list of tuples
            for t in lt: #t = tuple
                #print(t)
                if t[2] in [(1,2,1),(1,1,1)]:
                    clc[dpid].setdefault('sha1',0)  #sha1 = shadowing1, see conflict_pattern.spec
                    clc[dpid]['sha1'] += 1
                elif t[2] in [(2,1,1),(2,3,1)]:
                    clc[dpid].setdefault('sha2',0)  #sha2 = shadowing2
                    clc[dpid]['sha2'] += 1
                elif t[2] == (1,3,1):
                    clc[dpid].setdefault('gen1',0)  #gen1 = generalization1
                    clc[dpid]['gen1'] += 1
                elif t[2] == (2,2,1):
                    clc[dpid].setdefault('gen2',0)  #gen2 = generalization2
                    clc[dpid]['gen2'] += 1
                elif t[2] in [(1,2,0),(1,1,0),(0,2,0),(0,1,0),(0,3,0),(2,1,0),(2,3,0)]:
                    clc[dpid].setdefault('red',0)  #red = redundancy
                    clc[dpid]['red'] += 1
                elif t[2] == (1,4,1):
                    clc[dpid].setdefault('cor1',0)  #cor1 = correlation1
                    clc[dpid]['cor1'] += 1
                elif t[2] == (2,4,1):
                    clc[dpid].setdefault('cor2',0)  #cor2 = correlation2
                    clc[dpid]['cor2'] += 1
                elif t[2] in [(0,2,1),(0,3,1),(0,4,1)]:
                    clc[dpid].setdefault('cor3',0)  #cor3 = correlation3
                    clc[dpid]['cor3'] += 1
                elif t[2] == (0,1,1):
                    clc[dpid].setdefault('cor4',0)  #cor4 = correlation4
                    clc[dpid]['cor4'] += 1
                elif t[2] in [(1,3,0),(2,2,0),(1,4,0),(0,4,0),(2,4,0)]:
                    clc[dpid].setdefault('ove',0)  #ove = overlap
                    clc[dpid]['ove'] += 1
    c = 0 #count
    for dpid, cldic in clc.items(): #class dictionary
        for cls in cldic: #cls = class
            c += clc[dpid][cls]
    if opt == "dpid": 
        return [c,clc]

    clc2 = {} #count local conflicts 2, based on class.
    for dpid,cldic in clc.items(): #cldic = class dictionary
        for cls in cldic: #cls = class
            clc2.setdefault(cls,0)
            clc2[cls] += clc[dpid][cls]
    return [c,clc2]

def count_distributed_conflicts(dt):
    counts = {}
    for k,v in dt.items():
        counts[k] = len(v)
    return counts

def count_hidden_conflicts(hc):
    apps= {}
    for app, rs in hc[1].items(): #rs: rule set
        apps[app] = len(rs)
    return apps


