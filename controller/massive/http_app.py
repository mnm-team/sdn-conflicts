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

import json
import enum
from http.client import *


class HttpAppError(Exception):
    """ Dummy error class to avoid except
    clauses for to generic errors.
    """
    pass


class HttpAction(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DEL = "DELETE"


class HttpApp:
    """WebApp is a utility class to open a http
    connection on given parameters of a rest server,
    send a request and parse the response from a rest
    server. Any anticipated exceptions are wrapped in
    a string and returned. The response might be 'None'
    for rest endpoints that don't send a response.
    """

    def __init__(self, params):
        self.host = params["rest_server_host"]
        self.port = params["rest_server_port"]

    def conn(self, act, endpoint, data=None):
        
        error_message = ""
        response_body = None
        con = None
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        try:
            con = HTTPConnection(self.host, self.port)

            if act == HttpAction.GET or act == HttpAction.PUT:
                con.request(act.value, endpoint)
            else:
                # POST or DELETE so we need to add headers
                con.request(act.value, endpoint, data, headers)

            response = con.getresponse()
            response_body = response.read().decode('utf-8')  # read response as string
            try:
                response_body = json.loads(response_body)  # try to parse response as json
            except Exception as e:
                print(e)  # this is just a workaround for now

            # status will be 200 or an error occurred
            if response.status != 200:
                error_message = "Status: {} and reason: {} - body is: {}"
                error_message = error_message.format(response.status,
                                                     response.reason,
                                                     json.dumps(response_body, indent=1))

        except NotConnected:
            error_message = "Could not connect to host {} on port {}".format(self.host, self.port)
        except InvalidURL:
            error_message = "Wrong syntax for url: {}:{}".format(self.host, self.port)
        except CannotSendRequest:
            if data:
                error_message = "Could not send following request:\nheaders: {}\naction: {}\ndata: {}\nendpoint: {}"
                error_message = error_message.format(headers, act, data, endpoint)
            else:
                error_message = "Could not send following request:\naction: {}\nendpoint: {}".format(act, endpoint)
        except ResponseNotReady:
            error_message = "Response is not ready for http request!"
        except RemoteDisconnected:
            error_message = "Remote host {} disconnected http connection on port {}!".format(self.host, self.port)
        except ConnectionResetError:
            error_message = "Remote host {} refused the connection on port {}".format(self.host, self.port)

        if error_message:
            raise HttpAppError(error_message)

        con.close()
        return response_body

