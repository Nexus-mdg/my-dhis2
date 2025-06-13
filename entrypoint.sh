#!/usr/bin/env bash
set -e

echo "Starting DHIS2 container setup..."

# Download and install JDK
echo "Installing JDK 11..."
wget -O /pkg/openjdk.tar.gz "http://sharer:8000/jdk-11.tar.gz"
tar -zxvf /pkg/openjdk.tar.gz -C /opt/java/11

# Download and install Tomcat
echo "Installing Tomcat..."
wget -O /opt/tomcat/tomcat.tar.gz "http://sharer:8000/apache-tomcat-8.5.47.tar.gz"
tar -zxvf /opt/tomcat/tomcat.tar.gz -C /opt/tomcat

# Setup Java environment
export JAVA_HOME=$JAVA11_DIR
export PATH=$PATH:"$JAVA_HOME"/bin

echo "Using JDK 11 - unlimited strength cryptography is enabled by default"

# Build and install APR
echo "Building APR native library..."
cd $CATALINA_HOME/bin/
tar -xvzf $CATALINA_HOME/bin/tomcat-native.tar.gz
cd $CATALINA_HOME/bin/tomcat-native-1.2.23-src/native
echo "Contents of native directory:"
ls -1 $CATALINA_HOME/bin/tomcat-native-1.2.23-src/native
./configure && make && make install

# Clean up Tomcat webapps
rm -rf $CATALINA_HOME/webapps/*

# Setup timezone (create env)
echo "Setting up timezone to ${TIMEZONE:-UTC}"
TIMEZONE=${TIMEZONE:-UTC}
ln -snf /usr/share/zoneinfo/"$TIMEZONE" /etc/localtime && echo "$TIMEZONE" > /etc/timezone

# Build DHIS2 configuration
echo "Building DHIS2 configuration..."
declare -a conf=()

[ "${ENCRYPTED}" == "TRUE" ] && conf+=("server.https = on") || conf+=("server.https = off")
[ "${ENCRYPTED}" == "TRUE" ] && conf+=("server.http.port = 8443") || conf+=("server.http.port = 8080")
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

# Setup SSL/TLS if encryption is enabled
if [ "${ENCRYPTED}" == "TRUE" ]; then
  echo "Setting up HTTPS encryption..."
  RND=uid-$RANDOM-$RANDOM-$RANDOM-$RANDOM

  # Generate keystore
  keytool -genkey -keyalg RSA -noprompt -alias "$RND" \
    -dname "CN=localhost, OU=NA, O=NA, L=NA, S=NA, C=NA" \
    -keystore /opt/tomcat/keystore.jks -validity 36500 \
    -storepass "$RND" -keypass "$RND"

  # Generate PEM certificates
  openssl req -x509 -newkey rsa:4096 \
    -keyout /opt/tomcat/localhost-rsa-key.pem \
    -out /opt/tomcat/localhost-rsa-cert.pem \
    -days 36500 -passout pass:"$RND" \
    -subj "/C=MG/ST=Antananarivo/L=Antananarivo/O=Global Security/OU=IT Department/CN=localhost"

  # Copy HTTPS configuration
  cp -f /tmp/tomcat-conf-https/* "$CATALINA_HOME"/conf/
  sed -i 's/PEMsPassphrase/'"$RND"'/g' "$CATALINA_HOME"/conf/server.xml
else
  echo "Using HTTP configuration..."
  cp -f /tmp/tomcat-conf-http/* "$CATALINA_HOME"/conf/
fi

# Download DHIS2 WAR file
if [ -n "$DHIS2_WARFILE_URL" ]; then
  echo "Downloading DHIS2 warfile from $DHIS2_WARFILE_URL"
  curl -o "$CATALINA_HOME"/webapps/ROOT.war "$DHIS2_WARFILE_URL"
else
  echo "Warning: DHIS2_WARFILE_URL not set, skipping WAR file download"
fi

echo "Setup complete. Starting application..."
cd /

# Execute the command passed to the container
exec "$@"