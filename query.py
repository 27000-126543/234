from datetime import datetime
from models import SessionLocal, Equipment, EquipmentModel, EquipmentType, Employee, Department
from utils import parse_date, chunk_list
from logger import logger


class EquipmentQuery:
    
    @staticmethod
    def query(
        employee_id=None,
        model_id=None,
        equipment_type=None,
        status=None,
        start_date=None,
        end_date=None,
        keyword=None,
        page=1,
        page_size=100
    ):
        db = SessionLocal()
        try:
            query = db.query(Equipment)
            
            if employee_id:
                query = query.filter(Equipment.employee_id == employee_id)
            if model_id:
                query = query.filter(Equipment.model_id == model_id)
            if equipment_type:
                query = query.join(EquipmentModel).filter(EquipmentModel.type_id == equipment_type)
            if status:
                if isinstance(status, list):
                    query = query.filter(Equipment.status.in_(status))
                else:
                    query = query.filter(Equipment.status == status)
            if start_date:
                start = parse_date(start_date)
                query = query.filter(Equipment.purchase_date >= start)
            if end_date:
                end = parse_date(end_date)
                query = query.filter(Equipment.purchase_date <= end)
            if keyword:
                query = query.filter(
                    (Equipment.asset_code.like(f'%{keyword}%')) |
                    (Equipment.serial_number.like(f'%{keyword}%'))
                )
            
            total = query.count()
            
            offset = (page - 1) * page_size
            equipments = query.order_by(Equipment.created_at.desc())\
                            .offset(offset)\
                            .limit(page_size)\
                            .all()
            
            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'data': equipments
            }
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_equipment_lifecycle(equipment_id):
        db = SessionLocal()
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                return None
            
            from models import RepairRequest, ScrapApplication, LendingAgreement
            
            repairs = db.query(RepairRequest).filter(
                RepairRequest.equipment_id == equipment_id
            ).order_by(RepairRequest.created_at.desc()).all()
            
            scraps = db.query(ScrapApplication).filter(
                ScrapApplication.equipment_id == equipment_id
            ).order_by(ScrapApplication.created_at.desc()).all()
            
            agreements = db.query(LendingAgreement).filter(
                LendingAgreement.equipment_id == equipment_id
            ).order_by(LendingAgreement.created_at.desc()).all()
            
            from models import PurchaseOrder, InventoryCheckRecord
            
            po = db.query(PurchaseOrder).filter(
                PurchaseOrder.model_id == equipment.model_id
            ).first()
            
            check_records = db.query(InventoryCheckRecord).filter(
                InventoryCheckRecord.equipment_id == equipment_id
            ).order_by(InventoryCheckRecord.created_at.desc()).all()
            
            return {
                'equipment': equipment,
                'repairs': repairs,
                'scraps': scraps,
                'agreements': agreements,
                'purchase_order': po,
                'check_records': check_records,
                'events': EquipmentQuery._build_event_timeline(
                    equipment, repairs, scraps, agreements, check_records
                )
            }
        finally:
            db.close()
    
    @staticmethod
    def _build_event_timeline(equipment, repairs, scraps, agreements, check_records):
        events = []
        
        events.append({
            'time': equipment.purchase_date,
            'type': 'purchase',
            'title': '设备采购入库',
            'description': f'采购价格: {equipment.purchase_price}元, 资产编号: {equipment.asset_code}'
        })
        
        for agreement in agreements:
            if agreement.signed_at:
                events.append({
                    'time': agreement.signed_at,
                    'type': 'lending',
                    'title': '设备领用',
                    'description': f'领用人: {agreement.employee.name if agreement.employee else "未知"}'
                })
        
        for repair in repairs:
            events.append({
                'time': repair.created_at,
                'type': 'repair',
                'title': f'设备报修 - {repair.status}',
                'description': f'问题: {repair.description}, 费用: {repair.actual_cost or repair.estimated_cost}元'
            })
        
        for check in check_records:
            if check.confirmed_at:
                events.append({
                    'time': check.confirmed_at,
                    'type': 'check',
                    'title': f'盘点确认 - {check.check_result}',
                    'description': f'确认人: {check.employee.name if check.employee else "未知"}, 备注: {check.remark or ""}'
                })
        
        for scrap in scraps:
            if scrap.approved_at:
                events.append({
                    'time': scrap.approved_at,
                    'type': 'scrap',
                    'title': '设备报废',
                    'description': f'原因: {scrap.reason}, 剩余价值: {scrap.residual_value}元'
                })
        
        events.sort(key=lambda x: x['time'] if x['time'] else datetime.min, reverse=True)
        return events
    
    @staticmethod
    def get_employee_equipment(employee_id, status=None):
        db = SessionLocal()
        try:
            query = db.query(Equipment).filter(Equipment.employee_id == employee_id)
            if status:
                query = query.filter(Equipment.status == status)
            return query.order_by(Equipment.created_at.desc()).all()
        finally:
            db.close()
    
    @staticmethod
    def get_department_equipment(department_id):
        db = SessionLocal()
        try:
            equipments = db.query(Equipment).join(Employee).filter(
                Employee.department_id == department_id
            ).all()
            return equipments
        finally:
            db.close()
    
    @staticmethod
    def get_all_equipment_types():
        db = SessionLocal()
        try:
            types = db.query(EquipmentType).all()
            return types
        finally:
            db.close()
    
    @staticmethod
    def get_models_by_type(type_id):
        db = SessionLocal()
        try:
            models = db.query(EquipmentModel).filter(EquipmentModel.type_id == type_id).all()
            return models
        finally:
            db.close()
    
    @staticmethod
    def search_employees(keyword, limit=20):
        db = SessionLocal()
        try:
            employees = db.query(Employee).filter(
                (Employee.name.like(f'%{keyword}%')) |
                (Employee.id.like(f'%{keyword}%'))
            ).limit(limit).all()
            return employees
        finally:
            db.close()
    
    @staticmethod
    def get_all_departments():
        db = SessionLocal()
        try:
            depts = db.query(Department).all()
            return depts
        finally:
            db.close()
