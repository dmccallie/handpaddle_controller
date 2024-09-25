from pathlib import Path
import sys
from flask import Flask, render_template, jsonify, request, redirect, url_for
import random
import time
from telescope import CacheTelescope, AlpycaTelescope, get_servers
from alpaca.telescope import DriveRates, TelescopeAxes

app = Flask(__name__)

# initial page puts up note about searching for servers, starts HTMX GET
#  for server_search
@app.route('/')
def index():
    return render_template('index.html')

# sever_search is called by HTMX GET to get the list of servers
#  populates combo and swaps into the index page
@app.route('/server_search', methods=['GET'])
def server_search():
    print("Server search started")
    servers = get_servers() # use alpaca.discovery to get available servers
    # servers is [ (ip_address, server name ) ]
    print("Servers found: ", servers)
    servers_for_combo = [{'index': 0, 'name': 'Select a server'}]
    for i, server in enumerate(servers):
        new_server = {}
        servers_for_combo.append(new_server)
        new_server['index'] = i+1
        new_server['name'] = f"{servers[i][0]} - {servers[i][1]}" 

    servers_found = len(servers) > 0

    return render_template('select_server.html',  servers_found=servers_found,
                           servers_for_combo=servers_for_combo)
  
    # return render_template('index.html', 
    #             coords={'altitude': 0, 'azimuth': 0, 'ra': 0, 'dec': 0},
    #             servers=servers_for_combo, servers_found=True)

# server_select is called when a server is selected from the combo box using POST
#  then redirects to the paddle control page
@app.route('/server_select', methods=['POST'])
def server_select():
    print("Server selected with form = ", request.form)
    selected_option = request.form.get('servers-combo-box')
    # Handle the selected option here
    print(f"Selected server option: {selected_option}")
    # return '', 204  # Empty response, HTMX does not require content.
    return redirect(url_for('paddle'))

# page to display paddle controls and telescope status
@app.route('/paddle')
def paddle():
    # get the tracking rates supported by the telescope
    tracking_rates:list[DriveRates] = telescope.get_tracking_rates()
    for tr in tracking_rates:
        print(f"Tracking rate: {tr.name} = {tr.value}")

    # get the slewing rates supported by the telescope
    # just check RA, assume same for DEC
    # if None, then MoveAxis is not supported
    slewing_rates = telescope.get_axisrates(axis=TelescopeAxes.axisPrimary)
    # rates are in degrees per second!
    for sr in slewing_rates:
        print(f"Slewing rate: min: {sr.minv} and max: {sr.maxv}")

    return render_template('paddle.html', coords={'altitude': 0, 'azimuth': 0, 
            'ra': 0, 'dec': 0, 'slewing': False, 'tracking': False, 
            'tracking_rate': 0}, tracking_rates=tracking_rates, slewing_rates=slewing_rates)

# control is called when a control button is pressed
@app.route('/control', methods=['POST'])
def control():
    direction = request.form.get('direction')
    event_type = request.form.get('event_type')
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    print(f"{direction}-{event_type} at {current_time}")
    
    if direction == 'STOP':
        telescope.stop()
    
    elif event_type == "end":
        telescope.stop()
    
    elif event_type == "start":
        if direction == "UP":
            telescope.moveAxis('Up')
        elif direction == "DOWN":
            telescope.moveAxis('Down')
        elif direction == "LEFT":
            telescope.moveAxis('Left')
        elif direction == "RIGHT":
            telescope.moveAxis('Right')

    return '', 204  # Empty response, HTMX does not require content.

@app.route('/update_tracking', methods=['POST'])
def update_tracking():
    rate = request.form.get('tracking-rate')
    if rate:
        rate = int(rate)
    else:
        rate = 0
    print(f"Setting tracking rate to {rate}")
    tracking_on_off = request.form.get('tracking-enable')
    print("set tracking on/off to: ", tracking_on_off)
    if tracking_on_off == 'true':
        telescope.set_tracking(True)
    else:
        telescope.set_tracking(False)
    telescope.set_tracking_rate(DriveRates(rate))
    return '', 204

@app.route('/status', methods=['GET'])
def status():
    coords = telescope.get_coords()
    # coords = telescope.cache.get('coords')
    coords['slewing'] = telescope.is_slewing()
    coords['tracking'] = telescope.is_tracking()
    coords['tracking_rate'] = telescope.get_tracking_rate()

    return render_template('telescope_coords.html', coords=coords)

if __name__ == '__main__':

    # create shared telescope object
    try:
        # telescope = CacheTelescope(app)
        telescope = AlpycaTelescope(app)
    
    except RuntimeError as e:
        print("Initializing telescope failed: ", e)
        sys.exit(1)

    print("Telescope found - starting app")

    # discover services

    app.run(debug=True, port=5001)
