import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'equipment_management.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'

REPORT_DIR = os.path.join(BASE_DIR, 'reports')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

for directory in [REPORT_DIR, LOG_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)

BUDGET_APPROVAL_THRESHOLD = 500000
DEPRECIATION_MONTHS = 36
WARRANTY_MONTHS_DEFAULT = 12

POSITION_STANDARDS = {
    'CEO': {'laptop': 1, 'monitor': 2, 'phone': 1, 'max_budget': 50000},
    'Director': {'laptop': 1, 'monitor': 2, 'phone': 1, 'max_budget': 30000},
    'Manager': {'laptop': 1, 'monitor': 1, 'phone': 1, 'max_budget': 20000},
    'Engineer': {'laptop': 1, 'monitor': 1, 'phone': 0, 'max_budget': 25000},
    'Staff': {'laptop': 1, 'monitor': 1, 'phone': 0, 'max_budget': 12000},
    'Admin': {'laptop': 1, 'monitor': 1, 'phone': 1, 'max_budget': 10000},
    'Sales': {'laptop': 1, 'monitor': 0, 'phone': 1, 'max_budget': 15000},
}

PREFERRED_SUPPLIERS = [
    {'id': 'S001', 'name': '联想优选', 'rating': 4.8, 'categories': ['laptop', 'monitor', 'desktop']},
    {'id': 'S002', 'name': '戴尔商用', 'rating': 4.7, 'categories': ['laptop', 'monitor', 'desktop']},
    {'id': 'S003', 'name': '华为终端', 'rating': 4.6, 'categories': ['laptop', 'phone', 'tablet']},
    {'id': 'S004', 'name': '苹果企业', 'rating': 4.9, 'categories': ['laptop', 'phone', 'tablet']},
    {'id': 'S005', 'name': '惠普商用', 'rating': 4.5, 'categories': ['laptop', 'monitor', 'printer']},
]

WECHAT_WEBHOOK_URL = ''

SCHEDULED_TASK_TIME = '02:00'
