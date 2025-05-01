# bhukhlagikya/celery.py
import os
from celery import Celery
import logging

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bhukhlagikya.settings')

app = Celery('bhukhlagikya')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

logger.info(f"Celery broker configured: {app.conf.broker_url}")