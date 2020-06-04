import json
import os
import threading
import time

import requests

import constants
from configuration.configuration import configuration


class Management:
    def __init__(self):
        self.run_thread = threading.Thread(target=self.run)
        self.status = constants.Status.NOT_STARTED
        self.counter = 0

        self.files = None
        self.command_data = None

        self.response_data = None
        self.send_picture = False

    @property
    def polling_interval(self):
        return configuration.get_value('data_management', 'hb_interval')

    @property
    def hb_dest(self):
        return configuration.get_value('data_management', 'push_location')

    @property
    def token(self):
        return configuration.get_value('data_management', 'push_token')

    def start(self):
        self.status = constants.Status.RUNNING
        self.run_thread.start()

    def stop(self):
        self.status = constants.Status.STOPPED
        self.run_thread.join()

    def send_config(self):
        response = requests.post(self.hb_dest + '/api/command',
                                 json=configuration.get_configuration(),
                                 headers={'Authorization': 'Token ' + self.token})
        if response.status_code != 200:
            print('Error in sending config')

    def upload_picture(self):
        files = {'file': open(os.path.join(constants.TMP_DIRECTORY, 'preview.jpg'), 'rb').read()}
        response = requests.post(self.hb_dest + '/api/upload',
                                 files=files,
                                 headers={'Authorization': 'Token ' + self.token})
        if response.status_code == 200:
            return True
        return False

    def handle_command(self, command, data=None):
        self.response_data = {}
        if command == 'update_configuration':
            configuration.update_configuration(data)
            self.response_data = {'command_status': 'Success'}
        elif command == 'send_picture':
            if self.upload_picture():
                self.response_data = {'command_status': 'Success'}
            else:
                self.response_data = {'command_status': 'Failed to upload picture'}
        elif command == 'send_configuration':
            self.response_data = {'command_status': 'Success',
                                  'data': configuration.get_configuration()}

    def generate_hb_data(self):
        hb_data = {'time': time.time(),
                   'command': self.response_data}
        return hb_data

    def reset(self):
        self.files = {}
        self.response_data = {}
        self.send_picture = False

    def send_hb(self, hb_data):
        hb_data = json.loads(json.dumps(hb_data).replace('\'', '"'))
        if self.send_picture:
            response = requests.post(self.hb_dest + '/api/heartbeat',
                                     json=hb_data,
                                     headers={'Authorization': 'Token ' + self.token,
                                              'Content-Type': 'application/json'})
        else:
            response = requests.post(self.hb_dest + '/api/heartbeat',
                                     json=hb_data,
                                     headers={'Authorization': 'Token ' + self.token,
                                              'Content-Type': 'application/json'})
        if response.status_code != 200:
            print('Heartbeat sent to %s got status code: %d' % (self.hb_dest, response.status_code))
            print('Will retry later')
        else:
            self.reset()
            data = json.loads(response.text)
            if 'command' in data:
                command = data['command']
                if 'data' in data:
                    command_data = data['data']
                else:
                    command_data = None
                self.handle_command(command, command_data)

    def run(self):
        while self.status == constants.Status.RUNNING:
            try:
                time.sleep(1)
                if self.counter == self.polling_interval:
                    self.counter = 0
                    hb_data = self.generate_hb_data()
                    self.send_hb(hb_data)

                self.counter += 1
            except Exception as e:
                print('Error in manager: %s: %s' % (type(e).__name__, str(e)))


if __name__ == '__main__':
    manager = Management(5)
    manager.start()

    while True:
        continue
