import argparse
import json
import os
import sys
import tempfile
import time
import traceback

import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

import pytz

# Load environment variables
load_dotenv(".env.local")

BART_API_BASE_URL = 'https://api.bart.gov/api/bsa.aspx'
BART_API_KEY = os.getenv('BART_API_KEY')

PACIFIC_TZ = pytz.timezone('US/Pacific')
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bart_state.json')
STATE_MAX_AGE = timedelta(hours=24)

DRY_RUN = False


def load_state():
    """Return the state dict, or None if the file does not exist yet.

    A corrupt file is treated as empty (we will re-bootstrap from the live
    BART response) rather than crashing every 5 minutes.
    """
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except FileNotFoundError:
        return None
    except (ValueError, OSError) as e:
        print(f"WARNING: could not read state file {STATE_FILE} ({e}); starting with empty state")
        return {'seen': {}}
    if not isinstance(state, dict) or not isinstance(state.get('seen'), dict):
        print(f"WARNING: state file {STATE_FILE} has unexpected shape; starting with empty state")
        return {'seen': {}}
    return state


def save_state(state):
    """Atomically write the state file: temp file in same dir, fsync, replace."""
    d = os.path.dirname(STATE_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=d, prefix='bart_state.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, STATE_FILE)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def get_description(advisory):
    """Return the advisory description as a plain string.

    BART sometimes returns {'#cdata-section': '...'} and sometimes a plain
    string; handle both (and any close variant) without raising.
    """
    desc = advisory.get('description') if isinstance(advisory, dict) else None
    if isinstance(desc, str):
        return desc
    if isinstance(desc, dict):
        val = desc.get('#cdata-section')
        if val is None:
            val = desc.get('cdata-section')
        if val is None:
            for v in desc.values():
                if isinstance(v, str):
                    val = v
                    break
        return val if isinstance(val, str) else ''
    return ''


def get_advisory_id(advisory):
    """Return the advisory's unique id (BART uses '@id'), or None."""
    if not isinstance(advisory, dict):
        return None
    aid = advisory.get('@id')
    if aid is None:
        aid = advisory.get('id')
    return aid if isinstance(aid, str) else None


def fetch_advisories():
    """Fetch and parse BART advisories.

    Returns a list of advisory dicts, or None on a definitive failure
    (4xx or exhausted retries). Never raises.
    """
    max_attempts = 4
    timeout_s = 4
    sleep_s = 2

    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(BART_API_BASE_URL, params={
                'cmd': 'bsa',
                'key': BART_API_KEY,
                'json': 'y'
            }, timeout=timeout_s)
            if 400 <= response.status_code < 500:
                print(f"HTTP {response.status_code} (client error) from BART; not retrying. "
                      f"Body snippet: {response.text[:200]!r}")
                return None
            response.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == max_attempts:
                print(f"Error fetching BART advisories after {max_attempts} attempts: {e}")
                return None
            print(f"Fetch attempt {attempt} failed ({e}). Retrying in {sleep_s}s...")
            time.sleep(sleep_s)

    try:
        data = response.json()
    except ValueError as e:
        print(f"ERROR: BART response is not valid JSON ({e}). Snippet: {response.text[:200]!r}")
        return None
    if not isinstance(data, dict):
        print(f"ERROR: unexpected BART response shape (not an object). Snippet: {response.text[:200]!r}")
        return None
    root = data.get('root')
    if not isinstance(root, dict):
        print(f"ERROR: BART response missing 'root' object. Snippet: {response.text[:200]!r}")
        return None
    advisories = root.get('bsa')
    if advisories is None:
        print("No 'bsa' key in BART response; treating as no advisories.")
        return []
    if isinstance(advisories, dict):
        advisories = [advisories]
    if not isinstance(advisories, list):
        print(f"ERROR: unexpected 'bsa' shape ({type(advisories).__name__}). Snippet: {response.text[:200]!r}")
        return None
    result = [a for a in advisories if isinstance(a, dict)]
    if len(result) != len(advisories):
        print(f"WARNING: skipped {len(advisories) - len(result)} malformed advisory entries")
    return result


def post_to_threads(advisory):
    """Post an advisory to Threads. Returns True only on full success.

    NOTE: uses Authorization: Bearer header for the Threads API (finding #3 applied).
    """
    THREADS_USER_ID = os.getenv('THREADS_USER_ID')
    THREADS_ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
    if not THREADS_USER_ID or not THREADS_ACCESS_TOKEN:
        print("ERROR: THREADS_USER_ID or THREADS_ACCESS_TOKEN not set; cannot post.")
        return False

    # Truncate advisory to 500 characters if it exceeds the limit
    if len(advisory) > 500:
        advisory = advisory[:497] + '...'

    THREADS_API_URL = (
        f"https://graph.threads.net/{THREADS_USER_ID}/threads"
        f"?text={requests.utils.quote(advisory)}&media_type=TEXT"
    )

    headers = {'Authorization': f'Bearer {THREADS_ACCESS_TOKEN}'}

    # Step 1: create the draft. If anything fails here, nothing was posted,
    # so it is safe for the next run to retry with a fresh draft.
    try:
        response = requests.post(THREADS_API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Failed to create draft: {e}")
        return False

    creation_id = data.get('id') if isinstance(data, dict) else None
    if not creation_id:
        print(f"ERROR: Threads creation response missing 'id': {response.text[:200]!r}")
        return False

    # Step 2: publish that draft.
    publish_url = (
        f"https://graph.threads.net/{THREADS_USER_ID}/threads_publish"
        f"?creation_id={creation_id}"
    )
    try:
        publish_response = requests.post(publish_url, headers=headers, timeout=15)
        publish_response.raise_for_status()
        print("Advisory posted successfully.")
        return True
    except requests.exceptions.HTTPError:
        # Server explicitly rejected the publish: it was NOT posted.
        print("Threads publish rejected by server; not posted.")
        return False
    except requests.RequestException as e:
        # Read timeout or other ambiguous outcome after the request was sent:
        # the server may have already published. Assume posted so the advisory
        # is marked seen and the next run does not re-fire the same advisory.
        print(f"Publish returned an ambiguous outcome ({e}); assuming posted "
              f"to avoid a duplicate re-post next run.")
        return True


def prune_seen(seen, now):
    """Drop seen entries older than STATE_MAX_AGE. Returns number pruned."""
    pruned = 0
    for aid in list(seen.keys()):
        ts = seen[aid]
        try:
            if isinstance(ts, str):
                stored = datetime.fromisoformat(ts)
                if stored.tzinfo is None:
                    stored = PACIFIC_TZ.localize(stored)
            else:
                continue
            if now - stored > STATE_MAX_AGE:
                del seen[aid]
                pruned += 1
        except (ValueError, TypeError):
            print(f"WARNING: unparseable timestamp for seen id {aid}; keeping it")
    return pruned


def main():
    global DRY_RUN
    ap = argparse.ArgumentParser(description="Fetch BART advisories and post new ones to Threads.")
    ap.add_argument('--dry-run', action='store_true',
                    help="Do everything except the Threads POST calls; do not record posts as seen")
    args = ap.parse_args()
    DRY_RUN = args.dry_run
    if DRY_RUN:
        print("=== DRY RUN: no posts to Threads will be made ===")

    now = datetime.now(PACIFIC_TZ)

    state = load_state()
    advisories = fetch_advisories()
    if advisories is None:
        print("Fetch/parse failed; skipping this run. State file unchanged.")
        return

    # First-run bootstrap: mark everything currently live as seen WITHOUT posting.
    if state is None:
        state = {'seen': {}}
        for a in advisories:
            aid = get_advisory_id(a)
            if aid:
                state['seen'][aid] = now.isoformat()
        save_state(state)
        print(f"BOOTSTRAP: state file did not exist; initialized with {len(state['seen'])} "
              f"current advisory ids (NOT posted): {sorted(state['seen'].keys())}")
        print("No advisories posted (bootstrap run).")
        return

    pruned = prune_seen(state['seen'], now)
    if pruned:
        print(f"Pruned {pruned} seen entries older than 24h.")

    seen = state['seen']
    to_post = []
    newly_seen = {}
    for a in advisories:
        aid = get_advisory_id(a)
        desc = get_description(a).strip()
        if not aid:
            print("WARNING: advisory without a usable @id; skipping it")
            continue
        if desc.lower() == 'no delays reported.':
            print("No delays reported.")
            newly_seen[aid] = now.isoformat()
            continue
        if aid in seen:
            print(f"Advisory {aid} already seen; skipping.")
            continue
        to_post.append((aid, desc, a.get('posted')))
        newly_seen[aid] = now.isoformat()

    if not to_post:
        print("Nothing new to post.")
        if not DRY_RUN and newly_seen:
            seen.update(newly_seen)
            save_state(state)
        return

    if DRY_RUN:
        for aid, desc, posted in to_post:
            print(f"[DRY-RUN] WOULD POST advisory {aid} (posted={posted}): {desc}")
        print(f"[DRY-RUN] {len(to_post)} advisory(ies) would be posted; no posts made, seen-set not updated for them.")
        return

    posted_ids = []
    for aid, desc, posted in to_post:
        print(f"Advisory: {desc}")
        print(f"Posted Time: {posted}")
        if post_to_threads(desc):
            posted_ids.append(aid)

    if posted_ids:
        for aid in posted_ids:
            seen[aid] = now.isoformat()
        if newly_seen:
            seen.update(newly_seen)
        save_state(state)
        print(f"State updated; now tracking {len(seen)} seen ids.")
    else:
        print("No advisories posted successfully; state file not updated (will retry next run).")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
