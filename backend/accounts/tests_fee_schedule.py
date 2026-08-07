
from django.test import TestCase
from rest_framework.test import APIClient


class PublicFeeScheduleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_fee_schedule_returns_calculator(self):
        response = self.client.get(
            "/api/accounts/fee-schedule/",
            {"plan": "studio", "support_gmv": "1000", "tips_gmv": "100", "marketplace_gmv": "500"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["schedule"]["plan"], "studio")
        self.assertEqual(response.data["calculator"]["you_keep_total"], "1490.00")
        self.assertIn("free", response.data["plans"])
