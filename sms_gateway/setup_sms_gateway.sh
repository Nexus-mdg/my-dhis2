#!/bin/bash
# Clean Disease Surveillance Setup - ASCII only, no special characters

set -e

# Get DHIS2 URL from environment or use default
DHIS2_URL="${DHIS2_URL:-https://dhis2.stack}"
DHIS2_USERNAME="${DHIS2_USERNAME:-admin}"
DHIS2_PASSWORD="${DHIS2_PASSWORD:-district}"

echo "Setting up Disease Surveillance Tracker Program..."

log() {
    echo "[SURVEILLANCE] $(date '+%H:%M:%S') - $1"
}

log_success() {
    echo "[SURVEILLANCE] $(date '+%H:%M:%S') - SUCCESS: $1"
}

log_error() {
    echo "[SURVEILLANCE] $(date '+%H:%M:%S') - ERROR: $1"
}

wait_for_dhis2() {
    log "Waiting for DHIS2..."
    until curl -k -s -f "$DHIS2_URL/api/system/info" >/dev/null 2>&1; do
        sleep 5
    done
    log_success "DHIS2 is ready"
}

api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    log "Creating: $description"

    # Write clean JSON to temp file
    printf '%s' "$data" > /tmp/api_data.json

    local response=$(curl -k -s -w "%{http_code}" -o /tmp/api_response.json \
        -u "$DHIS2_USERNAME:$DHIS2_PASSWORD" \
        -H "Content-Type: application/json" \
        -X "$method" \
        --data-binary @/tmp/api_data.json \
        "$DHIS2_URL/api/$endpoint")

    if [ "$response" = "201" ] || [ "$response" = "200" ]; then
        local uid=$(cat /tmp/api_response.json | grep -o '"uid":"[^"]*"' | cut -d'"' -f4 | head -1 2>/dev/null || echo "")
        if [ -n "$uid" ]; then
            log_success "$description created (ID: $uid)"
            echo "$uid"
            return 0
        else
            log_success "$description created successfully"
            return 0
        fi
    else
        log_error "Failed to create $description (HTTP: $response)"
        cat /tmp/api_response.json 2>/dev/null || echo "No response"
        return 1
    fi
}

get_or_create() {
    local endpoint=$1
    local filter=$2
    local data=$3
    local description=$4

    local existing=$(curl -k -s -u "$DHIS2_USERNAME:$DHIS2_PASSWORD" \
        "$DHIS2_URL/api/$endpoint?filter=$filter&fields=id")

    local existing_id=$(echo "$existing" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | head -1)

    if [ -n "$existing_id" ]; then
        log_success "$description already exists (ID: $existing_id)"
        echo "$existing_id"
        return 0
    else
        local new_id=$(api_request "POST" "$endpoint" "$data" "$description")
        if [ $? -eq 0 ] && [ -n "$new_id" ]; then
            echo "$new_id"
            return 0
        else
            log_error "Failed to create $description"
            return 1
        fi
    fi
}

create_madagascar_ou() {
    log "Step 1: Madagascar Organisation Unit"
    local ou_data='{"name":"Madagascar","shortName":"Madagascar","description":"Republic of Madagascar","openingDate":"1960-06-26"}'
    get_or_create "organisationUnits" "name:eq:Madagascar" "$ou_data" "Madagascar OU"
}

create_patient_tet() {
    log "Step 2: Patient Tracked Entity Type"
    local tet_data='{"name":"Patient","shortName":"Patient","description":"Patient for surveillance"}'
    get_or_create "trackedEntityTypes" "name:eq:Patient" "$tet_data" "Patient TET"
}

create_attributes() {
    log "Step 3: Creating Attributes"

    local name_attr_data='{"name":"Patient Name","shortName":"Name","valueType":"TEXT","aggregationType":"NONE"}'
    local name_attr_id=$(get_or_create "trackedEntityAttributes" "name:eq:Patient Name" "$name_attr_data" "Name Attribute")

    local phone_attr_data='{"name":"Phone Number","shortName":"Phone","valueType":"PHONE_NUMBER","aggregationType":"NONE"}'
    local phone_attr_id=$(get_or_create "trackedEntityAttributes" "name:eq:Phone Number" "$phone_attr_data" "Phone Attribute")

    local age_attr_data='{"name":"Age","shortName":"Age","valueType":"INTEGER_POSITIVE","aggregationType":"NONE"}'
    local age_attr_id=$(get_or_create "trackedEntityAttributes" "name:eq:Age" "$age_attr_data" "Age Attribute")

    echo "$name_attr_id,$phone_attr_id,$age_attr_id"
}

create_data_elements() {
    log "Step 4: Creating Data Elements"

    local symptoms_data='{"name":"Symptoms","shortName":"Symptoms","valueType":"LONG_TEXT","aggregationType":"NONE","domainType":"TRACKER"}'
    local symptoms_id=$(get_or_create "dataElements" "name:eq:Symptoms" "$symptoms_data" "Symptoms DE")

    local temp_data='{"name":"Temperature","shortName":"Temperature","valueType":"NUMBER","aggregationType":"AVERAGE","domainType":"TRACKER"}'
    local temp_id=$(get_or_create "dataElements" "name:eq:Temperature" "$temp_data" "Temperature DE")

    local disease_data='{"name":"Suspected Disease","shortName":"Disease","valueType":"TEXT","aggregationType":"NONE","domainType":"TRACKER"}'
    local disease_id=$(get_or_create "dataElements" "name:eq:Suspected Disease" "$disease_data" "Disease DE")

    echo "$symptoms_id,$temp_id,$disease_id"
}

