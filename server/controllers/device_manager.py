import binascii
import datetime
import hashlib
import json
import os
import time

import controllers.db_enums as db_enums
import flask
import flask_sqlalchemy
import sqlalchemy
from controllers import auth_const, auth_utils, request_constants as req_const
from controllers.models import Base, UserInformation, AuthenticationInformation, Classification, Devices, DeviceCommands


class InvalidError(Exception):
    pass


def catch_db_error(return_none=True):
    def db_decorator(f):
        def func_wrapper(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except sqlalchemy.exc.OperationalError as e:
                print('error in catch_db_error: %s' % e)
                self.db.session.rollback()
                if return_none:
                    return None
                else:
                    return False

        return func_wrapper

    return db_decorator


class DeviceManager:
    def __init__(self, username, password, host, db_name='devices', port=5432):
        self.username = username
        self.password = password
        self.host = host
        self.db_name = db_name
        self.port = port

        self.db = None

    def connect_to_db(self):
        app = flask.Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = self.uri
        self.db = flask_sqlalchemy.SQLAlchemy(app)

    def create_db(self):
        try:
            test_engine = sqlalchemy.create_engine(self.uri)
            test_conn = test_engine.connect()
            test_conn.execute('commit')
            test_conn.close()
        except sqlalchemy.exc.OperationalError:
            default_uri = 'mysql://%s:%s@%s:%d/mysql' % (self.username,
                                                         self.password,
                                                         self.host,
                                                         self.port)
            default_engine = sqlalchemy.create_engine(default_uri)
            default_conn = default_engine.connect()
            default_conn.execute('commit')
            default_conn.execute('CREATE DATABASE %s;' % self.db_name)
            default_conn.execute('commit')
            default_conn.close()

    def create_tables(self):
        engine = sqlalchemy.create_engine(self.uri, convert_unicode=True)
        Base.metadata.create_all(engine)
        # self.db.create_all()
        # self.db.session.commit()
        self.create_auth_user()

    # --------------------------------------------------------
    # ---               USER AUTH STUFF                    ---
    # --------------------------------------------------------

    @catch_db_error(False)
    def is_admin(self, token):
        if token == '':
            return False
        user = self.db.session.query(AuthenticationInformation). \
            filter(AuthenticationInformation.token == token). \
            with_entities(AuthenticationInformation.role).first()

        if user is None:
            return False
        return user[0] == 1

    @catch_db_error(False)
    def is_user(self, token):
        if token == '':
            return False
        user = self.db.session.query(AuthenticationInformation). \
            filter(AuthenticationInformation.token == token). \
            with_entities(AuthenticationInformation.role).first()

        if user is None:
            return False
        return user[0] == 0

    @catch_db_error(False)
    def get_user_id_from_token(self, token):
        user = self.db.session.query(UserInformation, AuthenticationInformation). \
            filter(UserInformation.id == AuthenticationInformation.user_id). \
            filter(AuthenticationInformation.token == token). \
            with_entities(UserInformation).first()
        return user.id

    @catch_db_error(True)
    def user_exists(self, user_id=None, username=None):
        if user_id is not None:
            return len(self.db.session.query(UserInformation).filter(UserInformation.id == user_id).all()) == 1
        if username is not None:
            return len(self.db.session.query(UserInformation).filter(UserInformation.username == username).all()) == 1

    @catch_db_error(True)
    def get_username(self, user_id):
        user = self.db.session.query(UserInformation).filter(UserInformation.id == user_id).all()
        if not user:
            return None
        return user[0].username

    @catch_db_error(True)
    def get_user_id(self, username):
        user = self.db.session.query(UserInformation).filter(UserInformation.username == username).all()
        if not user:
            return None
        return user[0].id

    def get_users(self):
        users = self.db.session.query(UserInformation).all()
        formatted_users = []

        for user in users:
            formatted_users.append({req_const.NAME: user.name,
                                    req_const.USERNAME: user.username})

        return json.dumps(formatted_users)

    @catch_db_error(True)
    def authenticate(self, username, password):
        user = self.db.session.query(UserInformation).filter(UserInformation.username == username).all()
        if user is None or user == []:
            raise InvalidError('There is no account with this username.')
        user = user[0]
        (hash_type, salt, iteration_count, salty_hash, token) = self.db.session.query(AuthenticationInformation). \
            filter(AuthenticationInformation.user_id == user.id). \
            with_entities(AuthenticationInformation.hash_type,
                          AuthenticationInformation.salt,
                          AuthenticationInformation.iteration_count,
                          AuthenticationInformation.salty_hash,
                          AuthenticationInformation.token).first()

        byte_salty_hash = binascii.hexlify(hashlib.pbkdf2_hmac(hash_type,
                                                               str.encode(password),
                                                               str.encode(salt),
                                                               iteration_count))
        test_salty_hash = bytes.decode(byte_salty_hash)

        if test_salty_hash == salty_hash:
            return token
        else:
            raise InvalidError('This username address and/or password appears to be incorrect')

    def add_user(self, name, username, password, role):
        if self.user_exists(username=username):
            raise InvalidError('A user with this username already exists')

        try:
            new_user = UserInformation(name, username)
            self.db.session.add(new_user)
            self.db.session.commit()
        except sqlalchemy.exc.OperationalError as error:
            print('%s in add_user: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            raise

        if role == 'admin':
            role_id = 1
        else:
            role_id = 0

        try:
            salt = os.urandom(auth_const.SALT_LENGTH)
            passwd_hash = auth_utils.generate_hash(auth_const.DEFAULT_HASH_TYPE,
                                                   password,
                                                   auth_const.DEFAULT_ITER_COUNT,
                                                   salt=salt)
            auth_info = AuthenticationInformation(auth_const.DEFAULT_HASH_TYPE,
                                                  auth_const.DEFAULT_ITER_COUNT,
                                                  bytes.decode(binascii.hexlify(salt)),
                                                  bytes.decode(passwd_hash),
                                                  new_user.id,
                                                  role_id)
            self.db.session.add(auth_info)
            self.db.session.commit()
            return auth_info.token
        except sqlalchemy.exc.OperationalError as error:
            print('%s in add_user: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            self.db.session.commit()
            raise

    def change_user_password(self, username, new_password):
        try:
            if not self.user_exists(username=username):
                return False
            user = self.db.session.query(UserInformation).filter(UserInformation.username == username).first()
            auth = self.db.session.query(AuthenticationInformation).filter(
                AuthenticationInformation.user_id == user.id).first()
            salt = os.urandom(auth_const.SALT_LENGTH)
            passwd_hash = auth_utils.generate_hash(auth_const.DEFAULT_HASH_TYPE,
                                                   new_password,
                                                   auth_const.DEFAULT_ITER_COUNT,
                                                   salt=salt)

            auth.salt = bytes.decode(binascii.hexlify(salt))
            auth.salty_hash = bytes.decode(passwd_hash)
            auth.generate_token()
            self.db.session.commit()
        except sqlalchemy.exc.OperationalError as error:
            print('%s in change_user_password: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            raise

    def edit_user(self, username, new_password=None):
        try:
            user = self.db.session.query(UserInformation).filter(UserInformation.username == username).first()

            if user is None:
                return False

            if new_password is not None:
                self.change_user_password(username, new_password)
            self.db.session.commit()
            return True
        except sqlalchemy.exc.OperationalError as error:
            print('%s in edit_user: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            raise

    def delete_user(self, username):
        user = self.db.session.query(UserInformation).filter(UserInformation.username == username).first()

        if user is None or user == []:
            return False

        auth_info = self.db.session.query(AuthenticationInformation). \
            filter(AuthenticationInformation.user_id == user.id).first()

        try:
            self.db.session.delete(auth_info)
            self.db.session.delete(user)
            self.db.session.commit()
            return True
        except sqlalchemy.exc.OperationalError as error:
            print('%s in delete_user: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            self.db.session.commit()
            raise

    def get_id_from_username(self, username):
        user = self.db.session.query(UserInformation).filter(UserInformation.username == username).first()
        if user is None:
            return -1
        return user.id

    def create_auth_user(self):
        if self.user_exists(username='test'):
            return

        try:
            new_user = UserInformation('neil', 'test')
            self.db.session.add(new_user)
            self.db.session.commit()
        except sqlalchemy.exc.OperationalError as error:
            print('%s in add_user: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            raise

        try:
            salt = os.urandom(auth_const.SALT_LENGTH)
            passwd_hash = auth_utils.generate_hash(auth_const.DEFAULT_HASH_TYPE,
                                                   auth_const.DEFAULT_ADMIN_PSWD,
                                                   auth_const.DEFAULT_ITER_COUNT,
                                                   salt=salt)
            auth_info = AuthenticationInformation(auth_const.DEFAULT_HASH_TYPE,
                                                  auth_const.DEFAULT_ITER_COUNT,
                                                  bytes.decode(binascii.hexlify(salt)),
                                                  bytes.decode(passwd_hash),
                                                  new_user.id,
                                                  1)
            self.db.session.add(auth_info)
            self.db.session.commit()
        except sqlalchemy.exc.OperationalError as error:
            print('%s in add_user: %s' % (type(error).__name__, str(error)))
            self.db.session.rollback()
            self.db.session.commit()
            raise

    @property
    def uri(self):
        return 'mysql://%s:%s@%s:%d/%s' % (self.username,
                                           self.password,
                                           self.host,
                                           self.port,
                                           self.db_name)

    @catch_db_error(False)
    def user_exists(self, user_id=None, username=None):
        if user_id is not None:
            return len(self.db.session.query(UserInformation).
                       filter(UserInformation.id == user_id).all()) == 1
        if username is not None:
            return len(self.db.session.query(UserInformation).
                       filter(UserInformation.username == username).all()) == 1

    @catch_db_error(False)
    def device_exists(self, device_id=None, name=None):
        device_query = self.db.session.query(Devices)

        if device_id is not None:
            device_query = device_query.filter(Devices.id == device_id)
        if name is not None:
            device_query = device_query.filter(Devices.name.contains(name))
        return len(device_query.all()) >= 1

    @catch_db_error(False)
    def get_device_id(self, token):
        name = self.db.session.query(UserInformation, AuthenticationInformation).filter(
            UserInformation.id == AuthenticationInformation.user_id).filter(
            AuthenticationInformation.token == token).with_entities(UserInformation.name).first()
        if len(name) == 1:
            device_id = self.db.session.query(Devices).filter(Devices.name == name[0]).with_entities(Devices.id).first()
            if device_id is not None and len(device_id) == 1:
                return device_id[0]
            else:
                return None
        return None

    @catch_db_error(True)
    def get_entries(self, device_id, category=None, start_time=None, end_time=None):
        entries = self.db.session.query(Classification).filter(Classification.device_id == device_id)

        if start_time is not None:
            entries = entries.filter(Classification.record_time >= start_time)
        if end_time is not None:
            entries = entries.filter(Classification.record_time <= end_time)
        if category is not None:
            entries = entries.filter(Classification.category == category)
        entries = entries.with_entities(Classification.category,
                                        Classification.record_time,
                                        Classification.device_id).all()
        return entries

    @catch_db_error(True)
    def search_entries(self, device_ids=None, categories=None, start_time=None, end_time=None):
        entries = self.db.session.query(Classification)

        if device_ids is not None:
            entries = entries.filter(Classification.device_id.in_(device_ids))
        if categories is not None:
            entries = entries.filter(Classification.category.in_(categories))
        if start_time is not None:
            entries = entries.filter(Classification.record_time >= start_time)
        if end_time is not None:
            entries = entries.filter(Classification.record_time <= end_time)

        entries = entries.with_entities(Classification.category,
                                        Classification.record_time,
                                        Classification.device_id).all()
        return entries

    @catch_db_error(False)
    def add_entries(self, device_id, entries):
        # expecting a list of objects like this {'category': 'work van', 'time':123123, 'num_counts': 4}
        # 'num_counts' is optional, if not there, it will default to 1
        for entry in entries:
            entry_time = datetime.datetime.fromtimestamp(entry['time'])
            entry_category = entry['category']
            if 'num_counts' not in entry:
                entry_counts = 1
            else:
                entry_counts = entry['num_counts']

            if entry_time is None or entry_category is None:
                return False
            entry_category = entry_category.lower()
            if entry_counts is None:
                entry_counts = 1
            class_entry = Classification(device_id, entry_time, entry_category, entry_counts)
            self.db.session.add(class_entry)
        self.db.session.commit()
        return True

    @catch_db_error(False)
    def add_device(self, information):
        try:
            name = information['name']
            lat = information['lat']
            long = information['long']
        except Exception:
            return None
        new_device = Devices(name, lat, long, time.time())
        dev_token = self.add_user(name, name.replace(' ', ''), '', 'user')
        self.db.session.add(new_device)
        self.db.session.commit()
        return dev_token

    @catch_db_error(True)
    def get_devices(self, device_id=None, name=None):
        devices_query = self.db.session.query(Devices)
        if device_id is not None:
            devices_query = devices_query.filter(Devices.id == device_id)
        if name is not None:
            devices_query = devices_query.filter(Devices.name.contains(name))
        devices = devices_query.with_entities(Devices.id, Devices.name, Devices.lat, Devices.long, Devices.last_check_in).all()
        return devices

    @catch_db_error(True)
    def delete_device(self, device_id):
        entries = self.db.session.query(Classification).filter(Classification.device_id == device_id)
        entries.delete()
        device_query = self.db.session.query(Devices).filter(Devices.id == device_id)
        device_name = device_query.with_entities(Devices.name).first()[0]
        self.delete_user(device_name.replace(' ', ''))
        device_query.delete()
        self.db.session.commit()
        return True

    @catch_db_error(False)
    def check_in(self, device_id, checkin_time):
        device = self.db.session.query(Devices).filter(Devices.id == device_id).with_entities(Devices).first()
        if device is None:
            return False
        device.last_check_in = checkin_time
        self.db.session.commit()
        return True

    def convert_number_command(self, command):
        if command == 1:
            return 'update_configuration'
        elif command == 2:
            return 'send_picture'
        elif command == 3:
            return 'send_configuration'
        return None

    def convert_command_number(self, command):
        if command == 'update_configuration':
            return 1
        elif command == 'send_picture':
            return 2
        elif command == 'send_configuration':
            return 3
        return None

    @catch_db_error(True)
    def get_command(self, device_id):
        commands = self.db.session.query(Devices, DeviceCommands). \
            filter(DeviceCommands.device_id == Devices.id). \
            filter(Devices.id == device_id). \
            filter(DeviceCommands.status == db_enums.ServerCommandStatus.sent). \
            with_entities(DeviceCommands).first()
        if commands is None:
            commands = self.db.session.query(Devices, DeviceCommands). \
                filter(DeviceCommands.device_id == Devices.id). \
                filter(Devices.id == device_id). \
                filter(DeviceCommands.status == db_enums.ServerCommandStatus.received). \
                with_entities(DeviceCommands).first()
        if commands is None:
            return None, None
        command = self.convert_number_command(commands.command_number)

        data = json.loads(commands.command_data)
        commands.status = db_enums.ServerCommandStatus.sent
        self.db.session.commit()
        return command, data

    @catch_db_error(True)
    def get_command_information(self, command_id):
        command = self.db.session.query(DeviceCommands).filter(DeviceCommands.id == command_id).with_entities(
            DeviceCommands).first()
        if command.device_response is None:
            dev_resp = ''
        else:
            dev_resp = json.loads(command.device_response)
        command_data = {
            'command_number': command.command_number,
            'status': command.status.name,
            'response': dev_resp
        }
        return command_data

    @catch_db_error(False)
    def delete_command(self, command_id):
        command = self.db.session.query(DeviceCommands).filter(DeviceCommands.id == command_id).with_entities(
            DeviceCommands).first()
        self.db.session.delete(command)
        self.db.session.commit()
        return True

    @catch_db_error(True)
    def put_command(self, device_id, command_number, command_data):
        command = DeviceCommands(device_id, command_number, json.dumps(command_data))
        self.db.session.add(command)
        self.db.session.commit()
        command_id = command.id
        return command_id

    @catch_db_error(False)
    def update_command(self, device_id, command_data):
        command = self.db.session.query(Devices, DeviceCommands). \
            filter(DeviceCommands.device_id == Devices.id). \
            filter(Devices.id == device_id). \
            filter(DeviceCommands.status == db_enums.ServerCommandStatus.sent). \
            with_entities(DeviceCommands).first()
        if command is None or command_data is None:
            return True
        command.device_response = json.dumps(command_data)
        command.status = db_enums.ServerCommandStatus.completed
        self.db.session.commit()
        return True

    @catch_db_error(False)
    def clean_commands(self, max_age):
        delta = datetime.timedelta(seconds=max_age)
        now = datetime.datetime.now() - delta
        commands = self.db.session.query(DeviceCommands).filter(DeviceCommands.time < now).all()

        for command in commands:
            self.db.session.delete(command)
        self.db.session.commit()


if __name__ == '__main__':
    test = DeviceManager('root', 'password', 'localhost', 'devices', 5432)
    test.create_db()
    test.connect_to_db()
    print(test.get_entries('test'))
