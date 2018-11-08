import hashlib
import hmac
import datetime
import os
from uuid import uuid4
from json import load
import logging

import jwt
from chalice import UnauthorizedError

log = logging.getLogger('log-demo')
log.setLevel(logging.DEBUG)

with open(os.path.join('.chalice', 'config.json')) as f:
    _SECRET = load(f)['_secret'].encode('ascii')

def get_jwt_token(email, password, record):
    actual = hashlib.pbkdf2_hmac(
        record['hash'],
        password.encode(),
        record['salt'].value,
        record['rounds']
    )
    expected = record['hashed'].value
    if hmac.compare_digest(actual, expected):
        now = str(datetime.datetime.utcnow())
        unique_id = str(uuid4())
        payload = {
            'sub': email,
            'iat': now,
            'nbf': now,
            'jti': unique_id,
            # NOTE: We can also add 'exp' if we want tokens to expire.
        }
        return jwt.encode(payload, _SECRET, algorithm='HS256')
    raise UnauthorizedError('Invalid password')


def decode_jwt_token(token):
    log.debug(token)
    return jwt.decode(token, _SECRET, algorithms=['HS256'],options={'verify_iat': False,
                                                                    'verify_nbf': False})
