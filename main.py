import os
import sys
from datetime import datetime
from models import (
    init_db, SessionLocal, Department, Employee,
    EquipmentType, EquipmentModel
)
from config import POSITION_STANDARDS


def seed_database():
    db = SessionLocal()
    try:
        print("正在初始化基础数据...")
        
        if db.query(Department).count() == 0:
            departments = [
                {'id': 'D001', 'name': '技术部', 'budget': 500000, 'manager_id': 'E002'},
                {'id': 'D002', 'name': '市场部', 'budget': 300000, 'manager_id': 'E004'},
                {'id': 'D003', 'name': '行政部', 'budget': 200000, 'manager_id': 'E006'},
                {'id': 'D004', 'name': '财务部', 'budget': 200000, 'manager_id': 'E008'},
                {'id': 'D005', 'name': '人力资源部', 'budget': 150000, 'manager_id': 'E010'},
            ]
            for dept in departments:
                db.add(Department(**dept))
            print(f"  - 创建了 {len(departments)} 个部门")
        
        if db.query(Employee).count() == 0:
            employees = [
                {'id': 'E001', 'name': '张总', 'position': 'CEO', 'department_id': 'D001', 'email': 'ceo@company.com', 'phone': '13800000001'},
                {'id': 'E002', 'name': '李总监', 'position': 'Director', 'department_id': 'D001', 'email': 'tech_director@company.com', 'phone': '13800000002'},
                {'id': 'E003', 'name': '王工程师', 'position': 'Engineer', 'department_id': 'D001', 'email': 'wang@company.com', 'phone': '13800000003'},
                {'id': 'E004', 'name': '赵经理', 'position': 'Manager', 'department_id': 'D002', 'email': 'zhao@company.com', 'phone': '13800000004'},
                {'id': 'E005', 'name': '钱销售', 'position': 'Sales', 'department_id': 'D002', 'email': 'qian@company.com', 'phone': '13800000005'},
                {'id': 'E006', 'name': '孙行政', 'position': 'Admin', 'department_id': 'D003', 'email': 'sun@company.com', 'phone': '13800000006'},
                {'id': 'E007', 'name': '周员工', 'position': 'Staff', 'department_id': 'D003', 'email': 'zhou@company.com', 'phone': '13800000007'},
                {'id': 'E008', 'name': '吴财务', 'position': 'Manager', 'department_id': 'D004', 'email': 'wu@company.com', 'phone': '13800000008'},
                {'id': 'E009', 'name': '郑会计', 'position': 'Staff', 'department_id': 'D004', 'email': 'zheng@company.com', 'phone': '13800000009'},
                {'id': 'E010', 'name': '冯HR', 'position': 'Manager', 'department_id': 'D005', 'email': 'feng@company.com', 'phone': '13800000010'},
            ]
            for emp in employees:
                db.add(Employee(**emp))
            print(f"  - 创建了 {len(employees)} 个员工")
        
        if db.query(EquipmentType).count() == 0:
            types = [
                {'id': 'laptop', 'name': '笔记本电脑', 'category': '计算机', 'description': '便携式个人电脑'},
                {'id': 'desktop', 'name': '台式电脑', 'category': '计算机', 'description': '台式个人电脑'},
                {'id': 'monitor', 'name': '显示器', 'category': '外设', 'description': '电脑显示器'},
                {'id': 'phone', 'name': '手机', 'category': '移动设备', 'description': '办公用手机'},
                {'id': 'tablet', 'name': '平板电脑', 'category': '移动设备', 'description': '办公用平板电脑'},
                {'id': 'printer', 'name': '打印机', 'category': '外设', 'description': '办公打印机'},
            ]
            for t in types:
                db.add(EquipmentType(**t))
            print(f"  - 创建了 {len(types)} 个设备类型")
        
        if db.query(EquipmentModel).count() == 0:
            models = [
                {'id': 'M001', 'type_id': 'laptop', 'brand': '联想', 'model_name': 'ThinkPad X1 Carbon', 'spec': 'i7/16G/512G', 'unit_price': 12999, 'warranty_months': 36},
                {'id': 'M002', 'type_id': 'laptop', 'brand': '戴尔', 'model_name': 'Latitude 5440', 'spec': 'i5/16G/512G', 'unit_price': 8999, 'warranty_months': 24},
                {'id': 'M003', 'type_id': 'laptop', 'brand': '苹果', 'model_name': 'MacBook Pro 14', 'spec': 'M3/16G/512G', 'unit_price': 14999, 'warranty_months': 12},
                {'id': 'M004', 'type_id': 'monitor', 'brand': '戴尔', 'model_name': 'U2723QE', 'spec': '27寸/4K', 'unit_price': 4999, 'warranty_months': 36},
                {'id': 'M005', 'type_id': 'monitor', 'brand': '联想', 'model_name': 'T27i-30', 'spec': '27寸/2K', 'unit_price': 2499, 'warranty_months': 24},
                {'id': 'M006', 'type_id': 'phone', 'brand': '华为', 'model_name': 'Mate 60 Pro', 'spec': '12G/512G', 'unit_price': 6999, 'warranty_months': 12},
                {'id': 'M007', 'type_id': 'phone', 'brand': '苹果', 'model_name': 'iPhone 15 Pro', 'spec': '256G', 'unit_price': 7999, 'warranty_months': 12},
                {'id': 'M008', 'type_id': 'desktop', 'brand': '戴尔', 'model_name': 'OptiPlex 7010', 'spec': 'i7/16G/1T', 'unit_price': 7999, 'warranty_months': 36},
            ]
            for m in models:
                db.add(EquipmentModel(**m))
            print(f"  - 创建了 {len(models)} 个设备型号")
        
        db.commit()
        print("基础数据初始化完成！")
        
    except Exception as e:
        db.rollback()
        print(f"初始化数据失败: {str(e)}")
        raise
    finally:
        db.close()


