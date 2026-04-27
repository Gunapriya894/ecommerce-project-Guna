import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal

_STUBS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stubs'))
_SRC   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'gucart'))

os.environ['TABLE_NAME'] = 'gucart-table'


def get_module():
    # Remove every OTHER lambda folder so only gucart is on the path
    to_remove = [p for p in sys.path if
                 ('guproduct' in p or 'gurecommend' in p or 'gulogu' in p)
                 and p != _SRC]
    for p in to_remove:
        sys.path.remove(p)

    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)
    if _STUBS not in sys.path:
        sys.path.insert(0, _STUBS)

    if 'lambda_function' in sys.modules:
        del sys.modules['lambda_function']

    import lambda_function
    return lambda_function


def make_post(body): return {"httpMethod": "POST", "body": json.dumps(body)}
def make_get():      return {"httpMethod": "GET"}
def make_options():  return {"httpMethod": "OPTIONS"}

ITEMS = [{"name":"Laptop","price":75000,"quantity":1},{"name":"Mouse","price":1500,"quantity":2}]
CTX = MagicMock()


class TestCartOPTIONS(unittest.TestCase):
    def setUp(self):
        p = patch('boto3.resource'); self.mr = p.start(); self.mt = MagicMock()
        self.mr.return_value.Table.return_value = self.mt; self.addCleanup(p.stop)
        self.lm = get_module()

    def test_options_200(self):
        self.assertEqual(self.lm.lambda_handler(make_options(), CTX)['statusCode'], 200)

    def test_options_cors(self):
        r = self.lm.lambda_handler(make_options(), CTX)
        self.assertEqual(r['headers']['Access-Control-Allow-Origin'], '*')

    def test_options_body_ok(self):
        self.assertEqual(self.lm.lambda_handler(make_options(), CTX)['body'], 'OK')


class TestCartPOST(unittest.TestCase):
    def setUp(self):
        p = patch('boto3.resource'); self.mr = p.start(); self.mt = MagicMock()
        self.mr.return_value.Table.return_value = self.mt; self.addCleanup(p.stop)
        self.lm = get_module()

    def test_valid_cart_200(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"alice","items":ITEMS}), CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_calls_put_item(self):
        self.mt.put_item.return_value = {}
        self.lm.lambda_handler(make_post({"user":"alice","items":ITEMS}), CTX)
        self.mt.put_item.assert_called_once()

    def test_cart_stored_message(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"bob","items":ITEMS}), CTX)
        self.assertEqual(json.loads(r['body'])['message'], 'Cart stored')

    def test_correct_user_in_body(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"charlie","items":ITEMS}), CTX)
        self.assertEqual(json.loads(r['body'])['data']['user'], 'charlie')

    def test_correct_items_in_body(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"alice","items":ITEMS}), CTX)
        self.assertEqual(len(json.loads(r['body'])['data']['items']), 2)

    def test_correct_user_stored(self):
        self.mt.put_item.return_value = {}
        self.lm.lambda_handler(make_post({"user":"diana","items":ITEMS}), CTX)
        self.assertEqual(self.mt.put_item.call_args[1]['Item']['user'], 'diana')

    def test_correct_items_stored(self):
        self.mt.put_item.return_value = {}
        self.lm.lambda_handler(make_post({"user":"eve","items":ITEMS}), CTX)
        self.assertEqual(self.mt.put_item.call_args[1]['Item']['items'], ITEMS)

    def test_empty_items_valid(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"frank","items":[]}), CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_missing_items_defaults_empty(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"grace"}), CTX)
        self.assertEqual(json.loads(r['body'])['data']['items'], [])

    def test_missing_user_defaults_empty_string(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"items":ITEMS}), CTX)
        self.assertEqual(json.loads(r['body'])['data']['user'], '')

    def test_none_body_200(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler({"httpMethod":"POST","body":None}, CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_dynamodb_error_500(self):
        self.mt.put_item.side_effect = Exception("Write failed")
        r = self.lm.lambda_handler(make_post({"user":"henry","items":ITEMS}), CTX)
        self.assertEqual(r['statusCode'], 500)

    def test_dynamodb_error_body(self):
        self.mt.put_item.side_effect = Exception("Write failed")
        r = self.lm.lambda_handler(make_post({"user":"ivy","items":ITEMS}), CTX)
        self.assertIn('error', json.loads(r['body']))


class TestCartGET(unittest.TestCase):
    def setUp(self):
        p = patch('boto3.resource'); self.mr = p.start(); self.mt = MagicMock()
        self.mr.return_value.Table.return_value = self.mt; self.addCleanup(p.stop)
        self.lm = get_module()

    def test_get_200(self):
        self.mt.scan.return_value = {'Items': []}
        self.assertEqual(self.lm.lambda_handler(make_get(), CTX)['statusCode'], 200)

    def test_get_returns_list(self):
        self.mt.scan.return_value = {'Items': []}
        self.assertIsInstance(json.loads(self.lm.lambda_handler(make_get(), CTX)['body']), list)

    def test_get_all_carts(self):
        self.mt.scan.return_value = {'Items': [
            {'user':'alice','items':ITEMS},
            {'user':'bob',  'items':[{'name':'Tablet','price':40000,'quantity':1}]}
        ]}
        body = json.loads(self.lm.lambda_handler(make_get(), CTX)['body'])
        self.assertEqual(len(body), 2)

    def test_get_correct_user(self):
        self.mt.scan.return_value = {'Items': [{'user':'alice','items':ITEMS}]}
        body = json.loads(self.lm.lambda_handler(make_get(), CTX)['body'])
        self.assertEqual(body[0]['user'], 'alice')

    def test_get_empty_table(self):
        self.mt.scan.return_value = {'Items': []}
        self.assertEqual(json.loads(self.lm.lambda_handler(make_get(), CTX)['body']), [])

    def test_get_calls_scan_once(self):
        self.mt.scan.return_value = {'Items': []}
        self.lm.lambda_handler(make_get(), CTX)
        self.mt.scan.assert_called_once()

    def test_get_dynamodb_error_500(self):
        self.mt.scan.side_effect = Exception("Scan failed")
        self.assertEqual(self.lm.lambda_handler(make_get(), CTX)['statusCode'], 500)

    def test_decimal_serialized(self):
        self.mt.scan.return_value = {'Items': [
            {'user':'alice','items':[{'name':'Laptop','price':Decimal('75000'),'quantity':1}]}
        ]}
        self.assertEqual(self.lm.lambda_handler(make_get(), CTX)['statusCode'], 200)


class TestCartHeaders(unittest.TestCase):
    def setUp(self):
        p = patch('boto3.resource'); self.mr = p.start(); self.mt = MagicMock()
        self.mr.return_value.Table.return_value = self.mt; self.addCleanup(p.stop)
        self.lm = get_module()

    def test_post_cors(self):
        self.mt.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"user":"j","items":[]}), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_get_cors(self):
        self.mt.scan.return_value = {'Items': []}
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_error_cors(self):
        self.mt.scan.side_effect = Exception("Err")
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])


if __name__ == '__main__':
    unittest.main()