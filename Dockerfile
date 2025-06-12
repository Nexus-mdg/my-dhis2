FROM ubuntu:20.04


RUN apt -y update && \
    apt install -y locales \
            wget \
            curl \
            libtcnative-1 \
            libaprutil1-dev \
            libapr1-dev \
            libssl-dev \
            build-essential \
            fontconfig


# Set the locale
RUN locale-gen en_US.UTF-8
RUN locale-gen fr_FR.UTF-8
RUN update-locale

RUN mkdir /opt/java
RUN mkdir /opt/java/11
RUN mkdir /opt/dhis2/
RUN mkdir /tmp/tomcat-conf
RUN mkdir /pkg


RUN wget -O /pkg/openjdk.tar.gz "http://172.17.0.1:8000/jdk-11.tar.gz"
RUN tar -zxvf /pkg/openjdk.tar.gz -C /opt/java/11


ENV JAVA11_DIR="/opt/java/11/jdk-11"
ARG JAVA_HOME="/opt/java/11/jdk-11"
# Default JAVA_OPTS - can be overridden by docker-compose.yaml
ENV JAVA_OPTS "-Xmx2000m -Xms1000m -Djavax.servlet.request.encoding=UTF-8 -Dfile.encoding=UTF-8"

# Install Tomcat
RUN mkdir /opt/tomcat
RUN wget -O /opt/tomcat/tomcat.tar.gz "http://172.17.0.1:8000/apache-tomcat-8.5.47.tar.gz"
RUN tar -zxvf /opt/tomcat/tomcat.tar.gz -C /opt/tomcat
WORKDIR /
ENV CATALINA_HOME="/opt/tomcat/apache-tomcat-8.5.47"
ENV PATH $PATH:$CATALINA_HOME/bin

# APR
WORKDIR $CATALINA_HOME/bin/
RUN tar -xvzf $CATALINA_HOME/bin/tomcat-native.tar.gz
WORKDIR $CATALINA_HOME/bin/tomcat-native-1.2.23-src/native
RUN echo $(ls -1 $CATALINA_HOME/bin/tomcat-native-1.2.23-src/native)
RUN ./configure && make && make install
ENV LD_LIBRARY_PATH=/usr/local/apr/lib
WORKDIR /

RUN rm -R $CATALINA_HOME/webapps/*

# Entrypoint file
ADD entrypoint.sh /tmp
RUN chmod 755 /tmp/entrypoint.sh

COPY tomcatconf-https/ /tmp/tomcat-conf-https/
COPY tomcatconf-http/ /tmp/tomcat-conf-http/

ENV DHIS2_HOME="/opt/dhis2/"

EXPOSE 8080 8443

# Install postgres client
RUN apt-get install -y postgresql-client

# Policy
COPY /policy /policy

# Entrypoint
WORKDIR /pkg
ENTRYPOINT ["/tmp/entrypoint.sh"]

# RUN Tomcat
CMD ["catalina.sh", "run"]
