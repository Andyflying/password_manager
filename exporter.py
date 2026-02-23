"""
CSV导出模块，用于将密码数据导出为CSV格式
"""

import csv
import os
from typing import Dict, List
from password_manager import PasswordManager


class CSVExporter:
    """
    CSV导出器，将密码数据导出为CSV格式
    """

    def __init__(self, password_manager: PasswordManager):
        """
        初始化CSV导出器

        :param password_manager: 密码管理器实例
        """
        self.password_manager = password_manager

    def export_to_csv(self, csv_path: str) -> bool:
        """
        将所有密码数据导出到CSV文件

        :param csv_path: CSV文件输出路径
        :return: 是否导出成功
        """
        if not self.password_manager.is_authenticated():
            print("请先使用正确密码进行身份验证")
            return False

        # 获取所有产品数据
        all_data = self.password_manager.get_all_products()
        if all_data is None:
            print("无法获取账户数据")
            return False

        # 准备CSV数据
        csv_data = []
        for product_name, details in all_data.items():
            row = {
                "产品名称": product_name,
                "账号": details.get("account", ""),
                "密码": details.get("password", ""),
                "邮箱": details.get("email", ""),
                "手机号": details.get("phone", ""),
                "备注": details.get("remark", "")
            }
            csv_data.append(row)

        # 确保输出目录存在
        directory = os.path.dirname(csv_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # 写入CSV文件
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["产品名称", "账号", "密码", "邮箱", "手机号", "备注"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in csv_data:
                    writer.writerow(row)

            print(f"成功导出到CSV文件: {csv_path}")
            return True
        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False

    def export_selected_to_csv(self, csv_path: str, accounts: List[str]) -> bool:
        """
        将选定的账户导出到CSV文件

        :param csv_path: CSV文件输出路径
        :param accounts: 要导出的账户列表
        :return: 是否导出成功
        """
        if not self.password_manager.is_authenticated():
            print("请先使用正确密码进行身份验证")
            return False

        # 获取所有数据
        all_data = self.password_manager.get_all_products()
        if all_data is None:
            print("无法获取产品数据")
            return False

        # 过滤选定的产品
        csv_data = []
        for product_name in accounts:
            if product_name in all_data:
                details = all_data[product_name]
                row = {
                    "产品名称": product_name,
                    "账号": details.get("account", ""),
                    "密码": details.get("password", ""),
                    "邮箱": details.get("email", ""),
                    "手机号": details.get("phone", ""),
                    "备注": details.get("remark", "")
                }
                csv_data.append(row)
            else:
                print(f"产品 '{product_name}' 不存在，跳过")

        # 确保输出目录存在
        directory = os.path.dirname(csv_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # 写入CSV文件
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["产品名称", "账号", "密码", "邮箱", "手机号", "备注"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in csv_data:
                    writer.writerow(row)

            print(f"成功导出选定产品到CSV文件: {csv_path}")
            return True
        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False


def test_csv_exporter():
    """测试CSV导出功能"""
    import tempfile

    # 使用临时文件进行测试
    temp_db_path = tempfile.mktemp()
    temp_csv_path = tempfile.mktemp() + ".csv"

    try:
        # 创建密码管理器实例
        pm = PasswordManager(temp_db_path)

        # 初始化数据库
        pm.db.initialize_database("master_password")

        # 认证
        if not pm.authenticate("master_password"):
            print("认证失败")
            return

        # 添加一些测试数据
        pm.add_password("Gmail", "user@gmail.com", "password123",
                        "user@gmail.com", "13800138000", "个人邮箱")
        pm.add_password("Facebook", "user@facebook.com", "fb_password",
                        "user@facebook.com", "13900139000", "社交账号")

        # 创建CSV导出器
        exporter = CSVExporter(pm)

        # 测试完整导出
        export_success = exporter.export_to_csv(temp_csv_path)
        print(f"CSV导出: {'成功' if export_success else '失败'}")

        # 检查CSV文件内容
        if os.path.exists(temp_csv_path):
            with open(temp_csv_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"CSV文件内容:\n{content}")

    finally:
        # 清理测试文件
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)


if __name__ == "__main__":
    test_csv_exporter()