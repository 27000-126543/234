import uuid
import random
import string
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def generate_id(prefix=''):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{timestamp}{random_str}"


def generate_asset_code(category='EQ'):
    timestamp = datetime.now().strftime('%Y%m')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{category}-{timestamp}-{random_str}"


def calculate_depreciation(purchase_price, purchase_date, current_date=None, months=36):
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d %H:%M:%S')
    
    delta = relativedelta(current_date, purchase_date)
    months_passed = delta.years * 12 + delta.months
    
    if months_passed <= 0:
        return purchase_price, 0
    
    monthly_depreciation = purchase_price / months
    total_depreciation = monthly_depreciation * min(months_passed, months)
    current_value = max(purchase_price - total_depreciation, 0)
    
    return current_value, total_depreciation


def is_under_warranty(purchase_date, warranty_months=12):
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d %H:%M:%S')
    
    warranty_end = purchase_date + timedelta(days=warranty_months * 30)
    return datetime.now() <= warranty_end


def get_warranty_end_date(purchase_date, warranty_months=12):
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d %H:%M:%S')
    
    return purchase_date + timedelta(days=warranty_months * 30)


def format_date(date, fmt='%Y-%m-%d %H:%M:%S'):
    if date is None:
        return ''
    if isinstance(date, str):
        return date
    return date.strftime(fmt)


def parse_date(date_str):
    if isinstance(date_str, datetime):
        return date_str
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d', '%Y/%m/%d %H:%M:%S']:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return datetime.now()


def generate_qr_code_content(asset_code, equipment_id):
    return f"asset://{asset_code}?id={equipment_id}"


def get_month_period(date=None):
    if date is None:
        date = datetime.now()
    return date.strftime('%Y-%m')


def get_quarter_period(date=None):
    if date is None:
        date = datetime.now()
    quarter = (date.month - 1) // 3 + 1
    return f"{date.year}-Q{quarter}"


def calculate_usage_rate(total_count, in_use_count):
    if total_count == 0:
        return 0
    return round((in_use_count / total_count) * 100, 2)


def calculate_failure_rate(total_count, repair_count):
    if total_count == 0:
        return 0
    return round((repair_count / total_count) * 100, 2)


def chunk_list(lst, chunk_size=1000):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]
