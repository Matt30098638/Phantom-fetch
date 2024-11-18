from apscheduler.schedulers.background import BackgroundScheduler

def schedule_tasks(app):
    scheduler = BackgroundScheduler()
    scheduler.init_app(app)
    scheduler.start()

    # Add the scheduled task
    scheduler.add_job(
        func=process_pending_requests_task,
        trigger="interval",
        minutes=5,  # Run every 5 minutes
        id="process_pending_requests_task",
        replace_existing=True,
    )
