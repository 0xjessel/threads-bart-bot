import requests
import os
from dotenv import load_dotenv
from dateutil import parser
from datetime import datetime, timedelta
import pytz
import time  
from dateutil.tz import gettz  
from urllib.parse import quote 

# Load environment variables
load_dotenv(".env.local")

BART_API_BASE_URL = 'https://api.bart.gov/api/bsa.aspx'
BART_API_KEY = os.getenv('BART_API_KEY')

def fetch_advisories():
    max_retries = 12 

    pacific_tz = pytz.timezone('US/Pacific')
    current_time = datetime.now(pacific_tz)

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
            
            print(f"Attempt {attempt + 1} failed. Retrying in 5 seconds...")
            time.sleep(5)
            continue

    data = response.json()
    root = data['root']
    advisories = root['bsa']

    recent_advisories = []

    # Check if there's only one advisory and it's "No delays reported"
    if isinstance(advisories, list) and len(advisories) == 1 and advisories[0]['description']['#cdata-section'].lower() == "no delays reported.":
        print("No delays reported.")
        return []  

    # If it's not a "No delays reported" case, proceed with processing advisories
    for advisory in advisories:
        description = advisory['description']['#cdata-section']
        # Use the posted time from the advisory
        posted_time_str = advisory['posted'] 

        tzinfos = {"PDT": gettz("US/Pacific"), "PST": gettz("US/Pacific")}
        # Parse the posted time string with timezone awareness
        posted_time = parser.parse(posted_time_str, tzinfos=tzinfos)
        print(f"advisory posted time: {posted_time}")

        # Check if the advisory was posted within the last 5 minutes (with 5-second jitter)
        if posted_time >= current_time - timedelta(minutes=5, seconds=5):
            # Append a tuple of (description, posted_time) to recent_advisories
            print("adding advisory to post")
            recent_advisories.append((description, posted_time))
        else:
            print("advisory was older than 5 minutes, discarding")

    return recent_advisories

def post_to_threads(advisory):
    """
    Function to post advisory to Threads 
    """
    THREADS_USER_ID = os.getenv('THREADS_USER_ID')
    THREADS_ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
    
    # Truncate advisory to 500 characters if it exceeds the limit
    if len(advisory) > 500:
        advisory = advisory[:497] + '...'  
    
    # Construct the API URL with the user ID, advisory text (encoded inline), access token, and media_type
    THREADS_API_URL = f"https://graph.threads.net/{THREADS_USER_ID}/threads?text={quote(advisory)}&access_token={THREADS_ACCESS_TOKEN}&media_type=TEXT"
    
    try:
        response = requests.post(THREADS_API_URL)
        response.raise_for_status()
        
        # Step 1: Parse the JSON response to get creation_id
        data = response.json()
        creation_id = data.get('id')  # Assuming the response contains an 'id' field
        
        # Step 2: Use creation_id to POST to the publish endpoint
        publish_url = f"https://graph.threads.net/{THREADS_USER_ID}/threads_publish?creation_id={creation_id}&access_token={THREADS_ACCESS_TOKEN}"
        publish_response = requests.post(publish_url)
        publish_response.raise_for_status()  # Check for errors in the publish request
        
        print("Advisory posted successfully.")
    except requests.RequestException as e:
        print(f"Failed to post advisory: {e}")

if __name__ == '__main__':
    recent_advisories = fetch_advisories()
    if recent_advisories:
        for advisory, posted_time in recent_advisories:
            print(f"Advisory: {advisory}")
            print(f"Posted Time: {posted_time}")
            post_to_threads(advisory)  
    else:
        print("No advisories found within the last 5 minutes.")