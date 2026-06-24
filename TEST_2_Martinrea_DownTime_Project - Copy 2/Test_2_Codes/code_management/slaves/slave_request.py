# Slave code template
# Variables are configured per instance using metadata.
# This template is reused by all slave files.

import snap7
from snap7.util import *

PLC_IP = '<SLAVE_IP>'
RACK = 0
SLOT = 1

client = snap7.client.Client()
client.connect(PLC_IP, RACK, SLOT)

DB_NUMBER = 1
START = 0
SIZE = 64

data = client.db_read(DB_NUMBER, START, SIZE)

# Update variables by offset:
# Example metadata variable structure:
# [{"name":"sensor_value","offset":0},{"name":"motor_status","offset":4}]

client.disconnect()
