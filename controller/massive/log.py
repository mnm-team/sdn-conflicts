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
