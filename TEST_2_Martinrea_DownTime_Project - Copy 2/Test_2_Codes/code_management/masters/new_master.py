import snap7
from snap7.util import *

PLC_IP = '192.168.0.1'
RACK = 0
SLOT = 1

client = snap7.client.Client()
client.connect(PLC_IP, RACK, SLOT)

DB_NUMBER = 1
START = 0
SIZE = 16

result = client.db_read(DB_NUMBER, START, SIZE)

# Example: read a DWORD from DB1.DB0
value = get_dword(result, 0)
print('Read value:', value)

# Write a DWORD back
set_dword(result, 0, 12345)
client.db_write(DB_NUMBER, START, result)

client.disconnect()
