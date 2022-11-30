#!/usr/bin/env bash
set -e

printenv

# setup timezone (create env)
if [ -z "${TIMEZONE}" ]; then
  export TZ=$TIMEZONE
  ln -snf /usr/share/zoneinfo/"$TZ" /etc/localtime && echo "$TZ" > /etc/timezone
fi

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

if [ -f /run/secrets/credentials ]; then
    FILE="/run/secrets/credentials"
    conf+=("connection.username = $(awk 'NR==1{print $1}' ${FILE})")
    conf+=("connection.password = $(awk 'NR==2{print $1}' ${FILE})")
    conf+=("encryption.password = $(awk 'NR==3{print $1}' ${FILE})")
else
    echo -e "\031[37;44mSecret file not found, using random default credentials (dangerous)\033[0m"
    conf+=("connection.username = dhis")
    conf+=("connection.password = dhis")
    conf+=("encryption.password = abcdef123456@")
fi

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

exec "$@"