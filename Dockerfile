FROM ubuntu:20.04

# Ensure sharer service is available during build
# This is a build-time argument that can be passed if needed
ARG SHARER_HOST=sharer

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
RUN mkdir -p /opt/java/jdk \
    /opt/dhis2/ \
    /opt/tomcat \
    /tmp/tomcat-conf \
    /pkg


# Environment variables - will be set dynamically based on actual structure
ENV JAVA_OPTS="-Xmx2000m -Xms1000m -Djavax.servlet.request.encoding=UTF-8 -Dfile.encoding=UTF-8"
ENV DHIS2_HOME="/opt/dhis2/"
ENV LD_LIBRARY_PATH="/usr/local/apr/lib"

# Set CATALINA_HOME and JAVA_HOME dynamically after extraction
RUN CATALINA_HOME_DETECTED=$(find /opt/tomcat -name "catalina.sh" | head -1 | sed 's|/bin/catalina.sh||') && \
    JAVA_HOME_DETECTED=$(find /opt/java/jdk -name "java" -type f | head -1 | sed 's|/bin/java||') && \
    echo "Detected CATALINA_HOME: $CATALINA_HOME_DETECTED" && \
    echo "Detected JAVA_HOME: $JAVA_HOME_DETECTED" && \
    echo "export CATALINA_HOME=$CATALINA_HOME_DETECTED" >> /etc/environment && \
    echo "export JAVA_HOME=$JAVA_HOME_DETECTED" >> /etc/environment && \
    echo "export PATH=\$PATH:\$CATALINA_HOME/bin:\$JAVA_HOME/bin" >> /etc/environment

# Build APR during build phase (detect paths dynamically)
RUN CATALINA_HOME_BUILD=$(find /opt/tomcat -name "catalina.sh" | head -1 | sed 's|/bin/catalina.sh||') && \
    JAVA_HOME_BUILD=$(find /opt/java/jdk -name "java" -type f | head -1 | sed 's|/bin/java||') && \
    echo "Building APR with CATALINA_HOME: $CATALINA_HOME_BUILD and JAVA_HOME: $JAVA_HOME_BUILD" && \
    cd $CATALINA_HOME_BUILD/bin/ && \
    echo "Contents of Tomcat bin directory:" && ls -la && \
    if [ -f "tomcat-native.tar.gz" ]; then \
        tar -xvzf tomcat-native.tar.gz && \
        cd tomcat-native-*/native && \
        echo "Checking for JNI headers:" && \
        find $JAVA_HOME_BUILD -name "jni.h" -o -name "jni_md.h" | head -5 && \
        (./configure --with-apr=/usr/bin/apr-1-config \
                    --with-java-home=$JAVA_HOME_BUILD \
                    --with-ssl=yes \
                    --prefix=$CATALINA_HOME_BUILD && \
        make && make install) || echo "APR build failed, continuing without native library"; \
    else \
        echo "tomcat-native.tar.gz not found, skipping APR build"; \
    fi

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
