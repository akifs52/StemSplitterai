from saas.core.config import get_settings


def enqueue_split_job(job_id: str) -> bool:
    settings = get_settings()
    if settings.queue_backend == "none":
        return False
    if settings.queue_backend == "inline":
        from saas.worker import process_job

        process_job(job_id)
        return True

    from redis import Redis
    from rq import Queue

    redis_conn = Redis.from_url(settings.redis_url)
    queue = Queue(settings.rq_queue_name, connection=redis_conn)
    queue.enqueue("saas.worker.process_job", job_id, job_timeout="6h", result_ttl=86400, failure_ttl=604800)
    return True

