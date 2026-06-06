import os
import json
import logging
import requests
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from config import LOG_DIR, WECHAT_WEBHOOK_URL
from models import SessionLocal, OperationLog, Alert

logger = logging.getLogger('equipment_management')
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, 'system.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'error.log'),
        maxBytes=10*1024*1024,
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)


def log_operation(user_id, action, related_id=None, related_type=None, details=None, ip_address=None):
    try:
        db = SessionLocal()
        
        def json_default(obj):
            if isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        log = OperationLog(
            user_id=user_id,
            action=action,
            related_id=related_id,
            related_type=related_type,
            details=json.dumps(details, ensure_ascii=False, default=json_default) if details else None,
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
        db.close()
        logger.info(f"Operation: {action}, User: {user_id}, Related: {related_type}:{related_id}")
    except Exception as e:
        logger.error(f"Failed to log operation: {str(e)}")


def create_alert(alert_type, message, level='info', related_id=None, push=True):
    try:
        db = SessionLocal()
        alert = Alert(
            type=alert_type,
            level=level,
            message=message,
            related_id=related_id,
            is_pushed=False
        )
        db.add(alert)
        db.commit()
        
        if push and WECHAT_WEBHOOK_URL:
            push_wechat_alert(alert)
            alert.is_pushed = True
            db.commit()
        
        alert_id = alert.id
        db.close()
        logger.warning(f"Alert created: {level} - {alert_type} - {message}")
        return alert_id
    except Exception as e:
        logger.error(f"Failed to create alert: {str(e)}")
        return None


def push_wechat_alert(alert):
    if not WECHAT_WEBHOOK_URL:
        return False
    
    try:
        level_colors = {
            'info': '#1890ff',
            'warning': '#faad14',
            'error': '#f5222d',
            'critical': '#722ed1'
        }
        
        data = {
            'msgtype': 'markdown',
            'markdown': {
                'content': f"""## <font color="{level_colors.get(alert.level, '#1890ff')}">设备管理系统预警</font>

**预警类型**：{alert.type}
**预警级别**：{alert.level}
**预警时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**预警内容**：{alert.message}

{'**关联ID**：' + alert.related_id if alert.related_id else ''}
"""
            }
        }
        
        response = requests.post(WECHAT_WEBHOOK_URL, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to push wechat alert: {str(e)}")
        return False


def push_batch_alerts(alerts):
    success_count = 0
    for alert in alerts:
        if push_wechat_alert(alert):
            alert.is_pushed = True
            success_count += 1
    return success_count


def get_recent_alerts(limit=100, level=None):
    try:
        db = SessionLocal()
        query = db.query(Alert).order_by(Alert.created_at.desc())
        if level:
            query = query.filter(Alert.level == level)
        alerts = query.limit(limit).all()
        db.close()
        return alerts
    except Exception as e:
        logger.error(f"Failed to get recent alerts: {str(e)}")
        return []


def get_operation_logs(user_id=None, action=None, related_type=None, start_time=None, end_time=None, limit=1000):
    try:
        db = SessionLocal()
        query = db.query(OperationLog).order_by(OperationLog.created_at.desc())
        
        if user_id:
            query = query.filter(OperationLog.user_id == user_id)
        if action:
            query = query.filter(OperationLog.action.like(f'%{action}%'))
        if related_type:
            query = query.filter(OperationLog.related_type == related_type)
        if start_time:
            query = query.filter(OperationLog.created_at >= start_time)
        if end_time:
            query = query.filter(OperationLog.created_at <= end_time)
        
        logs = query.limit(limit).all()
        db.close()
        return logs
    except Exception as e:
        logger.error(f"Failed to get operation logs: {str(e)}")
        return []
