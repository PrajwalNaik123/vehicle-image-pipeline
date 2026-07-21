import logging

from redis import Redis
from rq import Queue, Worker

from app.db import REDIS_URL

logging.basicConfig(level=logging.INFO)

listen = ["image_processing"]

if __name__ == "__main__":
    conn = Redis.from_url(REDIS_URL)
    queues = [Queue(name, connection=conn) for name in listen]
    worker = Worker(queues, connection=conn)
    # default RQ retry behavior is none; job-level retry is configured where
    # jobs are enqueued (see main.py) so transient failures (e.g. DB blip)
    # get a couple of automatic retries before landing in the failed queue.
    worker.work()
