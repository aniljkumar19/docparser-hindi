from .db import SessionLocal
from .tasks import process_job

def run_process(job_id: str, api_key: str, filename: str, storage_uri: str):
    process_job(SessionLocal, job_id, api_key, filename, storage_uri)
