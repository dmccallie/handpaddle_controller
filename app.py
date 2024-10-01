from pathlib import Path
import logging
import sys
from flask import Flask, render_template, jsonify, request, redirect, url_for, g
import random
import time
from telescope import CacheTelescope, AlpycaTelescope, get_servers, MaestroTelescope
from alpaca.telescope import DriveRates, TelescopeAxes

app = Flask(__name__)

# @app.before_request
# def before_request():
#     g.suppress_logging = False
#     if request.path == '/status':  # suppress this one
#         print("Suppressing logging for /status")
#         g.suppress_logging = True

# @app.after_request
# def after_request(response):
#     if g.suppress_logging:
#         g.suppress_logging = False
#     return response

# doesnt work
class SuppressLoggingFilter(logging.Filter):
    def filter(self, record):
        # # Suppress logging if the flag is set
        # print("checking filter with suppress_logging = ", g.suppress_logging)
        # if g.suppress_logging == True:
        #     print("Filtering record ready to return true ", record)
        #    return True
        # print("filtering path = ", request.path)
        if g and g.suppress_logging:
            print("Filtering record = ", record)
            return True
        print("NOT Filtering record = ", record)
        return False   
    
    
# stop logging each request
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)
# werkzeug_logger.addFilter(SuppressLoggingFilter())

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

# page to display all the paddle controls and telescope status
@app.route('/paddle')
def paddle():

    # should be connected to a telescope by now
    telescope: AlpycaTelescope = shared_servers_cache['telescope']

    # get the tracking rates supported by the telescope
    tracking_rates:list[ DriveRates ] = telescope.get_tracking_rates()
    for tr in tracking_rates:
        print(f"Found tracking rate: {tr.name} = {tr.value}")

    # get whether tracking is turned on
    tracking = telescope.is_tracking()

    # get current tracking rate
    current_tracking_rate = telescope.get_tracking_rate()

    # get the moveaxis rates supported by the telescope
    # just check RA, assume same for DEC
    # if None, then MoveAxis is not supported
    
    # rates are dict with number, name and rate
    # for ascom, will be like "number: 2, name: "16x", rate: nnnn.nnnn"
    # for maestro, will be like "number: 2, name: View Velocity 2", rate: xxxx.xxxx"
    # rates will be in degrees per second??

    moveaxis_rates = telescope.get_MoveAxis_rates(axis=TelescopeAxes.axisPrimary)
    for mar in moveaxis_rates:
        print(f"Found MoveAxis rate: mar number = {mar['number']} name = {mar['name']} rate = {mar['rate']}")

    # these need to be cached in shared memory for use when control is called
    shared_servers_cache['moveaxis_rates'] = moveaxis_rates

    # set the default move axis rate item to number 1
    initial_rate_number = 1
    shared_servers_cache['moveaxis_rate_item'] = moveaxis_rates[initial_rate_number]

    return render_template('paddle.html', coords={'altitude': 0, 'azimuth': 0, 
            'ra': 0, 'dec': 0, 'slewing': False, 'tracking': False, 
            'tracking_rate': 0}, tracking_rates=tracking_rates, 
                current_tracking_rate=current_tracking_rate,
                moveaxis_rates=moveaxis_rates, selected_rate=initial_rate_number, tracking=tracking)

# control is called when a control button is pressed
# initially was HTMX, but now POST + JSON with direction and event_type
@app.route('/control', methods=['POST'])
def control():
    # get the telescope object from the cache
    telescope: AlpycaTelescope = shared_servers_cache['telescope']

    # get the json and extract the direction and event_type
    json_data = request.get_json()
    button_name = json_data['button_name']  #actually is id which gives direction
    event_type = json_data['event_type']  # start or stop (pointer down or up)

    # direction = request.form.get('direction')
    # event_type = request.form.get('event_type')

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # current slew rate is set via different POST event, so result was cached in shared memory
    # get the current (cached) MoveAxis rate item containing both the number, name, and rate
    # ascom uses rate, but maestro uses view velocity number

    if 'moveaxis_rate_item' in shared_servers_cache:
        rate_item = shared_servers_cache['moveaxis_rate_item']
    else:
        rate_item = {'number': 1, 'name': 'missing rate selection', 'rate': 0.0002777777777777778}
    
    print(f"control got {button_name}-{event_type} at {current_time}")
    
    if button_name == 'stop-btn':
        telescope.stop()
    
    # all moveaxis commands use the same "end" event
    elif event_type == "end":
        telescope.stop()
    
    elif event_type == "start":
        if button_name == "up-btn":
            telescope.moveAxis('Up', rate_item)
        elif button_name == "down-btn":
            telescope.moveAxis('Down', rate_item)
        elif button_name == "left-btn":
            telescope.moveAxis('Left', rate_item)
        elif button_name == "right-btn":
            telescope.moveAxis('Right', rate_item)

    # Return a JSON response indicating success
    response = {
        'status': 'success',
        'message': f'Event {event_type} received for button {button_name}'
    }
    return jsonify(response), 200  # Return 200 OK with the JSON response

    # return '', 204  # Empty response, HTMX does not require content.

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

# called when changing the MoveAxis rate (not same as tracking rate!)
# need to cache the selected "rate_item" since we don't have a way to get the current MA rate from telescope
# rate item has all info needed for moveaxis either for ASCOM or Maestro
# rate item: {'number': 2, 'name': '16x', 'rate': 0.0002777777777777778}
# or for maestro: {'number': 2, 'name': 'View Velocity 2', 'rate': 0.0002777777777777778}
@app.route('/update_moveaxis_rate', methods=['POST'])
def update_moveaxis_rate():
    new_rate_number = request.form.get('moveaxis_rate') # gets the rate number, not index
    if new_rate_number:
        new_rate_number = int(new_rate_number)
    else:
        new_rate_number = 1
    # extract the rate item from the cached rates list
    rate_item = shared_servers_cache['moveaxis_rates'][new_rate_number]

    print(f"Caching new MoveAxis rate item to {rate_item}")
    shared_servers_cache['moveaxis_rate_item'] = rate_item
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

@app.route('/send_command', methods=['POST'])
def send_command():
    command = request.form.get('command')
    print(f"Prepared to send command string: {command}")
    telescope = shared_servers_cache['telescope']
    resp = telescope.command_string(command)
    return f"{resp}", 200

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
        shared_servers_cache['moveaxis_rates'] = None # can't get these until telescope is connected
        shared_servers_cache['moveaxis_rate_item'] = None # 

    except Exception as e:
        print(f"Error getting servers: {e}")
        sys.exit(1)

    app.run(debug=True, port=5001)
