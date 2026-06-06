from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class Department(Base):
    __tablename__ = 'departments'
    
    id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    budget = Column(Float, default=0)
    used_budget = Column(Float, default=0)
    manager_id = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)


class Employee(Base):
    __tablename__ = 'employees'
    
    id = Column(String(20), primary_key=True)
    name = Column(String(50), nullable=False)
    position = Column(String(50), nullable=False)
    department_id = Column(String(20), ForeignKey('departments.id'))
    email = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)
    
    department = relationship('Department', backref='employees')


class EquipmentType(Base):
    __tablename__ = 'equipment_types'
    
    id = Column(String(20), primary_key=True)
    name = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class EquipmentModel(Base):
    __tablename__ = 'equipment_models'
    
    id = Column(String(50), primary_key=True)
    type_id = Column(String(20), ForeignKey('equipment_types.id'))
    brand = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    spec = Column(Text)
    unit_price = Column(Float, nullable=False)
    warranty_months = Column(Integer, default=12)
    created_at = Column(DateTime, default=datetime.now)
    
    type = relationship('EquipmentType', backref='models')


class Equipment(Base):
    __tablename__ = 'equipment'
    
    id = Column(String(50), primary_key=True)
    asset_code = Column(String(50), unique=True)
    model_id = Column(String(50), ForeignKey('equipment_models.id'))
    serial_number = Column(String(100))
    status = Column(String(20), default='in_stock')
    employee_id = Column(String(20), ForeignKey('employees.id'))
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(DateTime, nullable=False)
    warranty_end_date = Column(DateTime)
    current_value = Column(Float)
    location = Column(String(100))
    qr_code = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    
    model = relationship('EquipmentModel', backref='equipments')
    employee = relationship('Employee', backref='equipments')


class Inventory(Base):
    __tablename__ = 'inventory'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(50), ForeignKey('equipment_models.id'))
    quantity = Column(Integer, default=0)
    min_stock = Column(Integer, default=5)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    model = relationship('EquipmentModel', backref='inventory')


class Supplier(Base):
    __tablename__ = 'suppliers'
    
    id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    contact_person = Column(String(50))
    contact_phone = Column(String(20))
    email = Column(String(100))
    rating = Column(Float, default=0)
    categories = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(String(50), primary_key=True)
    applicant_id = Column(String(20), ForeignKey('employees.id'))
    department_id = Column(String(20), ForeignKey('departments.id'))
    equipment_type = Column(String(50), nullable=False)
    model_preference = Column(String(100))
    reason = Column(Text)
    status = Column(String(20), default='pending')
    total_amount = Column(Float, default=0)
    need_approval = Column(Boolean, default=False)
    approval_level = Column(Integer, default=0)
    current_approver = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)
    approved_at = Column(DateTime)
    
    applicant = relationship('Employee', foreign_keys=[applicant_id])
    department = relationship('Department')


class Inquiry(Base):
    __tablename__ = 'inquiries'
    
    id = Column(String(50), primary_key=True)
    application_id = Column(String(50), ForeignKey('applications.id'))
    supplier_id = Column(String(20), ForeignKey('suppliers.id'))
    model_id = Column(String(50), ForeignKey('equipment_models.id'))
    quoted_price = Column(Float, nullable=False)
    delivery_days = Column(Integer)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    
    application = relationship('Application', backref='inquiries')
    supplier = relationship('Supplier')
    model = relationship('EquipmentModel')


class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'
    
    id = Column(String(50), primary_key=True)
    application_id = Column(String(50), ForeignKey('applications.id'))
    supplier_id = Column(String(20), ForeignKey('suppliers.id'))
    model_id = Column(String(50), ForeignKey('equipment_models.id'))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')
    expected_delivery = Column(DateTime)
    actual_delivery = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    application = relationship('Application', backref='purchase_orders')
    supplier = relationship('Supplier')
    model = relationship('EquipmentModel')


