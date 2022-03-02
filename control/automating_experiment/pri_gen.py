#!/usr/bin/python

__author__ = 'Cuong Tran'
__email__  = 'cuongtran@mnm-team.org'
__licence__ = 'GPL2.0'

import sys
import itertools as it
"""
    First argument is the number of applications.
    Second argument is the smallest priority that an app can have, e.g., if $1=3 and we have 2 apps, the priority combination will be:
    3 3
    3 4
    4 3

    You can input the second argument, to be used as the base (smalles) priority an app can have, default value is 2.
    
    To run this program:
        python <this program name> <number of apps>
    or:
        python <this program name> <number of apps> <base priority>
    To have a nicer output, pipe the output of this program to the sort function of linux, e.g.,:
        python pri_gen.py 3 | sort
"""
#create base string:
try:
    na=int(sys.argv[1]) #number of apps
except (IndexError):
    print("Please input the number of applications in the first argument.")
    sys.exit(1) 
except (ValueError):
    print("The number of applications in the first argument must be a number.")
    sys.exit(2)

try:
    base=int(sys.argv[2]) #base priority (smallest priority)
except (IndexError):
    #print("You can input the second argument, to be used as the base (smalles) priority an app can have, default value is 2.")
    base=2
except (ValueError):
    #print("The base priority of applications must be a number, use default vaule of 2")
    base=2

bs = [] #base string
for i in range(na):
    bs.append('')

for i in range(na):
    j = 0
    for tmp in range(base,base+na):
        if j>i:
            break
        bs[i] += str(tmp)
        j += 1
#print bs

combi = []
for i in range(na):
    combi.append([])
#print combi

i = 0
for s in bs: #s = string
    combi[i] = it.combinations_with_replacement(bs[i],na)
    i += 1

t=1

cl=[] # combination list
for i in range(na):
    for e in combi[i]:
        s=set(e)
        if (len(s) == t):
            cl.append(e)
    t += 1

es = set() #end set
for i in cl:
    pl = it.permutations(i)
    for j in pl:
        es.add(j)

for i in es:
    for j in i:
        print j,
    print
