from __future__ import absolute_import, unicode_literals

import multiprocessing
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "talent_matching_server.settings")

app = Celery("talent_matching_server")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Konfigurasi langsung untuk Redis
app.conf.broker_url = "redis://redis:6379"
app.conf.result_backend = "redis"
app.conf.redis_host = "redis"
app.conf.redis_port = 6379
app.conf.redis_db = 0

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
