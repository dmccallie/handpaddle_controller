import threading
from typing import Any
# from flask_caching import Cache
from pathlib import Path

class CacheTelescope:
    motion = 'Stopped'
    def __init__(self, app):
        # Instantiate the cache which holds our fake telescope data
        cache = Cache()
        # cache.init_app(app=app, config={"CACHE_TYPE": "filesystem",'CACHE_DIR': Path('/tmp')})
        cache.init_app(app=app, config={"CACHE_TYPE": "simple"})
        self.cache = cache
        
        self.ra = 0.0 # hours
        self.dec = 0.0 # degrees
        self.altitude = 0.0 # degrees
        self.azimuth = 0.0

        self.motion= 'Stopped'
        self.cache.set('motion', self.motion)
        self.direction = ''
        self.cache.set('direction', self.direction)
    
        self.update_coords() # start fake update_coords function
        return None

    def stop(self):
        self.motion = 'Stopped'
        self.cache.set('motion', self.motion)
        self.cache.set('direction', '')
        print("Telescope stopped with cache motion: ", self.cache.get('motion'))
        return None
    
    def moveAxis(self, direction):
        self.motion = 'Slewing...'
        self.direction = direction
        self.cache.set('motion', self.motion)
        self.cache.set('direction', self.direction)
        print("Telescope slewing with cache motion, direction: ", self.cache.get('motion'), self.cache.get('direction'))

    def get_coords(self):
        return self.cache.get('coords')
    
    def is_slewing(self):
        return self.cache.get('motion')
    
    def update_coords(self):
        import random
        coords = {
            'altitude': random.randint(0, 90),
            'azimuth': random.randint(0, 360),
            'ra': round(random.uniform(0.0, 23.9), 2),
            'dec': round(random.uniform(-90.0, 90.0), 2),
        }
        self.cache.set('coords', coords)
        # call this function again in 0.2 seconds
        threading.Timer(0.2, self.update_coords).start()

        return None
    
from alpaca.telescope import Rate, Telescope, DriveRates, TelescopeAxes 
from alpaca.exceptions import *     # Or just the exceptions you want to catch
    

