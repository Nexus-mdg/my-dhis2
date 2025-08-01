#!/usr/bin/env bash
set -e

echo "Starting DHIS2 container setup..."

# Wait for ingress service to be ready
echo "Waiting for ingress service..."
until wget --spider -q --no-check-certificate https://ingress:8443 2>/dev/null; do
    echo "Ingress file sharing not ready, waiting 5 seconds..."
    sleep 5
done
echo "Ingress file sharing is ready!"

# Download and install JDK
echo "Installing JDK ..."
wget -O /pkg/openjdk.tar.gz --no-check-certificate "https://ingress:8443/${JAVA_ARCHIVE_FILE}"
tar -zxvf /pkg/openjdk.tar.gz -C /opt/java/jdk

# Download and install Tomcat
echo "Installing Tomcat..."
wget -O /opt/tomcat/tomcat.tar.gz --no-check-certificate "https://ingress:8443/${TOMCAT_ARCHIVE_FILE}"
tar -zxvf /opt/tomcat/tomcat.tar.gz -C /opt/tomcat

# Setup Java and Tomcat environment - detect paths dynamically
export CATALINA_HOME=$(find /opt/tomcat -name "catalina.sh" | head -1 | sed 's|/bin/catalina.sh||')
export JAVA_HOME=$(find /opt/java/jdk -name "java" -type f | head -1 | sed 's|/bin/java||')
export PATH="$PATH:$JAVA_HOME/bin:$CATALINA_HOME/bin"

echo "Using CATALINA_HOME: $CATALINA_HOME"
echo "Using JAVA_HOME: $JAVA_HOME"
echo "Java version: $($JAVA_HOME/bin/java -version 2>&1 | head -1)"
echo "Using JDK - unlimited strength cryptography is enabled by default"

# Build and install APR
echo "Building APR native library..."
cd $CATALINA_HOME/bin/
echo "Contents of Tomcat bin directory:"
ls -la
if [ -f "tomcat-native.tar.gz" ]; then
    tar -xvzf tomcat-native.tar.gz
    cd tomcat-native-*/native
    echo "Checking for JNI headers:"
    find $JAVA_HOME -name "jni.h" -o -name "jni_md.h" | head -5
    (./configure --with-apr=/usr/bin/apr-1-config \
                --with-java-home=$JAVA_HOME \
                --with-ssl=yes \
                --prefix=$CATALINA_HOME && \
    make && make install) || echo "APR build failed, continuing without native library"
else
    echo "tomcat-native.tar.gz not found, skipping APR build"
fi

# Clean up Tomcat webapps
rm -rf $CATALINA_HOME/webapps/*

# Setup timezone (create env)
echo "Setting up timezone to ${TIMEZONE:-UTC}"
TIMEZONE=${TIMEZONE:-UTC}
ln -snf /usr/share/zoneinfo/"$TIMEZONE" /etc/localtime && echo "$TIMEZONE" > /etc/timezone

# Build DHIS2 configuration
echo "Building DHIS2 configuration..."
declare -a conf=()

# Always use HTTPS for dhis2 service
conf+=("server.https = on")
conf+=("server.http.port = 8443")
conf+=("analytics.cache.expiration = 3600")
conf+=("connection.dialect = org.hibernate.dialect.PostgreSQLDialect")
conf+=("connection.driver_class = org.postgresql.Driver")
conf+=("connection.schema = update")

# Fix DB_PORT logic (was inverted)
if [ -n "${DB_PORT}" ]; then
  conf+=("connection.url = jdbc:postgresql://$DB_HOST:$DB_PORT/$DB_NAME")
else
  conf+=("connection.url = jdbc:postgresql://$DB_HOST/$DB_NAME")
fi

# Handle credentials
if [ -f /run/secrets/credentials ]; then
    FILE="/run/secrets/credentials"
    echo "Found credentials file"

    conf+=("connection.username = $(awk 'NR==1{print $1}' ${FILE})")
    conf+=("connection.password = $(awk 'NR==2{print $1}' ${FILE})")
    conf+=("encryption.password = $(awk 'NR==3{print $1}' ${FILE})")
else
    echo -e "\033[37;44mSecret file not found, using environment variables or defaults\033[0m"
    conf+=("connection.username = ${DB_USER:-dhis}")
    conf+=("connection.password = ${DB_PASSWORD:-dhis}")
    conf+=("encryption.password = ${ENCRYPTION_PASSWORD:-abcdefghijklmnopqrstuvwxyz0123456789@@}")
fi

# Write configuration
printf '%s\n' "${conf[@]}" > /opt/dhis2/dhis.conf
chmod 0600 /opt/dhis2/dhis.conf

# Setup SSL/TLS (always enabled for dhis2 service)
echo "Setting up HTTPS encryption..."
RND=uid-$RANDOM-$RANDOM-$RANDOM-$RANDOM

# Make sure Java tools are in PATH
export PATH="$JAVA_HOME/bin:$PATH"

# Generate keystore
"$JAVA_HOME/bin/keytool" -genkey -keyalg RSA -noprompt -alias "$RND" \
  -dname "CN=localhost, OU=NA, O=NA, L=NA, S=NA, C=NA" \
  -keystore /opt/tomcat/keystore.jks -validity 36500 \
  -storepass "$RND" -keypass "$RND"

# Generate PEM certificates
openssl req -x509 -newkey rsa:4096 \
  -keyout /opt/tomcat/localhost-rsa-key.pem \
  -out /opt/tomcat/localhost-rsa-cert.pem \
  -days 36500 -passout pass:"$RND" \
  -subj "${CERT_SUBJECT:-/C=MG/ST=World/L=World/O=VHT/OU=DEV/CN=dhis2_dhis2}"

# Copy HTTPS configuration
cp -f /tmp/tomcat-conf-https/* "$CATALINA_HOME"/conf/
sed -i 's/PEMsPassphrase/'"$RND"'/g' "$CATALINA_HOME"/conf/server.xml

# Download DHIS2 WAR file
if [ -n "$DHIS2_WARFILE_URL" ]; then
  echo "Downloading DHIS2 warfile from $DHIS2_WARFILE_URL"
  curl -k -o "$CATALINA_HOME"/webapps/ROOT.war "$DHIS2_WARFILE_URL"
else
  echo "Warning: DHIS2_WARFILE_URL not set, skipping WAR file download"
fi

echo "Setup complete. Starting application..."
cd /

# Execute the command passed to the container
exec "$@"
