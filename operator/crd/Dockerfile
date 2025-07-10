FROM python:3.10-slim
WORKDIR /app
COPY operator.py .
RUN pip install kopf kubernetes
ENTRYPOINT ["kopf", "run", "--standalone", "operator.py"]
