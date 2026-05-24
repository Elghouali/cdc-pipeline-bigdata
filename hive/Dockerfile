FROM apache/hive:4.0.0
USER root
RUN curl -L "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar" \
    -o /opt/hive/lib/mysql-connector-j-8.3.0.jar && \
    chmod 644 /opt/hive/lib/mysql-connector-j-8.3.0.jar
USER hive
