from firewall import FirewallMonitor
from ryu.base import app_manager
import utility_rest

class FirewallAPI(utility_rest.UtilityRest13):

  def __init__(self, *args, **kwargs):
    super(FirewallAPI, self).__init__(*args, **kwargs)
    

# also need rest topology
app_manager.require_app('ryu.app.ofctl_rest')

# for conveineance start firewall app from here
# creates its own thread for monitoring
fw = FirewallMonitor()
