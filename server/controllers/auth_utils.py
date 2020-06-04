import binascii
import hashlib
import os

from controllers import auth_const


def generate_hash(hash_type, password, iteration_count, salt_length=auth_const.SALT_LENGTH, salt=None):
    if salt is None:
        salt = os.urandom(salt_length)
    salt = binascii.hexlify(salt)
    dk = hashlib.pbkdf2_hmac(hash_type, str.encode(password), salt, iteration_count)
    return binascii.hexlify(dk)
