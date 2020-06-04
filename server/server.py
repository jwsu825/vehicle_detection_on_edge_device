import datetime
import json
import os
import threading
import time

from controllers import server_security as sec, request_constants
from controllers.device_manager import DeviceManager, InvalidError
from flask import Flask, request, Response, send_file

ALLOWED_EXTENSIONS = set(['jpg', 'jpeg'])
UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = DeviceManager('root', 'password', 'localhost', port=3306)
app.config['SQLALCHEMY_DATABASE_URI'] = db.uri
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db.create_db()
db.connect_to_db()
db.create_tables()
db.db.init_app(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_entries(entries):
    formatted_entries = []
    for entry in entries:
        formatted_entries.append({
            'category': entry[0],
            'time': entry[1].timestamp(),
            'id': entry[2]
        })
    return formatted_entries


@app.route('/api/devices', methods=['GET'])
@sec.admin_auth
def get_devices():
    device_id = request.args.get('id')
    name = request.args.get('name')
    devices = db.get_devices(device_id, name)
    if devices is None:
        return 'Error occurred'
    formatted_devices = []
    for dev in devices:
        formatted_devices.append({
            'id': dev[0],
            'name': dev[1],
            'lat': dev[2],
            'long': dev[3],
            'last-checkin': dev[4]
        })
    return return_formatted_data(200, {'devices': formatted_devices})


@app.route('/api/devices/<device_id>/entries', methods=['GET'])
@sec.admin_auth
def get_device_entries(device_id):
    entries = format_entries(db.get_entries(device_id))
    return return_formatted_data(200, {'entries': entries})


@app.route('/api/devices/<device_id>/entries', methods=['POST'])
@sec.user_auth
def add_entries(device_id):
    entries = request.json
    if not db.device_exists(int(device_id)):
        return Response('Device does not exist', 400)
    db.add_entries(device_id, entries)
    return return_formatted_data(200, {'data': 'Entries were added'})


@app.route('/api/devices/entries', methods=['POST'])
@sec.user_auth
def add_entries_general():
    token = request.headers.get('Authorization')
    just_token = token.split(' ')[1]
    device_id = db.get_device_id(just_token)
    if device_id is not None:
        entries = request.json
        if db.add_entries(device_id, entries):
            return return_formatted_data(200, {'data': 'Entries were added'})
        else:
            return return_error(500, 'Failed to add entries')
    return return_error(400, 'Device does not exist that matches the provided token')


@app.route('/api/devices/entries', methods=['GET'])
@sec.admin_auth
def get_entries_general():
    device_ids = request.args.get('ids')
    categories = request.args.get('cat')
    if device_ids is not None:
        device_ids = [int(i) for i in device_ids.split(',')]
    if categories is not None:
        categories = [i.lower() for i in categories.split(',')]

    min_time = request.args.get('min')
    max_time = request.args.get('max')

    if min_time is not None:
        min_time = datetime.datetime.fromtimestamp(float(min_time))
    if max_time is not None:
        max_time = datetime.datetime.fromtimestamp(float(max_time))

    entries = format_entries(db.search_entries(device_ids,
                                               categories,
                                               min_time,
                                               max_time))

    return return_formatted_data(200, {'entries': entries})


@app.route('/api/devices/add', methods=['POST'])
@sec.admin_auth
def add_device():
    try:
        device_information = request.json
        dev_token = db.add_device(device_information)
        if dev_token is not None:
            return return_formatted_data(200, {'token': dev_token})
        return return_error(400, 'Error in adding device')
    except Exception as e:
        return return_error(500, str(e))


@app.route('/api/devices/<device_id>/delete', methods=['POST'])
@sec.admin_auth
def delete_device(device_id):
    db.delete_device(device_id)
    return return_formatted_data(200, {'data': 'Device was deleted'})


@app.route('/api/devices/<device_id>/preview', methods=['GET'])
# @sec.admin_auth
def get_device_preview(device_id):
    filename = os.path.join(UPLOAD_FOLDER, '%s' % device_id, 'preview.jpg')
    if os.path.exists(filename):
        return send_file(filename, mimetype='image/jpg')
    return return_error(404, 'No preview image')


# login routes
@app.route('/api/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    try:
        token = db.authenticate(username,
                                password)
        return return_formatted_data(200, {'token': token})
    except InvalidError as error:
        return return_error(400, str(error))


@app.route('/api/check-token', methods=['GET'])
@sec.user_auth
def check_token():
    try:
        return return_formatted_data(200, {'success': 'Token is valid'})
    except InvalidError as error:
        return return_error(400, str(error))


@app.route('/api/upload', methods=['POST'])
@sec.user_auth
def upload_picture():
    token = request.headers.get('Authorization')
    just_token = token.split(' ')[1]
    device_id = db.get_device_id(just_token)
    if 'file' in request.files:
        file = request.files['file']
        filename = os.path.join(app.config['UPLOAD_FOLDER'] + '/', '%d/preview.jpg' % device_id)
        if not os.path.exists(os.path.dirname(filename)):
            os.mkdir(os.path.dirname(filename))
        if file:
            file.save(filename)
    return return_formatted_data(200, 'Success')


@app.route('/api/heartbeat', methods=['POST'])
@sec.user_auth
def heart_beat():
    token = request.headers.get('Authorization')
    just_token = token.split(' ')[1]
    device_id = db.get_device_id(just_token)
    try:
        hb_data = request.get_json(force=True)
    except Exception as e:
        return return_error(400, 'Error parsing data %s' % (str(e)))

    if hb_data is None:
        return return_error(400, 'Invalid heartbeat data')

    if 'command' in hb_data:
        db.update_command(device_id, hb_data['command'])

    if db.check_in(device_id, hb_data['time']):
        command, data = db.get_command(device_id)
        if command is not None:
            return return_command(command, data)
        return return_formatted_data(200, '')


@app.route('/api/devices/<device_id>/command', methods=['POST'])
@sec.admin_auth
def add_command(device_id):
    try:
        request_json = request.json
        command = request_json['command']
        if 'data' not in request_json:
            command_data = {}
        else:
            command_data = request_json['data']
        command_id = db.put_command(device_id, command, command_data)

        if command_id is not None:
            return return_formatted_data(200, {'command_id': command_id})
        else:
            return return_error(400, 'Something happened internally')
    except Exception as e:
        return return_formatted_data(400, 'Error: %s' % e)


@app.route('/api/commands/<command_id>', methods=['GET'])
@sec.admin_auth
def get_command(command_id):
    command_info = db.get_command_information(command_id)
    return return_formatted_data(200, command_info)


@app.route('/api/commands/<command_id>', methods=['DELETE'])
@sec.admin_auth
def delete_command(command_id):
    success = db.delete_command(command_id)
    if success:
        return return_formatted_data(200, 'Command Successfully Deleted')
    else:
        return return_error(500, 'Command failed to delete')


def start_cleaner():
    clean_thread = threading.Thread(target=cleanup_thread)
    clean_thread.start()


def cleanup_thread():
    max_age = 3600
    clean_interval = 5
    counter = 0

    while True:
        time.sleep(1)
        counter += 1
        if counter == clean_interval:
            counter = 0
            db.clean_commands(max_age)


def return_error(status_code, error):
    error_json = {'apiVersion': request_constants.API_VERSION,
                  'error': {'message': str(error)}}
    return Response(status=status_code, response=json.dumps(error_json))


def return_formatted_data(status_code, data):
    msg_json = {'apiVersion': request_constants.API_VERSION,
                'data': data}
    return Response(status=status_code, response=json.dumps(msg_json))


def return_command(command, data):
    msg_json = {'apiVersion': request_constants.API_VERSION,
                'command': command,
                'data': data}
    return Response(status=200, response=json.dumps(msg_json))


start_cleaner()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
