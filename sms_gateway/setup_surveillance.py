#!/usr/bin/env python3
"""
Disease Surveillance Setup for DHIS2
Python version - clean and reliable
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class DHIS2SurveillanceSetup:
    def __init__(self):
        self.base_url = os.getenv('DHIS2_URL', 'https://dhis2.stack')
        self.username = os.getenv('DHIS2_USERNAME', 'admin')
        self.password = os.getenv('DHIS2_PASSWORD', 'district')
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.verify = False
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[SURVEILLANCE] {timestamp} - {message}")

    def log_success(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[SURVEILLANCE] {timestamp} - SUCCESS: {message}")

    def log_error(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[SURVEILLANCE] {timestamp} - ERROR: {message}")

    def wait_for_dhis2(self, max_retries=30):
        self.log("Waiting for DHIS2...")
        for attempt in range(max_retries):
            try:
                response = self.session.get(f"{self.base_url}/api/system/info", timeout=10)
                if response.status_code == 200:
                    self.log_success("DHIS2 is ready")
                    return True
            except Exception:
                pass
            time.sleep(5)

        self.log_error("DHIS2 not available after waiting")
        return False

    def api_request(self, method, endpoint, data=None, description=""):
        self.log(f"Creating: {description}")

        url = f"{self.base_url}/api/{endpoint}"

        try:
            if method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == 'GET':
                response = self.session.get(url, timeout=30)
            else:
                response = self.session.request(method, url, json=data, timeout=30)

            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    if 'response' in result and 'uid' in result['response']:
                        uid = result['response']['uid']
                        self.log_success(f"{description} created (ID: {uid})")
                        return uid
                    elif 'uid' in result:
                        uid = result['uid']
                        self.log_success(f"{description} created (ID: {uid})")
                        return uid
                    else:
                        self.log_success(f"{description} created successfully")
                        return True
                except:
                    self.log_success(f"{description} created successfully")
                    return True
            else:
                self.log_error(f"Failed to create {description} (HTTP: {response.status_code})")
                try:
                    error_info = response.json()
                    self.log_error(f"Error details: {json.dumps(error_info, indent=2)}")
                except:
                    self.log_error(f"Response: {response.text}")
                return None

        except Exception as e:
            self.log_error(f"Exception creating {description}: {str(e)}")
            return None

    def get_or_create(self, endpoint, filter_param, data, description):
        # Check if exists
        try:
            response = self.session.get(
                f"{self.base_url}/api/{endpoint}?filter={filter_param}&fields=id"
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('pager', {}).get('total', 0) > 0:
                    existing_id = result[endpoint.split('/')[-1]][0]['id']
                    self.log_success(f"{description} already exists (ID: {existing_id})")
                    return existing_id
        except Exception as e:
            self.log(f"Error checking existing {description}: {str(e)}")

        # Create new
        return self.api_request('POST', endpoint, data, description)

    def create_madagascar_ou(self):
        self.log("Step 1: Madagascar Organisation Unit")
        ou_data = {
            "name": "Madagascar",
            "shortName": "Madagascar",
            "description": "Republic of Madagascar",
            "openingDate": "1960-06-26"
        }
        return self.get_or_create(
            "organisationUnits",
            "name:eq:Madagascar",
            ou_data,
            "Madagascar OU"
        )

    def create_patient_tet(self):
        self.log("Step 2: Patient Tracked Entity Type")
        tet_data = {
            "name": "Patient",
            "shortName": "Patient",
            "description": "Patient for surveillance"
        }
        return self.get_or_create(
            "trackedEntityTypes",
            "name:eq:Patient",
            tet_data,
            "Patient TET"
        )

    def create_attributes(self):
        self.log("Step 3: Creating Attributes")

        # Name attribute
        name_attr_data = {
            "name": "Patient Name",
            "shortName": "Name",
            "valueType": "TEXT",
            "aggregationType": "NONE"
        }
        name_attr_id = self.get_or_create(
            "trackedEntityAttributes",
            "name:eq:Patient Name",
            name_attr_data,
            "Name Attribute"
        )

        # Phone attribute
        phone_attr_data = {
            "name": "Phone Number",
            "shortName": "Phone",
            "valueType": "PHONE_NUMBER",
            "aggregationType": "NONE"
        }
        phone_attr_id = self.get_or_create(
            "trackedEntityAttributes",
            "name:eq:Phone Number",
            phone_attr_data,
            "Phone Attribute"
        )

        # Age attribute
        age_attr_data = {
            "name": "Age",
            "shortName": "Age",
            "valueType": "INTEGER_POSITIVE",
            "aggregationType": "NONE"
        }
        age_attr_id = self.get_or_create(
            "trackedEntityAttributes",
            "name:eq:Age",
            age_attr_data,
            "Age Attribute"
        )

        return name_attr_id, phone_attr_id, age_attr_id

    def create_data_elements(self):
        self.log("Step 4: Creating Data Elements")

        # Symptoms
        symptoms_data = {
            "name": "Symptoms",
            "shortName": "Symptoms",
            "valueType": "LONG_TEXT",
            "aggregationType": "NONE",
            "domainType": "TRACKER"
        }
        symptoms_id = self.get_or_create(
            "dataElements",
            "name:eq:Symptoms",
            symptoms_data,
            "Symptoms DE"
        )

        # Temperature
        temp_data = {
            "name": "Temperature",
            "shortName": "Temperature",
            "valueType": "NUMBER",
            "aggregationType": "AVERAGE",
            "domainType": "TRACKER"
        }
        temp_id = self.get_or_create(
            "dataElements",
            "name:eq:Temperature",
            temp_data,
            "Temperature DE"
        )

        # Disease
        disease_data = {
            "name": "Suspected Disease",
            "shortName": "Disease",
            "valueType": "TEXT",
            "aggregationType": "NONE",
            "domainType": "TRACKER"
        }
        disease_id = self.get_or_create(
            "dataElements",
            "name:eq:Suspected Disease",
            disease_data,
            "Disease DE"
        )

        return symptoms_id, temp_id, disease_id

    def create_program_and_stage(self, tet_id, ou_id, symptoms_id, temp_id, disease_id, name_attr_id, phone_attr_id,
                                 age_attr_id):
        self.log("Step 5: Creating Program (without stages first)")

        # First create program without stages
        program_data = {
            "name": "Disease Surveillance",
            "shortName": "Disease Surveillance",
            "description": "Disease surveillance program",
            "programType": "WITH_REGISTRATION",
            "trackedEntityType": {"id": tet_id},
            "organisationUnits": [{"id": ou_id}],
            "programTrackedEntityAttributes": [
                {
                    "trackedEntityAttribute": {"id": name_attr_id},
                    "mandatory": True,
                    "searchable": True,
                    "displayInList": True,
                    "sortOrder": 1
                },
                {
                    "trackedEntityAttribute": {"id": phone_attr_id},
                    "mandatory": False,
                    "searchable": False,
                    "displayInList": True,
                    "sortOrder": 2
                },
                {
                    "trackedEntityAttribute": {"id": age_attr_id},
                    "mandatory": True,
                    "searchable": False,
                    "displayInList": True,
                    "sortOrder": 3
                }
            ]
        }

        program_id = self.get_or_create(
            "programs",
            "name:eq:Disease Surveillance",
            program_data,
            "Disease Surveillance Program"
        )

        if not program_id:
            return None, None

        self.log("Step 6: Creating Program Stage")

        # Now create the program stage with program reference
        stage_data = {
            "name": "Case Registration",
            "description": "Initial case registration",
            "repeatable": False,
            "autoGenerateEvent": True,
            "program": {"id": program_id},
            "programStageDataElements": [
                {
                    "dataElement": {"id": symptoms_id},
                    "compulsory": True,
                    "allowProvidedElsewhere": False
                },
                {
                    "dataElement": {"id": temp_id},
                    "compulsory": True,
                    "allowProvidedElsewhere": False
                },
                {
                    "dataElement": {"id": disease_id},
                    "compulsory": True,
                    "allowProvidedElsewhere": False
                }
            ]
        }

        stage_id = self.get_or_create(
            "programStages",
            "name:eq:Case Registration",
            stage_data,
            "Registration Stage"
        )

        if stage_id:
            # Update program to include the stage
            self.log("Step 7: Updating Program with Stage")
            update_url = f"{self.base_url}/api/programs/{program_id}"
            program_data["programStages"] = [{"id": stage_id}]

            try:
                response = self.session.put(update_url, json=program_data, timeout=30)
                if response.status_code == 200:
                    self.log_success("Program updated with stage")
                else:
                    self.log_error(f"Failed to update program with stage (HTTP: {response.status_code})")
            except Exception as e:
                self.log_error(f"Exception updating program: {str(e)}")

        return program_id, stage_id

    def create_sms_notification(self, phone_attr_id, stage_id):
        self.log("Step 8: Creating SMS Notification")

        notification_data = {
            "name": "Case Registration SMS",
            "messageTemplate": "New case registered for patient",
            "deliveryChannels": ["SMS"],
            "notificationTrigger": "COMPLETION",
            "notificationRecipient": "PROGRAM_ATTRIBUTE",
            "recipientProgramAttribute": {"id": phone_attr_id},
            "programStage": {"id": stage_id}
        }

        # First check if notification exists
        try:
            response = self.session.get(
                f"{self.base_url}/api/programStages/{stage_id}?fields=notificationTemplates[id,name]"
            )
            if response.status_code == 200:
                result = response.json()
                if 'notificationTemplates' in result and len(result['notificationTemplates']) > 0:
                    for template in result['notificationTemplates']:
                        if template.get('name') == "Case Registration SMS":
                            self.log_success(f"SMS Notification already exists (ID: {template['id']})")
                            return template['id']
        except Exception as e:
            self.log(f"Error checking existing SMS notification: {str(e)}")

        # Create new notification directly in the program stage
        notification_url = f"{self.base_url}/api/programNotificationTemplates"
        try:
            response = self.session.post(notification_url, json=notification_data, timeout=30)
            if response.status_code in [200, 201]:
                result = response.json()
                if 'response' in result and 'uid' in result['response']:
                    notification_id = result['response']['uid']
                    self.log_success(f"SMS Notification created (ID: {notification_id})")

                    # Now associate the notification with the program stage
                    self.log("Associating notification with program stage...")
                    update_stage_url = f"{self.base_url}/api/programStages/{stage_id}"

                    # First get current stage data
                    stage_response = self.session.get(update_stage_url)
                    if stage_response.status_code == 200:
                        stage_data = stage_response.json()

                        # Add notification template to the stage
                        if 'notificationTemplates' not in stage_data:
                            stage_data['notificationTemplates'] = []

                        stage_data['notificationTemplates'].append({"id": notification_id})

                        # Update program stage with notification
                        update_response = self.session.put(update_stage_url, json=stage_data, timeout=30)
                        if update_response.status_code == 200:
                            self.log_success("Successfully associated notification with program stage")
                        else:
                            self.log_error(f"Failed to associate notification with stage (HTTP: {update_response.status_code})")
                            try:
                                error_info = update_response.json()
                                self.log_error(f"Error details: {json.dumps(error_info, indent=2)}")
                            except:
                                self.log_error(f"Response: {update_response.text}")

                    return notification_id
            else:
                self.log_error(f"Failed to create SMS Notification (HTTP: {response.status_code})")
                try:
                    error_info = response.json()
                    self.log_error(f"Error details: {json.dumps(error_info, indent=2)}")
                except:
                    self.log_error(f"Response: {response.text}")
                return None
        except Exception as e:
            self.log_error(f"Exception creating SMS notification: {str(e)}")
            return None

    def verify_metadata(self, metadata_ids):
        """
        Verify that all metadata components have been created successfully

        Args:
            metadata_ids (dict): Dictionary with metadata types as keys and their IDs as values

        Returns:
            bool: True if all metadata exists, False otherwise
        """
        self.log("Step 9: Verifying all metadata components")

        all_valid = True
        verification_results = {}

        for component_type, component_id in metadata_ids.items():
            if not component_id:
                verification_results[component_type] = False
                all_valid = False
                continue

            endpoint = None
            if component_type == "organisation_unit":
                endpoint = f"organisationUnits/{component_id}"
            elif component_type == "tracked_entity_type":
                endpoint = f"trackedEntityTypes/{component_id}"
            elif component_type == "program":
                endpoint = f"programs/{component_id}"
            elif component_type == "program_stage":
                endpoint = f"programStages/{component_id}"
            elif component_type == "notification_template":
                endpoint = f"programNotificationTemplates/{component_id}"
            elif component_type.endswith("_attribute"):
                endpoint = f"trackedEntityAttributes/{component_id}"
            elif component_type.endswith("_data_element"):
                endpoint = f"dataElements/{component_id}"

            if endpoint:
                try:
                    response = self.session.get(f"{self.base_url}/api/{endpoint}", timeout=10)
                    if response.status_code == 200:
                        self.log_success(f"Verified {component_type}: {component_id}")
                        verification_results[component_type] = True
                    else:
                        self.log_error(f"Failed to verify {component_type} with ID {component_id} (HTTP: {response.status_code})")
                        verification_results[component_type] = False
                        all_valid = False
                except Exception as e:
                    self.log_error(f"Exception verifying {component_type}: {str(e)}")
                    verification_results[component_type] = False
                    all_valid = False
            else:
                self.log_error(f"Unknown component type: {component_type}")
                verification_results[component_type] = False
                all_valid = False

        # Print summary table
        print()
        self.log("Verification Results:")
        max_len = max([len(k) for k in verification_results.keys()])
        for component, status in verification_results.items():
            status_str = "✓ OK" if status else "✗ FAILED"
            padding = " " * (max_len - len(component))
            self.log(f"  {component}{padding} : {status_str}")
        print()

        if all_valid:
            self.log_success("All metadata components verified successfully")
        else:
            self.log_error("Some metadata components could not be verified")

        return all_valid

    def setup(self):
        self.log("Starting setup...")

        if not self.wait_for_dhis2():
            return False

        try:
            # Create all components
            ou_id = self.create_madagascar_ou()
            if not ou_id:
                self.log_error("Cannot proceed without organisation unit")
                return False

            tet_id = self.create_patient_tet()
            if not tet_id:
                self.log_error("Cannot proceed without tracked entity type")
                return False

            name_attr_id, phone_attr_id, age_attr_id = self.create_attributes()
            if not all([name_attr_id, phone_attr_id, age_attr_id]):
                self.log_error("Failed to create all required attributes")
                return False

            symptoms_id, temp_id, disease_id = self.create_data_elements()
            if not all([symptoms_id, temp_id, disease_id]):
                self.log_error("Failed to create all required data elements")
                return False

            program_id, stage_id = self.create_program_and_stage(tet_id, ou_id, symptoms_id, temp_id, disease_id,
                                                                 name_attr_id, phone_attr_id, age_attr_id)
            if not program_id or not stage_id:
                self.log_error("Failed to create program and stage")
                return False

            notification_id = self.create_sms_notification(phone_attr_id, stage_id)

            # Verify all metadata components
            metadata_ids = {
                "organisation_unit": ou_id,
                "tracked_entity_type": tet_id,
                "name_attribute": name_attr_id,
                "phone_attribute": phone_attr_id,
                "age_attribute": age_attr_id,
                "symptoms_data_element": symptoms_id,
                "temperature_data_element": temp_id,
                "disease_data_element": disease_id,
                "program": program_id,
                "program_stage": stage_id,
                "notification_template": notification_id
            }

            verification_successful = self.verify_metadata(metadata_ids)

            # Summary
            self.log_success("Setup completed successfully")
            print()
            self.log("Created Components:")
            self.log(f"Madagascar OU: {ou_id}")
            self.log(f"Patient TET: {tet_id}")
            self.log(f"Program: {program_id}")
            self.log(f"SMS Template: {notification_id}")
            print()
            self.log("Test Instructions:")
            self.log(f"1. Go to: {self.base_url}/dhis-web-tracker-capture")
            self.log("2. Select: Madagascar")
            self.log("3. Select: Disease Surveillance program")
            self.log("4. Register patient with phone number")
            self.log("5. Complete registration event")
            self.log("6. Check SMS: http://dhis2.stack:8082")
            print()
            self.log("Ready for testing")

            return verification_successful

        except Exception as e:
            self.log_error(f"Setup failed with exception: {str(e)}")
            return False


def main():
    print("Setting up Disease Surveillance Tracker Program...")

    setup = DHIS2SurveillanceSetup()
    success = setup.setup()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
