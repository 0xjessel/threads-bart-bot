import requests
import os
from dotenv import load_dotenv
from dateutil import parser
from datetime import datetime, timedelta
import pytz

# Load environment variables
load_dotenv()

BART_API_BASE_URL = 'https://api.bart.gov/api/bsa.aspx'
BART_API_KEY = os.getenv('BART_API_KEY')

def fetch_advisories():
    try:
        response = requests.get(BART_API_BASE_URL, params={
            'cmd': 'bsa',
            'key': BART_API_KEY,
            'json': 'y'
        }, timeout=10)
        response.raise_for_status()

        data = response.json()
        advisories = data['root']['bsa']
        
        pacific_tz = pytz.timezone('US/Pacific')
        current_time = datetime.now(pacific_tz)

        # Create tzinfos dynamically
        tzinfos = {
            "PDT": pacific_tz,
            "PST": pacific_tz
        }

        recent_advisories = []

        for advisory in advisories:
            # Parse the time with tzinfos
            posted_time = parser.parse(advisory['posted'], tzinfos=tzinfos)

            if current_time - posted_time <= timedelta(minutes=1):
                description = advisory['description']['#cdata-section']
                recent_advisories.append(description)

        return recent_advisories

    except requests.RequestException as e:
        # suppress error for now to test cron job
        # print(f"Error fetching BART advisories: {e}")
        return None

if __name__ == '__main__':
    recent_advisories = fetch_advisories()
    if recent_advisories:
        for advisory in recent_advisories:
            print(advisory)
    """
    hide for now to test cron job
    else:
        print("No recent advisories found.")
    """