"""
密码管理模块，提供增删改查功能
"""

from typing import Dict, Optional, List
from password_db import PasswordDB


class PasswordManager:
    """
    密码管理器，提供对密码数据的CRUD操作
    """

    def __init__(self, db_path: str = "password_manager/data/passwords.enc"):
        """
        初始化密码管理器

        :param db_path: 数据库文件路径
        """
        self.db = PasswordDB(db_path)
        self.current_password = None

    def authenticate(self, password: str) -> bool:
        """
        使用密码验证身份

        :param password: 用户提供的密码
        :return: 是否验证成功
        """
        # 尝试加载数据以验证密码
        data = self.db.load_data(password)
        if data is not None:
            self.current_password = password
            return True
        return False

    def is_authenticated(self) -> bool:
        """
        检查是否已通过身份验证

        :return: 是否已认证
        """
        if self.current_password is None:
            return False

        # 验证当前密码是否仍然有效
        return self.db.load_data(self.current_password) is not None

    def _get_data(self) -> Optional[Dict]:
        """获取当前数据"""
        if not self.is_authenticated():
            print("请先使用正确密码进行身份验证")
            return None
        return self.db.load_data(self.current_password)

    def _save_data(self, data: Dict) -> bool:
        """保存数据"""
        if not self.is_authenticated():
            print("请先使用正确密码进行身份验证")
            return False
        return self.db.save_data(self.current_password, data)

    def add_password(self, product_name: str, account: str, password: str,
                     email: str = "", phone: str = "", remark: str = "") -> bool:
        """
        添加新的账户信息

        :param product_name: 产品名称（作为唯一标识）
        :param account: 账号
        :param password: 密码
        :param email: 邮箱（可选）
        :param phone: 手机号（可选）
        :param remark: 备注（可选）
        :return: 是否添加成功
        """
        data = self._get_data()
        if data is None:
            return False

        # 检查产品是否已存在
        if product_name in data:
            print(f"产品 '{product_name}' 已存在，请使用更新功能")
            return False

        # 添加新产品
        data[product_name] = {
            "account": account,
            "password": password,
            "email": email,
            "phone": phone,
            "remark": remark
        }

        return self._save_data(data)

    def get_password(self, product_name: str) -> Optional[Dict]:
        """
        获取指定产品的信息

        :param product_name: 产品名称
        :return: 账户信息或None
        """
        data = self._get_data()
        if data is None:
            return None

        if product_name in data:
            return data[product_name]
        else:
            print(f"产品 '{product_name}' 不存在")
            return None

    def update_password(self, product_name: str, account: str = None, password: str = None,
                        email: str = None, phone: str = None, remark: str = None) -> bool:
        """
        更新指定产品的信息

        :param product_name: 产品名称
        :param account: 新账号（可选）
        :param password: 新密码（可选）
        :param email: 新邮箱（可选）
        :param phone: 新手机号（可选）
        :param remark: 新备注（可选）
        :return: 是否更新成功
        """
        data = self._get_data()
        if data is None:
            return False

        if product_name not in data:
            print(f"产品 '{product_name}' 不存在")
            return False

        # 更新产品信息
        if account is not None:
            data[product_name]["account"] = account
        if password is not None:
            data[product_name]["password"] = password
        if email is not None:
            data[product_name]["email"] = email
        if phone is not None:
            data[product_name]["phone"] = phone
        if remark is not None:
            data[product_name]["remark"] = remark

        return self._save_data(data)

    def delete_password(self, product_name: str) -> bool:
        """
        删除指定产品

        :param product_name: 要删除的产品名称
        :return: 是否删除成功
        """
        data = self._get_data()
        if data is None:
            return False

        if product_name in data:
            del data[product_name]
            return self._save_data(data)
        else:
            print(f"产品 '{product_name}' 不存在")
            return False

    def list_products(self) -> List[str]:
        """
        列出所有产品名称（按字母正序排序）

        :return: 产品名称列表
        """
        data = self._get_data()
        if data is None:
            return []

        return sorted(list(data.keys()))

    def get_all_products(self) -> Optional[Dict]:
        """
        获取所有产品信息

        :return: 所有产品信息或None
        """
        return self._get_data()

    def change_master_password(self, new_password: str) -> bool:
        """
        更改主密码

        :param new_password: 新主密码
        :return: 是否更改成功
        """
        if not self.is_authenticated():
            print("请先使用正确密码进行身份验证")
            return False

        success = self.db.change_password(self.current_password, new_password)
        if success:
            self.current_password = new_password
        return success


def test_password_manager():
    """测试密码管理器功能"""
    import tempfile

    # 使用临时文件进行测试
    temp_db_path = tempfile.mktemp()

    try:
        # 创建密码管理器实例
        pm = PasswordManager(temp_db_path)

        # 初始化数据库
        pm.db.initialize_database("master_password")

        # 尝试认证
        auth_success = pm.authenticate("master_password")
        print(f"身份验证: {'成功' if auth_success else '失败'}")

        if not auth_success:
            print("认证失败，无法继续测试")
            return

        # 测试添加密码
        add_success = pm.add_password("Gmail", "user@gmail.com", "password123",
                                      "user@gmail.com", "13800138000", "个人邮箱")
        print(f"添加密码: {'成功' if add_success else '失败'}")

        # 测试获取密码
        product_info = pm.get_password("Gmail")
        print(f"获取密码: {'成功' if product_info is not None else '失败'}")
        if product_info:
            print(f"产品信息: {product_info}")

        # 测试列出产品
        products = pm.list_products()
        print(f"产品列表: {products}")

        # 测试更新密码
        update_success = pm.update_password("Gmail", password="new_password456")
        print(f"更新密码: {'成功' if update_success else '失败'}")

        # 验证更新
        updated_info = pm.get_password("Gmail")
        if updated_info:
            print(f"更新后密码: {updated_info['password']}")

        # 测试删除密码
        delete_success = pm.delete_password("Gmail")
        print(f"删除密码: {'成功' if delete_success else '失败'}")

        # 验证删除
        deleted_info = pm.get_password("Gmail")
        print(f"删除验证: {'已删除' if deleted_info is None else '未删除'}")

    finally:
        # 清理测试文件
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


if __name__ == "__main__":
    test_password_manager()