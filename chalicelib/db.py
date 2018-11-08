from uuid import uuid4
import logging

from boto3.dynamodb.conditions import Key


DEFAULT_EMAIL = 'default'
log = logging.getLogger('log-demo')
log.setLevel(logging.DEBUG)


class AppDB(object):
    def list_items(self):
        pass

    def add_item(self, description, metadata=None):
        pass

    def get_item(self, uid):
        pass

    def delete_item(self, uid):
        pass

    def update_item(self, uid, description=None, state=None,
                    metadata=None):
        pass


class InMemoryDB(AppDB):
    def __init__(self, state=None):
        if state is None:
            state = {}
        self._state = state

    def list_all_items(self):
        all_items = []
        for email in self._state:
            all_items.extend(self.list_items(email))
        return all_items

    def list_items(self, email=DEFAULT_EMAIL):
        return list(self._state.get(email, {}).values())

    def add_item(self, description, metadata=None, email=DEFAULT_EMAIL):
        if email not in self._state:
            self._state[email] = {}
        uid = str(uuid4())
        self._state[email][uid] = {
            'uid': uid,
            'description': description,
            'state': 'unstarted',
            'metadata': metadata if metadata is not None else {},
            'email': email
        }
        return uid

    def get_item(self, uid, email=DEFAULT_EMAIL):
        return self._state[email][uid]

    def delete_item(self, uid, email=DEFAULT_EMAIL):
        del self._state[email][uid]

    def update_item(self, uid, description=None, state=None,
                    metadata=None, email=DEFAULT_EMAIL):
        item = self._state[email][uid]
        if description is not None:
            item['description'] = description
        if state is not None:
            item['state'] = state
        if metadata is not None:
            item['metadata'] = metadata


class DynamoDB(AppDB):
    def __init__(self, table_resource):
        self._table = table_resource

    def list_all_items(self):
        response = self._table.scan()
        return response['Items']

    def list_items(self):#email=DEFAULT_EMAIL):
        response = self._table.scan()
        #log.debug(response)
        data = response['Items']
        #response = self._table.query(
           # KeyConditionExpression=Key('email').eq(email)
        #)
        while 'LastEvalutedKey' in response:
            response = self._table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])
        return data

    def add_item(self, description, metadata=None, email=DEFAULT_EMAIL):
        uid = str(uuid4())
        self._table.put_item(
            Item={
                'email': email,
                'uid': uid,
                'description': description,
                'state': 'unstarted',
                'metadata': metadata if metadata is not None else {},
            }
        )
        return uid

    def get_item(self, uid, email=DEFAULT_EMAIL):
        response = self._table.get_item(
            Key={
                'email': email,
                'uid': uid,
            },
        )
        try:
            return response['Item']
        except KeyError:
            return {'message':'Item does not exist'}

    def delete_item(self, uid, email=DEFAULT_EMAIL):
        self._table.delete_item(
            Key={
                'email': email,
                'uid': uid,
            }
        )

    def update_item(self, uid, description=None, state=None,
                    metadata=None, email=DEFAULT_EMAIL):
        # We could also use update_item() with an UpdateExpression.
        item = self.get_item(uid, email)
        if description is not None:
            item['description'] = description
        if state is not None:
            item['state'] = state
        if metadata is not None:
            item['metadata'] = metadata
        self._table.put_item(Item=item)
