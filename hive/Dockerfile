FROM apache/hive:4.0.0
USER root
ADD https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar \
    /opt/hive/lib/mysql-connector-j-8.3.0.jar
RUN chmod 644 /opt/hive/lib/mysql-connector-j-8.3.0.jar
USER hive
