Multicast to Explicit Agnostic Destinations (MEADcast) is a new multicast scheme where most of management tasks are performed by the sender, leaving the recipients untouched, i.e., they don't have to be changed or take part in the management task as in traditional multicast or other multicast schemes. The novelty of MEADcast includes:

+ The recipients are absolutely agnostic of the underlying technology, they just behave as usual.
+ Unlike traditional multicast which requires the overall upgrade of all routers, MEADcast enables gradual deployment of MEADcast-capable routers. The more support the network offers (i.e., more MEADcast-capable routers), the more bandwidth efficient the data delivery is.
+ The scheme supports fallback to unicast when there is no network support.
+ The MEADcast-capable routers don't have to maintain the multicast groups' information in order to perform routing, rendering them stateless and much more simpler compared to traditional multicast router.
+ The sender has the overall control of the data delivery and can regulate this process flexibly.

Initial results based on simulation and analysis prove the efficiency and potential of MEADcast. More details can be seen at the [MEADcast paper (page 13)](https://www.iariajournals.org/security/sec_v12_n12_2019_paged.pdf).

MEADcast in SDN is examined by Minh Nguyen, his thesis is available [here](https://www.mnm-team.org/pub/Fopras/nguy19/).
