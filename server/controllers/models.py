import time
from datetime import datetime

import controllers.db_enums as db_enums
import itsdangerous
import sqlalchemy

Base = sqlalchemy.ext.declarative.declarative_base()


class UserInformation(Base):
    __tablename__ = 'user_information'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(64))
    username = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)

    auth_info = sqlalchemy.orm.relationship('AuthenticationInformation',
                                            backref='author',
                                            lazy='dynamic')

    def __init__(self, name, username):
        self.name = name
        self.username = username


class AuthenticationInformation(Base):
    __tablename__ = 'auth_info'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    role = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey('user_information.id'),
                                nullable=False)
    hash_type = sqlalchemy.Column(sqlalchemy.String(30), nullable=False)
    iteration_count = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    salt = sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
    salty_hash = sqlalchemy.Column(sqlalchemy.String(200), nullable=False)
    token = sqlalchemy.Column(sqlalchemy.String(200))

    def __init__(self, hash_type, iteration_count, salt, salty_hash, user_id, role):
        self.hash_type = hash_type
        self.iteration_count = iteration_count
        self.salt = salt
        self.salty_hash = salty_hash
        self.user_id = user_id
        self.role = role

        self.generate_token()

    def generate_token(self):
        serializer = itsdangerous.JSONWebSignatureSerializer('123123')  # TODO: figure out a better way to do this
        self.token = bytes.decode(serializer.dumps({
            'user_id': self.user_id,
            'time': time.time()
        }))


# ------------------------------------------------------------
# --                   DEVICE INFO                          --
# ------------------------------------------------------------

class Devices(Base):
    __tablename__ = 'device_info'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(64))
    lat = sqlalchemy.Column(sqlalchemy.Float)
    long = sqlalchemy.Column(sqlalchemy.Float)
    last_check_in = sqlalchemy.Column(sqlalchemy.Float)

    device_id = sqlalchemy.orm.relationship('Classification',
                                            backref='author',
                                            lazy='dynamic')

    def __init__(self, name, lat, long, last_check_in):
        self.name = name
        self.lat = lat
        self.long = long
        self.last_check_in = last_check_in


class Classification(Base):
    __tablename__ = 'classification'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    device_id = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey('device_info.id'),
                                  nullable=False)
    record_time = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    category = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    num_counts = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    def __init__(self, device_id, record_time, category, num_counts):
        self.device_id = device_id
        self.record_time = record_time
        self.category = category
        self.num_counts = num_counts


class DeviceCommands(Base):
    __tablename__ = 'device_commands'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    device_id = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey('device_info.id'),
                                  nullable=False)
    command_number = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    time = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    command_data = sqlalchemy.Column(sqlalchemy.String(1000))
    device_response = sqlalchemy.Column(sqlalchemy.String(1000))
    status = sqlalchemy.Column(sqlalchemy.Enum(db_enums.ServerCommandStatus), nullable=False)

    def __init__(self, device_id, command, data_to_send):
        self.device_id = device_id
        self.command_number = command
        self.command_data = data_to_send
        self.status = db_enums.ServerCommandStatus.received
        self.time = datetime.now()
