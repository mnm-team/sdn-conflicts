# version 2.1 -  20210815
# Adds distributed conflict patterns with own pattern criteria and their explanation
# version 2.0 - 20201207
# Encode patterns directly by number tuple, e.g., (2,1,1)
# in table 5.10 of Dissertation: rule i: incoming or newer rule, rule j: existing or older rule

class Shadowing1 (local conflicts):
# forward, new rule (latter) is shadowed by existing (former) rule, conflict effect is logged for new rule
    pattern:
        (1,2,1) (1,1,1)
    effect:
        the latter (newer) rule becomes ineffective

class Shadowing2 (local conflicts):
# backward, existing rule (former) is shadowed by new rule (latter), conflict effect is logged for existing rule
    pattern:
        (2,1,1) (2,3,1)
    effect:
        the former (older) rule becomes ineffective

class Generalization1 (local conflicts):
# forward
    pattern:
        (1,3,1)
    effect:
        a part of the latter (newer) rule becomes ineffective

class Generalization2 (local conflicts):
# backward
    pattern:
        (2,2,1)
    effect:
        a part of the former (older) rule becomes ineffective
        
class Redundancy (local conflicts):
    pattern:
        (1,2,0) (1,1,0) (0,2,0) (0,1,0) (0,3,0) (2,1,0) (2,3,0) 
    effect:
        If there is no hidden conflicts from this pattern, it is harmless

class Correlation1 (local conflicts):
# forward
    pattern:
        (1,4,1)
    effect:
        a part of the latter (newer) rule becomes ineffective

class Correlation2 (local conflicts):
# backward
    pattern:
        (2,4,1)
    effect:
        a part of the former (older) rule becomes ineffective

class Correlation3 (local conflicts):
    pattern:
        (0,2,1) (0,3,1) (0,4,1) 
    effect:
        critical! not sure which rule will get effective and which becomes ineffective

class Correlation4 (local conflicts):
    pattern:
        (0,1,1)
    effect:
        the latter (newer) rule overrides an existing one

class Overlap (local conflicts):
    pattern:
        (1,3,0) (2,2,0) (1,4,0) (0,4,0) (2,4,0)
    effect:
	harmless


# distributed conflict properties

class IncompleteTransformation(distributed conflicts):
  pattern:
    (1,4,0,0,-1) (2,4,0,0,-1) (3,4,0,0,-1) (4,4,0,0,-1)
  effect:
    might lead to missing packet transformation

class Bypass(distributed conflicts):
  pattern:
    (1,4,0,1,-1) (2,4,0,1,-1) (3,4,0,1,-1) (4,4,0,1,-1)
  effect: 
   app might not deploy policy

class MultiTransform(distributed conflicts):
  pattern:
    (1,3,0,-1,-1) (2,3,0,-1,-1) (3,3,0,-1,-1) (4,3,0,-1,-1)
  effect:
    multiple packet transformations

class Spuriousness(distributed conflicts):
  pattern:
    (1,1,0,-1,-1) (2,1,0,-1,-1) (3,1,0,-1,-1) (4,1,0,-1,-1)
  effect:
    unwanted packets/bandwidth within the network

class Injection(distributed conflicts):
  pattern:
    (1,2,0,-1,-1) (2,2,0,-1,-1) (3,2,0,-1,-1) (4,2,0,-1,-1)
  effect:
    unintended packet transformation

class Loop(distributed conflicts):
  pattern:
    (1,0,1,-1,-1)
  effect:
    trapped packets that dont reach destination

class Occlusion(distributed conflicts):
  pattern:
    (1,5,0,-1) (2,5,0,-1) (3,5,0,-1) (4,5,0,-1)
  effect:
    trapped packets that dont reach their destination

class InvariantContention(distributed conflicts):
  pattern:
    (1,-1,0,1) (2,-1,0,1) (3,-1,0,1) (4,-1,0,1)
  effect:
    two applications interested and affecting the same or a subset oof one anothers invariants

#===end===#

Explanation of distributed conflict patterns:

Distributed patterns consist of criteria (match,actionCorrelation,location,appCoverage,appIntent).
The individual criteria except for appIntent are determined by comparing two (connected) rules in a rule path.
The two compared rules do not have to be directly connected.

The conflict types Occlusion, Dispersion and Focusing are exceptions.
For Occlusion there will not be any connections between the conflicting rules.
For dispersion and focusing the conflict is based on app intent, the rules will no exert the conflict.
Also, apps can have the same intent and it could indicate a conflict, but it might be a wanted effect.

match
# see below
# determined by comparing output matchmap of rule i with matchmap of rule j
# otherwise same as for local conflicts

