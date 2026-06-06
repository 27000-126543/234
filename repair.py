import random
from datetime import datetime, timedelta
from models import (
    SessionLocal, RepairRequest, Equipment, Employee,
    DepreciationRecord
)
from utils import generate_id, is_under_warranty, calculate_depreciation, get_month_period
from logger import log_operation, create_alert, logger
from config import DEPRECIATION_MONTHS
from approval import ApprovalManager


class RepairManager:
    
    @staticmethod
    def create_repair_request(equipment_id, reporter_id, description):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError("设备不存在")
            
            reporter = db.query(Employee).filter(Employee.id == reporter_id).first()
            if not reporter:
                raise ValueError("报修人不存在")
            
            under_warranty = is_under_warranty(
                equipment.purchase_date,
                equipment.model.warranty_months if equipment.model else 12
            )
            
            repair_type = 'warranty' if under_warranty else 'paid'
            estimated_cost = 0 if under_warranty else round(random.uniform(200, 2000), 2)
            
            rr = RepairRequest(
                id=generate_id('RR'),
                equipment_id=equipment_id,
                reporter_id=reporter_id,
                description=description,
                is_under_warranty=under_warranty,
                estimated_cost=estimated_cost,
                status='pending',
                repair_type=repair_type
            )
            
            db.add(rr)
            
            equipment.status = 'under_repair'
            
            db.commit()
            
            log_operation(
                reporter_id,
                '提交报修',
                related_id=rr.id,
                related_type='repair',
                details={
                    'equipment_id': equipment_id,
                    'under_warranty': under_warranty,
                    'estimated_cost': estimated_cost
                }
            )
            
            alert_level = 'info' if under_warranty else 'warning'
            create_alert(
                'repair_created',
                f'设备{equipment.asset_code}报修{"(在保内)" if under_warranty else "(保外)"}，预估费用{estimated_cost}元',
                level=alert_level,
                related_id=rr.id
            )
            
            if not under_warranty and estimated_cost > 500:
                approver = ApprovalManager.get_approver_by_level(2)
                if approver:
                    ApprovalManager.create_approval_record(
                        rr.id, 'repair', approver.id, 2
                    )
                    rr.status = 'pending_approval'
                    db.commit()
            
            db.refresh(rr)
            return rr
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create repair request: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def process_repair(repair_id, operator_id=None):
        db = SessionLocal()
        try:
            repair = db.query(RepairRequest).filter(RepairRequest.id == repair_id).first()
            if not repair:
                raise ValueError("维修单不存在")
            
            if repair.status not in ['pending', 'approved']:
                raise ValueError(f"维修单状态为{repair.status}，无法处理")
            
            equipment = db.query(Equipment).filter(Equipment.id == repair.equipment_id).first()
            
            if repair.is_under_warranty:
                repair.status = 'sent_to_factory'
                repair.logistics_track_no = generate_id('SF')
                repair.repair_type = 'factory_repair'
                
                create_alert(
                    'repair_sent_factory',
                    f'设备{equipment.asset_code if equipment else repair.equipment_id}已返厂维修，物流单号：{repair.logistics_track_no}',
                    level='info',
                    related_id=repair_id
                )
            else:
                engineers = db.query(Employee).filter(
                    Employee.position == 'Engineer'
                ).all()
                
                if engineers:
                    engineer = random.choice(engineers)
                    repair.engineer_id = engineer.id
                    repair.status = 'engineer_assigned'
                    repair.repair_type = 'onsite'
                    
                    create_alert(
                        'repair_engineer_assigned',
                        f'设备{equipment.asset_code if equipment else repair.equipment_id}已指派工程师{engineer.name}维修',
                        level='info',
                        related_id=repair_id
                    )
                else:
                    repair.status = 'in_progress'
                    repair.repair_type = 'external'
            
            db.commit()
            
            log_operation(
                operator_id or 'system',
                '处理维修单',
                related_id=repair_id,
                related_type='repair',
                details={'repair_type': repair.repair_type}
            )
            
            return repair
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process repair: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def update_repair_status(repair_id, status, actual_cost=None, remark=None, operator_id=None):
        db = SessionLocal()
        try:
            repair = db.query(RepairRequest).filter(RepairRequest.id == repair_id).first()
            if not repair:
                raise ValueError("维修单不存在")
            
            repair.status = status
            
            if actual_cost is not None:
                repair.actual_cost = actual_cost
            
            if status == 'completed':
                repair.completed_at = datetime.now()
                
                equipment = db.query(Equipment).filter(Equipment.id == repair.equipment_id).first()
                if equipment:
                    equipment.status = 'in_use'
                    
                    current_value, _ = calculate_depreciation(
                        equipment.purchase_price,
                        equipment.purchase_date,
                        datetime.now(),
                        DEPRECIATION_MONTHS
                    )
                    equipment.current_value = current_value
                    
                    dep_record = DepreciationRecord(
                        equipment_id=equipment.id,
                        period=get_month_period(),
                        depreciation_amount=equipment.purchase_price / DEPRECIATION_MONTHS,
                        current_value=current_value
                    )
                    db.add(dep_record)
                
                create_alert(
                    'repair_completed',
                    f'维修单{repair_id}已完成，实际费用{actual_cost or repair.estimated_cost}元',
                    level='info',
                    related_id=repair_id
                )
            
            db.commit()
            
            log_operation(
                operator_id or 'system',
                f'更新维修状态为{status}',
                related_id=repair_id,
                related_type='repair',
                details={'actual_cost': actual_cost, 'remark': remark}
            )
            
            return repair
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update repair status: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def track_logistics(repair_id):
        db = SessionLocal()
        try:
            repair = db.query(RepairRequest).filter(RepairRequest.id == repair_id).first()
            if not repair:
                raise ValueError("维修单不存在")
            
            if not repair.logistics_track_no:
                return {'status': 'no_tracking', 'message': '无物流单号'}
            
            statuses = ['已揽收', '运输中', '到达目的地', '派送中', '已签收']
            days_passed = min((datetime.now() - repair.created_at).days, 4)
            
            return {
                'tracking_no': repair.logistics_track_no,
                'status': statuses[min(days_passed, 4)],
                'estimated_delivery': repair.created_at + timedelta(days=7),
                'update_time': datetime.now()
            }
        finally:
            db.close()
    
    @staticmethod
    def get_equipment_repair_history(equipment_id):
        db = SessionLocal()
        try:
            repairs = db.query(RepairRequest).filter(
                RepairRequest.equipment_id == equipment_id
            ).order_by(RepairRequest.created_at.desc()).all()
            return repairs
        finally:
            db.close()
    
    @staticmethod
    def get_pending_repairs():
        db = SessionLocal()
        try:
            repairs = db.query(RepairRequest).filter(
                RepairRequest.status.in_(['pending', 'pending_approval', 'in_progress'])
            ).order_by(RepairRequest.created_at.desc()).all()
            return repairs
        finally:
            db.close()
    
    @staticmethod
    def calculate_average_repair_cost(start_date=None, end_date=None):
        db = SessionLocal()
        try:
            query = db.query(RepairRequest).filter(
                RepairRequest.status == 'completed',
                RepairRequest.actual_cost > 0
            )
            
            if start_date:
                query = query.filter(RepairRequest.completed_at >= start_date)
            if end_date:
                query = query.filter(RepairRequest.completed_at <= end_date)
            
            repairs = query.all()
            
            if not repairs:
                return 0, 0
            
            total_cost = sum(r.actual_cost for r in repairs)
            avg_cost = total_cost / len(repairs)
            
            return round(avg_cost, 2), len(repairs)
        finally:
            db.close()
