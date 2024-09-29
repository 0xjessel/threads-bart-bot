import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.tz import gettz
from fetch_and_post_bart_advisories import fetch_advisories 

class TestFetchAdvisories(unittest.TestCase):

    def setUp(self):
        self.pacific_tz = gettz("US/Pacific")

    @patch('fetch_and_post_bart_advisories.requests.get')  
    def test_fetch_advisories_with_valid_dates(self, mock_get):
        mock_get.return_value.json.return_value = {
            'root': {
                'date': "09/29/2024",
                'time': "14:32:01 PM PDT",
                'bsa': [{'description': {'#cdata-section': 'Test advisory 1'}}]
            }
        }
        recent_advisories = fetch_advisories()
        # base case check, string parsing works with PM string
        self.assertEqual(len(recent_advisories), 0)

        mock_get.return_value.json.return_value = {
            'root': {
                'date': "09/29/2024",
                'time': "04:32:01 AM PDT",
                'bsa': [{'description': {'#cdata-section': 'Test advisory 2'}}]
            }
        }
        recent_advisories = fetch_advisories()
        # base case check, string parsing works with AM string
        self.assertEqual(len(recent_advisories), 0)

    @patch('fetch_and_post_bart_advisories.requests.get')  
    def test_fetch_advisories_within_five_minutes(self, mock_get):
        # Set the current time for testing
        current_time = datetime.now(self.pacific_tz)

        # Mock response for an advisory within 5 minutes
        mock_get.return_value.json.return_value = {
            'root': {
                'date': current_time.strftime("%m/%d/%Y"),  # Today's date
                'time': (current_time - timedelta(minutes=3)).strftime("%H:%M:%S %p PDT"),  # 3 minutes ago
                'bsa': [{'description': {'#cdata-section': 'Advisory within 5 minutes'}}]
            }
        }
        recent_advisories = fetch_advisories()
        # Expect one advisory since it's within 5 minutes
        self.assertEqual(len(recent_advisories), 1)
        self.assertEqual(recent_advisories[0], 'Advisory within 5 minutes')

    @patch('fetch_and_post_bart_advisories.requests.get')  
    def test_fetch_advisories_greater_than_five_minutes(self, mock_get):
        # Set the current time for testing
        current_time = datetime.now(self.pacific_tz)

        # Mock response for an advisory greater than 5 minutes
        mock_get.return_value.json.return_value = {
            'root': {
                'date': current_time.strftime("%m/%d/%Y"),  # Today's date
                'time': (current_time - timedelta(minutes=10)).strftime("%H:%M:%S %p PDT"),  # 10 minutes ago 
                'bsa': [{'description': {'#cdata-section': 'Advisory greater than 5 minutes'}}]
            }
        }
        recent_advisories = fetch_advisories()
        # Expect no advisories since it's greater than 5 minutes
        self.assertEqual(len(recent_advisories), 0)

if __name__ == '__main__':
    unittest.main()