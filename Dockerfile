FROM python:3.7

RUN apt-get update -y && \
  apt-get install -y build-essential libpoppler-cpp-dev pkg-config python-dev poppler-utils

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY ./src /app
COPY ./Procfile /app/Procfile


ENV FLASK_APP=/app/app.py
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]