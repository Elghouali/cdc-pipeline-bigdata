FROM apache/hive:4.0.0
USER root
ADD https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar \
    /opt/hive/lib/mysql-connector-j-8.3.0.jar
ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
    /opt/hive/lib/hadoop-aws-3.3.4.jar
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar \
    /opt/hive/lib/aws-java-sdk-bundle-1.12.262.jar
RUN chmod 644 /opt/hive/lib/mysql-connector-j-8.3.0.jar \
              /opt/hive/lib/hadoop-aws-3.3.4.jar \
              /opt/hive/lib/aws-java-sdk-bundle-1.12.262.jar
USER hive
