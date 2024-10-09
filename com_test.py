# test python access to ASCOM com objects

import time
import win32com.client, pythoncom
from telescope import AlpacaCOMTelescope

testMT = win32com.client.Dispatch('Maestro.Telescope')
print("testMT returns ", testMT)

comTele = AlpacaCOMTelescope(None, 'ASCOM.Simulator.Telescope') 
T = comTele.T
#T = win32com.client.CastTo(t, 'ITelescopeV4')  # this is the correct way to cast to the interface
print("object returns t = ", T)
print("object name = ", T.Name)
print("object description = ", T.Description)
print("object connected = ", T.Connected)
print("object can set park = ", T.CanSetPark)
print("object can set find = ", T.CanFindHome)

from alpaca.telescope import Rate, Telescope, DriveRates, TelescopeAxes 

axis_rates = T.AxisRates(0) # 0 = primary axis
for rate in axis_rates:
    # this is different in Alapca version?  minv and maxv are used there
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

# get tracking rates

trs = T.TrackingRates
for tr in trs:
    # maps the integer to the enum with name of rate (used by gui)
    trenum  = DriveRates(tr)
    print("tracking rate = ", tr, trenum) # just prints the number, not the name

# use the class to get moveaxis rates
mars = comTele.get_MoveAxis_rates(TelescopeAxes.axisPrimary)
for mar in mars:
    print("move axis rate option = ", mar)

# test move axis
comTele.moveAxis(TelescopeAxes.axisPrimary, mars[1])
time.sleep(1)
comTele.stop()
print("after comtele move axis")

rate = 6
T.MoveAxis(0, rate)
print("after another move axis")

# set tracking rate to solar
try:
    T.Tracking = True
    T.TrackingRate = DriveRates.driveSidereal
    print("tracking rate is now ", T.TrackingRate)
except Exception as e:
    print("error setting tracking rate: ", e)

# set tracking rate to lunar with class
comTele.set_tracking_rate(DriveRates.driveLunar)
print("after call to comTele tracking rate is now ", DriveRates(T.TrackingRate))

print("tracking rate is now ", DriveRates(T.TrackingRate))

newRA = T.RightAscension + 2
newDEC = T.Declination + 10
if newRA > 24:
    newRA -= 24
if newDEC > 90:
    newDEC -= 180
if newDEC < -90:
    newDEC += 180
T.SlewToCoordinatesAsync(newRA, newDEC)
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
# T.MoveAxis(0, 1)
comTele.moveAxis("Up",  mars[1])
time.sleep(0.5)
print("MA triggered slewing = ", T.Slewing, comTele.is_slewing())
print("stop moving axis")
comTele.stop()
# T.MoveAxis(0, 0)
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