class LendingAgreement(Base):
    __tablename__ = 'lending_agreements'
    
    id = Column(String(50), primary_key=True)
    equipment_id = Column(String(50), ForeignKey('equipment.id'))
    employee_id = Column(String(20), ForeignKey('employees.id'))
    signed_at = Column(DateTime)
    signature = Column(Text)
    terms = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    equipment = relationship('Equipment', backref='agreements')
    employee = relationship('Employee')


class RepairRequest(Base):
    __tablename__ = 'repair_requests'
    
    id = Column(String(50), primary_key=True)
    equipment_id = Column(String(50), ForeignKey('equipment.id'))
    reporter_id = Column(String(20), ForeignKey('employees.id'))
    description = Column(Text, nullable=False)
    is_under_warranty = Column(Boolean, default=False)
    estimated_cost = Column(Float, default=0)
    status = Column(String(20), default='pending')
    repair_type = Column(String(20))
    engineer_id = Column(String(20))
    logistics_track_no = Column(String(100))
    actual_cost = Column(Float)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    equipment = relationship('Equipment', backref='repairs')
    reporter = relationship('Employee', foreign_keys=[reporter_id])


class InventoryCheckTask(Base):
    __tablename__ = 'inventory_check_tasks'
    
    id = Column(String(50), primary_key=True)
    year = Column(Integer, nullable=False)
    status = Column(String(20), default='pending')
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


class InventoryCheckRecord(Base):
    __tablename__ = 'inventory_check_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), ForeignKey('inventory_check_tasks.id'))
    equipment_id = Column(String(50), ForeignKey('equipment.id'))
    employee_id = Column(String(20), ForeignKey('employees.id'))
    check_result = Column(String(20))
    remark = Column(Text)
    confirmed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    task = relationship('InventoryCheckTask', backref='records')
    equipment = relationship('Equipment')
    employee = relationship('Employee')


class InventoryAdjustment(Base):
    __tablename__ = 'inventory_adjustments'
    
    id = Column(String(50), primary_key=True)
    task_id = Column(String(50), ForeignKey('inventory_check_tasks.id'))
    equipment_id = Column(String(50), ForeignKey('equipment.id'))
    adjust_type = Column(String(20))
    reason = Column(Text)
    responsible_person = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)
    
    task = relationship('InventoryCheckTask', backref='adjustments')
    equipment = relationship('Equipment')


class ScrapApplication(Base):
    __tablename__ = 'scrap_applications'
    
    id = Column(String(50), primary_key=True)
    equipment_id = Column(String(50), ForeignKey('equipment.id'))
    applicant_id = Column(String(20), ForeignKey('employees.id'))
    reason = Column(Text)
    residual_value = Column(Float)
    status = Column(String(20), default='pending')
    approved_at = Column(DateTime)
    parts_recycled = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    equipment = relationship('Equipment', backref='scraps')
    applicant = relationship('Employee')


class ApprovalRecord(Base):
    __tablename__ = 'approval_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    related_id = Column(String(50), nullable=False)
    related_type = Column(String(20), nullable=False)
    approver_id = Column(String(20), ForeignKey('employees.id'))
    level = Column(Integer, default=1)
    decision = Column(String(20))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    approver = relationship('Employee')


class OperationLog(Base):
    __tablename__ = 'operation_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20))
    action = Column(String(100), nullable=False)
    related_id = Column(String(50))
    related_type = Column(String(20))
    details = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.now, index=True)


class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)
    level = Column(String(20), default='info')
    message = Column(Text, nullable=False)
    related_id = Column(String(50))
    is_pushed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class DepreciationRecord(Base):
    __tablename__ = 'depreciation_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String(50), ForeignKey('equipment.id'))
    period = Column(String(20), nullable=False)
    depreciation_amount = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    equipment = relationship('Equipment', backref='depreciation_records')


engine = create_engine(DATABASE_URL, pool_size=100, max_overflow=200, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
