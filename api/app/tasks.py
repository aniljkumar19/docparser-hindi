from rq import Queue
from rq import Retry
from .worker import parse_job_task

def enqueue_parse(q: Queue, job_id: str):
    q.enqueue(
        parse_job_task,
        job_id,
        job_timeout=300,
        retry=Retry(max=2, interval=[10, 60])  # 2 retries at 10s and 60s
    )

