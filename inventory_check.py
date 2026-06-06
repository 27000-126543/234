from datetime import datetime
from models import (
    SessionLocal, InventoryCheckTask, InventoryCheckRecord,
    InventoryAdjustment, Equipment, Employee
)
from utils import generate_id
from logger import log_operation, create_alert, logger


class InventoryCheckManager:
    
    @staticmethod
    def create_annual_task(year=None):
        if year is None:
            year = datetime.now().year
        
        db = SessionLocal()
        try:
            existing = db.query(InventoryCheckTask).filter(
                InventoryCheckTask.year == year
            ).first()
            
            if existing:
                return existing
            
            task = InventoryCheckTask(
                id=generate_id('ICT'),
                year=year,
                status='pending'
            )
            db.add(task)
            
            equipments = db.query(Equipment).filter(
                Equipment.status != 'scrapped'
            ).all()
            
            records = []
            for equip in equipments:
                record = InventoryCheckRecord(
                    task_id=task.id,
                    equipment_id=equip.id,
                    employee_id=equip.employee_id,
                    check_result='pending'
                )
                records.append(record)
            
            db.bulk_save_objects(records)
            db.commit()
            
            log_operation(
                'system',
                '创建年度盘点任务',
                related_id=task.id,
                related_type='inventory_check',
                details={'year': year, 'equipment_count': len(equipments)}
            )
            
            create_alert(
                'inventory_check_created',
                f'{year}年度盘点任务已创建，共{len(equipments)}台设备待盘点',
                level='info',
                related_id=task.id
            )
            
            db.refresh(task)
            return task
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create inventory check task: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def start_check_task(task_id, operator_id=None):
        db = SessionLocal()
        try:
            task = db.query(InventoryCheckTask).filter(
                InventoryCheckTask.id == task_id
            ).first()
            
            if not task:
                raise ValueError("盘点任务不存在")
            
            if task.status != 'pending':
                raise ValueError(f"任务状态为{task.status}，无法开始")
            
            task.status = 'in_progress'
            task.started_at = datetime.now()
            
            db.commit()
            
            log_operation(
                operator_id or 'system',
                '开始盘点',
                related_id=task_id,
                related_type='inventory_check'
            )
            
            create_alert(
                'inventory_check_started',
                f'盘点任务{task_id}已开始，请相关员工扫码确认设备',
                level='info',
                related_id=task_id
            )
            
            return task
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to start check task: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def scan_and_confirm(record_id, employee_id, check_result, remark=None):
        db = SessionLocal()
        try:
            record = db.query(InventoryCheckRecord).filter(
                InventoryCheckRecord.id == record_id
            ).first()
            
            if not record:
                raise ValueError("盘点记录不存在")
            
            if record.employee_id and record.employee_id != employee_id:
                raise ValueError("只能确认自己名下的设备")
            
            record.check_result = check_result
            record.remark = remark
            record.confirmed_at = datetime.now()
            
            if check_result in ['lost', 'damaged', 'mismatch']:
                equipment = db.query(Equipment).filter(
                    Equipment.id == record.equipment_id
                ).first()
                
                adjust = InventoryAdjustment(
                    id=generate_id('IA'),
                    task_id=record.task_id,
                    equipment_id=record.equipment_id,
                    adjust_type=check_result,
                    reason=remark or f'盘点发现{check_result}',
                    responsible_person=employee_id
                )
                db.add(adjust)
                
                create_alert(
                    'inventory_diff_found',
                    f'盘点发现差异：设备{equipment.asset_code if equipment else record.equipment_id}，状态{check_result}',
                    level='warning',
                    related_id=record.task_id
                )
                
                if check_result == 'lost':
                    log_operation(
                        employee_id,
                        '盘点发现设备丢失',
                        related_id=record.equipment_id,
                        related_type='equipment',
                        details={'task_id': record.task_id}
                    )
            
            db.commit()
            
            log_operation(
                employee_id,
                '盘点确认',
                related_id=record.equipment_id,
                related_type='equipment',
                details={'result': check_result, 'task_id': record.task_id}
            )
            
            return record
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to scan and confirm: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def confirm_by_equipment(task_id, equipment_id, employee_id, check_result, remark=None):
        db = SessionLocal()
        try:
            record = db.query(InventoryCheckRecord).filter(
                InventoryCheckRecord.task_id == task_id,
                InventoryCheckRecord.equipment_id == equipment_id
            ).first()
            
            if not record:
                raise ValueError("盘点记录不存在")
            
            return InventoryCheckManager.scan_and_confirm(
                record.id, employee_id, check_result, remark
            )
        finally:
            db.close()
    
    @staticmethod
    def get_task_progress(task_id):
        db = SessionLocal()
        try:
            records = db.query(InventoryCheckRecord).filter(
                InventoryCheckRecord.task_id == task_id
            ).all()
            
            if not records:
                return {'total': 0, 'completed': 0, 'pending': 0, 'progress': 0}
            
            total = len(records)
            completed = sum(1 for r in records if r.check_result != 'pending')
            pending = total - completed
            progress = round((completed / total) * 100, 2)
            
            result_counts = {}
            for r in records:
                result_counts[r.check_result] = result_counts.get(r.check_result, 0) + 1
            
            return {
                'total': total,
                'completed': completed,
                'pending': pending,
                'progress': progress,
                'result_counts': result_counts
            }
        finally:
            db.close()
    
    @staticmethod
    def complete_task(task_id, operator_id=None):
        db = SessionLocal()
        try:
            task = db.query(InventoryCheckTask).filter(
                InventoryCheckTask.id == task_id
            ).first()
            
            if not task:
                raise ValueError("盘点任务不存在")
            
            task.status = 'completed'
            task.completed_at = datetime.now()
            
            adjustments = db.query(InventoryAdjustment).filter(
                InventoryAdjustment.task_id == task_id
            ).all()
            
            for adjust in adjustments:
                equipment = db.query(Equipment).filter(
                    Equipment.id == adjust.equipment_id
                ).first()
                if equipment:
                    if adjust.adjust_type == 'lost':
                        equipment.status = 'lost'
                    elif adjust.adjust_type == 'damaged':
                        equipment.status = 'damaged'
            
            db.commit()
            
            progress = InventoryCheckManager.get_task_progress(task_id)
            
            log_operation(
                operator_id or 'system',
                '完成盘点任务',
                related_id=task_id,
                related_type='inventory_check',
                details={
                    'progress': progress,
                    'adjustment_count': len(adjustments)
                }
            )
            
            create_alert(
                'inventory_check_completed',
                f'盘点任务{task_id}已完成，发现{len(adjustments)}项差异',
                level='info',
                related_id=task_id
            )
            
            return task
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to complete task: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_employee_pending_records(employee_id, task_id=None):
        db = SessionLocal()
        try:
            query = db.query(InventoryCheckRecord).filter(
                InventoryCheckRecord.employee_id == employee_id,
                InventoryCheckRecord.check_result == 'pending'
            )
            
            if task_id:
                query = query.filter(InventoryCheckRecord.task_id == task_id)
            
            records = query.order_by(InventoryCheckRecord.created_at.desc()).all()
            return records
        finally:
            db.close()
    
    @staticmethod
    def get_adjustments(task_id=None):
        db = SessionLocal()
        try:
            query = db.query(InventoryAdjustment)
            
            if task_id:
                query = query.filter(InventoryAdjustment.task_id == task_id)
            
            adjustments = query.order_by(InventoryAdjustment.created_at.desc()).all()
            return adjustments
        finally:
            db.close()
