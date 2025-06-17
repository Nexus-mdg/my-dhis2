#!/usr/bin/env python3
"""
Simple DHIS2 Event Poller Microservice
Polls for completed events using Redis timestamp tracking
"""

import requests
import redis
import json
import os
import time
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
DHIS2_URL = os.getenv('DHIS2_URL', 'http://dhis2_dhis2:8080')
DHIS2_TOKEN = os.getenv('DHIS2_TOKEN')
NOTIFICATION_URL = os.getenv('NOTIFICATION_URL', 'http://dhis2_notifications_rcvr:8080')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '10'))
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_KEY = 'dhis2:last_event_timestamp'

# Redis connection
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)


def get_last_timestamp():
    """Get last processed event timestamp from Redis"""
    timestamp = r.get(REDIS_KEY)
    if not timestamp:
        # Default to 1 hour ago if no timestamp stored
        timestamp = datetime.now().replace(microsecond=0).isoformat()
    return timestamp


def save_last_timestamp(timestamp):
    """Save last processed event timestamp to Redis"""
    r.set(REDIS_KEY, timestamp)


def poll_events():
    """Poll DHIS2 for completed events since last timestamp"""
    last_timestamp = get_last_timestamp()

    headers = {'Authorization': f'ApiToken {DHIS2_TOKEN}'}
    params = {
        'status': 'COMPLETED',
        'lastUpdated': f'>{last_timestamp}',
        'fields': 'event,program,programStage,trackedEntityInstance,eventDate,orgUnit,completedDate',
        'pageSize': 50
    }

    try:
        response = requests.get(f'{DHIS2_URL}/api/events',
                                headers=headers, params=params, verify=False)
        response.raise_for_status()
        return response.json().get('events', [])
    except Exception as e:
        print(f"Error polling events: {e}")
        return []


def send_notification(event):
    """Send event to notification receiver"""
    payload = {
        'type': 'tracker_event_completed',
        'timestamp': datetime.now().isoformat(),
        'event': event
    }

    try:
        response = requests.post(f'{NOTIFICATION_URL}/api/dhis2/notify',
                                 json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


def process_events():
    """Main processing function"""
    events = poll_events()

    if not events:
        return

    print(f"Found {len(events)} new events")
    latest_timestamp = None

    for event in events:
        event_id = event.get('event')
        completed_date = event.get('completedDate')

        if send_notification(event):
            print(f"✅ Sent event {event_id}")
            # Track latest timestamp
            if completed_date and (not latest_timestamp or completed_date > latest_timestamp):
                latest_timestamp = completed_date
        else:
            print(f"❌ Failed to send event {event_id}")

    # Save latest timestamp to Redis
    if latest_timestamp:
        save_last_timestamp(latest_timestamp)
        print(f"📝 Updated timestamp: {latest_timestamp}")


def main():
    """Main loop"""
    if not DHIS2_TOKEN:
        print("❌ DHIS2_TOKEN required")
        return

    print(f"🚀 Starting poller (interval: {POLL_INTERVAL}s)")

    while True:
        try:
            process_events()
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("🛑 Stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
