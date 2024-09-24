import threading
from flask_caching import Cache
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
    
from alpaca.telescope import *      # Multiple Classes including Enumerations
from alpaca.exceptions import *     # Or just the exceptions you want to catch
    

class AlpycaTelescope:
    def __init__(self, app):

        # connect to the ASCOM telescope
        self.T = Telescope('172.28.240.1:32323', 0) # Local Omni Simulator
        
        try:
            self.T.Connected = True
            print("Connected to telescope with description: ", self.T.Description)
            print('Starting slew to 2 hours east of meridian')
            self.T.Tracking = True
            self.T.SlewToCoordinatesAsync(self.T.SiderealTime + 2, 50)    # 2 hrs east of meridian

        except Exception as e:
            print(f"Error connecting to telescope: {e}")
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
        
    def get_tracking_rate(self):
        try:
            tr : DriveRates = self.T.TrackingRate
            return tr
        except Exception as e:
            print(f"Error getting telescope tracking rate: {e}")
            raise e
    
    def get_tracking_rates(self) -> list[DriveRates]:
        try:
            # should return list list of enum DriveRates
            # but over the wire, it loses the enum type
            # so map it here
            trs = self.T.TrackingRates
            named_rates = []
            for tr in trs:
                named_rates.append(DriveRates(tr))
            return named_rates
        except Exception as e:
            print(f"Error getting telescope tracking rates: {e}")
            raise e
        
    def set_tracking_rate(self, rate: DriveRates):
        try:
            self.T.TrackingRate = rate
        except Exception as e:
            print(f"Error setting telescope tracking rate: {e}")
            raise e

    def moveAxis(self, direction):
        try:
            rate = 1 # * 16 * DriveRates.driveSidereal # degrees per second
            if direction == 'Up':
                # dec is postive up to NCP at 90, negative down to SCP at -90
                self.T.MoveAxis(TelescopeAxes.axisSecondary, rate)
                self.T.CommandString('Arbitrary Maestro command for UP here', True)
            elif direction == 'Down':
                self.T.MoveAxis(TelescopeAxes.axisSecondary, -rate)
            
            elif direction == 'Left':
                self.T.MoveAxis(TelescopeAxes.axisPrimary, -rate) #RA
            elif direction == 'Right':
                self.T.MoveAxis(TelescopeAxes.axisPrimary, rate)
        except Exception as e:
            print(f"Error moving telescope axis: {e}")
            raise e
        
    def stop(self):
        try:
            if self.T.Slewing:
                self.T.AbortSlew()
                # very confusing, may need ddx between stop slew and stop MoveAxis?
                self.T.MoveAxis(TelescopeAxes.axisPrimary, 0)
        
        except Exception as e:
            print(f"Error stopping telescope: {e}")
            raise e
        
def get_servers(): # use alpaca.discovery to get available ALPACA servers
    from alpaca import discovery
    from alpaca import management
    servers = []
    try:
        print("Searching for servers...")
        svrs = discovery.search_ipv4(timeout=1)
        print("found servers:",  svrs)
        for svr in svrs:
            # return tuple of ip address and server name
            servers.append( (svr, management.description(svr)['ServerName']) ) # type: ignore

    except Exception as e:
        print(f"Error getting servers: {e}")
        return []

    return servers
