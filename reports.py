import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import cm
from models import (
    SessionLocal, Equipment, RepairRequest, EquipmentModel,
    Employee, Department, Application, PurchaseOrder,
    DepreciationRecord, ScrapApplication
)
from utils import calculate_usage_rate, calculate_failure_rate, format_date, chunk_list
from config import REPORT_DIR, DEPRECIATION_MONTHS
from logger import log_operation, logger


class ReportGenerator:
    
    @staticmethod
    def get_equipment_statistics(start_date=None, end_date=None):
        db = SessionLocal()
        try:
            query = db.query(Equipment)
            
            if start_date:
                query = query.filter(Equipment.created_at >= start_date)
            if end_date:
                query = query.filter(Equipment.created_at <= end_date)
            
            equipments = query.all()
            
            total_count = len(equipments)
            in_use_count = sum(1 for e in equipments if e.status == 'in_use')
            in_stock_count = sum(1 for e in equipments if e.status == 'in_stock')
            repair_count = sum(1 for e in equipments if e.status == 'under_repair')
            scrap_count = sum(1 for e in equipments if e.status == 'scrapped')
            lost_count = sum(1 for e in equipments if e.status == 'lost')
            
            usage_rate = calculate_usage_rate(total_count - scrap_count - lost_count, in_use_count)
            
            type_stats = {}
            for equip in equipments:
                type_name = equip.model.type.name if equip.model and equip.model.type else 'Unknown'
                if type_name not in type_stats:
                    type_stats[type_name] = {'total': 0, 'in_use': 0, 'in_stock': 0}
                type_stats[type_name]['total'] += 1
                if equip.status == 'in_use':
                    type_stats[type_name]['in_use'] += 1
                elif equip.status == 'in_stock':
                    type_stats[type_name]['in_stock'] += 1
            
            total_value = sum(e.current_value or 0 for e in equipments)
            total_purchase_value = sum(e.purchase_price for e in equipments)
            
            return {
                'total_count': total_count,
                'in_use_count': in_use_count,
                'in_stock_count': in_stock_count,
                'repair_count': repair_count,
                'scrap_count': scrap_count,
                'lost_count': lost_count,
                'usage_rate': usage_rate,
                'type_stats': type_stats,
                'total_value': total_value,
                'total_purchase_value': total_purchase_value,
                'total_depreciation': total_purchase_value - total_value
            }
        finally:
            db.close()
    
    @staticmethod
    def get_repair_statistics(start_date=None, end_date=None):
        db = SessionLocal()
        try:
            query = db.query(RepairRequest)
            
            if start_date:
                query = query.filter(RepairRequest.created_at >= start_date)
            if end_date:
                query = query.filter(RepairRequest.created_at <= end_date)
            
            repairs = query.all()
            
            total_repairs = len(repairs)
            completed_repairs = sum(1 for r in repairs if r.status == 'completed')
            warranty_repairs = sum(1 for r in repairs if r.is_under_warranty)
            paid_repairs = sum(1 for r in repairs if not r.is_under_warranty)
            
            total_cost = sum(r.actual_cost or r.estimated_cost for r in repairs if r.status == 'completed')
            avg_cost = total_cost / completed_repairs if completed_repairs > 0 else 0
            
            type_stats = {}
            for repair in repairs:
                equip = repair.equipment
                type_name = equip.model.type.name if equip and equip.model and equip.model.type else 'Unknown'
                if type_name not in type_stats:
                    type_stats[type_name] = 0
                type_stats[type_name] += 1
            
            equipments = db.query(Equipment).all()
            total_equip = len(equipments)
            failure_rate = calculate_failure_rate(total_equip, total_repairs)
            
            return {
                'total_repairs': total_repairs,
                'completed_repairs': completed_repairs,
                'warranty_repairs': warranty_repairs,
                'paid_repairs': paid_repairs,
                'total_cost': round(total_cost, 2),
                'avg_cost': round(avg_cost, 2),
                'type_stats': type_stats,
                'failure_rate': failure_rate
            }
        finally:
            db.close()
    
    @staticmethod
    def get_depreciation_statistics():
        db = SessionLocal()
        try:
            equipments = db.query(Equipment).filter(
                Equipment.status != 'scrapped'
            ).all()
            
            monthly_depreciation = sum(e.purchase_price / DEPRECIATION_MONTHS for e in equipments)
            total_current_value = sum(e.current_value or 0 for e in equipments)
            total_purchase = sum(e.purchase_price for e in equipments)
            
            records = db.query(DepreciationRecord).order_by(
                DepreciationRecord.period
            ).all()
            
            period_data = {}
            for record in records:
                if record.period not in period_data:
                    period_data[record.period] = {'amount': 0, 'count': 0}
                period_data[record.period]['amount'] += record.depreciation_amount
                period_data[record.period]['count'] += 1
            
            return {
                'monthly_depreciation': round(monthly_depreciation, 2),
                'total_current_value': round(total_current_value, 2),
                'total_purchase': round(total_purchase, 2),
                'total_depreciated': round(total_purchase - total_current_value, 2),
                'period_data': period_data
            }
        finally:
            db.close()
    
    @staticmethod
    def generate_trend_charts(output_dir=None):
        if output_dir is None:
            output_dir = REPORT_DIR
        
        db = SessionLocal()
        try:
            today = datetime.now()
            months = []
            for i in range(11, -1, -1):
                month_start = today - relativedelta(months=i)
                months.append(month_start.strftime('%Y-%m'))
            
            monthly_data = {
                'months': months,
                'new_equipment': [],
                'repair_count': [],
                'scrap_count': []
            }
            
            for month in months:
                month_start = datetime.strptime(month + '-01', '%Y-%m-%d')
                if month_start.month == 12:
                    month_end = datetime(month_start.year + 1, 1, 1)
                else:
                    month_end = datetime(month_start.year, month_start.month + 1, 1)
                
                new_count = db.query(Equipment).filter(
                    Equipment.created_at >= month_start,
                    Equipment.created_at < month_end
                ).count()
                
                repair_count = db.query(RepairRequest).filter(
                    RepairRequest.created_at >= month_start,
                    RepairRequest.created_at < month_end
                ).count()
                
                scrap_count = db.query(ScrapApplication).filter(
                    ScrapApplication.created_at >= month_start,
                    ScrapApplication.created_at < month_end,
                    ScrapApplication.status == 'approved'
                ).count()
                
                monthly_data['new_equipment'].append(new_count)
                monthly_data['repair_count'].append(repair_count)
                monthly_data['scrap_count'].append(scrap_count)
            
            chart_paths = {}
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(months, monthly_data['new_equipment'], marker='o', label='新增设备', linewidth=2)
            ax.plot(months, monthly_data['repair_count'], marker='s', label='报修数量', linewidth=2)
            ax.plot(months, monthly_data['scrap_count'], marker='^', label='报废数量', linewidth=2)
            ax.set_title('设备管理趋势（近12个月）', fontsize=14, fontweight='bold')
            ax.set_xlabel('月份', fontsize=12)
            ax.set_ylabel('数量', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            trend_path = os.path.join(output_dir, 'trend_chart.png')
            plt.savefig(trend_path, dpi=150, bbox_inches='tight')
            plt.close()
            chart_paths['trend'] = trend_path
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            equip_stats = ReportGenerator.get_equipment_statistics()
            status_labels = ['使用中', '在库', '维修中', '已报废', '丢失']
            status_values = [
                equip_stats['in_use_count'],
                equip_stats['in_stock_count'],
                equip_stats['repair_count'],
                equip_stats['scrap_count'],
                equip_stats['lost_count']
            ]
            colors_list = ['#52c41a', '#1890ff', '#faad14', '#8c8c8c', '#f5222d']
            ax1.pie(status_values, labels=status_labels, autopct='%1.1f%%', colors=colors_list)
            ax1.set_title('设备状态分布', fontsize=12, fontweight='bold')
            
            repair_stats = ReportGenerator.get_repair_statistics()
            repair_labels = ['在保内维修', '保外维修']
            repair_values = [repair_stats['warranty_repairs'], repair_stats['paid_repairs']]
            ax2.pie(repair_values, labels=repair_labels, autopct='%1.1f%%', colors=['#52c41a', '#faad14'])
            ax2.set_title('维修类型分布', fontsize=12, fontweight='bold')
            
            plt.tight_layout()
            pie_path = os.path.join(output_dir, 'pie_charts.png')
            plt.savefig(pie_path, dpi=150, bbox_inches='tight')
            plt.close()
            chart_paths['pie'] = pie_path
            
            return chart_paths
        except Exception as e:
            logger.error(f"Failed to generate charts: {str(e)}")
            return {}
        finally:
            db.close()
    
    @staticmethod
    def generate_excel_report(output_path=None):
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(REPORT_DIR, f'equipment_report_{timestamp}.xlsx')
        
        db = SessionLocal()
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                equip_stats = ReportGenerator.get_equipment_statistics()
                repair_stats = ReportGenerator.get_repair_statistics()
                dep_stats = ReportGenerator.get_depreciation_statistics()
                
                summary_data = {
                    '指标': ['设备总数', '使用中', '在库', '维修中', '已报废', '丢失',
                           '使用率', '总采购价值', '当前总价值', '累计折旧',
                           '报修总数', '已完成维修', '平均维修成本', '故障率',
                           '月折旧额'],
                    '数值': [
                        equip_stats['total_count'],
                        equip_stats['in_use_count'],
                        equip_stats['in_stock_count'],
                        equip_stats['repair_count'],
                        equip_stats['scrap_count'],
                        equip_stats['lost_count'],
                        f"{equip_stats['usage_rate']}%",
                        f"{equip_stats['total_purchase_value']:.2f}",
                        f"{equip_stats['total_value']:.2f}",
                        f"{equip_stats['total_depreciation']:.2f}",
                        repair_stats['total_repairs'],
                        repair_stats['completed_repairs'],
                        f"{repair_stats['avg_cost']:.2f}",
                        f"{repair_stats['failure_rate']}%",
                        f"{dep_stats['monthly_depreciation']:.2f}"
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='汇总统计', index=False)
                
                equipments = db.query(Equipment).all()
                equip_data = []
                for e in equipments:
                    equip_data.append({
                        '资产编号': e.asset_code,
                        '设备类型': e.model.type.name if e.model and e.model.type else '',
                        '品牌型号': f"{e.model.brand if e.model else ''} {e.model.model_name if e.model else ''}",
                        '序列号': e.serial_number,
                        '状态': e.status,
                        '使用人': e.employee.name if e.employee else '',
                        '采购价格': e.purchase_price,
                        '采购日期': format_date(e.purchase_date),
                        '当前价值': e.current_value,
                        '保修到期': format_date(e.warranty_end_date)
                    })
                pd.DataFrame(equip_data).to_excel(writer, sheet_name='设备清单', index=False)
                
                repairs = db.query(RepairRequest).order_by(RepairRequest.created_at.desc()).all()
                repair_data = []
                for r in repairs:
                    repair_data.append({
                        '报修单号': r.id,
                        '设备编号': r.equipment.asset_code if r.equipment else '',
                        '报修人': r.reporter.name if r.reporter else '',
                        '问题描述': r.description,
                        '是否在保': '是' if r.is_under_warranty else '否',
                        '预估费用': r.estimated_cost,
                        '实际费用': r.actual_cost,
                        '状态': r.status,
                        '报修时间': format_date(r.created_at),
                        '完成时间': format_date(r.completed_at)
                    })
                pd.DataFrame(repair_data).to_excel(writer, sheet_name='维修记录', index=False)
                
                depts = db.query(Department).all()
                dept_data = []
                for dept in depts:
                    dept_equips = db.query(Equipment).join(Employee).filter(
                        Employee.department_id == dept.id
                    ).all()
                    dept_data.append({
                        '部门': dept.name,
                        '预算总额': dept.budget,
                        '已使用预算': dept.used_budget,
                        '剩余预算': dept.budget - dept.used_budget,
                        '设备数量': len(dept_equips),
                        '设备总价值': sum(e.current_value or 0 for e in dept_equips)
                    })
                pd.DataFrame(dept_data).to_excel(writer, sheet_name='部门统计', index=False)
            
            logger.info(f"Excel report generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate excel report: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def generate_pdf_report(output_path=None):
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(REPORT_DIR, f'equipment_report_{timestamp}.pdf')
        
        try:
            chart_paths = ReportGenerator.generate_trend_charts()
            
            equip_stats = ReportGenerator.get_equipment_statistics()
            repair_stats = ReportGenerator.get_repair_statistics()
            dep_stats = ReportGenerator.get_depreciation_statistics()
            
            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                  leftMargin=2*cm, rightMargin=2*cm,
                                  topMargin=2*cm, bottomMargin=2*cm)
            
            story = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=20,
                spaceAfter=30,
                textColor=colors.HexColor('#1890ff')
            )
            
            story.append(Paragraph('企业设备管理统计报告', title_style))
            story.append(Paragraph(f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
            
            story.append(Paragraph('一、核心指标概览', styles['Heading2']))
            story.append(Spacer(1, 0.3*cm))
            
            summary_data = [
                ['指标', '数值', '指标', '数值'],
                ['设备总数', str(equip_stats['total_count']), '使用率', f"{equip_stats['usage_rate']}%"],
                ['使用中', str(equip_stats['in_use_count']), '故障率', f"{repair_stats['failure_rate']}%"],
                ['在库', str(equip_stats['in_stock_count']), '月折旧额', f"{dep_stats['monthly_depreciation']}元"],
                ['总采购价值', f"{equip_stats['total_purchase_value']:.2f}元", '平均维修成本', f"{repair_stats['avg_cost']}元"],
                ['当前总价值', f"{equip_stats['total_value']:.2f}元", '累计折旧', f"{equip_stats['total_depreciation']:.2f}元"]
            ]
            
            t = Table(summary_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1890ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.gray)
            ]))
            story.append(t)
            story.append(Spacer(1, 0.8*cm))
            
            if 'trend' in chart_paths:
                story.append(Paragraph('二、趋势分析图表', styles['Heading2']))
                story.append(Spacer(1, 0.3*cm))
                img = Image(chart_paths['trend'], width=16*cm, height=9*cm)
                story.append(img)
                story.append(Spacer(1, 0.5*cm))
            
            if 'pie' in chart_paths:
                story.append(Paragraph('三、设备与维修分布', styles['Heading2']))
                story.append(Spacer(1, 0.3*cm))
                img = Image(chart_paths['pie'], width=16*cm, height=7*cm)
                story.append(img)
                story.append(Spacer(1, 0.5*cm))
            
            story.append(Paragraph('四、设备类型统计', styles['Heading2']))
            story.append(Spacer(1, 0.3*cm))
            
            type_data = [['设备类型', '总数', '使用中', '在库', '使用率']]
            for type_name, stats in equip_stats['type_stats'].items():
                usage = calculate_usage_rate(stats['total'], stats['in_use'])
                type_data.append([
                    type_name,
                    str(stats['total']),
                    str(stats['in_use']),
                    str(stats['in_stock']),
                    f"{usage}%"
                ])
            
            t2 = Table(type_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#52c41a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.gray)
            ]))
            story.append(t2)
            
            doc.build(story)
            
            logger.info(f"PDF report generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate pdf report: {str(e)}")
            raise


