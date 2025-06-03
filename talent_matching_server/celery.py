from __future__ import absolute_import, unicode_literals

import multiprocessing
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "talent_matching_server.settings")

app = Celery("talent_matching_server")
app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
