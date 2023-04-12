from utils.devices import Dewar

print('Starting script')

try:
    dewar = Dewar('XF:lob5lab9-ES:AMX', name='XF:lob5lab9-ES:AMX')
except:
    print('Exception: {}')

while True:
    pass