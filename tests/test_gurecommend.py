import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal

_STUBS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stubs'))
_SRC   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'gurecommend'))

os.environ['TABLE_NAME'] = 'gurecommend-table'


def get_module():
    # Remove every OTHER lambda folder so only gurecommend is on the path
    to_remove = [p for p in sys.path if
                 ('guproduct' in p or 'gucart' in p or 'gulogu' in p)
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


def _post(body): return {"httpMethod": "POST", "body": json.dumps(body)}
def _get():      return {"httpMethod": "GET"}
def _opts():     return {"httpMethod": "OPTIONS"}
CTX = MagicMock()

# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendOPTIONS(unittest.TestCase):
    def setUp(self):
        self.p = patch('boto3.resource'); mr = self.p.start()
        self.mt = MagicMock(); mr.return_value.Table.return_value = self.mt
        self.addCleanup(self.p.stop); self.lm = get_module()

    def test_options_200(self):
        self.assertEqual(self.lm.lambda_handler(_opts(), CTX)['statusCode'], 200)

    def test_options_cors(self):
        self.assertEqual(self.lm.lambda_handler(_opts(), CTX)['headers']['Access-Control-Allow-Origin'], '*')

    def test_options_body_ok(self):
        self.assertEqual(self.lm.lambda_handler(_opts(), CTX)['body'], 'OK')


class TestGetRecommendationsLogic(unittest.TestCase):
    """Pure logic — no DynamoDB."""
    def setUp(self):
        self.p = patch('boto3.resource'); mr = self.p.start()
        self.mt = MagicMock(); mr.return_value.Table.return_value = self.mt
        self.addCleanup(self.p.stop); self.lm = get_module()

    def test_laptop_returns_mouse(self):
        self.assertIn("Mouse", self.lm.get_recommendations("Laptop Pro X"))

    def test_laptop_returns_keyboard(self):
        self.assertIn("Keyboard", self.lm.get_recommendations("Laptop Pro X"))

    def test_laptop_case_insensitive(self):
        self.assertIn("Mouse", self.lm.get_recommendations("LAPTOP"))

    def test_mouse_returns_mousepad(self):
        self.assertIn("Mouse Pad", self.lm.get_recommendations("Gaming Mouse"))

    def test_keyboard_returns_wrist_rest(self):
        self.assertIn("Wrist Rest", self.lm.get_recommendations("Mechanical Keyboard"))

    def test_phone_returns_phone_case(self):
        self.assertIn("Phone Case", self.lm.get_recommendations("iPhone 15"))

    def test_phone_returns_power_bank(self):
        self.assertIn("Power Bank", self.lm.get_recommendations("Samsung Phone"))

    def test_earbuds_returns_charging_cable(self):
        self.assertIn("Charging Cable", self.lm.get_recommendations("Wireless Earbuds"))

    def test_headphones_matched_via_phone_keyword(self):
        # 'phone' is in 'headphones' so phone recs are returned — this is real lambda behaviour
        recs = self.lm.get_recommendations("Sony Headphones")
        self.assertEqual(recs, self.lm.RELATED["phone"])

    def test_monitor_returns_hdmi(self):
        self.assertIn("HDMI Cable", self.lm.get_recommendations("4K Monitor"))

    def test_tablet_returns_stylus(self):
        self.assertIn("Stylus", self.lm.get_recommendations("iPad Tablet"))

    def test_charger_returns_power_bank(self):
        self.assertIn("Power Bank", self.lm.get_recommendations("Fast Charger"))

    def test_camera_returns_memory_card(self):
        self.assertIn("Memory Card", self.lm.get_recommendations("DSLR Camera"))

    def test_camera_returns_tripod(self):
        self.assertIn("Tripod", self.lm.get_recommendations("DSLR Camera"))

    def test_unknown_product_returns_default(self):
        self.assertEqual(self.lm.get_recommendations("Unknown Gadget XYZ"), self.lm.RELATED["default"])

    def test_unknown_returns_power_bank(self):
        self.assertIn("Power Bank", self.lm.get_recommendations("Random Product"))

    def test_empty_string_returns_default(self):
        self.assertEqual(self.lm.get_recommendations(""), self.lm.RELATED["default"])

    def test_returns_list_type(self):
        self.assertIsInstance(self.lm.get_recommendations("Laptop"), list)

    def test_recommendations_not_empty(self):
        self.assertGreater(len(self.lm.get_recommendations("Laptop")), 0)

    def test_default_keyword_not_matched_as_product(self):
        self.assertEqual(self.lm.get_recommendations("default product"), self.lm.RELATED["default"])


class TestRecommendPOST(unittest.TestCase):
    def setUp(self):
        self.p = patch('boto3.resource'); mr = self.p.start()
        self.mt = MagicMock(); mr.return_value.Table.return_value = self.mt
        self.addCleanup(self.p.stop)
        self.mt.put_item.return_value = {}
        self.lm = get_module()

    def test_laptop_returns_200(self):
        self.assertEqual(self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)['statusCode'], 200)

    def test_product_echoed_in_body(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop Pro"}), CTX)
        self.assertEqual(json.loads(r['body'])['product'], 'Laptop Pro')

    def test_recommendations_key_in_body(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertIn('recommendations', json.loads(r['body']))

    def test_recommendations_is_list(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertIsInstance(json.loads(r['body'])['recommendations'], list)

    def test_recommendations_not_empty(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertGreater(len(json.loads(r['body'])['recommendations']), 0)

    def test_laptop_recs_has_mouse(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertIn("Mouse", json.loads(r['body'])['recommendations'])

    def test_laptop_recs_has_keyboard(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertIn("Keyboard", json.loads(r['body'])['recommendations'])

    def test_phone_recs_has_phone_case(self):
        r = self.lm.lambda_handler(_post({"product":"Phone"}), CTX)
        self.assertIn("Phone Case", json.loads(r['body'])['recommendations'])

    def test_unknown_returns_default_recs(self):
        r = self.lm.lambda_handler(_post({"product":"Unknown XYZ"}), CTX)
        self.assertEqual(json.loads(r['body'])['recommendations'], self.lm.RELATED["default"])

    def test_saves_record_to_dynamodb(self):
        self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.mt.put_item.assert_called_once()

    def test_saved_record_has_uuid_id(self):
        self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        saved = self.mt.put_item.call_args[1]['Item']
        self.assertIn('id', saved)
        self.assertEqual(len(saved['id']), 36)

    def test_saved_record_has_product_name(self):
        self.lm.lambda_handler(_post({"product":"Gaming Mouse"}), CTX)
        self.assertEqual(self.mt.put_item.call_args[1]['Item']['product'], 'Gaming Mouse')

    def test_saved_record_has_recommendations(self):
        self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        saved = self.mt.put_item.call_args[1]['Item']
        self.assertIsInstance(saved['recommendations'], list)

    def test_empty_product_uses_default(self):
        r = self.lm.lambda_handler(_post({"product":""}), CTX)
        self.assertEqual(json.loads(r['body'])['recommendations'], self.lm.RELATED["default"])

    def test_missing_product_key_uses_default(self):
        r = self.lm.lambda_handler(_post({}), CTX)
        self.assertEqual(json.loads(r['body'])['recommendations'], self.lm.RELATED["default"])

    def test_none_body_returns_200(self):
        r = self.lm.lambda_handler({"httpMethod":"POST","body":None}, CTX)
        self.assertEqual(r['statusCode'], 200)

    def test_dynamodb_error_returns_500(self):
        self.mt.put_item.side_effect = Exception("DB error")
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertEqual(r['statusCode'], 500)

    def test_dynamodb_error_has_error_key(self):
        self.mt.put_item.side_effect = Exception("DB error")
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertIn('error', json.loads(r['body']))

    def test_five_calls_generate_five_unique_ids(self):
        ids = set()
        for _ in range(5):
            self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
            ids.add(self.mt.put_item.call_args[1]['Item']['id'])
        self.assertEqual(len(ids), 5)


class TestRecommendGET(unittest.TestCase):
    def setUp(self):
        self.p = patch('boto3.resource'); mr = self.p.start()
        self.mt = MagicMock(); mr.return_value.Table.return_value = self.mt
        self.addCleanup(self.p.stop); self.lm = get_module()

    def test_get_200(self):
        self.mt.scan.return_value = {'Items': []}
        self.assertEqual(self.lm.lambda_handler(_get(), CTX)['statusCode'], 200)

    def test_get_returns_list(self):
        self.mt.scan.return_value = {'Items': []}
        self.assertIsInstance(json.loads(self.lm.lambda_handler(_get(), CTX)['body']), list)

    def test_get_returns_two_records(self):
        self.mt.scan.return_value = {'Items': [
            {'id':'u1','product':'Laptop', 'recommendations':['Mouse']},
            {'id':'u2','product':'Monitor','recommendations':['HDMI Cable']},
        ]}
        self.assertEqual(len(json.loads(self.lm.lambda_handler(_get(), CTX)['body'])), 2)

    def test_get_correct_product_field(self):
        self.mt.scan.return_value = {'Items': [
            {'id':'u1','product':'Camera','recommendations':['Tripod']}
        ]}
        body = json.loads(self.lm.lambda_handler(_get(), CTX)['body'])
        self.assertEqual(body[0]['product'], 'Camera')

    def test_get_empty_table(self):
        self.mt.scan.return_value = {'Items': []}
        self.assertEqual(json.loads(self.lm.lambda_handler(_get(), CTX)['body']), [])

    def test_get_calls_scan_once(self):
        self.mt.scan.return_value = {'Items': []}
        self.lm.lambda_handler(_get(), CTX)
        self.mt.scan.assert_called_once()

    def test_get_dynamodb_error_500(self):
        self.mt.scan.side_effect = Exception("Scan error")
        self.assertEqual(self.lm.lambda_handler(_get(), CTX)['statusCode'], 500)


class TestRecommendHeaders(unittest.TestCase):
    def setUp(self):
        self.p = patch('boto3.resource'); mr = self.p.start()
        self.mt = MagicMock(); mr.return_value.Table.return_value = self.mt
        self.addCleanup(self.p.stop)
        self.mt.put_item.return_value = {}
        self.mt.scan.return_value = {'Items': []}
        self.lm = get_module()

    def test_post_has_cors(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_get_has_cors(self):
        r = self.lm.lambda_handler(_get(), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_error_has_cors(self):
        self.mt.scan.side_effect = Exception("Err")
        r = self.lm.lambda_handler(_get(), CTX)
        self.assertIn('Access-Control-Allow-Origin', r['headers'])

    def test_post_content_type(self):
        r = self.lm.lambda_handler(_post({"product":"Laptop"}), CTX)
        self.assertEqual(r['headers']['Content-Type'], 'application/json')


if __name__ == '__main__':
    unittest.main(verbosity=2)