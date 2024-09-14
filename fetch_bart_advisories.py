import requests
import os
from dotenv import load_dotenv
from dateutil import parser
from datetime import datetime, timedelta
import pytz
import time  # Add this import at the top of the file
from dateutil.tz import gettz  # Add this import at the top of the file

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
    root = data['root']
    advisories = root['bsa']
    
    pacific_tz = pytz.timezone('US/Pacific')
    current_time = datetime.now(pacific_tz)

    # Create tzinfos dictionary
    tzinfos = {"PDT": gettz("US/Pacific"), "PST": gettz("US/Pacific")}

    recent_advisories = []

    # Check if there's only one advisory and it's "No delays reported"
    if isinstance(advisories, list) and len(advisories) == 1 and advisories[0]['description']['#cdata-section'].lower() == "no delays reported.":
        return []

    # If it's not a "No delays reported" case, proceed with processing advisories
    for advisory in advisories:
        description = advisory['description']['#cdata-section']
        # Use the root date and time as the posted time
        posted_time_str = f"{root['date']} {root['time']}"
        posted_time = parser.parse(posted_time_str, tzinfos=tzinfos)
        posted_time = posted_time.astimezone(pacific_tz)

        time_difference = current_time - posted_time
        if time_difference <= timedelta(minutes=5):
            recent_advisories.append(description)

    return recent_advisories

if __name__ == '__main__':
    recent_advisories = fetch_advisories()
    if recent_advisories:
        for advisory in recent_advisories:
            print(advisory)
    """
    suppress while testing
    else:
        print("No advisories found.")
    """