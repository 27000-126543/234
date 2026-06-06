from datetime import datetime
from models import (
    SessionLocal, Equipment, EquipmentModel, Inventory, PurchaseOrder,
    Employee, LendingAgreement, Application
)
from utils import generate_id, generate_asset_code, generate_qr_code_content, calculate_depreciation, get_warranty_end_date
from logger import log_operation, create_alert, logger
from config import DEPRECIATION_MONTHS, WARRANTY_MONTHS_DEFAULT


class InventoryManager:
    
    @staticmethod
    def receive_equipment(po_id):
        db = SessionLocal()
        try:
            po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                raise ValueError("采购订单不存在")
            
            equipments = []
            for i in range(po.quantity):
                equip_id = generate_id('EQ')
                asset_code = generate_asset_code(po.model.type_id if po.model else 'EQ')
                
                warranty_end = get_warranty_end_date(
                    datetime.now(),
                    po.model.warranty_months if po.model else WARRANTY_MONTHS_DEFAULT
                )
                
                current_value, _ = calculate_depreciation(
                    po.unit_price,
                    datetime.now(),
                    datetime.now(),
                    DEPRECIATION_MONTHS
                )
                
                equipment = Equipment(
                    id=equip_id,
                    asset_code=asset_code,
                    model_id=po.model_id,
                    serial_number=generate_id('SN'),
                    status='in_stock',
                    purchase_price=po.unit_price,
                    purchase_date=datetime.now(),
                    warranty_end_date=warranty_end,
                    current_value=current_value,
                    qr_code=generate_qr_code_content(asset_code, equip_id)
                )
                db.add(equipment)
                equipments.append(equipment)
                
                inventory = db.query(Inventory).filter(Inventory.model_id == po.model_id).first()
                if inventory:
                    inventory.quantity += 1
                else:
                    inventory = Inventory(
                        model_id=po.model_id,
                        quantity=1,
                        min_stock=5
                    )
                    db.add(inventory)
            
            po.status = 'received'
            db.commit()
            
            for equip in equipments:
                log_operation(
                    'system',
                    '设备入库',
                    related_id=equip.id,
                    related_type='equipment',
                    details={
                        'asset_code': equip.asset_code,
                        'po_id': po_id,
                        'purchase_price': po.unit_price
                    }
                )
            
            create_alert(
                'equipment_received',
                f'采购订单{po_id}已入库，共{po.quantity}台设备',
                level='info',
                related_id=po_id
            )
            
            return equipments
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to receive equipment: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_available_equipment(equipment_type=None, model_id=None):
        db = SessionLocal()
        try:
            query = db.query(Equipment).filter(Equipment.status == 'in_stock')
            
            if model_id:
                query = query.filter(Equipment.model_id == model_id)
            elif equipment_type:
                query = query.join(EquipmentModel).filter(EquipmentModel.type_id == equipment_type)
            
            equipments = query.all()
            return equipments
        finally:
            db.close()
    
    @staticmethod
    def get_equipment_by_asset_code(asset_code):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.asset_code == asset_code).first()
            return equipment
        finally:
            db.close()
    
    @staticmethod
    def get_equipment_by_id(equipment_id):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            return equipment
        finally:
            db.close()
    
    @staticmethod
    def update_equipment_status(equipment_id, status, **kwargs):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError("设备不存在")
            
            equipment.status = status
            for key, value in kwargs.items():
                if hasattr(equipment, key):
                    setattr(equipment, key, value)
            
            db.commit()
            
            log_operation(
                'system',
                f'更新设备状态为{status}',
                related_id=equipment_id,
                related_type='equipment'
            )
            
            return equipment
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update equipment status: {str(e)}")
            raise
        finally:
            db.close()


