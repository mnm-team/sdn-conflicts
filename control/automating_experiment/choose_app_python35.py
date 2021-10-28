#python:
#https://docs.python.org/2/library/itertools.html
import sys
import itertools
def powerset(iterable):
  s = list(iterable)
  return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(2,len(s)+1))

num_app = int(sys.argv[1])
#for i in powerset([1,2,3]):
#for i in powerset(range(1,num_app+1)):
#  print i
#tmp = [i for i in powerset(range(1,num_app+1))]
tmp = [i for i in powerset(range(0,num_app))]
for j in tmp:
  #print([' '.join(k) for k in j])
  for k in j:
    print (k,"", end='')
  print()

