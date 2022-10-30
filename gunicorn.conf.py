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

SECRET_KEY = '264af6580bf8977d9ad15007e48efcd583ec8083a706532841709ad2249d59f6'

disable_redirect_access_to_syslog = True
# print_config = True