class LendingManager:
    
    @staticmethod
    def assign_equipment(application_id, equipment_id, operator_id=None):
        db = SessionLocal()
        try:
            application = db.query(Application).filter(Application.id == application_id).first()
            if not application:
                raise ValueError("申请不存在")
            
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError("设备不存在")
            
            if equipment.status != 'in_stock':
                raise ValueError(f"设备状态为{equipment.status}，无法分配")
            
            employee = db.query(Employee).filter(Employee.id == application.applicant_id).first()
            if not employee:
                raise ValueError("申请人不存在")
            
            equipment.employee_id = employee.id
            equipment.status = 'pending_agreement'
            
            application.status = 'pending_agreement'
            
            agreement = LendingAgreement(
                id=generate_id('LA'),
                equipment_id=equipment_id,
                employee_id=employee.id,
                terms="""
                1. 员工应妥善保管设备，不得私自转借他人
                2. 设备正常使用损坏由公司承担维修费用
                3. 人为损坏或丢失需按折旧后价值赔偿
                4. 员工离职时需归还设备
                5. 设备仅限工作用途使用
                """
            )
            db.add(agreement)
            
            inventory = db.query(Inventory).filter(Inventory.model_id == equipment.model_id).first()
            if inventory and inventory.quantity > 0:
                inventory.quantity -= 1
            
            db.commit()
            
            log_operation(
                operator_id or 'system',
                '分配设备',
                related_id=equipment_id,
                related_type='equipment',
                details={
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'application_id': application_id
                }
            )
            
            create_alert(
                'equipment_assigned',
                f'设备{equipment.asset_code}已分配给{employee.name}，请签署领用协议',
                level='info',
                related_id=equipment_id
            )
            
            return agreement
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to assign equipment: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def sign_agreement(agreement_id, employee_id, signature=None):
        db = SessionLocal()
        try:
            agreement = db.query(LendingAgreement).filter(LendingAgreement.id == agreement_id).first()
            if not agreement:
                raise ValueError("领用协议不存在")
            
            if agreement.employee_id != employee_id:
                raise ValueError("只有指定领用人可以签署协议")
            
            agreement.signed_at = datetime.now()
            agreement.signature = signature or f'SIGNED_{employee_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            
            equipment = db.query(Equipment).filter(Equipment.id == agreement.equipment_id).first()
            if equipment:
                equipment.status = 'in_use'
            
            application = db.query(Application).filter(
                Application.applicant_id == employee_id,
                Application.status == 'pending_agreement'
            ).first()
            if application:
                application.status = 'completed'
            
            db.commit()
            
            log_operation(
                employee_id,
                '签署领用协议',
                related_id=agreement_id,
                related_type='agreement',
                details={'equipment_id': agreement.equipment_id}
            )
            
            create_alert(
                'agreement_signed',
                f'设备{equipment.asset_code}领用协议已签署，设备已锁定到{equipment.employee.name}',
                level='info',
                related_id=equipment.id
            )
            
            return agreement
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sign agreement: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_employee_equipment(employee_id, status=None):
        db = SessionLocal()
        try:
            query = db.query(Equipment).filter(Equipment.employee_id == employee_id)
            
            if status:
                query = query.filter(Equipment.status == status)
            
            equipments = query.order_by(Equipment.created_at.desc()).all()
            return equipments
        finally:
            db.close()
    
    @staticmethod
    def return_equipment(equipment_id, operator_id=None):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError("设备不存在")
            
            if equipment.status not in ['in_use', 'pending_agreement']:
                raise ValueError(f"设备状态为{equipment.status}，无法归还")
            
            old_employee_id = equipment.employee_id
            old_employee_name = equipment.employee.name if equipment.employee else ''
            
            equipment.employee_id = None
            equipment.status = 'in_stock'
            equipment.location = '仓库'
            
            inventory = db.query(Inventory).filter(Inventory.model_id == equipment.model_id).first()
            if inventory:
                inventory.quantity += 1
            
            db.commit()
            
            log_operation(
                operator_id or 'system',
                '设备归还',
                related_id=equipment_id,
                related_type='equipment',
                details={
                    'old_employee_id': old_employee_id,
                    'old_employee_name': old_employee_name
                }
            )
            
            create_alert(
                'equipment_returned',
                f'设备{equipment.asset_code}已归还，状态更新为在库',
                level='info',
                related_id=equipment_id
            )
            
            return equipment
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to return equipment: {str(e)}")
            raise
        finally:
            db.close()
