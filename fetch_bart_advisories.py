import requests
import os
from dotenv import load_dotenv
from dateutil import parser
from datetime import datetime, timedelta
import pytz
import time  # Add this import at the top of the file

# Load environment variables
load_dotenv(".env.local")

BART_API_BASE_URL = 'https://api.bart.gov/api/bsa.aspx'
BART_API_KEY = os.getenv('BART_API_KEY')

def fetch_advisories():
    max_retries = 10 

    for attempt in range(max_retries):
        try:
            response = requests.get(BART_API_BASE_URL, params={
                'cmd': 'bsa',
                'key': BART_API_KEY,
                'json': 'y'
            }, timeout=4)  # 4 seconds timeout
            response.raise_for_status()
            break  # If successful, break out of the retry loop
        except requests.RequestException as e:
            if attempt == max_retries - 1:  # If it's the last attempt
                print(f"Error fetching BART advisories after {max_retries} attempts: {e}")
                return None
            
            print(f"Attempt {attempt + 1} failed. Retrying in 10 seconds...")
            time.sleep(10)
            continue

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

        if current_time - posted_time <= timedelta(minutes=5): # 5 minutes delta since cron job runs every 5 minutes
            description = advisory['description']['#cdata-section']
            recent_advisories.append(description)

    return recent_advisories

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