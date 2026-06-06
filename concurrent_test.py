"""
企业设备管理系统 - 并发压力测试脚本

功能：
1. 模拟多用户并发创建设备申请
2. 模拟多用户并发查询设备信息
3. 测试数据库连接池稳定性
4. 测试并发下的数据一致性
5. 统计响应时间和成功率
"""

import os
import sys
import time
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import init_db, SessionLocal, Equipment, Employee
from procurement import ApplicationManager
from query import EquipmentQuery
from logger import logger


class ConcurrentTester:
    
    def __init__(self):
        self.results = defaultdict(list)
        self.lock = threading.Lock()
        self.success_count = 0
        self.failure_count = 0
    
    def test_create_application(self, user_id, test_id):
        """测试创建设备申请"""
        start_time = time.time()
        try:
            equipment_types = ['laptop', 'monitor', 'phone']
            eq_type = random.choice(equipment_types)
            
            app = ApplicationManager.create_application(
                applicant_id=user_id,
                equipment_type=eq_type,
                reason=f'并发测试申请 - {test_id}'
            )
            
            elapsed = time.time() - start_time
            with self.lock:
                self.success_count += 1
                self.results['create_application'].append({
                    'test_id': test_id,
                    'user_id': user_id,
                    'success': True,
                    'elapsed': elapsed,
                    'app_id': app.id
                })
            
            return True, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            with self.lock:
                self.failure_count += 1
                self.results['create_application'].append({
                    'test_id': test_id,
                    'user_id': user_id,
                    'success': False,
                    'elapsed': elapsed,
                    'error': str(e)
                })
            return False, elapsed
    
    def test_query_equipment(self, user_id, test_id):
        """测试设备查询"""
        start_time = time.time()
        try:
            keywords = ['laptop', 'ThinkPad', 'EQ', '']
            keyword = random.choice(keywords)
            
            result = EquipmentQuery.query(
                keyword=keyword,
                page=1,
                page_size=20
            )
            
            elapsed = time.time() - start_time
            with self.lock:
                self.success_count += 1
                self.results['query_equipment'].append({
                    'test_id': test_id,
                    'user_id': user_id,
                    'success': True,
                    'elapsed': elapsed,
                    'record_count': result['total']
                })
            
            return True, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            with self.lock:
                self.failure_count += 1
                self.results['query_equipment'].append({
                    'test_id': test_id,
                    'user_id': user_id,
                    'success': False,
                    'elapsed': elapsed,
                    'error': str(e)
                })
            return False, elapsed
    
    def test_db_connection(self, test_id):
        """测试数据库连接"""
        start_time = time.time()
        try:
            db = SessionLocal()
            equip_count = db.query(Equipment).count()
            emp_count = db.query(Employee).count()
            db.close()
            
            elapsed = time.time() - start_time
            with self.lock:
                self.success_count += 1
                self.results['db_connection'].append({
                    'test_id': test_id,
                    'success': True,
                    'elapsed': elapsed,
                    'equip_count': equip_count,
                    'emp_count': emp_count
                })
            
            return True, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            with self.lock:
                self.failure_count += 1
                self.results['db_connection'].append({
                    'test_id': test_id,
                    'success': False,
                    'elapsed': elapsed,
                    'error': str(e)
                })
            return False, elapsed
    
    def run_test(self, test_name, test_func, num_threads, num_requests):
        """运行指定测试"""
        print(f"\n{'='*60}")
        print(f"开始测试: {test_name}")
        print(f"并发线程数: {num_threads}, 总请求数: {num_requests}")
        print(f"{'='*60}")
        
        self.success_count = 0
        self.failure_count = 0
        
        user_ids = ['E001', 'E002', 'E003', 'E004', 'E005', 'E006', 'E007', 'E008', 'E009', 'E010']
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_requests):
                user_id = random.choice(user_ids)
                if test_func == self.test_db_connection:
                    futures.append(executor.submit(test_func, i))
                else:
                    futures.append(executor.submit(test_func, user_id, i))
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Test task failed: {str(e)}")
        
        total_time = time.time() - start_time
        
        test_results = self.results.get(test_name, [])
        
        success_tests = [r for r in test_results if r['success']]
        failure_tests = [r for r in test_results if not r['success']]
        
        if success_tests:
            avg_time = sum(r['elapsed'] for r in success_tests) / len(success_tests)
            max_time = max(r['elapsed'] for r in success_tests)
            min_time = min(r['elapsed'] for r in success_tests)
        else:
            avg_time = max_time = min_time = 0
        
        print(f"\n测试结果:")
        print(f"  总耗时: {total_time:.2f} 秒")
        print(f"  成功数: {len(success_tests)}")
        print(f"  失败数: {len(failure_tests)}")
        print(f"  成功率: {(len(success_tests)/len(test_results)*100):.2f}%")
        print(f"  平均响应时间: {avg_time*1000:.2f} ms")
        print(f"  最大响应时间: {max_time*1000:.2f} ms")
        print(f"  最小响应时间: {min_time*1000:.2f} ms")
        print(f"  QPS (每秒请求数): {len(test_results)/total_time:.2f}")
        
        if failure_tests:
            print(f"\n失败示例 (前5条):")
            for i, fail in enumerate(failure_tests[:5]):
                print(f"  {i+1}. 测试ID: {fail['test_id']}, 错误: {fail.get('error', 'Unknown')[:80]}")
        
        return {
            'test_name': test_name,
            'total_time': total_time,
            'success_count': len(success_tests),
            'failure_count': len(failure_tests),
            'success_rate': len(success_tests)/len(test_results)*100 if test_results else 0,
            'avg_response_time_ms': avg_time * 1000,
            'qps': len(test_results)/total_time if total_time > 0 else 0
        }
    
    def run_all_tests(self):
        """运行所有并发测试"""
        print("\n" + "="*70)
        print("企业设备管理系统 - 并发压力测试")
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        all_results = []
        
        print("\n" + "="*70)
        print("第一阶段: 数据库连接测试")
        print("="*70)
        result = self.run_test(
            "db_connection",
            self.test_db_connection,
            num_threads=50,
            num_requests=500
        )
        all_results.append(result)
        
        print("\n" + "="*70)
        print("第二阶段: 设备查询测试")
        print("="*70)
        result = self.run_test(
            "query_equipment",
            self.test_query_equipment,
            num_threads=30,
            num_requests=300
        )
        all_results.append(result)
        
        print("\n" + "="*70)
        print("第三阶段: 混合并发测试 (高负载)")
        print("="*70)
        self.results.clear()
        self.success_count = 0
        self.failure_count = 0
        
        user_ids = ['E001', 'E002', 'E003', 'E004', 'E005']
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            
            for i in range(200):
                user_id = random.choice(user_ids)
                futures.append(executor.submit(self.test_db_connection, f'db_{i}'))
            
            for i in range(200):
                user_id = random.choice(user_ids)
                futures.append(executor.submit(self.test_query_equipment, user_id, f'query_{i}'))
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Mixed test task failed: {str(e)}")
        
        total_time = time.time() - start_time
        total_requests = self.success_count + self.failure_count
        
        print(f"\n混合测试结果:")
        print(f"  总耗时: {total_time:.2f} 秒")
        print(f"  总请求数: {total_requests}")
        print(f"  成功数: {self.success_count}")
        print(f"  失败数: {self.failure_count}")
        print(f"  成功率: {(self.success_count/total_requests*100):.2f}%")
        print(f"  总QPS: {total_requests/total_time:.2f}")
        
        all_results.append({
            'test_name': 'mixed_concurrent',
            'total_time': total_time,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.success_count/total_requests*100 if total_requests > 0 else 0,
            'qps': total_requests/total_time if total_time > 0 else 0
        })
        
        print("\n" + "="*70)
        print("测试汇总报告")
        print("="*70)
        print(f"{'测试名称':<25} {'成功率':<10} {'平均响应(ms)':<15} {'QPS':<10}")
        print("-"*70)
        for res in all_results:
            avg_ms = res.get('avg_response_time_ms', 0)
            print(f"{res['test_name']:<25} {res['success_rate']:>8.2f}%  {avg_ms:>12.2f}     {res['qps']:>8.2f}")
        
        all_success = all(r['success_rate'] >= 95 for r in all_results)
        print("\n" + "="*70)
        if all_success:
            print("✅ 并发测试通过！所有测试成功率 >= 95%")
        else:
            print("⚠️  部分测试成功率低于 95%，建议进一步优化")
        print("="*70)
        
        return all_results


def main():
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成！")
    
    tester = ConcurrentTester()
    tester.run_all_tests()


if __name__ == '__main__':
    main()
