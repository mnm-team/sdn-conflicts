# Copyright (C) 2021 Nicholas Reyes - nicholasreyes@hotmail.de
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
__author__ = 'Nicholas Reyes'
__email__ = 'nicholasreyes@hotmail.de'
__licence__ = 'GPL2.0'

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
