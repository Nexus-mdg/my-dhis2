#!/usr/bin/env bash
set -e

wget -O /pkg/openjdk.tar.gz "http://sharer:8000/jdk-11.tar.gz"
tar -zxvf /pkg/openjdk.tar.gz -C /opt/java/11
wget -O /opt/tomcat/tomcat.tar.gz "http://sharer:8000/apache-tomcat-8.5.47.tar.gz"
tar -zxvf /opt/tomcat/tomcat.tar.gz -C /opt/tomcat

# APR
WORKDIR $CATALINA_HOME/bin/
RUN tar -xvzf $CATALINA_HOME/bin/tomcat-native.tar.gz
WORKDIR $CATALINA_HOME/bin/tomcat-native-1.2.23-src/native
RUN echo $(ls -1 $CATALINA_HOME/bin/tomcat-native-1.2.23-src/native)
RUN ./configure && make && make install
ENV LD_LIBRARY_PATH=/usr/local/apr/lib

rm -R $CATALINA_HOME/webapps/*



# Only JDK 11 is supported now
export JAVA_HOME=$JAVA11_DIR
PATH=$PATH:"$JAVA_HOME"/bin

# JDK 11 has unlimited strength cryptography enabled by default, no need to install JCE policy files
echo "Using JDK 11 - unlimited strength cryptography is enabled by default"

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

if [ -f /run/secrets/credentials ]; then
    FILE="/run/secrets/credentials"
    echo "Found credentials file"

    conf+=("connection.username = $(awk 'NR==1{print $1}' ${FILE})")
    conf+=("connection.password = $(awk 'NR==2{print $1}' ${FILE})")
    conf+=("encryption.password = $(awk 'NR==3{print $1}' ${FILE})")
else
    echo -e "\031[37;44mSecret file not found, using random default credentials (dangerous)\033[0m"
    conf+=("connection.username = dhis")
    conf+=("connection.password = dhis")
    conf+=("encryption.password = abcdefghijklmnopqrstuvwxyz0123456789@@")
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