class QueryExporter:
    
    @staticmethod
    def query_lifecycle(employee_id=None, model_id=None, start_date=None, end_date=None, equipment_type=None):
        db = SessionLocal()
        try:
            query = db.query(Equipment)
            
            if employee_id:
                query = query.filter(Equipment.employee_id == employee_id)
            if model_id:
                query = query.filter(Equipment.model_id == model_id)
            if equipment_type:
                query = query.join(EquipmentModel).filter(EquipmentModel.type_id == equipment_type)
            if start_date:
                query = query.filter(Equipment.purchase_date >= start_date)
            if end_date:
                query = query.filter(Equipment.purchase_date <= end_date)
            
            equipments = query.order_by(Equipment.created_at.desc()).all()
            
            results = []
            for equip in equipments:
                repairs = db.query(RepairRequest).filter(
                    RepairRequest.equipment_id == equip.id
                ).order_by(RepairRequest.created_at.desc()).all()
                
                scraps = db.query(ScrapApplication).filter(
                    ScrapApplication.equipment_id == equip.id
                ).first()
                
                results.append({
                    'equipment': equip,
                    'repairs': repairs,
                    'scrap': scraps,
                    'repair_count': len(repairs),
                    'total_repair_cost': sum(r.actual_cost or 0 for r in repairs if r.status == 'completed')
                })
            
            return results
        finally:
            db.close()
    
    @staticmethod
    def export_to_excel(data, output_path=None, sheet_name='Sheet1'):
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(REPORT_DIR, f'export_{timestamp}.xlsx')
        
        export_data = []
        for item in data:
            equip = item['equipment'] if isinstance(item, dict) else item
            row = {
                '资产编号': equip.asset_code,
                '设备类型': equip.model.type.name if equip.model and equip.model.type else '',
                '品牌': equip.model.brand if equip.model else '',
                '型号': equip.model.model_name if equip.model else '',
                '状态': equip.status,
                '使用人': equip.employee.name if equip.employee else '',
                '使用人工号': equip.employee_id or '',
                '采购价格': equip.purchase_price,
                '采购日期': format_date(equip.purchase_date),
                '当前价值': equip.current_value,
                '保修到期': format_date(equip.warranty_end_date),
                '维修次数': item.get('repair_count', 0) if isinstance(item, dict) else 0,
                '累计维修费用': item.get('total_repair_cost', 0) if isinstance(item, dict) else 0
            }
            export_data.append(row)
        
        df = pd.DataFrame(export_data)
        df.to_excel(output_path, sheet_name=sheet_name, index=False, engine='openpyxl')
        
        logger.info(f"Exported {len(export_data)} records to {output_path}")
        return output_path
    
    @staticmethod
    def batch_export(equipments, output_path=None):
        return QueryExporter.export_to_excel(equipments, output_path, '设备全生命周期记录')


def run_daily_report():
    logger.info("Starting daily report generation...")
    
    try:
        excel_path = ReportGenerator.generate_excel_report()
        pdf_path = ReportGenerator.generate_pdf_report()
        
        log_operation(
            'system',
            '生成日报',
            details={
                'excel_path': excel_path,
                'pdf_path': pdf_path
            }
        )
        
        logger.info(f"Daily reports generated: Excel={excel_path}, PDF={pdf_path}")
        return {'excel': excel_path, 'pdf': pdf_path}
    except Exception as e:
        logger.error(f"Failed to generate daily report: {str(e)}")
        raise
