FROM apache/hive:4.0.0
USER root

# Download JDBC and S3A JARs needed for MariaDB-backed Hive Metastore + MinIO.
# RUN curl is used instead of ADD so Docker layer caching works correctly —
# ADD with HTTP URLs always re-downloads on every build regardless of cache.
RUN curl -fsSL -o /opt/hive/lib/mysql-connector-j-8.3.0.jar \
      https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar \
 && curl -fsSL -o /opt/hive/lib/hadoop-aws-3.3.4.jar \
      https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
 && curl -fsSL -o /opt/hive/lib/aws-java-sdk-bundle-1.12.262.jar \
      https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar \
 && chmod 644 \
      /opt/hive/lib/mysql-connector-j-8.3.0.jar \
      /opt/hive/lib/hadoop-aws-3.3.4.jar \
      /opt/hive/lib/aws-java-sdk-bundle-1.12.262.jar

USER hive
