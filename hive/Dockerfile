# syntax=docker/dockerfile:1
FROM apache/hive:4.0.0
USER root

# Use BuildKit remote ADD for versioned Maven artifacts. No Debian package
# installation is needed, so the build does not depend on retired apt indexes.
# Keep these versions aligned with the existing Hive/Hadoop configuration.
ADD --chmod=644 https://repo.maven.apache.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar /opt/hive/lib/mysql-connector-j-8.3.0.jar
ADD --chmod=644 https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar /opt/hive/lib/hadoop-aws-3.3.4.jar
ADD --chmod=644 https://repo.maven.apache.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar /opt/hive/lib/aws-java-sdk-bundle-1.12.262.jar

USER hive
