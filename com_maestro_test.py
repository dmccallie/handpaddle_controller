import win32com.client, pythoncom
import platform

print("current python archtecture = ", platform.architecture())

def open_ascom_chooser(device_type="Telescope"):
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = device_type
    progid = chooser.Choose("")

    if progid:
        # device = win32com.client.Dispatch(prog_id)
        return progid
    else:
        return None
    
progid = open_ascom_chooser("Telescope")
if progid:
    T = win32com.client.Dispatch(progid)
    print(f"Selected telescope: {T.Name}")
else:
    print("No telescope selected")
    exit()

# T = win32com.client.Dispatch('Maestro.Telescope')
T.Connected = True
print(f"Telescope object:{T.Description} has connected status:{ T.Connected}")
print(f"Driver Info = {T.DriverInfo}")

print(f"Current RA and Dec = {T.RightAscension}, {T.Declination}")

T.TrackingRate = 1 # DriveRates.driveLunar is 1
print(f"Tracking rate is now {T.TrackingRate}")

try:
    reply = T.CommandString("CGra", Raw=False) # should return current RA
    print(f"Successful reply from CGra CommandString = {reply}")
except Exception as e:
    print(f"Error from CGra CommandString = {e}")

try:
    reply = T.CommandString("XXam", Raw=False) # should cancel all automatic motion (slews)
    print(f"Successful reply from XXam CommandString = {reply}")
except Exception as e:
    print(f"Error from XXam CommandString = {e}")

T.Connected = False
