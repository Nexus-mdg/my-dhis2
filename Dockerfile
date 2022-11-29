FROM ubuntu:20.04


RUN apt -y update && \
    install -y locales \
            awk \
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
RUN mkdir /opt/dhis2/
RUN mkdir /tmp/tomcat-conf
RUN mkdir /pkg

RUN curl --output /pkg/openjdk8.tar.gz "https://for-dhis2.s3.eu-north-1.amazonaws.com/openjdk-8u40-b25-linux-x64-10_feb_2015.tar.gz"
RUN tar -zxvf /pkg/openjdk8.tar.gz -C /opt/java

ENV JAVA_HOME="/opt/java/java-se-8u40-ri"
ENV PATH $PATH:$JAVA_HOME/bin
# Important
ENV JAVA_OPTS "$OPTS"

# Install Tomcat
RUN mkdir /opt/tomcat
RUN curl --output /opt/tomcat/tomcat.tar.gz "https://for-dhis2.s3.eu-north-1.amazonaws.com/apache-tomcat-8.5.47.tar.gz"
RUN tar -zxvf tomcat.tar.gz -C /opt/tomcat
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
ADD /src/entrypoint.sh /tmp
RUN chmod 755 /tmp/entrypoint.sh

# Sed all params here
RUN cat /opt/dhis2/dhis.conf

COPY src/tomcatconf/ /tmp/tomcat-conf

ENV DHIS2_HOME="/opt/dhis2/"

EXPOSE 8080 8443

# Install postgres client
RUN apt-get install -y postgresql-client

# Entrypoint
WORKDIR /pkg
ENTRYPOINT ["/tmp/entrypoint.sh"]

# RUN Tomcat
CMD ["catalina.sh", "run"]
