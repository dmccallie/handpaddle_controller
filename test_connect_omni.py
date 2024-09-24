import time
from alpaca.telescope import *      # Multiple Classes including Enumerations
from alpaca.exceptions import *     # Or just the exceptions you want to catch
from alpaca import discovery
from alpaca import management


svrs = discovery.search_ipv4(timeout=1)  # Note there is an IPv6 function as well
print(svrs)
for svr in svrs: # svr = ip address
    print(f"At {svr}")
    print (f"  V{management.apiversions(svr)} server")
    print (f"  {management.description(svr)['ServerName']}") # type: ignore # server name
    devs = management.configureddevices(svr)
    for dev in devs:
        print(f"    {dev['DeviceType']}[{dev['DeviceNumber']}]: {dev['DeviceName']}")

T = Telescope('localhost:32323', 0) # Local Omni Simulator
try:
    T.Connected = True
    print(f'Connected to {T.Name}')
    print(T.Description)
    T.Tracking = True               # Needed for slewing (see below)
    print('Starting slew...')
    T.SlewToCoordinatesAsync(T.SiderealTime + 2, 50)    # 2 hrs east of meridian
    while(T.Slewing):
        time.sleep(5)               # What do a few seconds matter?
    print('... slew completed successfully.')
    print(f'RA={T.RightAscension} DE={T.Declination}')
    print('Turning off tracking then attempting to slew...')
    T.Tracking = False
    T.SlewToCoordinatesAsync(T.SiderealTime + 2, 55)    # 5 deg slew N
    # This will fail for tracking being off
    print("... you won't get here!")
except Exception as e:              # Should catch specific InvalidOperationException
    print(f'Slew failed: {str(e)}')
finally:                            # Assure that you disconnect
    print("Disconnecting...")
    T.Connected = False