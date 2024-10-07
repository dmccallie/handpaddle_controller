# test python access to ASCOM com objects

import time
import win32com.client, pythoncom

T = win32com.client.Dispatch('ASCOM.Simulator.Telescope')  # runs the .net version apparently?
print("object returns t = ", T)
print("object name = ", T.Name)
print("object description = ", T.Description)
print("object connected = ", T.Connected)
print("object can set park = ", T.CanSetPark)
print("object can set find = ", T.CanFindHome)
axis_rates = T.AxisRates(0)
for rate in axis_rates:
    cast_rate = win32com.client.CastTo(rate, 'IRate')
    print("axis rate = ", cast_rate.Minimum, cast_rate.Maximum)


# casted_object = win32com.client.CastTo(axis_rates, 'Rate')


print("connecting....")
T.Connected = True
print("object connected = ", T.Connected)

print("UN parking....")
T.Unpark()
T.Tracking = True
print("object parked = ", T.AtPark)
# slew to 2 hours past current RA
print(("current RA = ", T.RightAscension))
print(("current DEC = ", T.Declination))
print(("current AZ = ", T.Azimuth))
print(("current ALT = ", T.Altitude))

# set tracking rate to solar
try:
    T.Tracking = True
    T.TrackingRate = 5
    print("tracking rate is now ", T.TrackingRate)
except Exception as e:
    print("error setting tracking rate: ", e)
print("tracking rate is now ", T.TrackingRate)

T.SlewToCoordinatesAsync(T.RightAscension + 2, T.Declination + 10)
print("returned from slew command")
for i in range(20):
    print(("current RA = ", T.RightAscension))
    print(("current DEC = ", T.Declination))
    print(("current AZ = ", T.Azimuth))
    print(("current ALT = ", T.Altitude))
    print("---------------------")
    if T.Slewing:
        print("slewing")
        time.sleep(2)
    else:
        break

# try moveaxis
print("moving axis")
T.MoveAxis(0, 1)
time.sleep(2)
print("slewing = ", T.Slewing)
print("stop moving axis")
T.MoveAxis(0, 0)
print("after stop slewing = ", T.Slewing)

T.Tracking = False
print("parking....")
T.Park()


# supported actions
sa = T.SupportedActions
for action in sa:
    print("supported action = ", action)


# print("trying commandstring")
# try:
#     res = T.Action("SlewToRaDec",["p1", "p2"])
#     print("action worked")
# except:
#     print("action failed")

# res = T.Action("SlewToRaDec",["p1", "p2"])

# Release the COM object (force cleanup)
com_object = None  # Removes the Python reference to the object
pythoncom.CoUninitialize()  # Uninitializes COM
print("done")