actionCorrelation
-1: dontcare
0: action i == output and action j == output # no obvious problem
1: action i == output and action j = drop # spuriousness
2: action i == output and action j = transform # can be injection depending on coverage
3: action i == transform and action j == transform # multi-transform
4: action i == any or none (aka wavering edge) and action j = transform # bypass or incomplete transform depending on coverage
5: action i == transform and action j == any # this will lead to occlusion but there is no connection between rule i and j

location
0: target switch i != target switch j
1: target switch i == target switch j

appCoverage
-1: dontcare
0: path exists with target switch but no policy
1: path exists without target switch

appIntent
-1: dontcare
0: intersecting
1: disjunct


match
# see below
# determined by comparing output matchmap of rule i with matchmap of rule j
# otherwise same as for local conflicts

actionCorrelation
0: action i == output and action j == output # no obvious problem
1: action i == output and action j = drop # spuriousness
2: action i == output and action j = transform # can be injection depending on coverage
3: action i == transform and action j == transform # multi-transform
4: action i == any (also no preceding rule aka wavering edge) and action j = transform # bypass or incomplete transform depending on coverage

location
0: target switch i != target switch j
1: target switch i == target switch j

coverage
-1: dontcare
0: path exists with target switch but no policy
1: path exists without target switch


# version 1.0 - 20201130
# Encode patterns in "natural language"

# the description of the conflict database is after the python style, some can be reused directly in the detector code written in python, e.g., in printing out the effect of a conflict class
# Local conflicts
# i und j are rules, e.g., i is the rule to be installed, j is the existing rule in the target switch
class Shadowing (local conflicts):
    pattern:
        priority(i) < priority(j), match(i) subsetof match(j), action(i) != action(j)
        #priority_i <= priority_j, match_i <= match_j, action_i != action_j
    effect:
         rule %s becomes ineffective, i

class Generalization (local conflicts):
    pattern:
        priority(i) > priority(j), match(i) subsetof match(j), action(i) != action(j)
        #priority_i >= priority_j, match_i <= match_j, action_i != action_j
    effect:
        a part of rule %s specialised by rule %s becomes ineffective, j, i

class Redundancy (local conflicts):
    pattern:
        match(i) subsetof match(j), action(i) == action(j)
        or
        match(i) supersetof match(j), action(i) == action(j)
        #match_i <= match_j, action_i == action_j
    effect:
        If there is no hidden conflicts from this pattern, it is harmless

class Correlation1 (local conflicts):
    pattern:
       match(i) overlap match(j), action(i) != action (j)
        #( match(i) not subsetof match(j) ) and ( match(i) not supersetof match(j) ) and ( match(i) overlap match(j) ), action(i) != action (j)
    effect:
        a part of the lower priority rule becomes ineffective
       
class Correlation2 (local conflicts):
    pattern:
        priority(i) == priority(j), match(i) subsetof match(j), action(i) != action(j)
        or
        priority(i) == priority(j), match(i) supersetof match(j), action(i) != action(j)
        #priority(i) == priority(j), ( match(i) subsetof match(j) ) or ( match(i) supersetof match(j) ), action(i) != action(j)
    effect:
        critical! not sure which rule will get effective and which becomes ineffective

class Overlap (local conflicts):
    pattern:
        match(i) overlap match(j), action(i) == action(j)
        # ( match(i) not subsetof match(j) ) and ( match(i) not supersetof match(j) ) and ( match(i) overlap match(j) ), action(i) == action(j)
    effect:
	harmless

#class Overlap2:
#    pattern:
#        priority(i) == priority(j), ( match(i) subsetof match(j) ) or ( match(i) supersetof match(j) ), action(i) != action(j)
#    effect:
#	harmless

# Distributed conflicts:
        

    






#===end===#
All lines after the above line are just comments

Each conflict class is separated with other classes by an empty line. There must be no empty line in each conflict class description.
# Keywords:
class
pattern
comment begins with a #
#function
priority(i) : get the priority of rule i
match
action

Operator: >  <  =  !=  ==, subsetof, propersubsetof, supersetof, propersupersetof, overlap, or, and, not ()
subsetof and supersetof include the equal relationship, i.e., a set is also a subset or a superset of itself.
#should we include the propersubsetof and propersupersetof?
overlap means not subsetof, not supersetof but the intersection between two sets is not empty.



# () is for grouping
#note that subset and superset include the equal == relationship between two sets
There is no empty lines within each conflict class description, i.e., between class, pattern, effect. Otherwise, the parsing of this file does not work correctly.


#====end===# marks the end of all conflict patterns 

