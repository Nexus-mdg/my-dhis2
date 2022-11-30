#!/usr/bin/env bash
set -e


if [ -f /run/secrets/credentials ]; then
  FILE="/run/secrets/credentials"
  echo "Found credentials file"
  username=$(awk 'NR==1{print $2}' ${FILE})
  password=$(awk 'NR==2{print $2}' ${FILE})
  encryption_key=$(awk 'NR==3{print $2}' ${FILE})
else
  username="dhis"
  password="dhis"
  encryption_key="abcdefghijklmnopqrstuvwxyz0123456789@@"
fi


if [[ "${USE_OPEN_JDK}" == *"8"* ]]; then
  export JAVA_HOME=$JAVA8_DIR
else
  export JAVA_HOME=$JAVA11_DIR
fi

PATH=$PATH:"$JAVA_HOME"/bin

# save JAVA_HOME in conf file
touch "$CATALINA_HOME"/bin/setenv.sh
echo "export JAVA_HOME=$JAVA_HOME" >> "$CATALINA_HOME"/bin/setenv.sh

# set up policy for java
if [[ "${JAVA_HOME}" == *"8"* ]]; then
  echo "Attempting to install JCE for Java 8"
  mv "$JAVA_HOME"/jre/lib/security/local_policy.jar "$JAVA_HOME"/jre/lib/security/local_policy.jar.native
  mv "$JAVA_HOME"/jre/lib/security/US_export_policy.jar "$JAVA_HOME"/jre/lib/security/US_export_policy.jar.native
  cp /US_export_policy.jar "$JAVA_HOME"/jre/lib/security/
  cp /policy/local_policy.jar "$JAVA_HOME"/jre/lib/security/
  cp /policy/local_policy.jar "$JAVA_HOME"/jre/lib/security/
  cp /policy/README.txt "$JAVA_HOME"/jre/lib/security/
  chown --reference="$JAVA_HOME"/jre/lib/security/local_policy.jar.native "$JAVA_HOME"/jre/lib/security/local_policy.jar
  chown --reference="$JAVA_HOME"/jre/lib/security/US_export_policy.jar.native "$JAVA_HOME"/jre/lib/security/US_export_policy.jar
  chmod --reference="$JAVA_HOME"/jre/lib/security/local_policy.jar.native "$JAVA_HOME"/jre/lib/security/local_policy.jar
  chmod --reference="$JAVA_HOME"/jre/lib/security/US_export_policy.jar.native "$JAVA_HOME"/jre/lib/security/US_export_policy.jar
fi

# setup timezone (create env)
echo "Setting up timezone to $TIMEZONE"
ln -snf /usr/share/zoneinfo/"$TIMEZONE" /etc/localtime && echo "$TIMEZONE" > /etc/timezone

declare -a conf=()

[ "${ENCRYPTED}" == "TRUE" ] && conf+=("server.https = on") || conf+=("server.https = off")
[ "${ENCRYPTED}" == "TRUE" ] && conf+=("server.http.port = 8443") || conf+=("server.http.port = 8080")
conf+=("analytics.cache.expiration = 3600")
conf+=("connection.dialect = org.hibernate.dialect.PostgresSQLDialect")
conf+=("connection.driver_class = org.postgresql.Driver")
conf+=("connection.schema = update")

if [ -z "${DB_PORT}" ]; then
  conf+=("connection.url = jdbc:postgresql://$DB_HOST:$DB_PORT/$DB_NAME")
else
  conf+=("connection.url = jdbc:postgresql://$DB_HOST/$DB_NAME")
fi

conf+=("connection.username = $username")
conf+=("connection.password = $password")
conf+=("encryption.password = $encryption_key")

printf '%s\n' "${conf[@]}" >> /opt/dhis2/dhis.conf
chmod 0600 /opt/dhis2/dhis.conf

if [ "${ENCRYPTED}" == "TRUE" ]; then
  echo "Encryption is set !"
  RND=uid-$RANDOM-$RANDOM-$RANDOM-$RANDOM
  keytool -genkey -keyalg RSA -noprompt -alias "$RND" -dname "CN=localhost, OU=NA, O=NA, L=NA, S=NA, C=NA" -keystore /opt/tomcat/keystore.jks -validity 36500 -storepass "$RND" -keypass "$RND"
  openssl req -x509 -newkey rsa:4096 -keyout /opt/tomcat/localhost-rsa-key.pem -out /opt/tomcat/localhost-rsa-cert.pem -days 36500 -passout pass:"$RND" -subj "/C=MG/ST=Antananarivo/L=Antananarivo/O=Global Security/OU=IT Department/CN=localhost"
  cp -f /tmp/tomcat-conf-https/* "$CATALINA_HOME"/conf/
  sed -i 's/PEMsPassphrase/'"$RND"'/g' "$CATALINA_HOME"/conf/server.xml
else
  echo "Encryption is not set !"
  cp -f /tmp/tomcat-conf-http/* "$CATALINA_HOME"/conf/
fi

echo "Downloading DHIS2 warfile at $DHIS2_WARFILE_URL"
curl  -o "$CATALINA_HOME"/webapps/ROOT.war "$DHIS2_WARFILE_URL"

cd /

sh -c /src/app.sh

exec "$@"