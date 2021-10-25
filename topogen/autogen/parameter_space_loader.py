import json
import os
import pyangbind.lib.pybindJSON as pybindJSON
from pyangbind.lib.serialise import pybindJSONDecoder
from sdn_testbed_spec import sdn_testbed_spec
from sdn_testbed_spec_v2 import sdn_testbed_spec_v2

class ParameterSpaceLoader:

  def loadSdnTestbedSpec(self, spec):
    """ Given a path to a YANG model serialized to 
    a json, the structure in the json is loaded into
    a python class hierarchy generated with pyang.
    This method returns the serialized model and the YANG model version,
    (not the YANG version!).
    """
    try:
      model = sdn_testbed_spec_v2()
      ietfJson = json.load(open(os.path.abspath(spec), 'r'))
      pybindJSONDecoder.load_ietf_json(ietfJson, None, None, obj=model)
      return model, 2
    except Exception as e:
      print("Could not load v2 model from json file {}".format(spec))
      print("Trying to parse as legacy v1 model")
      try:
        model = sdn_testbed_spec()
        ietfJson = json.load(open(os.path.abspath(spec), 'r'))
        pybindJSONDecoder.load_ietf_json(ietfJson, None, None, obj=model)
        return model, 1     
      except Exception as e:
        print("Could not load model from json file {}".format(spec))
        print(e)
        raise Exception(e)
    except Exception as e:
      print("Could not load model from json file {}".format(spec))
      print(e)
      raise Exception(e)
