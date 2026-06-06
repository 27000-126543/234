import random
from datetime import datetime, timedelta
from models import (
    SessionLocal, Application, Equipment, EquipmentModel, Inventory,
    Supplier, Inquiry, PurchaseOrder, Department, Employee
)
from utils import generate_id, calculate_depreciation
from config import POSITION_STANDARDS, PREFERRED_SUPPLIERS, BUDGET_APPROVAL_THRESHOLD
from logger import log_operation, create_alert, logger
from approval import ApprovalManager


class ApplicationManager:
    
    @staticmethod
    def validate_position_standard(employee_id, equipment_type):
        db = SessionLocal()
        try:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                return False, "员工不存在"
            
            position = employee.position
            standards = POSITION_STANDARDS.get(position, {})
            max_count = standards.get(equipment_type, 0)
            
            if max_count == 0:
                return False, f"岗位{position}不允许申请{equipment_type}类型设备"
            
            current_count = db.query(Equipment).filter(
                Equipment.employee_id == employee_id,
                Equipment.status == 'in_use'
            ).join(EquipmentModel).filter(
                EquipmentModel.type_id == equipment_type
            ).count()
            
            if current_count >= max_count:
                return False, f"已达到岗位配置上限，当前{current_count}台，上限{max_count}台"
            
            return True, f"岗位配置校验通过，当前{current_count}台，上限{max_count}台"
        finally:
            db.close()
    
    @staticmethod
    def validate_budget(department_id, amount):
        db = SessionLocal()
        try:
            dept = db.query(Department).filter(Department.id == department_id).first()
            if not dept:
                return False, "部门不存在"
            
            remaining = dept.budget - dept.used_budget
            if amount > remaining:
                return False, f"部门预算不足，剩余预算{remaining}元，申请金额{amount}元"
            
            return True, f"预算校验通过，剩余预算{remaining}元"
        finally:
            db.close()
    
    @staticmethod
    def create_application(applicant_id, equipment_type, model_preference=None, reason=None):
        db = SessionLocal()
        try:
            applicant = db.query(Employee).filter(Employee.id == applicant_id).first()
            if not applicant:
                raise ValueError("申请人不存在")
            
            valid, msg = ApplicationManager.validate_position_standard(applicant_id, equipment_type)
            if not valid:
                raise ValueError(msg)
            
            app_id = generate_id('APP')
            
            model = None
            estimated_price = 0
            if model_preference:
                model = db.query(EquipmentModel).filter(
                    EquipmentModel.model_name.like(f'%{model_preference}%')
                ).first()
                if model:
                    estimated_price = model.unit_price
            
            standards = POSITION_STANDARDS.get(applicant.position, {})
            max_budget = standards.get('max_budget', 10000)
            if estimated_price == 0:
                estimated_price = min(max_budget, 10000)
            
            valid, msg = ApplicationManager.validate_budget(applicant.department_id, estimated_price)
            if not valid:
                raise ValueError(msg)
            
            need_approval = estimated_price > 10000
            approval_level = 0
            current_approver = None
            
            if need_approval:
                approval_level = 1
                approver = ApprovalManager.get_approver_by_level(1, applicant.department_id)
                if approver:
                    current_approver = approver.id
            
            application = Application(
                id=app_id,
                applicant_id=applicant_id,
                department_id=applicant.department_id,
                equipment_type=equipment_type,
                model_preference=model_preference,
                reason=reason,
                status='pending_approval' if need_approval else 'approved',
                total_amount=estimated_price,
                need_approval=need_approval,
                approval_level=approval_level,
                current_approver=current_approver,
                approved_at=datetime.now() if not need_approval else None
            )
            
            db.add(application)
            
            if need_approval and current_approver:
                ApprovalManager.create_approval_record(
                    app_id, 'application', current_approver, 1
                )
            
            db.commit()
            
            log_operation(
                applicant_id,
                '创建设备申请',
                related_id=app_id,
                related_type='application',
                details={
                    'equipment_type': equipment_type,
                    'model_preference': model_preference,
                    'estimated_price': estimated_price
                }
            )
            
            if not need_approval:
                create_alert(
                    'application_created',
                    f'新设备申请已自动通过：{app_id}，金额{estimated_price}元',
                    level='info',
                    related_id=app_id
                )
            else:
                create_alert(
                    'application_pending',
                    f'新设备申请待审批：{app_id}，金额{estimated_price}元',
                    level='warning',
                    related_id=app_id
                )
            
            db.refresh(application)
            return application
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create application: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def check_inventory_and_process(application_id):
        db = SessionLocal()
        try:
            application = db.query(Application).filter(Application.id == application_id).first()
            if not application:
                raise ValueError("申请不存在")
            
            if application.status != 'approved':
                raise ValueError("申请未通过审批")
            
            equipment_type = application.equipment_type
            inventory_items = db.query(Inventory).join(EquipmentModel).filter(
                EquipmentModel.type_id == equipment_type,
                Inventory.quantity > 0
            ).all()
            
            if inventory_items:
                inv = inventory_items[0]
                inv.quantity -= 1
                
                equipment = db.query(Equipment).filter(
                    Equipment.model_id == inv.model_id,
                    Equipment.status == 'in_stock'
                ).first()
                
                if equipment:
                    application.status = 'ready_to_assign'
                    db.commit()
                    
                    create_alert(
                        'inventory_available',
                        f'申请{application_id}库存可用，设备：{equipment.asset_code}',
                        level='info',
                        related_id=application_id
                    )
                    
                    return {
                        'success': True,
                        'has_inventory': True,
                        'equipment_id': equipment.id
                    }
            
            return {
                'success': True,
                'has_inventory': False,
                'message': '库存不足，需要采购'
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to check inventory: {str(e)}")
            raise
        finally:
            db.close()


class ProcurementManager:
    
    @staticmethod
    def create_inquiries(application_id):
        db = SessionLocal()
        try:
            application = db.query(Application).filter(Application.id == application_id).first()
            if not application:
                raise ValueError("申请不存在")
            
            equipment_type = application.equipment_type
            relevant_suppliers = [
                s for s in PREFERRED_SUPPLIERS
                if equipment_type in s['categories']
            ]
            
            if not relevant_suppliers:
                raise ValueError(f"没有找到{equipment_type}类型的供应商")
            
            inquiries = []
            for supplier_info in relevant_suppliers:
                supplier = db.query(Supplier).filter(Supplier.id == supplier_info['id']).first()
                if not supplier:
                    supplier = Supplier(
                        id=supplier_info['id'],
                        name=supplier_info['name'],
                        rating=supplier_info['rating'],
                        categories=','.join(supplier_info['categories'])
                    )
                    db.add(supplier)
                
                base_price = application.total_amount
                quoted_price = round(base_price * random.uniform(0.9, 1.1), 2)
                
                inquiry = Inquiry(
                    id=generate_id('INQ'),
                    application_id=application_id,
                    supplier_id=supplier_info['id'],
                    quoted_price=quoted_price,
                    delivery_days=random.randint(3, 15),
                    status='quoted'
                )
                db.add(inquiry)
                inquiries.append(inquiry)
            
            application.status = 'inquiring'
            db.commit()
            
            log_operation(
                'system',
                '发起询价',
                related_id=application_id,
                related_type='application',
                details={'supplier_count': len(inquiries)}
            )
            
            return inquiries
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create inquiries: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def select_best_supplier(application_id):
        db = SessionLocal()
        try:
            inquiries = db.query(Inquiry).filter(
                Inquiry.application_id == application_id,
                Inquiry.status == 'quoted'
            ).all()
            
            if not inquiries:
                raise ValueError("没有找到询价记录")
            
            scored_inquiries = []
            for inquiry in inquiries:
                supplier = inquiry.supplier
                price_score = 100 - (inquiry.quoted_price / max(i.quoted_price for i in inquiries)) * 50
                rating_score = supplier.rating * 10 if supplier.rating else 0
                delivery_score = max(0, 100 - inquiry.delivery_days * 5)
                
                total_score = price_score * 0.4 + rating_score * 0.3 + delivery_score * 0.3
                scored_inquiries.append((inquiry, total_score))
            
            scored_inquiries.sort(key=lambda x: x[1], reverse=True)
            best_inquiry, best_score = scored_inquiries[0]
            
            return best_inquiry, best_score
        except Exception as e:
            logger.error(f"Failed to select supplier: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def create_purchase_order(application_id):
        db = SessionLocal()
        try:
            application = db.query(Application).filter(Application.id == application_id).first()
            if not application:
                raise ValueError("申请不存在")
            
            best_inquiry, score = ProcurementManager.select_best_supplier(application_id)
            
            model = db.query(EquipmentModel).filter(
                EquipmentModel.type_id == application.equipment_type
            ).first()
            
            if not model:
                model = EquipmentModel(
                    id=generate_id('MOD'),
                    type_id=application.equipment_type,
                    brand=best_inquiry.supplier.name,
                    model_name=f'{application.equipment_type}-标准款',
                    unit_price=best_inquiry.quoted_price,
                    warranty_months=12
                )
                db.add(model)
            
            total_amount = best_inquiry.quoted_price
            
            po = PurchaseOrder(
                id=generate_id('PO'),
                application_id=application_id,
                supplier_id=best_inquiry.supplier_id,
                model_id=model.id,
                quantity=1,
                unit_price=best_inquiry.quoted_price,
                total_amount=total_amount,
                status='pending_delivery',
                expected_delivery=datetime.now() + timedelta(days=best_inquiry.delivery_days)
            )
            
            db.add(po)
            application.status = 'purchasing'
            best_inquiry.status = 'selected'
            
            need_approval = total_amount > BUDGET_APPROVAL_THRESHOLD
            if need_approval:
                po.status = 'pending_approval'
                approver = ApprovalManager.get_approver_by_level(4)
                if approver:
                    ApprovalManager.create_approval_record(
                        po.id, 'purchase', approver.id, 4
                    )
                
                create_alert(
                    'purchase_over_budget',
                    f'采购订单超预算需总监审批：{po.id}，金额{total_amount}元',
                    level='warning',
                    related_id=po.id
                )
            else:
                po.status = 'approved'
                create_alert(
                    'purchase_created',
                    f'采购订单已生成：{po.id}，供应商{best_inquiry.supplier.name}，金额{total_amount}元',
                    level='info',
                    related_id=po.id
                )
            
            db.commit()
            
            log_operation(
                'system',
                '生成采购订单',
                related_id=po.id,
                related_type='purchase',
                details={
                    'supplier': best_inquiry.supplier.name,
                    'amount': total_amount,
                    'score': score
                }
            )
            
            return po
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create purchase order: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def confirm_delivery(po_id, actual_delivery_date=None):
        db = SessionLocal()
        try:
            po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                raise ValueError("采购订单不存在")
            
            if actual_delivery_date is None:
                actual_delivery_date = datetime.now()
            
            po.status = 'delivered'
            po.actual_delivery = actual_delivery_date
            
            application = db.query(Application).filter(Application.id == po.application_id).first()
            if application:
                application.status = 'delivered'
            
            dept = db.query(Department).filter(Department.id == application.department_id).first()
            if dept:
                dept.used_budget += po.total_amount
            
            db.commit()
            
            create_alert(
                'delivery_confirmed',
                f'采购订单已到货：{po_id}，金额{po.total_amount}元',
                level='info',
                related_id=po_id
            )
            
            log_operation(
                'system',
                '确认到货',
                related_id=po_id,
                related_type='purchase',
                details={'actual_delivery': actual_delivery_date}
            )
            
            return po
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to confirm delivery: {str(e)}")
            raise
        finally:
            db.close()
