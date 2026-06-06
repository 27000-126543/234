import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import SCHEDULED_TASK_TIME
from reports import run_daily_report
from logger import logger, create_alert


scheduler = None


def daily_task():
    logger.info("=" * 50)
    logger.info("执行每日定时任务")
    logger.info("=" * 50)
    
    try:
        reports = run_daily_report()
        
        create_alert(
            'daily_report_ready',
            f'每日统计报表已生成：\nExcel: {reports.get("excel", "")}\nPDF: {reports.get("pdf", "")}',
            level='info'
        )
        
        logger.info("每日定时任务执行完成")
        return True
    except Exception as e:
        logger.error(f"每日定时任务执行失败: {str(e)}")
        create_alert(
            'daily_task_failed',
            f'每日定时任务执行失败：{str(e)}',
            level='error'
        )
        return False


def init_scheduler():
    global scheduler
    
    if scheduler and scheduler.running:
        logger.warning("调度器已在运行")
        return scheduler
    
    scheduler = BackgroundScheduler()
    
    hour, minute = SCHEDULED_TASK_TIME.split(':')
    
    scheduler.add_job(
        daily_task,
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        id='daily_equipment_report',
        name='每日设备统计报表',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"调度器已启动，每日任务执行时间: {SCHEDULED_TASK_TIME}")
    
    return scheduler


def stop_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("调度器已停止")


def run_task_now(task_name='daily'):
    if task_name == 'daily':
        return daily_task()
    else:
        logger.warning(f"未知任务: {task_name}")
        return False


def get_scheduled_jobs():
    global scheduler
    if not scheduler:
        return []
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
        })
    return jobs
