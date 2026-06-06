from datetime import datetime
from models import (
    SessionLocal, ScrapApplication, Equipment, Employee,
    DepreciationRecord, Inventory
)
from utils import generate_id, calculate_depreciation
from logger import log_operation, create_alert, logger
from config import DEPRECIATION_MONTHS
from approval import ApprovalManager


class ScrapManager:
    
    @staticmethod
    def create_scrap_application(equipment_id, applicant_id, reason):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError("设备不存在")
            
            if equipment.status in ['scrapped', 'pending_scrap']:
                raise ValueError(f"设备状态为{equipment.status}，无法重复申请报废")
            
            current_value, total_depreciation = calculate_depreciation(
                equipment.purchase_price,
                equipment.purchase_date,
                datetime.now(),
                DEPRECIATION_MONTHS
            )
            
            scrap = ScrapApplication(
                id=generate_id('SA'),
                equipment_id=equipment_id,
                applicant_id=applicant_id,
                reason=reason,
                residual_value=current_value,
                status='pending_approval'
            )
            
            db.add(scrap)
            equipment.status = 'pending_scrap'
            
            approval_level = 2 if current_value > 5000 else 1
            approver = ApprovalManager.get_approver_by_level(approval_level)
            if approver:
                ApprovalManager.create_approval_record(
                    scrap.id, 'scrap', approver.id, approval_level
                )
            
            db.commit()
            
            log_operation(
                applicant_id,
                '提交报废申请',
                related_id=scrap.id,
                related_type='scrap',
                details={
                    'equipment_id': equipment_id,
                    'residual_value': current_value,
                    'reason': reason
                }
            )
            
            create_alert(
                'scrap_created',
                f'设备{equipment.asset_code}报废申请已提交，剩余价值{current_value}元',
                level='warning',
                related_id=scrap.id
            )
            
            db.refresh(scrap)
            return scrap
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create scrap application: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def validate_residual_value(equipment_id):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                return False, "设备不存在"
            
            current_value, total_depreciation = calculate_depreciation(
                equipment.purchase_price,
                equipment.purchase_date,
                datetime.now(),
                DEPRECIATION_MONTHS
            )
            
            depreciation_rate = (total_depreciation / equipment.purchase_price) * 100 if equipment.purchase_price > 0 else 0
            
            can_scrap = depreciation_rate >= 70 or current_value < 100
            
            message = f"剩余价值{current_value}元，已折旧{round(depreciation_rate, 2)}%"
            if not can_scrap:
                message += "，建议继续使用或进行维修评估"
            
            return can_scrap, message, current_value
        finally:
            db.close()
    
    @staticmethod
    def process_scrap(scrap_id, parts_recycled=None, operator_id=None):
        db = SessionLocal()
        try:
            scrap = db.query(ScrapApplication).filter(ScrapApplication.id == scrap_id).first()
            if not scrap:
                raise ValueError("报废申请不存在")
            
            if scrap.status != 'approved':
                raise ValueError(f"报废申请状态为{scrap.status}，请先审批")
            
            equipment = db.query(Equipment).filter(Equipment.id == scrap.equipment_id).first()
            if not equipment:
                raise ValueError("设备不存在")
            
            equipment.status = 'scrapped'
            
            if parts_recycled:
                scrap.parts_recycled = parts_recycled
            
            last_depreciation = DepreciationRecord(
                equipment_id=equipment.id,
                period=datetime.now().strftime('%Y-%m'),
                depreciation_amount=scrap.residual_value,
                current_value=0
            )
            db.add(last_depreciation)
            
            inventory = db.query(Inventory).filter(Inventory.model_id == equipment.model_id).first()
            if inventory:
                inventory.quantity = max(0, inventory.quantity - 1)
            
            db.commit()
            
            log_operation(
                operator_id or 'system',
                '执行报废清理',
                related_id=scrap_id,
                related_type='scrap',
                details={
                    'equipment_id': scrap.equipment_id,
                    'residual_value': scrap.residual_value,
                    'parts_recycled': parts_recycled
                }
            )
            
            create_alert(
                'scrap_completed',
                f'设备{equipment.asset_code}已完成报废处理，回收配件：{parts_recycled or "无"}',
                level='info',
                related_id=scrap_id
            )
            
            return scrap
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process scrap: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_scrap_candidates():
        db = SessionLocal()
        try:
            equipments = db.query(Equipment).filter(
                Equipment.status.in_(['in_use', 'in_stock', 'damaged'])
            ).all()
            
            candidates = []
            for equip in equipments:
                current_value, total_depreciation = calculate_depreciation(
                    equip.purchase_price,
                    equip.purchase_date,
                    datetime.now(),
                    DEPRECIATION_MONTHS
                )
                
                depreciation_rate = (total_depreciation / equip.purchase_price) * 100 if equip.purchase_price > 0 else 0
                
                if depreciation_rate >= 80 or current_value < 500:
                    candidates.append({
                        'equipment': equip,
                        'current_value': current_value,
                        'depreciation_rate': depreciation_rate,
                        'recommended': True
                    })
            
            return candidates
        finally:
            db.close()
    
    @staticmethod
    def get_pending_scraps():
        db = SessionLocal()
        try:
            scraps = db.query(ScrapApplication).filter(
                ScrapApplication.status.in_(['pending_approval', 'approved'])
            ).order_by(ScrapApplication.created_at.desc()).all()
            return scraps
        finally:
            db.close()
    
    @staticmethod
    def get_scrap_history(equipment_id=None):
        db = SessionLocal()
        try:
            query = db.query(ScrapApplication).filter(ScrapApplication.status == 'completed')
            
            if equipment_id:
                query = query.filter(ScrapApplication.equipment_id == equipment_id)
            
            scraps = query.order_by(ScrapApplication.created_at.desc()).all()
            return scraps
        finally:
            db.close()
