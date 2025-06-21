#!/usr/bin/env python3
"""
DHIS2 Root User Creator
Creates a new 'root' user with UUID-based password
"""

import requests
import uuid
import json
import urllib3
import os
from datetime import datetime
from requests.auth import HTTPBasicAuth
import base64

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DHIS2RootUserCreator:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # Ignore self-signed certificates
        self.session.auth = HTTPBasicAuth(username, password)

    def generate_new_password(self):
        """Generate a new password from the first part of a UUID4 with all requirements"""
        new_uuid = str(uuid.uuid4())
        password_part = new_uuid.split('-')[0]
        # Ensure we have uppercase, lowercase, number, and special character
        # Take first 6 chars, make some uppercase, add requirements
        base = password_part[:6]
        password_with_requirements = base.upper()[:2] + base.lower()[2:4] + "1@RND" + base.upper()[4:6]
        return new_uuid, password_with_requirements

    def check_root_user_exists(self):
        """Check if root user already exists"""
        try:
            url = f"{self.base_url}/api/users"
            params = {
                'filter': 'userCredentials.username:eq:root',
                'fields': 'id,userCredentials[username,id]'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()

            users = response.json().get('users', [])
            return users[0] if users else None

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to check root user: {e}")

    def get_admin_user_for_template(self):
        """Get the admin user details to use as template"""
        try:
            url = f"{self.base_url}/api/users"
            params = {
                'filter': f'userCredentials.username:eq:{self.username}',
                'fields': '*'
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()

            users = response.json().get('users', [])
            if not users:
                raise Exception(f"User '{self.username}' not found")

            return users[0]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get admin user details: {e}")

    def create_root_user(self, new_password):
        """Create a new root user with admin privileges"""
        try:
            # Get admin user as template
            admin_user = self.get_admin_user_for_template()

            # Generate proper DHIS2 UIDs (11 characters, must start with letter)
            root_user_id = 'R' + str(uuid.uuid4()).replace('-', '')[:10]  # Start with 'R'
            root_cred_id = 'C' + str(uuid.uuid4()).replace('-', '')[:10]  # Start with 'C'

            # Create root user payload based on admin user
            root_user = {
                "id": root_user_id,
                "firstName": "Root",
                "surname": "Administrator",
                "email": "root@example.com",  # Simple valid email
                "userCredentials": {
                    "id": root_cred_id,
                    "username": "root",
                    "password": new_password,
                    "disabled": False,
                    "accountNonExpired": True,
                    "credentialsNonExpired": True,
                    "accountNonLocked": True,
                    "twoFA": False,
                    "externalAuth": False,
                    "openId": "",
                    "ldapId": "",
                    "userRoles": admin_user.get('userCredentials', {}).get('userRoles', [])
                },
                "organisationUnits": admin_user.get('organisationUnits', []),
                "dataViewOrganisationUnits": admin_user.get('dataViewOrganisationUnits', []),
                "teiSearchOrganisationUnits": admin_user.get('teiSearchOrganisationUnits', []),
                "userGroups": admin_user.get('userGroups', [])
            }

            # Create the user
            url = f"{self.base_url}/api/users"
            response = self.session.post(url, json=root_user)
            response.raise_for_status()

            print(f"[DHIS2] Root user created successfully with ID: {root_user_id}")
            return root_user_id

        except requests.exceptions.RequestException as e:
            # Print more detailed error info
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = f" - Response: {e.response.text}"
            except:
                pass
            raise Exception(f"Failed to create root user: {e}{error_detail}")

    def update_root_password(self, user_id, new_password):
        """Update root user's password if it already exists"""
        try:
            # Try the simpler userCredentials update approach for existing users
            url = f"{self.base_url}/api/userCredentials"

            # Get user credentials
            response = self.session.get(f"{url}?filter=username:eq:root&fields=*")
            response.raise_for_status()

            user_creds = response.json().get('userCredentials', [])
            if not user_creds:
                raise Exception("Root user credentials not found")

            user_cred = user_creds[0]
            user_cred_id = user_cred['id']

            # Update password
            user_cred['password'] = new_password

            response = self.session.put(f"{url}/{user_cred_id}", json=user_cred)
            response.raise_for_status()

            print(f"[DHIS2] Root user password updated successfully")
            return True

        except requests.exceptions.RequestException as e:
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = f" - Response: {e.response.text}"
            except:
                pass
            raise Exception(f"Failed to update root password: {e}{error_detail}")

    def verify_root_credentials(self, new_password):
        """Verify the new root credentials work"""
        try:
            test_session = requests.Session()
            test_session.verify = False
            test_session.auth = HTTPBasicAuth("root", new_password)

            url = f"{self.base_url}/api/me"
            response = test_session.get(url)
            response.raise_for_status()

            # Store the password for later use in disable_admin_user
            self.current_root_password = new_password
            return True

        except requests.exceptions.RequestException:
            return False

    def disable_admin_user(self):
        """Disable the original admin user for security"""
        try:
            # Get the admin user ID
            admin_user = self.get_admin_user_for_template()
            admin_user_id = admin_user['id']

            print(f"[DHIS2] Disabling admin user with ID: {admin_user_id}")

            # Use PATCH request to disable the user (same as browser network trace)
            url = f"{self.base_url}/api/users/{admin_user_id}"
            patch_data = [{
                "op": "replace",
                "path": "/disabled",
                "value": True
            }]

            # Create a new session with root credentials for this operation
            root_session = requests.Session()
            root_session.verify = False
            root_session.auth = HTTPBasicAuth("root", self.current_root_password)

            # Set proper content type for PATCH request
            headers = {
                'Content-Type': 'application/json-patch+json'
            }

            response = root_session.patch(url, json=patch_data, headers=headers)
            response.raise_for_status()

            print(f"[DHIS2] ✅ Admin user disabled successfully")
            return True

        except requests.exceptions.RequestException as e:
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = f" - Response: {e.response.text}"
            except:
                pass
            print(f"[DHIS2] ⚠️  Failed to disable admin user: {e}{error_detail}")
            return False
        """Verify the new root credentials work"""
        try:
            test_session = requests.Session()
            test_session.verify = False
            test_session.auth = HTTPBasicAuth("root", new_password)

            url = f"{self.base_url}/api/me"
            response = test_session.get(url)
            response.raise_for_status()

            return True

        except requests.exceptions.RequestException:
            return False

    def setup_root_user(self):
        """Main method to create/update root user"""
        try:
            print("[DHIS2] Connecting to DHIS2 at:", self.base_url)
            print("[DHIS2] Using current credentials:", f"{self.username} / {'*' * len(self.password)}")

            # Test connection first
            print("[DHIS2] Testing connection...")
            test_response = self.session.get(f"{self.base_url}/api/me")
            test_response.raise_for_status()
            print(f"[DHIS2] Connection successful, user: {test_response.json().get('name', 'Unknown')}")

            # Check if root user already exists
            print("[DHIS2] Checking if root user already exists...")
            existing_root = self.check_root_user_exists()

            # Generate new password
            full_uuid, new_password = self.generate_new_password()
            print("[DHIS2] Generated UUID:", full_uuid)
            print("[DHIS2] New password for root user:", new_password)

            if existing_root:
                print(f"[DHIS2] Root user already exists with ID: {existing_root['id']}")
                print("[DHIS2] Updating existing root user password...")
                self.update_root_password(existing_root['id'], new_password)
                user_id = existing_root['id']
                action = 'updated'
            else:
                print("[DHIS2] Root user doesn't exist, creating new root user...")
                user_id = self.create_root_user(new_password)
                action = 'created'

            # Verify new credentials
            print("[DHIS2] Verifying new root credentials...")
            if self.verify_root_credentials(new_password):
                print("[DHIS2] ✅ Root user setup completed successfully!")

                # Now disable the original admin user for security
                print("[DHIS2] Disabling original admin user for security...")
                admin_disabled = self.disable_admin_user()

                return {
                    'success': True,
                    'username': 'root',
                    'new_password': new_password,
                    'full_uuid': full_uuid,
                    'user_id': user_id,
                    'action': action,
                    'admin_disabled': admin_disabled
                }
            else:
                print("[DHIS2] ❌ Root user setup failed - verification unsuccessful")
                return {'success': False, 'error': 'Verification failed'}

        except Exception as e:
            print(f"[DHIS2] ❌ Error: {e}")
            return {'success': False, 'error': str(e)}


def write_credentials_file(result, dhis2_url):
    """Write credentials to a file in /app for easy access"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/app/secrets/dhis2_credentials_{timestamp}.txt"

    try:
        with open(filename, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"🎉 DHIS2 ROOT USER {result.get('action', 'CREATED').upper()} SUCCESSFULLY\n")
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

            f.write("📋 QUICK COPY-PASTE SECTION:\n")
            f.write("┌" + "─" * 50 + "┐\n")
            f.write(f"│ Username: {result['username']:<37} │\n")
            f.write(f"│ Password: {result['new_password']:<37} │\n")
            f.write("└" + "─" * 50 + "┘\n\n")

            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"DHIS2 URL: {dhis2_url}\n")
            f.write(f"Action: Root user {result.get('action', 'created')}\n")

            if result.get('admin_disabled'):
                f.write(f"Security: Original admin user disabled ✅\n")
            else:
                f.write(f"Security: Original admin user NOT disabled ⚠️\n")

        # Set file permissions to be readable only by owner
        os.chmod(filename, 0o600)
        return filename

    except Exception as e:
        print(f"[DHIS2] ❌ Failed to write credentials file: {e}")
        return None


def get_dhis2_auth():
    """
    Returns (session, username) for DHIS2 API access.
    Prefers Bearer token from /run/secrets/dhis2-token if present and non-empty.
    Otherwise, uses username/password from env or secrets.
    """
    session = requests.Session()
    session.verify = False
    token_path = '/run/secrets/dhis2-token'
    token = None
    if os.path.exists(token_path):
        with open(token_path, 'r') as f:
            token = f.read().strip()
    if token:
        session.headers.update({'Authorization': f'Bearer {token}'})
        return session, None  # Username not needed for Bearer
    # Fallback to username/password
    username = os.getenv('DHIS2_USERNAME')
    password = os.getenv('DHIS2_PASSWORD')
    # Try to read from secrets if not set
    if not username or not password:
        cred_path = '/run/secrets/admin-credentials'
        if os.path.exists(cred_path):
            with open(cred_path, 'r') as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    username = lines[0].strip()
                    password = lines[1].strip()
    if not username or not password:
        raise Exception('DHIS2 credentials not found in environment or secrets')
    session.auth = HTTPBasicAuth(username, password)
    return session, username


def main():
    DHIS2_URL = os.getenv('DHIS2_URL')
    if not DHIS2_URL:
        print("[DHIS2] ❌ DHIS2_URL environment variable is required")
        exit(1)
    session, username = get_dhis2_auth()
    # Pass session and username to DHIS2RootUserCreator
    creator = DHIS2RootUserCreator(DHIS2_URL, username, None)
    creator.session = session  # Use the session with correct auth
    result = creator.setup_root_user()

    if result['success']:
        # Write credentials to file
        credentials_file = write_credentials_file(result, DHIS2_URL)

        if credentials_file:
            print()
            print("=" * 80)
            print(f"🎉 DHIS2 ROOT USER {result['action'].upper()} SUCCESSFULLY")
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
            if result.get('admin_disabled'):
                print("🔒 SECURITY: Original admin user has been disabled")
            else:
                print("⚠️  SECURITY: Original admin user could not be disabled")
            print()
            print("=" * 80)
        else:
            # Fallback to console output if file writing fails
            print()
            print("=" * 80)
            print(f"🎉 DHIS2 ROOT USER {result['action'].upper()} SUCCESSFULLY")
            print("=" * 80)
            print(f"Username: {result['username']}")
            print(f"Password: {result['new_password']}")
            print(f"URL: {DHIS2_URL}/dhis-web-commons/security/login.action")
            if result.get('admin_disabled'):
                print("🔒 Original admin user disabled")
            else:
                print("⚠️  Original admin user NOT disabled")
            print("=" * 80)

    else:
        print(f"[DHIS2] ❌ Failed to setup root user: {result['error']}")


if __name__ == "__main__":
    main()
