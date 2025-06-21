#!/usr/bin/env python3
"""
DHIS2 Root User Creator
Creates a new 'root' user with UUID-based password if it doesn't exist already
"""

import requests
import uuid
import urllib3
import os
import time
import sys
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def wait_for_dhis2(url, max_retries=30, retry_delay=10):
    """
    Wait for DHIS2 to become available by trying to connect to it.
    Returns True when connection succeeds, False after max retries.
    """
    print(f"[DHIS2] Waiting for DHIS2 at {url} to become available...")

    session = requests.Session()
    session.verify = False  # Ignore SSL errors

    for retry in range(1, max_retries + 1):
        try:
            # Try a simple HEAD request to check if the server is responding
            response = session.head(url, timeout=5)
            if response.status_code < 500:
                print(f"[DHIS2] ✅ DHIS2 is responding after {retry} tries")

                # Try a more specific API call to ensure DHIS2 is fully up
                try:
                    api_response = session.get(f"{url}/api/system/info", timeout=5)
                    api_response.raise_for_status()
                    print(f"[DHIS2] ✅ DHIS2 API is available!")
                    return True
                except Exception:
                    print("[DHIS2] DHIS2 responded but API not yet available, waiting...")
            else:
                print(f"[DHIS2] Server responded with status {response.status_code}, waiting...")

        except requests.exceptions.RequestException:
            print(f"[DHIS2] Attempt {retry}/{max_retries}: DHIS2 not ready yet, waiting {retry_delay} seconds...")

        # Wait before next attempt
        time.sleep(retry_delay)

    print(f"[DHIS2] ❌ DHIS2 did not become available after {max_retries} retries")
    return False


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

            if existing_root:
                print(f"[DHIS2] Root user already exists with ID: {existing_root['id']}")
                print("[DHIS2] ✅ No action needed - using existing root user")
                # Return success with existing user info, but don't change anything
                return {
                    'success': True,
                    'username': 'root',
                    'user_id': existing_root['id'],
                    'action': 'exists',
                    'admin_disabled': False  # Don't report admin as disabled since we didn't check
                }

            # Generate new password for new root user
            full_uuid, new_password = self.generate_new_password()
            print("[DHIS2] Generated UUID:", full_uuid)
            print("[DHIS2] New password for root user:", new_password)

            # Create new root user
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
        # Handle case where we're using an existing root user (no new password)
        if result.get('action') == 'exists':
            with open(filename, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write("🎉 EXISTING DHIS2 ROOT USER FOUND\n")
                f.write("=" * 80 + "\n\n")
                f.write("ℹ️ Root user already exists - no new credentials created\n")
                f.write(f"User ID: {result.get('user_id')}\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"DHIS2 URL: {dhis2_url}\n")
                f.write(f"Action: No action - existing root user\n")
                f.write("Note: Admin user was not disabled\n")
            os.chmod(filename, 0o600)
            return filename

        # Normal case - new or updated root user
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


def main():
    # Get DHIS2 URL from environment variable
    DHIS2_URL = os.getenv('DHIS2_URL')

    if not DHIS2_URL:
        print("[DHIS2] ❌ DHIS2_URL environment variable is required")
        exit(1)

    print(f"[DHIS2] Using DHIS2 URL from environment: {DHIS2_URL}")

    # Wait for DHIS2 to become available before proceeding
    if not wait_for_dhis2(DHIS2_URL):
        print("[DHIS2] ❌ Could not connect to DHIS2 after multiple attempts")
        sys.exit(1)

    # First try with the default credentials
    username = os.getenv('DHIS2_USERNAME', 'admin')
    password = os.getenv('DHIS2_PASSWORD', 'district')

    print(f"[DHIS2] Using credentials: {username} / {'*' * len(password)}")

    # Create root user creator and execute
    creator = DHIS2RootUserCreator(DHIS2_URL, username, password)

    # Try to test the connection first
    try:
        print("[DHIS2] Testing initial connection with admin credentials...")
        test_response = creator.session.get(f"{DHIS2_URL}/api/me")
        test_response.raise_for_status()
        print(f"[DHIS2] Admin credentials working: {test_response.json().get('name', 'Unknown')}")
        # If we get here, admin credentials work
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 401:
            # Admin credentials failed - try root user
            print("[DHIS2] Admin credentials failed (401) - admin likely disabled")
            print("[DHIS2] Attempting to authenticate with root user...")

            # To find the root password, let's read previous credential files
            root_password = None
            secrets_dir = "/app/secrets/"
            try:
                # List credentials files and sort by timestamp (newest first)
                if os.path.exists(secrets_dir):
                    credentials_files = sorted([f for f in os.listdir(secrets_dir) if f.startswith('dhis2_credentials_')],
                                              reverse=True)

                    for cred_file in credentials_files:
                        try:
                            print(f"[DHIS2] Checking credentials file: {cred_file}")
                            with open(os.path.join(secrets_dir, cred_file), 'r') as f:
                                content = f.read()
                                # Look for password in the credential file
                                for line in content.split('\n'):
                                    if line.startswith("Password:"):
                                        root_password = line.replace("Password:", "").strip()
                                        print(f"[DHIS2] Found root password in {cred_file}")
                                        break
                            if root_password:
                                break
                        except Exception as file_err:
                            print(f"[DHIS2] Error reading credential file {cred_file}: {file_err}")
            except Exception as dir_err:
                print(f"[DHIS2] Error accessing credentials directory: {dir_err}")

            if not root_password:
                print("[DHIS2] Could not find root password in credential files")
                print("[DHIS2] Trying alternate approaches...")

                # If no password found in files, we could try common patterns or pull from env
                # For security, we should require it to be set in environment if not found
                root_password = os.getenv('DHIS2_ROOT_PASSWORD')

            if root_password:
                print("[DHIS2] Trying with root user...")
                creator = DHIS2RootUserCreator(DHIS2_URL, "root", root_password)
                try:
                    test_response = creator.session.get(f"{DHIS2_URL}/api/me")
                    test_response.raise_for_status()
                    print(f"[DHIS2] Root credentials working: {test_response.json().get('name', 'Unknown')}")
                except Exception as root_err:
                    print(f"[DHIS2] Root authentication failed: {root_err}")
                    print("[DHIS2] Cannot proceed without valid credentials")
                    sys.exit(1)
            else:
                print("[DHIS2] No root password available, cannot proceed")
                sys.exit(1)
        else:
            # Some other error
            print(f"[DHIS2] Connection error: {e}")
            sys.exit(1)

    # Now proceed with setup using working credentials
    result = creator.setup_root_user()

    if result['success']:
        # Write credentials to file
        credentials_file = write_credentials_file(result, DHIS2_URL)

        if credentials_file:
            print()
            print("=" * 80)

            if result.get('action') == 'exists':
                print("🎉 EXISTING DHIS2 ROOT USER FOUND - NO ACTION NEEDED")
            else:
                print(f"🎉 DHIS2 ROOT USER {result['action'].upper()} SUCCESSFULLY")

            print("=" * 80)
            print()
            print("📁 CREDENTIALS SAVED TO FILE:")
            print(f"   {credentials_file}")
            print()

            if result.get('action') != 'exists':
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
                    print("⚠️  SECURITY: Original admin user was NOT disabled")
            else:
                print("ℹ️  Using existing root user - no changes made")

            print()
            print("=" * 80)
        else:
            # Fallback to console output if file writing fails
            print()
            print("=" * 80)
            if result.get('action') == 'exists':
                print("🎉 EXISTING DHIS2 ROOT USER FOUND - NO ACTION NEEDED")
            else:
                print(f"🎉 DHIS2 ROOT USER {result['action'].upper()} SUCCESSFULLY")
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
