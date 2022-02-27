# sdn-conflicts

We examine conflicts in Software-Defined Networks (SDN) and have obtained the following results.

+ Conflicts are classified into three broad categories: local conflicts, distributed conflicts and hidden conflicts. They are further sub-categorised into 19 conflict classes, each is featured by its unique pattern or property that enables its detection.
+ We opt for the experimental approach in researching conflicts in addition to the formal analytical approach, as the latter one alone exposes the inherent limitations that could not be addressed comprehensively. The number of experiments derived from the parameter space for experiments is huge. Therefore, we create a framework for automating the experiments using virtual machines (KVM, Xen, virtualbox) (see directory *control/automating_experiment*). The results published in the *sdn-results* directory are collected from more than 11.700 individual experiments conducted almost automatically by our framework.
+ We develop a prototype for detecting conflicts in SDN (see Directory *controller/massive*), that can detect local conflicts, traffic drop/loop in general, suspicious packet-modifications, and hidden conflicts of the class *event suppression by local handling*.
+ We implement a set of control applications (see Directory *controller/massive*), e.g., End-point Load Balancer (EpLB), Path Load Balancer (PLB), Firewall (FW), Shortest-Path First Routing/Switching (routing), ARP cache, NDP, Path Enforcer (PE), Host Shadowing (HS), Source-based Passive Path Load Balancer (PPLB4S), Destination-based Passive Path Load Balancer (PPLB4D)...
+ The network topology can be generated automatically based on the specification of hosts, switches and their links in a python file (e.g., see file *topology/autogen/sample_topology.py*). Various network topologies have been used for researching conflicts, including random and designed topologies, one of those is the [MWN network](https://www.lrz.de/services/netz/mwn-ueberblick_en/)
+ We have also examined MEADcast in SDN (see Directory MEADcast_in_SDN. Multicast to Explicit Agnostic Destinations (MEADcast) is a new multicast scheme where most of management tasks are performed by the sender, leaving the recipients untouched, i.e., they don't have to be changed or take part in the management task as in traditional multicast or other multicast schemes.

We use [ryu SDN Framework](https://github.com/faucetsdn/ryu) for the SDN controller, and [Open vSwitch](https://www.openvswitch.org/) for the OpenFlow SDN Devices.

Nicholas Reyes examined distributed conflicts in SDN and extended the framework to a higher level of automation. His thesis is available [here](https://www.nm.ifi.lmu.de/pub/Diplomarbeiten/reye21/).

Minh Nguyen implemented MEADcast in SDN (sender side), more information can be found in his [thesis](https://www.nm.ifi.lmu.de/pub/Fopras/nguy19/).

Rosalie Kletzander deployed a test-bed for researching conflicts in SDN during the worrk on her [thesis](https://www.nm.ifi.lmu.de/pub/Fopras/klet17/).

More publications related to conflicts in SDN, our methodology for this research and results can be found in this [link](https://www.nm.ifi.lmu.de/~cuongtran/). Feel free to contact us for further information.

