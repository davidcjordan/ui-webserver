# gunicorn.conf.py
# the default_proc_name doesn't appear to work
proc_name = "boomerwebserver"
default_proc_name = "boomerwebserver"
bind = "0.0.0.0:1111"
workers = 1
worker_class = "eventlet"
backlog = 2
# log config done in a different file.

# Whether to send Django output to the error log 
capture_output = True

# removed SECRET_KEY = ''    since gunicorn doesn't appear to need it.

disable_redirect_access_to_syslog = True
# print_config = True