In our implementation, we represent all the relationship in numbers to accelerate the pattern comparison (comparing in number is quicker than comparing in string in python language, we believe)
The relationship between two matches (sets) are represented by numbers from 0 to 4:
+ 0 : (disjoint)
+ 1 : (equal)
+ 2 : (propersubsetof)
+ 3 : (propersupersetof)
+ 4 : (overlap (not subsetof and not supersetof and intersection is not empty))
The subsetof relationship is reflected by 1,3
The supersetof relationship is reflected by 1,2

The relationship between two priority values:
+ -1 : donot care
+ 0 : priority(i) == priority(j)
+ 1 : priority(i) < priority(j)
+ 2 : priority(i) > priority(j)

The relationship between two action values:
+ 0 : action(i) == action(j)
+ 1 : action(i) != action(j)



The redundancy local conflict has the following patterns: ("class Redundancy (local conflicts)", [(0, 1, 0), (0, 2, 0), (1, 1, 0), (1, 2, 0), (2, 1, 0), (2,2, 0), (0, 1, 0), (0, 3, 0), (1, 1, 0), (1, 3, 0), (2, 1, 0), (2, 3, 0)], 'If there is no hidden conflicts from this pattern, it is harmless'), among those, the patterns (0,1,0) and (1,1,0) are ignored while considering conflicts although the rule exposing these patterns with the existing rules in the rule database (self.ft) are still installed in the data plane. These rules, however, are not updated in the rule database (self.ft). The effect of the rule installation may be: update the timer of the rule (for the pattern (0,1,0)), or a backup rule with longer life time if the rule of higher priority but same match, action (pattern (1,1,0)) expires and gets removed.

Patterns:
('class Shadowing (local conflicts)', [(1, 1, 1), (1, 2, 1)], 'rule %s becomes ineffective, i')
('class Generalization (local conflicts)', [(2, 1, 1), (2, 2, 1)], 'a part of rule %s specialised by rule %s becomes ineffective, j, i')
('class Redundancy (local conflicts)', [(0, 1, 0), (0, 2, 0), (1, 1, 0), (1, 2, 0), (2, 1, 0), (2, 2, 0), (0, 3, 0), (1, 3, 0), (2, 3, 0)], 'If there is no hidden conflicts from this pattern, it is harmless')
('class Correlation1 (local conflicts)', [(0, 4, 1), (1, 4, 1), (2, 4, 1)], 'a part of the lower priority rule becomes ineffective')
('class Correlation2 (local conflicts)', [(0, 1, 1), (0, 2, 1), (0, 3, 1)], 'critical! not sure which rule will get effective and which becomes ineffective')
('class Overlap (local conflicts)', [(0, 4, 0), (1, 4, 0), (2, 4, 0)], 'harmless')


The above patterns, however, do not cover the case of incoming (new) rules shadow the existing rules in the flow tables, i.e., the pattern: (2, 3, 1). So, imagine the case in which there is no conflicts in the flow table, then a new rule to be installed has higher priority, covering match and different action than an existing rule in that flow table, that means, there needs to be another pattern, so-called reverse shadowing. We can possibly define the reverse/negation function: not(1,2,1) = (2,3,1).

From table 5.10 in dissertation, we have 24 patterns:
				correct		incorrect
1.  (1,2,1) shadowing		x
2.  (1,2,0) redundancy		x
3.  (1,1,1) shadowing		x
4.  (1,1,0) redundancy		x
5.  (1,3,1) generalization xxx
6.  (1,3,0) overlap		x
7.  (1,4,1) correlation		x
8.  (1,4,0) overlap		x

9.  (0,2,1) correlation		x
10. (0,2,0) redundancy		x
11. (0,1,1) correlation		x
12. (0,1,0) redundancy		x
13  (0,3,1) correlation		x
14. (0,3,0) redundancy		x
15. (0,4,1) correlation		x
16. (0,4,0) overlap		x

17. (2,2,1) generalization	x
18. (2,2,0) overlap		x
19. (2,1,1) shadowing				x (generalization)
20. (2,1,0) redundancy		x
21  (2,3,1) shadowing	xxx
22. (2,3,0) redundancy		x
23. (2,4,1) correlation		x
24. (2,4,0) overlap		x

So, we should:
+ use the encoded patterns above for local conflicts directly as the input for the detector.
+ specify in table 5.10 additionally a column: new rule (j), existing rule (i) and the effect on the existing rule. This needs to be considered in detecting local conflicts, as upon the presence of the incoming rule, the existing rules appears to have no problem. The incoming rule of the pattern 21 (2,3,1) has no problem but the rule shadowed by the new rule becomes ineffective.