class AlpycaTelescope:
    def __init__(self, app, server_ip:str):

        # connect to the ASCOM telescope
        self.server_ip = server_ip
        self.T = Telescope(server_ip, 0) 
        
        try:
            self.T.Connected = True
            print("Connected to telescope with description: ", self.T.Description)
            # print('Starting slew to 2 hours east of meridian')
            print("Current Sideral Time: ", self.T.SiderealTime)
            self.T.Tracking = True
            # new_ra = self.T.SiderealTime + 2
            # if new_ra > 24.0:
            #     new_ra = new_ra - 24.0

            # get supported actions dumped to terminal
            actions = self.T.SupportedActions
            print("----------- Telescope's supported actions: ------------------")
            for action in actions:
                print(action)
            print("------------------ End of supported actions ------------------")
            # self.T.SlewToCoordinatesAsync( new_ra, 50)    # 2 hrs east of meridian

        except Exception as e:
            print(f"Error connecting to telescope: {e}")
            raise e
    
    def _send_command(self, command: str):
        try:
            resp = self.T.CommandString(command, True)
            return resp
        except Exception as e:
            print(f"Error sending telescope command: {e}")
            raise e

    def get_coords(self) -> dict:
        try:
            coords = {
                'altitude': self.T.Altitude,
                'azimuth': self.T.Azimuth,
                'ra': self.T.RightAscension,
                'dec': self.T.Declination,
            }
            return coords
        except Exception as e:
            print(f"Error getting telescope coordinates: {e}")
            raise e

    def is_slewing(self):
        try:
            return self.T.Slewing
        except Exception as e:
            print(f"Error checking if telescope is slewing: {e}")
            raise

    def is_tracking(self):
        try:
            return self.T.Tracking
        except Exception as e:
            print(f"Error checking if telescope is tracking: {e}")
            raise e
        
    def set_tracking(self, tracking: bool):
        try:
            self.T.Tracking = tracking
        except Exception as e:
            print(f"Error setting telescope tracking: {e}")
            raise e
        
    def get_tracking_rate(self):
        try:
            tr = self.T.TrackingRate
            return DriveRates(tr)
        except Exception as e:
            print(f"Error getting telescope tracking rate: {e}")
            raise e
    
    def get_tracking_rates(self) -> list[DriveRates]:
        try:
            # should return list list of enum DriveRates
            # but over the wire, it loses the enum type (becomes int)
            # so map it back to DriveRates here
            trs = self.T.TrackingRates
            named_rates = []
            for tr in trs:
                named_rates.append(DriveRates(tr))
            return named_rates
        except Exception as e:
            print(f"Error getting telescope tracking rates: {e}")
            raise e
        
    def set_tracking_rate(self, rate: DriveRates):
        # expect rate to be an enum DriveRates
        try:
            self.T.TrackingRate = rate
        except Exception as e:
            print(f"Error setting telescope tracking rate: {e}")
            raise e

    def get_MoveAxis_rates(self, axis:TelescopeAxes= TelescopeAxes.axisPrimary) -> list[ dict[str, Any] ]:
        # compromise to support Maestro's non-ASCOM features
        # this driver does the ASCOM, subclass will add Maestro features
        rate_choices = []
        try:
            # first get the ASCOM rates. These are list of [min, max] in degrees per second
            # list of Rate objects, which in COM are IRate objects which have Maximun and Minimum properties
            # in alpaca, it's minv and maxv ???

            ar = self.T.AxisRates(axis)
            # for now, return the min and max for each returned value.
            # in long run, need to sample for 2x, 4x, 16x, etc.
            choice_count = 0
            for r in ar:
                # the min for this rate range
                rate_choice = {}
                rate_choice['number'] = choice_count # used to select "view velocity" for Maestro
                rate_choice['name'] = 'Rate ' + str(choice_count)
                rate_choice['rate'] = r.minv # degrees per second
                rate_choices.append(rate_choice)
                choice_count += 1
                # the max for this rate range
                rate_choice = {}
                rate_choice['number'] = choice_count
                rate_choice['name'] = 'Rate ' + str(choice_count)
                rate_choice['rate'] = r.maxv # degrees per second
                choice_count += 1
                rate_choices.append(rate_choice)
            return rate_choices
        
        except Exception as e:
            print(f"Error getting telescope axis rates: {e}")
            raise e
    
    def set_moveaxis_rate(self, rate_item: dict[str, Any]):
        # for ascom and alpaca scopes this doesnt do anything
        # for Maestro, it will set the view velocity
        pass


    # rate is in degrees per second, extracted from the rate_choices list
    # rate will have been validated against the T.AxisRates list for this telescope
    # this doesn't work for Maestro, so subclass will override it
    def moveAxis(self, direction, rate_item: dict[str, Any]):

        # for ascom, rate_item is a dict with keys 'number', 'name', 'rate'
        # extract the selected rate (degrees per second)
        rate = float(rate_item['rate'])
        print("entering AlpycaTelescope.moveAxis with direction and rate = ", direction, rate)
        try:
            # rate = 1 # * 16 * DriveRates.driveSidereal # degrees per second
            if direction == 'Up':
                # dec is postive up to NCP at 90, negative down to SCP at -90
                self.T.MoveAxis(TelescopeAxes.axisSecondary, rate)
                # self.T.CommandString('Arbitrary Maestro command for UP here', True)
            elif direction == 'Down':
                self.T.MoveAxis(TelescopeAxes.axisSecondary, -rate)
            
            elif direction == 'Left':
                self.T.MoveAxis(TelescopeAxes.axisPrimary, -rate) #RA
            elif direction == 'Right':
                self.T.MoveAxis(TelescopeAxes.axisPrimary, rate)
        except Exception as e:
            print(f"Error moving telescope axis: {e}")
            raise e
        
    def stop(self, direction:str):
        # for Maestro, direction is used, not for Alpaca/ASCOM
        try:
            # if self.T.Slewing:
            #     self.T.AbortSlew()
            #     # very confusing, may need ddx between stop slew and stop MoveAxis?
            self.T.MoveAxis(TelescopeAxes.axisPrimary, 0)
            self.T.MoveAxis(TelescopeAxes.axisSecondary, 0)
        except Exception as e:
            print(f"Error stopping telescope: {e}")
            raise e
        
    def command_string(self, command: str):
        try:
            resp = self._send_command(command)
            # resp = self.T.CommandString(command, True)
            print(f"Command String with {command} returned: {resp}")
            return resp
        except Exception as e:
            print(f"Error sending telescope command: {e}")
            raise e
        
