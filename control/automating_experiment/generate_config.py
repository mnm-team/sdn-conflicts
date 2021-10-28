#https://docs.python.org/2/library/itertools.html#itertools.product
#https://docs.python.org/3/tutorial/controlflow.html#tut-unpacking-arguments
import sys
import itertools

def product(*args, **kwds):
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

#for i in sys.argv:
#  print i
tmp_list=[]
for i in range(1,len(sys.argv)):
  #print sys.argv[i]
  tmp_list.append(range(1,int(sys.argv[i])+1))
#print("tmp_list = %s"%tmp_list)

tmp = [i for i in product(*tmp_list)]
#print tmp
for j in tmp:
  #print([' '.join(k) for k in j])
  for k in j:
    print k,
  print

