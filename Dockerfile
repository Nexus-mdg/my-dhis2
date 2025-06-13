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
            fontconfig \
            postgresql-client

# Set the locale
RUN locale-gen en_US.UTF-8
RUN locale-gen fr_FR.UTF-8
RUN update-locale

# Create directories
RUN mkdir -p /opt/java/11 \
    /opt/dhis2/ \
    /opt/tomcat \
    /tmp/tomcat-conf \
    /pkg

# Environment variables
ENV JAVA11_DIR="/opt/java/11/jdk-11"
ENV JAVA_HOME="/opt/java/11/jdk-11"
ENV JAVA_OPTS="-Xmx2000m -Xms1000m -Djavax.servlet.request.encoding=UTF-8 -Dfile.encoding=UTF-8"
ENV CATALINA_HOME="/opt/tomcat/apache-tomcat-8.5.47"
ENV PATH="$PATH:$CATALINA_HOME/bin"
ENV DHIS2_HOME="/opt/dhis2/"
ENV LD_LIBRARY_PATH="/usr/local/apr/lib"

# Copy configuration and scripts
COPY tomcatconf-https/ /tmp/tomcat-conf-https/
COPY tomcatconf-http/ /tmp/tomcat-conf-http/
COPY /policy /policy
ADD entrypoint.sh /tmp/entrypoint.sh
RUN chmod 755 /tmp/entrypoint.sh

EXPOSE 8080 8443

WORKDIR /pkg
ENTRYPOINT ["/tmp/entrypoint.sh"]
CMD ["catalina.sh", "run"]