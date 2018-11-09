# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#

import os
import logging
import boto3
import botocore
from chalice import Chalice, AuthResponse
from chalicelib import auth, db
from boto3.dynamodb.types import Binary

app = Chalice(app_name='swiperapp')
app.debug = True
_DB = None
_USER_DB = None
log = logging.getLogger('log-demo')
log.setLevel(logging.DEBUG)

@app.route('/register', methods=['POST'])
def create_user():
    body = app.current_request.json_body 
    warning_messages = []
    try:
        body['email'] 
        if len(body['email']) > 200:
            warning_messages.append('Email is too long.')
        if '@' not in body['email']:
            warning_messages.append('Email is not formated correctly.')
        # Add check for valid .edu email
        # And add college
    except KeyError:
        warning_messages.append('Email is required.')
    
    try:
        body['password']
        if len(body['password']) <= 10:
            warning_messages.append('Password must be 10 or more characters.')
        if len(body['password']) > 40:
            warning_messages.append('Password is too long.')
    except:
        warning_messages.append('Password is required.')
    
    if warning_messages:
        return {'warning_messages': warning_messages}
    
    try:
        body['first_name']
    except KeyError:
        body['first_name'] = 'default'
    try:
        body['last_name']
    except KeyError:
        body['last_name'] = 'default'

    password_fields = auth.encode_password(body['password'])
    item = {
        'email': body['email'],
        'first_name': body['first_name'],
        'last_name': body['last_name'],
        'college': 'default',
        'hash': password_fields['hash'],
        'salt': Binary(password_fields['salt']),
        'rounds': password_fields['rounds'],
        'hashed': Binary(password_fields['hashed'])
    }

    try:
        log.debug(get_users_db())
        get_users_db().put_item(Item=item,
                        ConditionExpression='attribute_not_exists(email)'
                        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {'warning_messages':'Email is already registered.'}
    
    return {'message':'success'} 

@app.route('/login', methods=['POST'])
def login():
    body = app.current_request.json_body
    record = get_users_db().get_item(
        Key={'email': body['email']})
    log.debug(record)
    jwt_token = auth.get_jwt_token(
        body['email'], body['password'], record['Item'])
    
    return {'token': jwt_token.decode('utf-8')}


@app.authorizer()
def jwt_auth(auth_request):
    token = auth_request.token
    decoded = auth.decode_jwt_token(token)
    return AuthResponse(routes=['*'], principal_id=decoded['sub'])


def get_users_db():
    global _USER_DB
    if _USER_DB is None:
        _USER_DB = boto3.resource('dynamodb').Table(
            os.environ['USERS_TABLE_NAME'])
    return _USER_DB


# Rest API code


def get_app_db():
    global _DB
    if _DB is None:
        _DB = db.DynamoDB(
            boto3.resource('dynamodb').Table(
                os.environ['APP_TABLE_NAME'])
        )
    return _DB


def get_authorized_email(current_request):
    return current_request.context['authorizer']['principalId']


@app.route('/swipemap', methods=['GET'])
def get_meals():
    # email = get_authorized_email(app.current_request)
    return get_app_db().list_items()


@app.route('/myswipes', methods=['POST'], authorizer=jwt_auth)
def add_new_meal():
    body = app.current_request.json_body
    email = get_authorized_email(app.current_request)
    return get_app_db().add_item(
        email=email,
        description=body['description'],
        metadata=body.get('metadata'),
    )


@app.route('/myswipes/{uid}', methods=['GET'], authorizer=jwt_auth)
def get_meal(uid):
    email = get_authorized_email(app.current_request)
    return get_app_db().get_item(uid, email=email)


@app.route('/myswipes/{uid}', methods=['DELETE'], authorizer=jwt_auth)
def delete_meal(uid):
    email = get_authorized_email(app.current_request)
    return get_app_db().delete_item(uid, email=email)


@app.route('/myswipes/{uid}', methods=['PUT'], authorizer=jwt_auth)
def update_meal(uid):
    body = app.current_request.json_body
    email = get_authorized_email(app.current_request)
    get_app_db().update_item(
        uid,
        description=body.get('description'),
        state=body.get('state'),
        metadata=body.get('metadata'),
        email=email)
