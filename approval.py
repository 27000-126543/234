from datetime import datetime
from models import SessionLocal, ApprovalRecord, Employee, Application, PurchaseOrder, RepairRequest, ScrapApplication
from logger import log_operation, create_alert, logger
from config import BUDGET_APPROVAL_THRESHOLD


class ApprovalManager:
    
    @staticmethod
    def get_approval_level(amount):
        if amount <= 10000:
            return 1
        elif amount <= 100000:
            return 2
        elif amount <= BUDGET_APPROVAL_THRESHOLD:
            return 3
        else:
            return 4
    
    @staticmethod
    def get_approver_by_level(level, department_id=None):
        db = SessionLocal()
        try:
            if level == 1:
                approvers = db.query(Employee).filter(
                    Employee.position.in_(['Manager', 'Department Manager'])
                ).limit(1).all()
            elif level == 2:
                approvers = db.query(Employee).filter(
                    Employee.position.in_(['Director', 'Department Director'])
                ).limit(1).all()
            elif level >= 3:
                approvers = db.query(Employee).filter(
                    Employee.position.in_(['CEO', 'Director', 'CFO'])
                ).limit(1).all()
            else:
                approvers = []
            
            return approvers[0] if approvers else None
        finally:
            db.close()
    
    @staticmethod
    def create_approval_record(related_id, related_type, approver_id, level=1):
        db = SessionLocal()
        try:
            record = ApprovalRecord(
                related_id=related_id,
                related_type=related_type,
                approver_id=approver_id,
                level=level,
                decision='pending'
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            
            create_alert(
                'approval_pending',
                f'新的审批待处理：{related_type}，审批级别：{level}',
                level='info',
                related_id=related_id
            )
            
            return record
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create approval record: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def process_approval(record_id, decision, comment=None, approver_id=None):
        db = SessionLocal()
        try:
            record = db.query(ApprovalRecord).filter(ApprovalRecord.id == record_id).first()
            if not record:
                raise ValueError("审批记录不存在")
            
            record.decision = decision
            record.comment = comment
            record.created_at = datetime.now()
            
            if decision == 'approved':
                result = ApprovalManager._on_approval_approved(db, record)
            elif decision == 'rejected':
                result = ApprovalManager._on_approval_rejected(db, record)
            else:
                result = {'success': False, 'message': '无效的审批决定'}
            
            db.commit()
            
            log_operation(
                approver_id or record.approver_id,
                f'审批{decision}',
                related_id=record.related_id,
                related_type=record.related_type,
                details={'comment': comment, 'level': record.level}
            )
            
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to process approval: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def _on_approval_approved(db, record):
        related_type = record.related_type
        related_id = record.related_id
        
        if related_type == 'application':
            application = db.query(Application).filter(Application.id == related_id).first()
            if application:
                next_level = record.level + 1
                max_level = ApprovalManager.get_approval_level(application.total_amount)
                
                if next_level > max_level:
                    application.status = 'approved'
                    application.approved_at = datetime.now()
                    create_alert(
                        'application_approved',
                        f'设备申请已通过审批：{application.id}',
                        level='info',
                        related_id=related_id
                    )
                    return {'success': True, 'message': '申请已通过全部审批'}
                else:
                    next_approver = ApprovalManager.get_approver_by_level(next_level)
                    if next_approver:
                        application.approval_level = next_level
                        application.current_approver = next_approver.id
                        ApprovalManager.create_approval_record(
                            related_id, related_type, next_approver.id, next_level
                        )
                    return {'success': True, 'message': f'已提交第{next_level}级审批'}
        
        elif related_type == 'purchase':
            purchase = db.query(PurchaseOrder).filter(PurchaseOrder.id == related_id).first()
            if purchase:
                purchase.status = 'approved'
                create_alert(
                    'purchase_approved',
                    f'采购订单已批准：{purchase.id}',
                    level='info',
                    related_id=related_id
                )
                return {'success': True, 'message': '采购订单已批准'}
        
        elif related_type == 'repair':
            repair = db.query(RepairRequest).filter(RepairRequest.id == related_id).first()
            if repair:
                repair.status = 'approved'
                return {'success': True, 'message': '维修申请已批准'}
        
        elif related_type == 'scrap':
            scrap = db.query(ScrapApplication).filter(ScrapApplication.id == related_id).first()
            if scrap:
                scrap.status = 'approved'
                scrap.approved_at = datetime.now()
                create_alert(
                    'scrap_approved',
                    f'报废申请已批准：{scrap.id}',
                    level='warning',
                    related_id=related_id
                )
                return {'success': True, 'message': '报废申请已批准'}
        
        return {'success': True, 'message': '审批通过'}
    
    @staticmethod
    def _on_approval_rejected(db, record):
        related_type = record.related_type
        related_id = record.related_id
        
        if related_type == 'application':
            application = db.query(Application).filter(Application.id == related_id).first()
            if application:
                application.status = 'rejected'
                create_alert(
                    'application_rejected',
                    f'设备申请被驳回：{application.id}',
                    level='warning',
                    related_id=related_id
                )
        
        elif related_type == 'purchase':
            purchase = db.query(PurchaseOrder).filter(PurchaseOrder.id == related_id).first()
            if purchase:
                purchase.status = 'rejected'
        
        elif related_type == 'repair':
            repair = db.query(RepairRequest).filter(RepairRequest.id == related_id).first()
            if repair:
                repair.status = 'rejected'
        
        elif related_type == 'scrap':
            scrap = db.query(ScrapApplication).filter(ScrapApplication.id == related_id).first()
            if scrap:
                scrap.status = 'rejected'
        
        return {'success': True, 'message': '审批已驳回'}
    
    @staticmethod
    def get_pending_approvals(approver_id=None, level=None, related_type=None):
        db = SessionLocal()
        try:
            query = db.query(ApprovalRecord).filter(ApprovalRecord.decision == 'pending')
            
            if approver_id:
                query = query.filter(ApprovalRecord.approver_id == approver_id)
            if level:
                query = query.filter(ApprovalRecord.level == level)
            if related_type:
                query = query.filter(ApprovalRecord.related_type == related_type)
            
            records = query.order_by(ApprovalRecord.created_at.desc()).all()
            return records
        finally:
            db.close()
