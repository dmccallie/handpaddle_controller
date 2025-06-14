# hack to see if we can catch Maestro dropping tracking randomly
import alpaca as alpaca
from alpaca.telescope import Telescope
from alpaca import discovery

# use logging to document the process
import logging

import time
import winsound  # Add this import at the top with your other imports

def send_command(command: str):
    # custom version of CommandString for Maestro, supressing the "raw" parameter
    # NO, send the raw to Ascom Remote, and the suppression occurs there, before forwarding to Maestro
    try:
        # start = time.perf_counter()
        resp = T.CommandString(command, True) 
        # print(f"Command String with {command} returned: {resp} took: {(time.perf_counter()-start)*1000:.4f}mSec")
        return resp
    except Exception as e:
        print(f"Error sending telescope command: {e}")
        raise e

def monitor_tracking(wait_sec = 1.0, random_slews=False):
    # don't start if scope is not tracking
    # assume user will start tracking manually
    while not T.Tracking:
        logging.info("Waiting for telescope to start tracking...")
        time.sleep(5)

    logging.info("Telescope is now tracking. Monitoring Tracking, RA and DEC...")
    prior_ra = T.RightAscension
    prior_dec = T.Declination
    prior_tracking = True
    prior_move_mode = send_command("PGmm")  # Get initial move mode
    logging.info(f"Initial Telescope Move Mode: {prior_move_mode}")

    if random_slews:
        logging.info("Random slews enabled. Will slew to random positions during monitoring.")
    count = 0
    if random_slews:
        import random
        import math

        def random_slew():
            # Slew to a nearby random position no more then 5 degrees away
            # 1 degree = 24 hours / 360 degrees = 4 minutes per degree
            ra = T.RightAscension + (24.0/360.0) * random.uniform(-5, 5)
            dec = T.Declination # + (24.0/360.0) * random.uniform(-5, 5)
            logging.info(f"Random slew to position: RA={ra}, DEC={dec}")
            T.SlewToCoordinatesAsync(ra, dec)
            # wait for the slew to complete
            while T.Slewing:
                time.sleep(1)

    changed_by_random_slew = False  # Flag to track if the change was due to a random slew

    while True:
        if random_slews:
            count += 1
            if count % 60 == 0:
                random_slew()
                changed_by_random_slew = True
        try:
            measure_start = time.perf_counter()
            t = T.Tracking
            ra = T.RightAscension
            dec = T.Declination

            # get move mode
            move_mode = send_command("PGmm")
            # logging.info(f"Move Mode: {move_mode}")
            
            if (t != prior_tracking) or (ra != prior_ra) or (dec != prior_dec) or (move_mode != prior_move_mode):

                seconds = (prior_ra - ra) * 3600 # convert RA difference to seconds
                
                logging.info(f"Telescope status changed: Tracking: {t}, RA: {ra} (delta seconds: {seconds}), DEC: {dec} Move Mode: {move_mode}")
                if not changed_by_random_slew:
                    play_alert(frequency=800, duration=100, repeats=2)  # More urgent alert
                    pass

                prior_tracking = t
                prior_ra = ra
                prior_dec = dec
                prior_move_mode = move_mode
                changed_by_random_slew = False  # Reset the flag after processing
                measure_time = time.perf_counter() - measure_start
                logging.info(f"Tracking check took {measure_time:.4f} seconds")

            time.sleep(wait_sec)  # Check every wait_sec seconds

        except Exception as e:
            logging.error(f"Error during tracking check: {e}")
            time.sleep(5)  # Wait before retrying


def play_alert(frequency=1000, duration=1000, repeats=1):
    """Play an alert sound with optional repetition"""
    try:
        for _ in range(repeats):
            winsound.Beep(frequency, duration)
            time.sleep(0.1)  # Short pause between repeats
    except Exception as e:
        logging.error(f"Error playing sound alert: {e}")


if __name__ == "__main__":
    # Set up discovery to find the Alpaca server

    # log our status changes
    # write to log file and terminal
    logging.basicConfig(filename='monitor_tracking.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    # force log to terminal as well
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting Alpaca Telescope Tracking Monitor...")
    logging.info( "Searching for Alpaca servers...")
    svrs = discovery.search_ipv4(timeout=1)
    logging.info(f"found ALPACA server(s): {svrs}")

    if len(svrs) == 0:
        logging.error("No ALPACA servers found, exiting.")
        exit(1)

    # Use the first server found
    logging.info(f"Using server IP: {svrs[0]}")

    server_ip = svrs[0]

    T = Telescope(server_ip, 0) 

    try:
        T.Connected = True
        logging.info(f"Connected with Alpaca Maestro to telescope with description: {T.Description}")
        logging.info(f"Current Telescope Sideral Time: {T.SiderealTime}")
        logging.info(f"Current Telescope Tracking Status: {T.Tracking}")
    except Exception as e:
        logging.error(f"Error connecting to telescope: {e}")
        raise e

    # Start monitoring tracking
    monitor_tracking(wait_sec=1.0, random_slews=False)
    # Note: random_slews is not used in this version, but can be implemented later if needed