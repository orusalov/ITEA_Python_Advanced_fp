DEBUG = False
PORT = 8000
ENDPOINT = 'tg'
CHECK_TIME_INTERVAL = 3600 #seconds
# TOKEN = ''
# HOST = ''
# CERTIFICATE = ''

try:
    from .local_config import *
except ImportError:
    print('No local config. TOKEN needed')
