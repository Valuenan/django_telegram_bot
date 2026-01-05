from __future__ import absolute_import, unicode_literals
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_telegram_bot.settings')
# app = Celery('tasks', broker='redis://guest@localhost//')
app = Celery('django_telegram_bot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()