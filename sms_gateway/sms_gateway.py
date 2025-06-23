#!/usr/bin/env python3
"""
DHIS2 SMS Gateway Service
Receives SMS messages through DHIS2's SMS gateway feature and processes them.
"""

import json
import os
import re
from datetime import datetime
from bottle import Bottle, request, response, static_file, run

app = Bottle()

SMS_LOG_FILE = 'sms_messages.json'
PORT = 8082
HOST = '0.0.0.0'


def load_sms_messages():
    """Load SMS messages from JSON file"""
    if not os.path.exists(SMS_LOG_FILE):
        return []
    try:
        with open(SMS_LOG_FILE, 'r') as f:
            return json.load(f)
    except:
        return []


def save_sms_message(data):
    """Save new SMS message to JSON file"""
    messages = load_sms_messages()
    message = {
        'timestamp': datetime.now().isoformat(),
        'data': data,
        'processed': False,
        'id': len(messages) + 1
    }
    messages.insert(0, message)

    # Keep only last 1000 messages
    messages = messages[:1000]

    with open(SMS_LOG_FILE, 'w') as f:
        json.dump(messages, f, indent=2)

    return message


def extract_sms_content(data):
    """Extract SMS content from various possible formats"""
    content = {}

    # Common SMS gateway fields
    fields_to_extract = [
        'text', 'message', 'body', 'content',
        'originator', 'sender', 'from', 'msisdn',
        'recipient', 'to', 'gateway_id', 'received_date'
    ]

    for field in fields_to_extract:
        if field in data:
            content[field] = data[field]

    # Try to extract from nested structures
    if 'sms' in data:
        content.update(extract_sms_content(data['sms']))

    return content


def process_dhis2_sms_commands(text, sender):
    """
    Process DHIS2 SMS commands - this is a basic example
    DHIS2 supports various SMS command formats for data entry
    """
    if not text:
        return {"status": "error", "message": "Empty SMS text"}

    text = text.strip().upper()

    # Example: Basic data set reporting format
    # Format: "DATASETCODE PERIOD ORGUNIT VALUE1 VALUE2..."
    # Example: "BCG 202312 OU123 45 23 12"

    parts = text.split()
    if len(parts) < 4:
        return {
            "status": "error",
            "message": "Invalid format. Expected: DATASETCODE PERIOD ORGUNIT VALUES..."
        }

    dataset_code = parts[0]
    period = parts[1]
    org_unit = parts[2]
    values = parts[3:]

    # Basic validation
    if not re.match(r'^\d{6}$', period):  # YYYYMM format
        return {
            "status": "error",
            "message": f"Invalid period format: {period}. Expected YYYYMM"
        }

    processed_data = {
        "dataset_code": dataset_code,
        "period": period,
        "org_unit": org_unit,
        "values": values,
        "sender": sender,
        "status": "parsed"
    }

    return {
        "status": "success",
        "message": f"Data received for {dataset_code} period {period}",
        "processed_data": processed_data
    }


@app.route('/api/sms/receive', method='POST')
def receive_sms():
    """Receive SMS from DHIS2 SMS gateway"""
    try:
        # Handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            data = request.json or {}
        else:
            data = dict(request.forms)

        if not data:
            response.status = 400
            return {'error': 'No data received'}

        # Extract SMS content
        sms_content = extract_sms_content(data)

        # Save the raw message
        saved_message = save_sms_message({
            'raw_data': data,
            'extracted_content': sms_content
        })

        # Process DHIS2 commands if text is available
        text = sms_content.get('text') or sms_content.get('message') or sms_content.get('body')
        sender = sms_content.get('originator') or sms_content.get('sender') or sms_content.get('from')

        processing_result = None
        if text:
            processing_result = process_dhis2_sms_commands(text, sender)

            # Update the saved message with processing result
            messages = load_sms_messages()
            for msg in messages:
                if msg.get('id') == saved_message['id']:
                    msg['processing_result'] = processing_result
                    msg['processed'] = True
                    break

            with open(SMS_LOG_FILE, 'w') as f:
                json.dump(messages, f, indent=2)

        return {
            'success': True,
            'message': 'SMS received and processed',
            'sms_id': saved_message['id'],
            'processing_result': processing_result
        }

    except Exception as e:
        response.status = 500
        return {'error': str(e)}


@app.route('/api/sms/status/<sms_id>')
def sms_status(sms_id):
    """Get status of a specific SMS"""
    try:
        messages = load_sms_messages()
        for msg in messages:
            if str(msg.get('id')) == str(sms_id):
                return {
                    'id': msg['id'],
                    'timestamp': msg['timestamp'],
                    'processed': msg.get('processed', False),
                    'processing_result': msg.get('processing_result'),
                    'content': msg['data'].get('extracted_content', {})
                }

        response.status = 404
        return {'error': 'SMS not found'}
    except Exception as e:
        response.status = 500
        return {'error': str(e)}


@app.route('/api/sms/messages')
def list_messages():
    """List all SMS messages (JSON API)"""
    try:
        messages = load_sms_messages()
        return {
            'total': len(messages),
            'messages': messages
        }
    except Exception as e:
        response.status = 500
        return {'error': str(e)}


