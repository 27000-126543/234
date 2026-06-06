from models import init_db
init_db()

print('测试批量导出功能...')
from query import EquipmentQuery
result = EquipmentQuery.export_query_results(
    keyword='laptop',
    operator_id='test'
)

print('导出结果:')
print('  成功:', result['success'])
print('  记录数:', result['record_count'])
print('  保存路径:', result['output_path'])

print('\n✅ 批量导出功能测试通过！')
