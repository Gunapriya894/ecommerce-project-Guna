import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal

_STUBS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stubs'))
_SRC   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'guproduct'))

os.environ['TABLE_NAME'] = 'guproduct-table'


def get_module():
    # Remove every OTHER lambda folder so only guproduct is on the path
    to_remove = [p for p in sys.path if
                 ('gucart' in p or 'gurecommend' in p or 'gulogu' in p)
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

CTX = MagicMock()

# ──────────────────────────────────────────────────────────────────────────────

class TestProductOPTIONS(unittest.TestCase):

    def setUp(self):
        patcher = patch('boto3.resource')
        self.mock_res = patcher.start()
        self.mock_table = MagicMock()
        self.mock_res.return_value.Table.return_value = self.mock_table
        self.addCleanup(patcher.stop)
        self.lm = get_module()

    def test_options_returns_200(self):
        r = self.lm.lambda_handler(make_options(), CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_options_cors_header(self):
        r = self.lm.lambda_handler(make_options(), CTX)
        self.assertEqual(r['headers']['Access-Control-Allow-Origin'], '*')

    def test_options_body_ok(self):
        r = self.lm.lambda_handler(make_options(), CTX)
        self.assertEqual(r['body'], 'OK')


class TestProductPOST(unittest.TestCase):

    def setUp(self):
        patcher = patch('boto3.resource')
        self.mock_res = patcher.start()
        self.mock_table = MagicMock()
        self.mock_res.return_value.Table.return_value = self.mock_table
        self.addCleanup(patcher.stop)
        self.lm = get_module()

    def test_valid_product_returns_200(self):
        self.mock_table.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"id":"P1","name":"Laptop","price":75000,"stock":10}), CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_valid_product_calls_put_item(self):
        self.mock_table.put_item.return_value = {}
        self.lm.lambda_handler(make_post({"id":"P1","name":"Laptop","price":75000,"stock":10}), CTX)
        self.mock_table.put_item.assert_called_once()

    def test_returns_success_message(self):
        self.mock_table.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"id":"P2","name":"Mouse","price":1500,"stock":50}), CTX)
        body = json.loads(r['body'])
        self.assertEqual(body['message'], 'Product stored')

    def test_returns_product_data(self):
        self.mock_table.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"id":"P3","name":"Keyboard","price":3000,"stock":25}), CTX)
        body = json.loads(r['body'])
        self.assertEqual(body['data']['id'], 'P3')
        self.assertEqual(body['data']['name'], 'Keyboard')

    def test_missing_id_returns_400(self):
        r = self.lm.lambda_handler(make_post({"name":"Laptop","price":75000}), CTX)
        self.assertEqual(r['statusCode'], 400)

    def test_missing_id_error_message(self):
        r = self.lm.lambda_handler(make_post({"name":"Laptop"}), CTX)
        body = json.loads(r['body'])
        self.assertIn('error', body)
        self.assertIn('Product ID', body['error'])

    def test_empty_id_returns_400(self):
        r = self.lm.lambda_handler(make_post({"id":"  ","name":"Laptop","price":1000}), CTX)
        self.assertEqual(r['statusCode'], 400)

    def test_empty_body_returns_400(self):
        r = self.lm.lambda_handler({"httpMethod":"POST","body":"{}"}, CTX)
        self.assertEqual(r['statusCode'], 400)

    def test_none_body_returns_400(self):
        r = self.lm.lambda_handler({"httpMethod":"POST","body":None}, CTX)
        self.assertEqual(r['statusCode'], 400)

    def test_price_stored_as_decimal(self):
        self.mock_table.put_item.return_value = {}
        self.lm.lambda_handler(make_post({"id":"P4","name":"Monitor","price":25000.50,"stock":5}), CTX)
        item = self.mock_table.put_item.call_args[1]['Item']
        self.assertEqual(item['price'], Decimal('25000.5'))

    def test_stock_stored_as_int(self):
        self.mock_table.put_item.return_value = {}
        self.lm.lambda_handler(make_post({"id":"P5","name":"Webcam","price":5000,"stock":30}), CTX)
        item = self.mock_table.put_item.call_args[1]['Item']
        self.assertEqual(item['stock'], 30)

    def test_dynamodb_error_returns_500(self):
        self.mock_table.put_item.side_effect = Exception("DB error")
        r = self.lm.lambda_handler(make_post({"id":"P6","name":"Tablet","price":40000,"stock":15}), CTX)
        self.assertEqual(r['statusCode'], 500)

    def test_dynamodb_error_body_has_error(self):
        self.mock_table.put_item.side_effect = Exception("DB error")
        r = self.lm.lambda_handler(make_post({"id":"P7","name":"Tablet","price":40000,"stock":15}), CTX)
        body = json.loads(r['body'])
        self.assertIn('error', body)