create_program_stage() {
    local symptoms_id=$1
    local temp_id=$2
    local disease_id=$3

    log "Step 5: Creating Program Stage"

    local stage_data='{"name":"Case Registration","description":"Initial case registration","repeatable":false,"autoGenerateEvent":true,"programStageDataElements":[{"dataElement":{"id":"'$symptoms_id'"},"compulsory":true,"allowProvidedElsewhere":false},{"dataElement":{"id":"'$temp_id'"},"compulsory":true,"allowProvidedElsewhere":false},{"dataElement":{"id":"'$disease_id'"},"compulsory":true,"allowProvidedElsewhere":false}]}'

    get_or_create "programStages" "name:eq:Case Registration" "$stage_data" "Registration Stage"
}

create_program() {
    local tet_id=$1
    local ou_id=$2
    local stage_id=$3
    local name_attr_id=$4
    local phone_attr_id=$5
    local age_attr_id=$6

    log "Step 6: Creating Program"

    local program_data='{"name":"Disease Surveillance","shortName":"Disease Surveillance","description":"Disease surveillance program","type":"WITH_REGISTRATION","trackedEntityType":{"id":"'$tet_id'"},"organisationUnits":[{"id":"'$ou_id'"}],"programStages":[{"id":"'$stage_id'"}],"programTrackedEntityAttributes":[{"trackedEntityAttribute":{"id":"'$name_attr_id'"},"mandatory":true,"searchable":true,"displayInList":true,"sortOrder":1},{"trackedEntityAttribute":{"id":"'$phone_attr_id'"},"mandatory":false,"searchable":false,"displayInList":true,"sortOrder":2},{"trackedEntityAttribute":{"id":"'$age_attr_id'"},"mandatory":true,"searchable":false,"displayInList":true,"sortOrder":3}]}'

    get_or_create "programs" "name:eq:Disease Surveillance" "$program_data" "Disease Surveillance Program"
}

create_sms_notification() {
    local phone_attr_id=$1

    log "Step 7: Creating SMS Notification"

    local notification_data='{"name":"Case Registration SMS","messageTemplate":"New case registered for patient","deliveryChannels":["SMS"],"notificationTrigger":"PROGRAM_STAGE_COMPLETION","notificationRecipient":"PROGRAM_ATTRIBUTE","recipientProgramAttribute":{"id":"'$phone_attr_id'"}}'

    get_or_create "programNotificationTemplates" "name:eq:Case Registration SMS" "$notification_data" "SMS Notification"
}

main() {
    log "Starting setup..."
    wait_for_dhis2

    # Create components step by step
    local ou_id=$(create_madagascar_ou)
    if [ -z "$ou_id" ]; then
        log_error "Cannot proceed without organisation unit"
        exit 1
    fi

    local tet_id=$(create_patient_tet)
    if [ -z "$tet_id" ]; then
        log_error "Cannot proceed without tracked entity type"
        exit 1
    fi

    local attr_ids=$(create_attributes)
    local name_attr_id=$(echo "$attr_ids" | cut -d',' -f1)
    local phone_attr_id=$(echo "$attr_ids" | cut -d',' -f2)
    local age_attr_id=$(echo "$attr_ids" | cut -d',' -f3)

    if [ -z "$name_attr_id" ] || [ -z "$phone_attr_id" ] || [ -z "$age_attr_id" ]; then
        log_error "Failed to create all required attributes"
        exit 1
    fi

    local de_ids=$(create_data_elements)
    local symptoms_id=$(echo "$de_ids" | cut -d',' -f1)
    local temp_id=$(echo "$de_ids" | cut -d',' -f2)
    local disease_id=$(echo "$de_ids" | cut -d',' -f3)

    if [ -z "$symptoms_id" ] || [ -z "$temp_id" ] || [ -z "$disease_id" ]; then
        log_error "Failed to create all required data elements"
        exit 1
    fi

    local stage_id=$(create_program_stage "$symptoms_id" "$temp_id" "$disease_id")
    if [ -z "$stage_id" ]; then
        log_error "Failed to create program stage"
        exit 1
    fi

    local program_id=$(create_program "$tet_id" "$ou_id" "$stage_id" "$name_attr_id" "$phone_attr_id" "$age_attr_id")
    if [ -z "$program_id" ]; then
        log_error "Failed to create program"
        exit 1
    fi

    local notification_id=$(create_sms_notification "$phone_attr_id")

    # Clean up temp files
    rm -f /tmp/api_response.json /tmp/api_data.json

    log_success "Setup completed successfully"
    echo ""
    log "Created Components:"
    log "Madagascar OU: $ou_id"
    log "Patient TET: $tet_id"
    log "Program: $program_id"
    log "SMS Template: $notification_id"
    echo ""
    log "Test Instructions:"
    log "1. Go to: $DHIS2_URL/dhis-web-tracker-capture"
    log "2. Select: Madagascar"
    log "3. Select: Disease Surveillance program"
    log "4. Register patient with phone number"
    log "5. Complete registration event"
    log "6. Check SMS: http://dhis2.stack:8082"
    echo ""
    log "Ready for testing"
}

main "$@"