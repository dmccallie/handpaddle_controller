from pathlib import Path
import sys
from flask import Flask, render_template, jsonify, request, redirect, url_for
import random
import time
from telescope import CacheTelescope, AlpycaTelescope, get_servers
from alpaca.telescope import DriveRates, TelescopeAxes

app = Flask(__name__)
shared_servers_cache = {} # global dictionary to hold server and telescope data


# initial page puts up note about searching for servers, starts HTMX GET
#  for server_search
@app.route('/')
def index():
    # assuming we have pre-fetched the server list, show the pick list to user
    print("Index page called with shared_servers_cache: ", shared_servers_cache)
    if 'shared_server_list' in shared_servers_cache:
        servers = shared_servers_cache['shared_server_list']
        print("Servers found: ", servers)
        if len(servers) > 0:
            servers_found = True
            # make first choice in combo box a "Select a server" choice - better way to do this?????
            servers_for_combo = [{'index': 0, 'name': 'Select a server'}]
            for i, server in enumerate(servers):
                new_server = {}
                servers_for_combo.append(new_server)
                new_server['index'] = i+1
                new_server['name'] = f"{servers[i][0]} - {servers[i][1]}" 
        else:
            servers_found = False
    else:
        servers_found = False
        servers_for_combo = []

    return render_template('index.html', servers_found=servers_found,
                           servers_for_combo=servers_for_combo)

# # sever_search is called by HTMX GET to get the list of servers
# # populates combo and swaps into the index page
# # don't need this with pre-fetching server list
# @app.route('/server_search', methods=['GET'])
# def server_search():
    
#     if 'servers' in shared_servers_cache:
#         servers = shared_servers_cache['shared_server_list']
#         print("Cached Servers found: ", servers)
#     else:
#         print("Server search started")
#         shared_servers_cache['shared_servers'] = get_servers()
#         servers = shared_servers_cache['shared_server_list']
#         print("Server search returns: ", servers)

#     servers_found = len(servers) > 0

#     servers_for_combo = [{'index': 0, 'name': 'Select a server'}]
#     for i, server in enumerate(servers):
#         new_server = {}
#         servers_for_combo.append(new_server)
#         new_server['index'] = i+1
#         new_server['name'] = f"{servers[i][0]} - {servers[i][1]}" 



#     return render_template('select_server.html',  servers_found=servers_found,
#                            servers_for_combo=servers_for_combo)
  
# server_select is called when a server is selected from the combo box using POST
# then redirects to the paddle control page
@app.route('/server_select', methods=['POST'])
def server_select():
    print("Server selected with form = ", request.form)
    selected_option = request.form.get('servers-combo-box')
    print(f"Selected server option: {selected_option}")
    if selected_option == '0':
        return redirect(url_for('index'))
    else:
        selected_server = shared_servers_cache['shared_server_list'][int(selected_option)-1]
        print(f"Selected server: {selected_server}")
        # create telescope object and cache it
        try:
            telescope = AlpycaTelescope(app, selected_server[0]) # selected_server[0] is the IP address
            shared_servers_cache['telescope'] = telescope
        except Exception as e:
            print(f"Error connecting to telescope at {selected_server} error= {e}")
            return render_template('error.html', message="Error connecting to telescope")
        
    return redirect(url_for('paddle'))

# page to display paddle controls and telescope status
@app.route('/paddle')
def paddle():

    # should be connected to a telescope by now
    telescope: AlpycaTelescope = shared_servers_cache['telescope']

    # get the tracking rates supported by the telescope
    tracking_rates:list[DriveRates] = telescope.get_tracking_rates()
    for tr in tracking_rates:
        print(f"Tracking rate: {tr.name} = {tr.value}")

    # get whether tracking is turned on
    tracking = telescope.is_tracking()

    # get current tracking rate
    current_tracking_rate = telescope.get_tracking_rate()

    # get the moveaxis rates supported by the telescope
    # just check RA, assume same for DEC
    # if None, then MoveAxis is not supported
    moveaxis_rates = telescope.get_MoveAxis_rates(axis=TelescopeAxes.axisPrimary)
    # rates are in degrees per second!
    for mar in moveaxis_rates:
        print(f"MoveAxis rate: mar name = {mar['name']} rate = {mar['rate']}")

    return render_template('paddle.html', coords={'altitude': 0, 'azimuth': 0, 
            'ra': 0, 'dec': 0, 'slewing': False, 'tracking': False, 
            'tracking_rate': 0}, tracking_rates=tracking_rates, 
                current_tracking_rate=current_tracking_rate,
                moveaxis_rates=moveaxis_rates, tracking=tracking)

