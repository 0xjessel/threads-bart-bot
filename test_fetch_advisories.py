import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.tz import gettz
import json
from fetch_and_post_bart_advisories import fetch_advisories 

class TestFetchAdvisories(unittest.TestCase):

    def setUp(self):
        self.pacific_tz = gettz("US/Pacific")

    @patch('fetch_and_post_bart_advisories.requests.get')  
    def test_fetch_advisories_within_five_minutes(self, mock_get):
        # Set the current time for testing
        current_time = datetime.now(self.pacific_tz)

        # Define the posted time for the advisory
        posted_time = (current_time - timedelta(minutes=3)).strftime("%a %b %d %Y %I:%M %p PDT")  # 3 minutes ago

        # Mock response for an advisory within 5 minutes
        mock_get.return_value.json.return_value = {
            'root': {
                'date': current_time.strftime("%m/%d/%Y"),  
                'time': current_time.strftime("%H:%M:%S %p PDT"),  
                'bsa': [{
                    'description': {'#cdata-section': 'Advisory within 5 minutes'},
                    'posted': posted_time  
                }]
            }
        }
        recent_advisories = fetch_advisories()
        # Expect one advisory since it's within 5 minutes
        self.assertEqual(len(recent_advisories), 1)
        self.assertEqual(recent_advisories[0][0], 'Advisory within 5 minutes')  

    @patch('fetch_and_post_bart_advisories.requests.get')  
    def test_fetch_advisories_greater_than_five_minutes(self, mock_get):
        # Set the current time for testing
        current_time = datetime.now(self.pacific_tz)

        # Define the posted time for the advisory
        posted_time = (current_time - timedelta(minutes=10)).strftime("%a %b %d %Y %I:%M %p PDT")  # 10 minutes ago

        # Mock response for an advisory greater than 5 minutes
        mock_get.return_value.json.return_value = {
            'root': {
                'date': current_time.strftime("%m/%d/%Y"), 
                'time': current_time.strftime("%H:%M:%S %p PDT"),  
                'bsa': [{
                    'description': {'#cdata-section': 'Advisory greater than 5 minutes'},
                    'posted': posted_time  
                }]
            }
        }
        recent_advisories = fetch_advisories()
        # Expect no advisories since it's greater than 5 minutes
        self.assertEqual(len(recent_advisories), 0)

    @patch('fetch_and_post_bart_advisories.requests.get')  
    def test_no_delays_reported(self, mock_get):
        # Mock response for "No delays reported"
        mock_get.return_value.json.return_value = {
            'root': {
                'date': "09/29/2024",
                'time': "17:07:01 PM PDT",
                'bsa': [{
                    'description': {'#cdata-section': "No delays reported."},
                    'sms_text': {'#cdata-section': "No delays reported."}
                }]
            }
        }
        
        recent_advisories = fetch_advisories()
        # Expect no advisories since the response indicates "No delays reported."
        self.assertEqual(len(recent_advisories), 0)

    @patch('fetch_and_post_bart_advisories.requests.get')  
    @patch('fetch_and_post_bart_advisories.datetime')
    def test_triple_advisories_from_json(self, mock_datetime, mock_get):
        # Load the JSON file
        with open('example-outputs/triple_advisory.json') as f:
            mock_response = json.load(f)

        # Mock the requests.get response
        mock_get.return_value.json.return_value = mock_response

        # Set the time to be 4 minutes after the most recent advisory
        mock_datetime.now.return_value = parser.parse("Wed Oct 02 2024 09:49 PM PDT", tzinfos={"PDT": self.pacific_tz, "PST": self.pacific_tz})
        

        # Call the fetch_advisories function
        recent_advisories = fetch_advisories()

        # Check the expected output
        expected_advisories = [
            (
                "There is a station closure at Lake Merritt. ",
                parser.parse("Wed Oct 02 2024 09:45 PM PDT", tzinfos={"PDT": self.pacific_tz, "PST": self.pacific_tz})
            ),
        ]

        # Check if the recent advisories match the expected advisories
        self.assertEqual(len(recent_advisories), len(expected_advisories))
        for advisory, expected in zip(recent_advisories, expected_advisories):
            self.assertEqual(advisory[0], expected[0])  # Check description
            self.assertEqual(advisory[1], expected[1])  # Check posted time

if __name__ == '__main__':
    unittest.main()