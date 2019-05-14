import threading


def new_thread_with_jobs(jobs, wait=True, daemon=True, args=(), kwargs={}):
    """
    Run each job with a new thread
    :param jobs:
    :param wait:
    :param daemon:
    :param args:
    :param kwargs:
    :return:
    """
    threads = []
    if not isinstance(jobs, list):
        jobs = [jobs]
    for job in jobs:
        thread = threading.Thread(target=job, args=args, kwargs=kwargs)
        thread.setDaemon(daemon)
        thread.start()
        threads.append(thread)
    if wait:
        for thread in threads:
            thread.join()