# control is called when a control button is pressed
@app.route('/control', methods=['POST'])
def control():
    # get the telescope object from the cache
    telescope: AlpycaTelescope = shared_servers_cache['telescope']

    direction = request.form.get('direction')
    event_type = request.form.get('event_type')
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # get the current MoveAxis rate (is a float)
    moveaxis_rate = shared_servers_cache['moveaxis_rate']
    if moveaxis_rate is None:
        moveaxis_rate = 1.0


    print(f"{direction}-{event_type} at {current_time}")
    
    if direction == 'STOP':
        telescope.stop()
    
    # all moveaxis commands use the same "end" event
    elif event_type == "end":
        telescope.stop()
    
    elif event_type == "start":
        if direction == "UP":
            telescope.moveAxis('Up', moveaxis_rate)
        elif direction == "DOWN":
            telescope.moveAxis('Down', moveaxis_rate)
        elif direction == "LEFT":
            telescope.moveAxis('Left', moveaxis_rate)
        elif direction == "RIGHT":
            telescope.moveAxis('Right', moveaxis_rate)

    return '', 204  # Empty response, HTMX does not require content.

@app.route('/update_tracking', methods=['POST'])
def update_tracking():
    # get the telescope object from the cache
    telescope: AlpycaTelescope = shared_servers_cache['telescope']

    if telescope is not None:
        rate = request.form.get('tracking-rate')
        if rate:
            rate = int(rate)
        else:
            rate = 0
        print(f"Setting tracking rate to {rate}")
        tracking_on_off = request.form.get('tracking-enable')
        print("set tracking on/off to: ", tracking_on_off)
        if tracking_on_off == '1':
            telescope.set_tracking(True)
        else:
            telescope.set_tracking(False)
        telescope.set_tracking_rate(DriveRates(rate))
    return '', 204

# called when changing the MoveAxis rate
# need to cache this since we don't have a way to get the current MA rate from telescope
@app.route('/update_moveaxis_rate', methods=['POST'])
def update_moveaxis_rate():
    new_rate = request.form.get('moveaxis_rate')
    if new_rate:
        new_rate = float(new_rate)
    else:
        new_rate = 1.0
    print(f"Setting MoveAxis rate to {new_rate}")
    shared_servers_cache['moveaxis_rate'] = new_rate
    return '', 204


@app.route('/status', methods=['GET'])
def status():
    
    # get the telescope object from the cache
    telescope: AlpycaTelescope = shared_servers_cache['telescope']

    if telescope is None:
        coords = {'altitude': 0, 'azimuth': 0, 'ra': 0, 'dec': 0}
        coords['slewing'] = False
        coords['tracking'] = False
        coords['tracking_rate'] = 0
    else:
        coords = telescope.get_coords()
        coords['slewing'] = telescope.is_slewing()
        coords['tracking'] = telescope.is_tracking()
        coords['tracking_rate'] = telescope.get_tracking_rate()
    
    return render_template('telescope_coords.html', coords=coords)

if __name__ == '__main__':

    # create shared telescope object
    # will be shared across users, since there is only one telescope
    # try:
    #     # telescope = CacheTelescope(app)
    #     telescope = AlpycaTelescope(app)
    
    # except RuntimeError as e:
    #     print("Initializing telescope failed: ", e)
    #     sys.exit(1)

    # create a shared global object to hold the server location data (discovery data)
    # this object will be shared across users as well, since they are all on the same LAN
    # do that when app starts up, since it is a one-time operation
    try:
        servers = get_servers()
        # if this were a multi-server app, we'd need to use Redis or some other shared cache
        shared_servers_cache['shared_server_list'] = servers  # cache in memory, will be shared across users

        shared_servers_cache['telescope'] = None # can't create telescope until user has selected a server
        shared_servers_cache['moveaxis_rate'] = 1.0 # default rate for MoveAxis

    except Exception as e:
        print(f"Error getting servers: {e}")
        sys.exit(1)

    app.run(debug=True, port=5001)
