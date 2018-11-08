import os
import unittest
import boto3
from uuid import uuid4

from chalicelib.db import InMemoryDB
from chalicelib.db import DynamoDB


class TestDB(unittest.TestCase):
    def setUp(self):
        self.db_dict = {}
        self.db = InMemoryDB(self.db_dict)

    def tearDown(self):
        response = self.db.list_all_items()
        for item in response:
            self.db.delete_item(item['uid'], email=item['email'])

    def test_can_add_and_retrieve_data(self):
        id = self.db.add_item('First item')
        self.assertDictContainsSubset(
            {'description': 'First item',
             'state': 'unstarted',
             'metadata': {}},
            self.db.get_item(id),
        )

    def test_can_add_and_list_data(self):
        id = self.db.add_item('First item')
        items = self.db.list_items()
        print(items)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['uid'], id)

    def test_can_add_and_delete_data(self):
        id = self.db.add_item('First item')
        self.assertEqual(len(self.db.list_items()), 1)
        self.db.delete_item(id)
        self.assertEqual(len(self.db.list_items()), 0)

    def test_can_add_and_update_data(self):
        id = self.db.add_item('First item')
        self.db.update_item(id, state='started')
        self.assertEqual(self.db.get_item(id)['state'], 'started')

    def test_can_add_and_retrieve_data_with_specified_email(self):
        email = 'myemail'
        id = self.db.add_item('First item', email=email)
        self.assertDictContainsSubset(
            {'description': 'First item',
             'state': 'unstarted',
             'metadata': {},
             'email': email},
            self.db.get_item(id, email=email)
        )

    def test_can_add_and_list_data_with_specified_email(self):
        email = 'myemail'
        id = self.db.add_item('First item', email=email)
        items = self.db.list_items(email=email)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['uid'], id)
        self.assertEqual(items[0]['email'], email)

    def test_can_add_and_delete_data_with_specified_email(self):
        email = 'myemail'
        id = self.db.add_item('First item', email=email)
        self.assertEqual(len(self.db.list_items(email=email)), 1)
        self.db.delete_item(id, email=email)
        self.assertEqual(len(self.db.list_items(email=email)), 0)

    def test_can_add_and_update_data_with_specified_email(self):
        email = 'myemail'
        id = self.db.add_item('First item', email=email)
        self.db.update_item(id, state='started', email=email)
        self.assertEqual(self.db.get_item(
            id, email=email)['state'], 'started')

    def test_list_all_items(self):
        id = self.db.add_item('First item', email='user')
        other_id = self.db.add_item('First item', email='otheruser')
        items = self.db.list_all_items()
        self.assertEqual(len(items), 2)
        users = [item['email'] for item in items]
        other_ids = [item['uid'] for item in items]
        self.assertEqual(['user', 'otheruser'], users)
        self.assertEqual([id, other_id], other_ids)


@unittest.skipUnless(os.environ.get('RUN_INTEG_TESTS', False),
                     "Skipping integ tests (RUN_INTEG_TESTS) not test.")
class TestDynamoDB(TestDB):
    @classmethod
    def setUpClass(cls):
        cls.TABLE_NAME = 'mealswiper-integ-%s' % str(uuid4())
        client = boto3.client('dynamodb')
        client.create_table(
            TableName=cls.TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'uid',
                    'KeyType': 'RANGE',
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S',
                },
                {
                    'AttributeName': 'uid',
                    'AttributeType': 'S',
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            }
        )
        waiter = client.get_waiter('table_exists')
        waiter.wait(TableName=cls.TABLE_NAME, WaiterConfig={'Delay': 1})

    @classmethod
    def tearDownClass(cls):
        client = boto3.client('dynamodb')
        client.delete_table(TableName=cls.TABLE_NAME)
        waiter = client.get_waiter('table_not_exists')
        waiter.wait(TableName=cls.TABLE_NAME, WaiterConfig={'Delay': 1})

    def setUp(self):
        resource = boto3.resource('dynamodb')
        self.table = resource.Table(self.TABLE_NAME)
        self.db = DynamoDB(self.table)