def demo_full_workflow():
    print("\n" + "=" * 70)
    print("演示：企业设备全生命周期管理流程")
    print("=" * 70)
    
    try:
        print("\n【步骤1】员工提交设备申请")
        print("-" * 50)
        from procurement import ApplicationManager
        from models import Application, ScrapApplication, Employee
        
        applicant_id = 'E005'
        db_emp = SessionLocal()
        employee = db_emp.query(Employee).filter(Employee.id == applicant_id).first()
        db_emp.close()
        print(f"申请人: {employee.name} ({employee.position})")
        
        application = ApplicationManager.create_application(
            applicant_id=applicant_id,
            equipment_type='laptop',
            model_preference='ThinkPad',
            reason='新入职员工需要配备办公电脑'
        )
        print(f"申请单号: {application.id}")
        print(f"设备类型: {application.equipment_type}")
        print(f"预估金额: {application.total_amount}元")
        print(f"申请状态: {application.status}")
        
        if application.status == 'pending_approval':
            print("\n【步骤1.5】自动通过审批（演示用）")
            print("-" * 50)
            db = SessionLocal()
            app = db.query(Application).filter(Application.id == application.id).first()
            if app:
                app.status = 'approved'
                app.approved_at = datetime.now()
                db.commit()
                print(f"申请 {application.id} 已自动通过审批")
            db.close()
        
        print("\n【步骤2】检查库存并发起询价")
        print("-" * 50)
        from procurement import ProcurementManager
        
        result = ApplicationManager.check_inventory_and_process(application.id)
        has_inventory = result.get('has_inventory')
        print(f"库存检查结果: {'有库存' if has_inventory else '库存不足，需要采购'}")
        
        if not has_inventory:
            ProcurementManager.create_inquiries(application.id)
            db2 = SessionLocal()
            from models import Inquiry
            inquiries = db2.query(Inquiry).filter(Inquiry.application_id == application.id).all()
            print(f"已向 {len(inquiries)} 家供应商发起询价:")
            for inq in inquiries:
                supplier_name = inq.supplier.name if inq.supplier else '未知供应商'
                print(f"  - {supplier_name}: 报价 {inq.quoted_price}元, 货期 {inq.delivery_days}天")
            db2.close()
            
            print("\n【步骤3】智能选择最优供应商并生成采购单")
            print("-" * 50)
            ProcurementManager.create_purchase_order(application.id)
            db3 = SessionLocal()
            from models import PurchaseOrder
            po = db3.query(PurchaseOrder).filter(PurchaseOrder.application_id == application.id).first()
            supplier_name = po.supplier.name if po and po.supplier else '未知供应商'
            expected_delivery = po.expected_delivery.strftime('%Y-%m-%d') if po and po.expected_delivery else '未知'
            print(f"采购单号: {po.id}")
            print(f"供应商: {supplier_name}")
            print(f"采购金额: {po.total_amount}元")
            print(f"预计到货: {expected_delivery}")
            
            print("\n【步骤4】确认到货并入库")
            print("-" * 50)
            from inventory import InventoryManager
            
            ProcurementManager.confirm_delivery(po.id)
            InventoryManager.receive_equipment(po.id)
            db4 = SessionLocal()
            from models import Equipment
            equipments = db4.query(Equipment).filter(
                Equipment.model_id == po.model_id,
                Equipment.status == 'in_stock'
            ).all()
            if not equipments:
                equipments = db4.query(Equipment).filter(
                    Equipment.model_id == po.model_id
                ).all()
            print(f"可用设备数量: {len(equipments)}")
            for eq in equipments:
                model_name = eq.model.model_name if eq.model else '未知型号'
                print(f"  - 资产编号: {eq.asset_code}, 型号: {model_name}, 状态: {eq.status}")
            db4.close()
        else:
            print("\n【步骤3-4】跳过采购，使用现有库存设备")
            print("-" * 50)
            db4 = SessionLocal()
            from models import Equipment
            equipments = db4.query(Equipment).filter(
                Equipment.status == 'in_stock'
            ).all()
            print(f"可用库存设备数量: {len(equipments)}")
            for eq in equipments:
                model_name = eq.model.model_name if eq.model else '未知型号'
                print(f"  - 资产编号: {eq.asset_code}, 型号: {model_name}")
            db4.close()
        
        print("\n【步骤5】分配设备给员工")
        print("-" * 50)
        from inventory import LendingManager
        
        db5a = SessionLocal()
        equip_for_assign = db5a.query(Equipment).filter(
            Equipment.status == 'in_stock'
        ).first()
        if not equip_for_assign:
            equip_for_assign = db5a.query(Equipment).first()
            if equip_for_assign:
                equip_for_assign.status = 'in_stock'
                equip_for_assign.employee_id = None
                db5a.commit()
        equipment_id = equip_for_assign.id
        asset_code = equip_for_assign.asset_code
        db5a.close()
        
        LendingManager.assign_equipment(
            application_id=application.id,
            equipment_id=equipment_id,
            operator_id='E006'
        )
        db5 = SessionLocal()
        from models import LendingAgreement
        agreement = db5.query(LendingAgreement).filter(
            LendingAgreement.equipment_id == equipment_id
        ).first()
        print(f"分配设备: {asset_code} -> {employee.name}")
        print(f"领用协议号: {agreement.id}")
        agreement_id = agreement.id
        db5.close()
        
        print("\n【步骤6】员工签署电子领用协议")
        print("-" * 50)
        LendingManager.sign_agreement(
            agreement_id=agreement_id,
            employee_id=applicant_id,
            signature='EMPLOYEE_SIGNATURE_001'
        )
        print("领用协议已签署，设备状态更新为: in_use")
        
        print("\n【步骤7】设备报修流程")
        print("-" * 50)
        from repair import RepairManager
        
        RepairManager.create_repair_request(
            equipment_id=equipment_id,
            reporter_id=applicant_id,
            description='电脑无法开机，电源指示灯不亮'
        )
        db6 = SessionLocal()
        from models import RepairRequest
        repair = db6.query(RepairRequest).filter(
            RepairRequest.equipment_id == equipment_id
        ).order_by(RepairRequest.created_at.desc()).first()
        print(f"报修单号: {repair.id}")
        print(f"是否在保: {'是' if repair.is_under_warranty else '否'}")
        print(f"预估费用: {repair.estimated_cost}元")
        is_under_warranty = repair.is_under_warranty
        repair_id = repair.id
        estimated_cost = repair.estimated_cost
        db6.close()
        
        RepairManager.process_repair(repair_id)
        print(f"维修处理: 已{'返厂维修' if is_under_warranty else '指派工程师'}")
        
        RepairManager.update_repair_status(
            repair_id=repair_id,
            status='completed',
            actual_cost=estimated_cost
        )
        print("维修已完成，设备恢复使用")
        
        print("\n【步骤8】生成年度盘点任务")
        print("-" * 50)
        from inventory_check import InventoryCheckManager
        
        InventoryCheckManager.create_annual_task()
        db7 = SessionLocal()
        from models import InventoryCheckTask
        task = db7.query(InventoryCheckTask).order_by(
            InventoryCheckTask.created_at.desc()
        ).first()
        task_id = task.id
        print(f"盘点任务号: {task_id}")
        print(f"盘点年度: {task.year}")
        db7.close()
        
        InventoryCheckManager.start_check_task(task_id)
        
        records = InventoryCheckManager.get_employee_pending_records(applicant_id, task_id)
        print(f"待盘点设备数: {len(records)}")
        
        for record in records:
            InventoryCheckManager.scan_and_confirm(
                record_id=record.id,
                employee_id=applicant_id,
                check_result='normal',
                remark='设备正常使用中'
            )
        print("员工扫码确认完成")
        
        progress = InventoryCheckManager.get_task_progress(task_id)
        print(f"盘点进度: {progress['progress']}%")
        
        InventoryCheckManager.complete_task(task_id)
        print("年度盘点任务完成")
        
        print("\n【步骤9】设备报废流程")
        print("-" * 50)
        from scrap import ScrapManager
        
        can_scrap, msg, residual_value = ScrapManager.validate_residual_value(equipment_id)
        print(f"报废评估: {msg}")
        
        ScrapManager.create_scrap_application(
            equipment_id=equipment_id,
            applicant_id=applicant_id,
            reason='设备已使用多年，性能无法满足工作需求'
        )
        db8 = SessionLocal()
        scrap = db8.query(ScrapApplication).filter(
            ScrapApplication.equipment_id == equipment_id
        ).order_by(ScrapApplication.created_at.desc()).first()
        scrap_id = scrap.id
        print(f"报废申请号: {scrap_id}")
        print(f"剩余价值: {scrap.residual_value}元")
        
        scrap_app = db8.query(ScrapApplication).filter(ScrapApplication.id == scrap_id).first()
        if scrap_app:
            scrap_app.status = 'approved'
            scrap_app.approved_at = datetime.now()
            db8.commit()
            print("报废申请已自动通过审批")
        db8.close()
        
        ScrapManager.process_scrap(scrap_id, parts_recycled='内存、硬盘', operator_id='E006')
        print("设备已完成报废处理，配件已回收")
        
        print("\n【步骤10】生成统计报表")
        print("-" * 50)
        from reports import ReportGenerator
        
        equip_stats = ReportGenerator.get_equipment_statistics()
        print(f"设备总数: {equip_stats['total_count']}")
        print(f"使用率: {equip_stats['usage_rate']}%")
        print(f"总采购价值: {equip_stats['total_purchase_value']}元")
        print(f"当前总价值: {equip_stats['total_value']}元")
        
        repair_stats = ReportGenerator.get_repair_statistics()
        print(f"报修总数: {repair_stats['total_repairs']}")
        print(f"平均维修成本: {repair_stats['avg_cost']}元")
        print(f"故障率: {repair_stats['failure_rate']}%")
        
        excel_path = ReportGenerator.generate_excel_report()
        pdf_path = ReportGenerator.generate_pdf_report()
        print(f"\nExcel报表: {excel_path}")
        print(f"PDF报表: {pdf_path}")
        
        print("\n" + "=" * 70)
        print("全流程演示完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"演示过程出错: {str(e)}")
        import traceback
        traceback.print_exc()


def show_menu():
    print("\n" + "=" * 60)
    print("企业级员工办公设备全生命周期自动化管理系统")
    print("=" * 60)
    print("1. 初始化数据库")
    print("2. 运行完整流程演示")
    print("3. 生成统计报表")
    print("4. 查询设备信息")
    print("5. 启动定时任务调度器")
    print("6. 查看设备统计信息")
    print("0. 退出系统")
    print("-" * 60)


def main():
    print("正在初始化系统...")
    init_db()
    print("数据库初始化完成！")
    
    while True:
        show_menu()
        choice = input("请选择操作 (0-6): ").strip()
        
        if choice == '0':
            print("感谢使用，再见！")
            break
        
        elif choice == '1':
            seed_database()
        
        elif choice == '2':
            demo_full_workflow()
        
        elif choice == '3':
            print("正在生成报表...")
            from reports import ReportGenerator
            excel_path = ReportGenerator.generate_excel_report()
            pdf_path = ReportGenerator.generate_pdf_report()
            print(f"Excel报表: {excel_path}")
            print(f"PDF报表: {pdf_path}")
        
        elif choice == '4':
            from query import EquipmentQuery
            keyword = input("请输入资产编号/序列号关键词 (直接回车查看全部): ").strip()
            result = EquipmentQuery.query(keyword=keyword, page_size=20)
            print(f"\n共找到 {result['total']} 条记录")
            for eq in result['data']:
                model_name = eq.model.model_name if eq.model else 'Unknown'
                emp_name = eq.employee.name if eq.employee else '未分配'
                print(f"  {eq.asset_code} | {model_name} | {eq.status} | {emp_name}")
        
        elif choice == '5':
            from scheduler import init_scheduler, get_scheduled_jobs, run_task_now
            init_scheduler()
            jobs = get_scheduled_jobs()
            print("定时任务已启动:")
            for job in jobs:
                print(f"  {job['name']} - 下次执行: {job['next_run_time']}")
            
            run_now = input("是否立即执行一次日报? (y/n): ").strip().lower()
            if run_now == 'y':
                run_task_now('daily')
                print("日报执行完成！")
        
        elif choice == '6':
            from reports import ReportGenerator
            stats = ReportGenerator.get_equipment_statistics()
            repair_stats = ReportGenerator.get_repair_statistics()
            dep_stats = ReportGenerator.get_depreciation_statistics()
            
            print("\n设备统计:")
            print(f"  总数: {stats['total_count']}")
            print(f"  使用中: {stats['in_use_count']}")
            print(f"  在库: {stats['in_stock_count']}")
            print(f"  维修中: {stats['repair_count']}")
            print(f"  使用率: {stats['usage_rate']}%")
            print(f"  总价值: {stats['total_value']:.2f}元")
            
            print("\n维修统计:")
            print(f"  报修总数: {repair_stats['total_repairs']}")
            print(f"  平均维修成本: {repair_stats['avg_cost']}元")
            print(f"  故障率: {repair_stats['failure_rate']}%")
            
            print("\n折旧统计:")
            print(f"  月折旧额: {dep_stats['monthly_depreciation']:.2f}元")
            print(f"  累计折旧: {dep_stats['total_depreciated']:.2f}元")
        
        else:
            print("无效的选择，请重新输入！")
        
        input("\n按回车键继续...")


if __name__ == '__main__':
    main()
