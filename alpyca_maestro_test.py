from alpaca.telescope import Telescope, DriveRates

T = Telescope('192.168.1.140:11111', 0) # connect to Maestro via Ascom Remote
T.Connected = True
print(f"Telescope object:{T.Description} has connected status:{ T.Connected}")
print(f"Driver Info = {T.DriverInfo}")

# this works
print(f"Current RA and Dec = {T.RightAscension}, {T.Declination}")

# this works
T.TrackingRate = DriveRates.driveLunar
print(f"Tracking rate is now {T.TrackingRate}")

# this fails
try:
    reply = T.CommandString("CGra", Raw=True) # should return current RA
    print(f"Successful reply from CGra CommandString = {reply}")
except Exception as e:
    print(f"Error from CGra CommandString = {e}")

#this fails
try:
    reply = T.CommandString("XXam", Raw=True) # should cancel all automatic motion (slews)
    print(f"Successful reply from XXam CommandString = {reply}")
except Exception as e:
    print(f"Error from XXam CommandString = {e}")

T.Connected = False