# subclass of AlpycaTelescope but based on COM objects!
import win32com.client

class AlpacaCOMTelescope(AlpycaTelescope):
    # using COM to connect, not really "alpaca" but subclassed from AlpycaTelescope
    def __init__(self, app, server_ip:str):
        # super().__init__(app, server_ip)
        try:
            print("ready to connect to telescope with address: ", server_ip)
            import pythoncom
            pythoncom.CoInitialize()
            self.T = win32com.client.Dispatch(server_ip)
            print("telescope object = ", self.T)

            self.T.Connected = True
            print("Connected to telescope with description: ", self.T.Description)
            # print('Starting slew to 2 hours east of meridian')
            print("Current Sideral Time: ", self.T.SiderealTime)
            self.T.Tracking = True
            # new_ra = self.T.SiderealTime + 2
            # if new_ra > 24.0:
            #     new_ra = new_ra - 24.0

            # get supported actions dumped to terminal
            # actions = self.T.SupportedActions
            # print("----------- Telescope's supported actions: ------------------")
            # for action in actions:
            #     print(action)
            # print("------------------ End of supported actions ------------------")
            # self.T.SlewToCoordinatesAsync( new_ra, 50)    # 2 hrs east of meridian

        except Exception as e:
            print(f"Error connecting to telescope: {e}")
            raise e
        
    def get_MoveAxis_rates(self, axis:TelescopeAxes= TelescopeAxes.axisPrimary) -> list[ dict[str, Any] ]:
            # COM version, using different def of Rate
            rate_choices = []
            try:
                # first get the ASCOM rates. These are list of [min, max] in degrees per second
                # list of Rate objects, which in COM are IRate objects which have Maximun and Minimum properties
                # in alpaca, it's minv and maxv ???

                ar = self.T.AxisRates(axis)
                # for now, return the min and max for each returned value.
                # in long run, need to sample for 2x, 4x, 16x, etc.
                choice_count = 0
                for r in ar:
                    # the min for this rate range
                    rate_choice = {}
                    rate_choice['number'] = choice_count # used to select "view velocity" for Maestro
                    rate_choice['name'] = 'Rate ' + str(choice_count)
                    # rate_choice['rate'] = r.minv # degrees per second
                    rate_choice['rate'] = r.Minimum # degrees per second
                    rate_choices.append(rate_choice)
                    choice_count += 1
                    # the max for this rate range
                    rate_choice = {}
                    rate_choice['number'] = choice_count
                    rate_choice['name'] = 'Rate ' + str(choice_count)
                    # rate_choice['rate'] = r.maxv # degrees per second
                    rate_choice['rate'] = r.Maximum # degrees per second
                    choice_count += 1
                    rate_choices.append(rate_choice)
                return rate_choices
            
            except Exception as e:
                print(f"Error getting telescope axis rates: {e}")
                raise e
            
    def moveAxis(self, direction, rate_item: dict[str, Any]):

        # for ascom, rate_item is a dict with keys 'number', 'name', 'rate'
        # extract the selected rate (degrees per second)
        # can't use the TelescopeAxed enum, so use the number to select the axis
        rate = float(rate_item['rate'])
        rate = int(rate)
        print("entering AlpycaCOMTelescope.moveAxis with direction and rate = ", direction, rate)
        print("current RA = ", self.T.RightAscension)
        print("current DEC = ", self.T.Declination)
        print("current tracking rate = ", self.T.TrackingRate)
        print("tracking status = ", self.T.Tracking)
        mars = self.get_MoveAxis_rates(TelescopeAxes.axisPrimary)
        print("move axis rate options = ", mars)

        # import pythoncom
        # pythoncom.CoInitialize()
        # newT = win32com.client.Dispatch('ASCOM.Simulator.Telescope')
        # print("new telescope object = ", newT)
        # print("original telescope object = ", self.T)

        
        # newRA = newT.RightAscension + 1
        # newDEC = newT.Declination + 5
        # if newRA > 24:
        #     newRA -= 24
        # if newDEC > 90:
        #     newDEC -= 180
        # if newDEC < -90:
        #     newDEC += 180
        # print("NEW T is about to slewing to new RA, DEC: ", newRA, newDEC)
        # newT.SlewToCoordinatesAsync(newRA, newDEC)
        # print("returned from NEW T slew command")

        try:
            # rate = 1 # * 16 * DriveRates.driveSidereal # degrees per second
            if direction == 'Up':
                # dec is postive up to NCP at 90, negative down to SCP at -90
                self.T.MoveAxis(1, rate)
                # self.T.CommandString('Arbitrary Maestro command for UP here', True)
            elif direction == 'Down':
                self.T.MoveAxis(1, -rate)
            
            elif direction == 'Left':
                self.T.MoveAxis(0, -rate) #RA
            elif direction == 'Right':
                self.T.MoveAxis(0, rate)
        except Exception as e:
            print(f"Error moving telescope axis: {e}")
            raise e
        
    def stop(self, direction:str):
        try:
            # if self.T.Slewing:
            #     self.T.AbortSlew()
            #     # very confusing, may need ddx between stop slew and stop MoveAxis?
            self.T.MoveAxis(0, 0)
            self.T.MoveAxis(1, 0)
        except Exception as e:
            print(f"Error stopping telescope: {e}")
            raise e

