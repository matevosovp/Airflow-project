FROM apache/airflow:2.7.3-python3.10

COPY --chown=airflow:root part1_airflow/requirements.txt /tmp/project-requirements.txt

RUN pip install --no-cache-dir -r /tmp/project-requirements.txt
