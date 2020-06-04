import json
from functools import wraps

from controllers.device_manager import DeviceManager
from controllers.request_constants import API_VERSION
from flask import request, Response

db = DeviceManager('root', 'password', 'localhost', port=3306)
db.connect_to_db()


def return_error(status_code, error):
    error_json = {'apiVersion': API_VERSION,
                  'error': {'message': str(error)}}
    return Response(status=status_code, response=json.dumps(error_json))


def check_role(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')

            just_token = token.split(' ')[1]

            if db.is_user(just_token):
                return json.dumps({'role': 0})
            elif db.is_admin(just_token):
                return json.dumps({'role': 1})
            return return_error(401, 'Authorization Forbidden')
        except:
            # I acknowledge that it isn't the best practice to have this broad of an except block
            # but don't want this to fail at all so it must happen
            return return_error(401, 'Authroization Forbidden')

    return decorator


def user_auth(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            just_token = token.split(' ')[1]
        except (AttributeError, IndexError):
            print('error in user_auth')
            return return_error(401, 'Authorization Forbidden')

        if db.is_user(just_token):
            return func(*args, **kwargs)
        elif db.is_admin(just_token):
            return func(*args, **kwargs)

        return return_error(401, 'Authorization Forbidden')

    return decorator


def admin_auth(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        try:
            just_token = token.split(' ')[1]
        except (AttributeError, IndexError):
            print('error in admin_auth')
            return return_error(401, 'Authorization Forbidden')

        if db.is_admin(just_token):
            return func(*args, **kwargs)

        return return_error(401, 'Authorization forbidden')

    return decorator
