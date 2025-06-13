#!/usr/bin/env python3
"""
DHIS2 Admin Password Changer
Changes the default admin user password to a UUID-based password
"""

import requests
import uuid
import json
import urllib3
import os
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DHIS2PasswordChanger:
    def __init__(self, base_url, username="admin", password="district"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # Ignore self-signed certificates
        self.session.auth = HTTPBasicAuth(username, password)

    def generate_new_password(self):
        """Generate a new password from the first part of a UUID4"""
        new_uuid = str(uuid.uuid4())
        password_part = new_uuid.split('-')[0]
        return new_uuid, password_part

    def get_admin_user(self):
        """Get the admin user details"""
        try:
            url = f"{self.base_url}/api/users"
            params = {
                'filter': f'userCredentials.username:eq:{self.username}',
                'fields': 'id,userCredentials[username,id]'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()

            users = response.json().get('users', [])
            if not users:
                raise Exception(f"User '{self.username}' not found")

            return users[0]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get user details: {e}")

    def update_password(self, user_id, new_password):
        """Update the user's password"""
        try:
            url = f"{self.base_url}/api/users/{user_id}"

            # First get the full user object
            response = self.session.get(url)
            response.raise_for_status()
            user_data = response.json()

            # Update the password in userCredentials
            user_data['userCredentials']['password'] = new_password

            # Send the update
            response = self.session.put(url, json=user_data)
            response.raise_for_status()

            return True

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to update password: {e}")

    def verify_new_credentials(self, new_password):
        """Verify the new password works"""
        try:
            test_session = requests.Session()
            test_session.verify = False
            test_session.auth = HTTPBasicAuth(self.username, new_password)

            url = f"{self.base_url}/api/me"
            response = test_session.get(url)
            response.raise_for_status()

            return True

        except requests.exceptions.RequestException:
            return False

    def change_password(self):
        """Main method to change the password"""
        try:
            print("[DHIS2] Connecting to DHIS2 at:", self.base_url)
            print("[DHIS2] Using current credentials:", f"{self.username} / {self.password}")

            # Get admin user details
            print("[DHIS2] Getting admin user details...")
            admin_user = self.get_admin_user()
            user_id = admin_user['id']
            print("[DHIS2] Found user ID:", user_id)

            # Generate new password
            full_uuid, new_password = self.generate_new_password()
            print("[DHIS2] Generated UUID:", full_uuid)
            print("[DHIS2] New password:", new_password)

            # Update password
            print("[DHIS2] Updating password...")
            self.update_password(user_id, new_password)

            # Verify new credentials
            print("[DHIS2] Verifying new credentials...")
            if self.verify_new_credentials(new_password):
                print("[DHIS2] ✅ Password changed successfully!")
                return {
                    'success': True,
                    'username': self.username,
                    'new_password': new_password,
                    'full_uuid': full_uuid
                }
            else:
                print("[DHIS2] ❌ Password update failed - verification unsuccessful")
                return {'success': False, 'error': 'Verification failed'}

        except Exception as e:
            print(f"[DHIS2] ❌ Error: {e}")
            return {'success': False, 'error': str(e)}


def write_credentials_file(result, dhis2_url):
    """Write credentials to a file in /app for easy access"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/app/dhis2_credentials_{timestamp}.txt"

    try:
        with open(filename, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("🎉 DHIS2 ADMIN PASSWORD CHANGED SUCCESSFULLY\n")
            f.write("=" * 80 + "\n\n")

            f.write("📋 COPY THESE CREDENTIALS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Username: {result['username']}\n")
            f.write(f"Password: {result['new_password']}\n")
            f.write("-" * 40 + "\n\n")

            f.write("🔗 LOGIN URL:\n")
            f.write(f"{dhis2_url}/dhis-web-commons/security/login.action\n\n")

            f.write("🆔 FULL UUID REFERENCE:\n")
            f.write(f"{result['full_uuid']}\n\n")

            f.write("=" * 80 + "\n")
            f.write("⚠️  IMPORTANT: Save these credentials in a secure location!\n")
            f.write("=" * 80 + "\n\n")

            f.write("📋 QUICK COPY-PASTE SECTION:\n")
            f.write("┌" + "─" * 50 + "┐\n")
            f.write(f"│ Username: {result['username']:<37} │\n")
            f.write(f"│ Password: {result['new_password']:<37} │\n")
            f.write("└" + "─" * 50 + "┘\n\n")

            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DHIS2 URL: {dhis2_url}\n")

        # Set file permissions to be readable only by owner
        os.chmod(filename, 0o600)
        return filename

    except Exception as e:
        print(f"[DHIS2] ❌ Failed to write credentials file: {e}")
        return None


def main():
    # Get DHIS2 URL from environment variable
    DHIS2_URL = os.getenv('DHIS2_URL')

    if not DHIS2_URL:
        print("[DHIS2] ❌ DHIS2_URL environment variable is required")
        print("[DHIS2] Set it with: export DHIS2_URL=https://your-dhis2-server.com")
        return

    print(f"[DHIS2] Using DHIS2 URL from environment: {DHIS2_URL}")

    # Optional: customize credentials from environment or use defaults
    username = os.getenv('DHIS2_USERNAME', 'admin')
    password = os.getenv('DHIS2_PASSWORD', 'district')

    print(f"[DHIS2] Using credentials: {username} / {'*' * len(password)}")

    # Create password changer and execute
    changer = DHIS2PasswordChanger(DHIS2_URL, username, password)
    result = changer.change_password()

    if result['success']:
        # Write credentials to file
        credentials_file = write_credentials_file(result, DHIS2_URL)

        if credentials_file:
            print()
            print("=" * 80)
            print("🎉 DHIS2 ADMIN PASSWORD CHANGED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("📁 CREDENTIALS SAVED TO FILE:")
            print(f"   {credentials_file}")
            print()
            print("📋 QUICK ACCESS:")
            print(f"   cat {credentials_file}")
            print()
            print("🔑 LOGIN DETAILS:")
            print(f"   Username: {result['username']}")
            print(f"   Password: {result['new_password']}")
            print(f"   URL: {DHIS2_URL}/dhis-web-commons/security/login.action")
            print()
            print("=" * 80)
            print("⚠️  Credentials file is readable only by owner (chmod 600)")
            print("=" * 80)
        else:
            # Fallback to console output if file writing fails
            print()
            print("=" * 80)
            print("🎉 DHIS2 ADMIN PASSWORD CHANGED SUCCESSFULLY")
            print("=" * 80)
            print(f"Username: {result['username']}")
            print(f"Password: {result['new_password']}")
            print(f"URL: {DHIS2_URL}/dhis-web-commons/security/login.action")
            print("=" * 80)

    else:
        print(f"[DHIS2] ❌ Failed to change password: {result['error']}")


def run_entrypoint():
    """Entry point function for container usage"""
    print()
    print("🚀 DHIS2 Password Changer - Container Entry Point")
    print("=" * 60)
    main()


if __name__ == "__main__":
    main()