class TestProductGET(unittest.TestCase):

    def setUp(self):
        patcher = patch('boto3.resource')
        self.mock_res = patcher.start()
        self.mock_table = MagicMock()
        self.mock_res.return_value.Table.return_value = self.mock_table
        self.addCleanup(patcher.stop)
        self.lm = get_module()

    def test_get_returns_200(self):
        self.mock_table.scan.return_value = {'Items': []}
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_get_returns_list(self):
        self.mock_table.scan.return_value = {'Items': []}
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertIsInstance(json.loads(r['body']), list)

    def test_get_returns_all_products(self):
        self.mock_table.scan.return_value = {'Items': [
            {'id':'P1','name':'Laptop','price':Decimal('75000'),'stock':10},
            {'id':'P2','name':'Mouse', 'price':Decimal('1500'), 'stock':50},
        ]}
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertEqual(len(json.loads(r['body'])), 2)

    def test_get_correct_fields(self):
        self.mock_table.scan.return_value = {'Items': [
            {'id':'P1','name':'Laptop','price':Decimal('75000'),'stock':10}
        ]}
        body = json.loads(self.lm.lambda_handler(make_get(), CTX)['body'])
        self.assertEqual(body[0]['id'], 'P1')
        self.assertEqual(body[0]['price'], 75000.0)

    def test_get_empty_table(self):
        self.mock_table.scan.return_value = {'Items': []}
        body = json.loads(self.lm.lambda_handler(make_get(), CTX)['body'])
        self.assertEqual(body, [])

    def test_get_calls_scan_once(self):
        self.mock_table.scan.return_value = {'Items': []}
        self.lm.lambda_handler(make_get(), CTX)
        self.mock_table.scan.assert_called_once()

    def test_get_dynamodb_error_returns_500(self):
        self.mock_table.scan.side_effect = Exception("Table not found")
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertEqual(r['statusCode'], 500)

    def test_decimal_serialized_as_float(self):
        self.mock_table.scan.return_value = {'Items': [
            {'id':'P1','name':'Cam','price':Decimal('999.99'),'stock':3}
        ]}
        r = self.lm.lambda_handler(make_get(), CTX)
        body = json.loads(r['body'])
        self.assertEqual(body[0]['price'], 999.99)


class TestProductHeaders(unittest.TestCase):

    def setUp(self):
        patcher = patch('boto3.resource')
        self.mock_res = patcher.start()
        self.mock_table = MagicMock()
        self.mock_res.return_value.Table.return_value = self.mock_table
        self.addCleanup(patcher.stop)
        self.lm = get_module()

    def test_post_has_cors(self):
        self.mock_table.put_item.return_value = {}
        r = self.lm.lambda_handler(make_post({"id":"P1","name":"T","price":100,"stock":1}), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_get_has_cors(self):
        self.mock_table.scan.return_value = {'Items': []}
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_get_has_content_type(self):
        self.mock_table.scan.return_value = {'Items': []}
        r = self.lm.lambda_handler(make_get(), CTX)
        self.assertEqual(r['headers']['Content-Type'], 'application/json')


if __name__ == '__main__':
    unittest.main()