@app.route('/')
def index():
    """Main page showing SMS messages"""
    messages = load_sms_messages()

    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>DHIS2 SMS Gateway</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c5aa0; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; }}
        .endpoint {{ background: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; font-family: monospace; }}
        .stats {{ display: flex; gap: 20px; margin: 10px 0; }}
        .stat {{ background: #f8f9fa; padding: 10px; border-radius: 5px; }}
        .message {{ background: white; border: 1px solid #ddd; border-radius: 8px; margin: 10px 0; padding: 15px; }}
        .message.processed {{ border-left: 4px solid #28a745; }}
        .message.error {{ border-left: 4px solid #dc3545; }}
        .message-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .message-time {{ color: #666; font-size: 14px; }}
        .message-id {{ background: #007bff; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
        .message-content {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0; }}
        .sms-text {{ font-weight: bold; color: #2c5aa0; }}
        .processing-result {{ background: #e9ecef; padding: 10px; border-radius: 5px; margin-top: 10px; }}
        .success {{ color: #28a745; }}
        .error {{ color: #dc3545; }}
        .empty {{ text-align: center; color: #666; padding: 40px; }}
        .refresh {{ background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-right: 10px; }}
        .clear {{ background: #dc3545; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        .json-toggle {{ background: #6c757d; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 12px; }}
        .json-data {{ display: none; background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; font-size: 12px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 DHIS2 SMS Gateway</h1>
        <div class="endpoint">SMS Endpoint: POST /api/sms/receive</div>
        <div class="endpoint">Status API: GET /api/sms/status/&lt;id&gt;</div>
        <div class="endpoint">Messages API: GET /api/sms/messages</div>

        <div class="stats">
            <div class="stat">Total Messages: {len(messages)}</div>
            <div class="stat">Processed: {len([m for m in messages if m.get('processed')])}</div>
            <div class="stat">Pending: {len([m for m in messages if not m.get('processed')])}</div>
        </div>
    </div>

    <div>
        <button class="refresh" onclick="location.reload()">🔄 Refresh</button>
        <button class="clear" onclick="clearMessages()">🗑️ Clear All</button>
    </div>

    <div id="messages">
'''

    if not messages:
        html += '<div class="empty">No SMS messages received yet</div>'
    else:
        for message in messages:
            time_str = datetime.fromisoformat(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            message_class = 'processed' if message.get('processed') else ''

            # Extract content for display
            content = message['data'].get('extracted_content', {})
            text = content.get('text') or content.get('message') or content.get('body', 'No text content')
            sender = content.get('originator') or content.get('sender') or content.get('from', 'Unknown')

            # Processing result
            result = message.get('processing_result', {})
            result_class = 'success' if result.get('status') == 'success' else 'error' if result.get(
                'status') == 'error' else ''

            html += f'''
            <div class="message {message_class}">
                <div class="message-header">
                    <div class="message-time">⏰ {time_str}</div>
                    <div class="message-id">ID: {message.get('id', 'N/A')}</div>
                </div>

                <div class="message-content">
                    <div><strong>From:</strong> {sender}</div>
                    <div class="sms-text"><strong>Text:</strong> {text}</div>
                </div>

                {f'<div class="processing-result {result_class}"><strong>Processing:</strong> {result.get("message", "No processing result")}</div>' if result else ''}

                <button class="json-toggle" onclick="toggleJson({message.get('id', 0)})">Show Raw Data</button>
                <div id="json-{message.get('id', 0)}" class="json-data">{json.dumps(message, indent=2)}</div>
            </div>
            '''

    html += '''
    </div>

    <script>
        function toggleJson(id) {
            const element = document.getElementById('json-' + id);
            const button = element.previousElementSibling;
            if (element.style.display === 'none' || element.style.display === '') {
                element.style.display = 'block';
                button.textContent = 'Hide Raw Data';
            } else {
                element.style.display = 'none';
                button.textContent = 'Show Raw Data';
            }
        }

        function clearMessages() {
            if (confirm('Are you sure you want to clear all SMS messages?')) {
                fetch('/api/sms/clear', {method: 'POST'})
                    .then(() => location.reload())
                    .catch(err => alert('Error clearing messages: ' + err));
            }
        }
    </script>
</body>
</html>'''

    return html


@app.route('/api/sms/clear', method='POST')
def clear_messages():
    """Clear all SMS messages"""
    try:
        with open(SMS_LOG_FILE, 'w') as f:
            json.dump([], f)
        return {'success': True, 'message': 'All messages cleared'}
    except Exception as e:
        response.status = 500
        return {'error': str(e)}


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'dhis2-sms-gateway', 'timestamp': datetime.now().isoformat()}


if __name__ == '__main__':
    print(f"🚀 Starting DHIS2 SMS Gateway Service on port {PORT}")
    print(f"📱 SMS Endpoint: http://0.0.0.0:{PORT}/api/sms/receive")
    print(f"🖥️  View messages: http://0.0.0.0:{PORT}")
    print(f"📊 Status API: http://0.0.0.0:{PORT}/api/sms/status/<id>")
    print(f"📋 Messages API: http://0.0.0.0:{PORT}/api/sms/messages")
    run(app, host=HOST, port=PORT, debug=False)
