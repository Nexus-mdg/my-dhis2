#!/usr/bin/env python3
"""
Simple DHIS2 Notification Receiver
A minimal BottlePy server that receives notifications and displays them.
"""

import json
import os
from datetime import datetime
from bottle import Bottle, request, response, static_file, run

app = Bottle()

NOTIFICATIONS_FILE = 'notifications.json'
PORT = 8080
HOST = '0.0.0.0'


def load_notifications():
    """Load notifications from JSON file"""
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []


def save_notification(data):
    """Save new notification to JSON file"""
    notifications = load_notifications()
    notification = {
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    notifications.insert(0, notification)

    with open(NOTIFICATIONS_FILE, 'w') as f:
        json.dump(notifications, f, indent=2)

    return notification


@app.route('/api/dhis2/notify', method='POST')
def receive_notification():
    """Receive DHIS2 notification"""
    try:
        data = request.json
        if not data:
            response.status = 400
            return {'error': 'No data received'}

        save_notification(data)
        return {'success': True, 'message': 'Notification received'}

    except Exception as e:
        response.status = 500
        return {'error': str(e)}


@app.route('/')
def index():
    """Main page showing notifications"""
    notifications = load_notifications()

    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>DHIS2 Notifications</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c5aa0; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; }}
        .endpoint {{ background: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; font-family: monospace; }}
        .notification {{ background: white; border: 1px solid #ddd; border-radius: 8px; margin: 10px 0; padding: 15px; }}
        .notification-time {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
        .notification-data {{ background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }}
        .empty {{ text-align: center; color: #666; padding: 40px; }}
        .refresh {{ background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📨 DHIS2 Notifications</h1>
        <div class="endpoint">Endpoint: POST /api/dhis2/notify</div>
        <div>Total notifications: {len(notifications)}</div>
    </div>

    <button class="refresh" onclick="location.reload()">🔄 Refresh</button>

    <div id="notifications">
'''

    if not notifications:
        html += '<div class="empty">No notifications received yet</div>'
    else:
        for notification in notifications:
            time_str = datetime.fromisoformat(notification['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            data_str = json.dumps(notification['data'], indent=2)
            html += f'''
            <div class="notification">
                <div class="notification-time">⏰ {time_str}</div>
                <div class="notification-data">{data_str}</div>
            </div>
            '''

    html += '''
    </div>
</body>
</html>'''

    return html


if __name__ == '__main__':
    print(f"🚀 Starting DHIS2 Notification Receiver on port {PORT}")
    print(f"📨 DHIS2 Endpoint: http://0.0.0.0:{PORT}/api/dhis2/notify")
    print(f"🖥️  View notifications: http://0.0.0.0:{PORT}")
    run(app, host=HOST, port=PORT, debug=False)
