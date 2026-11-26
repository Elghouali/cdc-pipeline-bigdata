FROM apache/spark:3.5.3-python3
USER root
# The Spark JVM and Ivy require a real, writable home even when launched
# directly by Kubernetes rather than the base image entrypoint.
RUN mkdir -p /home/spark /tmp/spark-local \
    && chown 185:0 /home/spark /tmp/spark-local
ENV HOME=/home/spark
COPY --chown=185:0 spark_jobs/ /opt/spark-apps/
USER 185
