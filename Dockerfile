FROM python:3.9-slim-buster
ARG ver
RUN pip install mwdstdb[gunicorn]==${ver}

ENV REDIS_URL=redis://localhost/
ENV CPA_MONKEY_DENY=CELERY.SEND_TASK,ALL_BACKENDS
ENV CALC_URL=http://localhost:5000/
ENV MONGO_DB_URL=mongodb://localhost
ENV MONGO_DB_NAME=test

ENTRYPOINT ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "mwdstdb.main:app"]
