import os
from typing import Optional
from rq import Queue
from redis import Redis

REDIS_URL = os.getenv("REDIS_URL")
_q: Optional[Queue] = None

def get_queue() -> Optional[Queue]:
    global _q
    if REDIS_URL and _q is None:
        redis = Redis.from_url(REDIS_URL)
        _q = Queue("parse", connection=redis)
    return _q
