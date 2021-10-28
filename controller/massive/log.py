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


import datetime
import enum
import os

class LogLevel(enum.Enum):

    Info = "INFO"
    Warn = "WARNING"
    Err = "ERROR"
    Crit = "CRITICAL"
    Debug = "DEBUG"
    # Quiet can be used to set a default log_level per parent class
    # and easily suppress any prints to stdout if they are not relevant
    Quiet = "QUIET"


class Log:

    def __init__(self, params):

        js_config = params
        # this should be a path to local directory and a base file name
        self.log_fn = os.path.abspath(js_config['logger_file'])

    def write(self, caller, log_level, message):
        """The write method adds a timestamp to a given
        message and writes it to a log file that was specified
        on initialisation. Depending on the LogLevel text is
        colored. If LogLevel is Debug the message is written
        to stdout.
        """

        context = type(caller).__name__
        timestamp = datetime.datetime.now()
        log_str = "{}"
        log_str = log_str.format(message)

        if log_level == LogLevel.Quiet:
          # do not log anything to stout or file
          return
        elif log_level == LogLevel.Debug:
            print(log_str)  # print to stdout for development/testing and /dev/null else
        else:
            #print(log_str)  # print to stdout for development/testing and /dev/null else
            with open(self.log_fn, "a") as f:
              f.write(log_str)  # write to log file if LogLevel is not Debug or Quiet
