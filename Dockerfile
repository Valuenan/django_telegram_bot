# Dockerfile

FROM python:3.9
WORKDIR /django_telegram_bot

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN python -m pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ADD django_telegram_bot /django_telegram_bot/