# subclass to handle Maestro specific features
# this subclass assumes connection via COM
class MaestroCOMTelescope(AlpacaCOMTelescope):
    # def __init__(self, app, server_ip:str):
    #     super().__init__(app, server_ip)
    #     self.T = Telescope(server_ip, 0) # ASCOM class handles most things
    #     return None

    # Maestro doesn't support MoveAxis, so override it using CommandString
    # rate will be a number that determines which "view velocity" to use
    # 1 = view velocity 1, 2 = view velocity 2, etc.
    # 5 = use the "slew" velocity
    # all rates will be at 100% of the velocity

    def get_MoveAxis_rates(self, axis:TelescopeAxes= TelescopeAxes.axisPrimary) -> list[ dict[str, Any] ]:
        # compromise to support Maestro's non-ASCOM features
        # use view velocities instead of ASCOMs get AxisRates'
        # when should the get called to refresh?
        
        rate_choices = []
        # create four fake rate choices, matching the four view velocities bur feth
        #   current rate from Maestro
        for i in range(0, 4): #0,1,2,3,
            rate_choice = {}
            rate_choice['number'] = i
            rate_choice['name'] = 'View Velocity ' + str(i+1)
            cmd = f"KGv{i+1}"
            resp = self._send_command(cmd)
            rate_choice['rate'] = i+1 # I think this is a string with units
            rate_choices.append(rate_choice)
        
        # add a fifth rate choice for "slew" velocity
        rate_choice = {}
        rate_choice['number'] = 4
        rate_choice['name'] = 'Slew Velocity'
        cmd = "KGcv" # get current view velocity
        resp = self._send_command(cmd)
        rate_choice['rate'] = 5 # I think this is a string with units
        rate_choices.append(rate_choice)

        return rate_choices        

    def set_moveaxis_rate(self, rate_item: dict[str, Any]):
        # for Maestro, this sets the View Velocity, which will effect subsequent MoveAxis commands
        # we also use this to go in and out of slew mode
        # number tells us which view velocity to use, 0 to 3 for view velocities 1 to 4, 4 for slew velocity
        view_velocity_number = int(rate_item['number'])

        # set the view velocity - maybe this should be a separate paddle control??
        # vvnumber is 0 to 3 for view velocities 1 to 4, 4 for slew velocity
        if view_velocity_number < 0 or view_velocity_number > 4:
            raise ValueError("Invalid view velocity index number")
        if view_velocity_number == 4:
            cmd = "KSsl" # put in slew mode
            resp = self._send_command(cmd)
            print(f"Setting view velocity to Slew mode with command {cmd} returned  {resp}")
        else:
            # set to Maestro's view velocity 1-4
            cmd = f"KScv{view_velocity_number+1}"
            resp = self._send_command(cmd)
            # and then make sure its not in slew mode
            cmd = "KCsl" # take out of slew mode
            resp = self._send_command(cmd)
            print(f"set VV and took out of slew mode with command {cmd} returned: {resp}")
            

    def moveAxis(self, direction, rate_item: dict[str, Any]): # rate is in degrees per second
        # for maestro we don't use rate_item - see set_moveaxis_rate
        print("entering MaestroCOMTelescope.moveAxis")

        try:
            if direction == 'Up':
                # dec is postive up to NCP at 90, negative down to SCP at -90
                # self.T.MoveAxis(TelescopeAxes.axisSecondary, rate)
                cmd = "KSpu100"
                # resp = self.T.CommandString(cmd, True)
                resp = self._send_command(cmd)
                print(f"Start moving axis UP with command {cmd} returned: {resp}")
            
            elif direction == 'Down':
                # uses whatever view velocity was set to but always at 100%
                cmd = "KSpd100"
                #resp = self.T.CommandString(cmd, True)
                resp = self._send_command(cmd)
                print(f"Start moving axis DOWN with command {cmd} returned: {resp}")
                #self.T.MoveAxis(TelescopeAxes.axisSecondary, -rate)
                # self.T.CommandString('Arbitrary Maestro command for DOWN here', True)
            
            elif direction == 'Left':
                cmd = "KSpl100"
                # resp = self.T.CommandString(cmd, True)
                resp = self._send_command(cmd)
                print(f"Start moving axis LEFT with command {cmd} returned: {resp}")

                #self.T.MoveAxis(TelescopeAxes.axisPrimary, -rate) #RA
                # self.T.CommandString('Arbitrary Maestro command for LEFT here', True)
            elif direction == 'Right':
                cmd = "KSpr100"
                # resp = self.T.CommandString(cmd, True)
                resp = self._send_command(cmd)
                print(f"Start moving axis RIGHT with command {cmd} returned: {resp}")
                # self.T.MoveAxis(TelescopeAxes.axisPrimary, rate)
                # self.T.CommandString('Arbitrary Maestro command for RIGHT here', True)
        except Exception as e:
            print(f"Error moving telescope axis: {e}")
            raise e
        

    def stop(self, direction:str):
        try:
            if direction == 'Left' or direction == 'Right':
                cmd = "XXlr"
                resp = self._send_command(cmd)
                # resp = self.T.CommandString(cmd, True)
                print(f"Stopping LeftRight motion with command {cmd} direction:{direction} returned: {resp}")
            
            elif direction == 'Up' or direction == 'Down':
                cmd = "XXud"
                resp = self._send_command(cmd)
                # resp = self.T.CommandString(cmd, True)
                print(f"Stopping UpDown motion with command {cmd} direction:{direction} returned: {resp}")
            
            else:
                print(f"Unknown direction to stop: {direction} - stopping all motion")
                cmd = "XXam" # stop all automatic motion (GoTo slews etc)
                resp = self._send_command(cmd)
                print(f"Stopping all automatic motion with command {cmd} returned: {resp}")
        
        except Exception as e:
            print(f"Error stopping telescope: {e}")
            raise e
        
    def _send_command(self, cmd:str):
        # our Maestro only takes one command
        resp = self.T.CommandString(cmd)
        return resp

def get_servers(alpaca=True, com=True): # use alpaca.discovery to get available ALPACA servers
    # added support for "com" servers, hand-enumerated for now

    from alpaca import discovery
    from alpaca import management

    servers = []
    try:
        if alpaca:
            print("Searching for ASCOM servers...")
            svrs = discovery.search_ipv4(timeout=1)
            print("found ALPACA servers:",  svrs)
            for svr in svrs:
            # tuple of ip address [0] and server name [1], server_type [2]
                servers.append( (svr, management.description(svr)['ServerName'], "alpaca" )) # type: ignore
        if com:
            servers.append(('ASCOM.Simulator.Telescope', 'ASCOM Telescope Simulator', "com"))
            servers.append(('Maestro.Telescope', 'Maestro via COM', "maestro-com"))
            # servers.append(('ASCOM.Simulator.Telescope', 'Maestro via COM', "maestro-com"))

        return servers

    except Exception as e:
        print(f"Error getting ALPACA and COM servers: {e}")
        return []
