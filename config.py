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

# 企业微信群机器人Webhook地址配置
# 配置说明：
# 1. 打开企业微信，进入需要接收预警的群聊
# 2. 点击群设置 -> 群机器人 -> 添加机器人
# 3. 选择"自定义"机器人，输入机器人名称（如"设备管理预警"）
# 4. 创建成功后会生成Webhook地址，格式如下：
#    https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# 5. 将完整的Webhook地址粘贴到下方即可
# 注意：此配置仅用于异常预警通知，如不需要可留空
WECHAT_WEBHOOK_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-webhook-key-here'

SCHEDULED_TASK_TIME = '02:00'
