"""
密码数据库模块，用于管理加密的密码存储文件
"""

import os
import json
from typing import Dict, Any, Optional
from encryptor import Encryptor


class PasswordDB:
    """
    管理加密密码数据库
    """

    def __init__(self, db_path: str = "password_manager/data/passwords.enc"):
        """
        初始化密码数据库

        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.ensure_directory_exists()

    def ensure_directory_exists(self):
        """确保数据库目录存在"""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def load_data(self, password: str) -> Optional[Dict[str, Any]]:
        """
        使用提供的密码加载并解密数据

        :param password: 用于解密的密码
        :return: 解密后的数据或None
        """
        if not os.path.exists(self.db_path):
            # 如果文件不存在，返回空数据
            return {}

        try:
            with open(self.db_path, 'rb') as f:
                # 读取盐值 (前16字节)
                salt = f.read(16)
                # 读取IV (接下来16字节)
                iv = f.read(16)
                # 读取剩余的是密文
                ciphertext = f.read()

            if len(salt) != 16 or len(iv) != 16:
                print("数据库文件格式错误")
                return None

            # 使用密码创建加密器并解密
            encryptor = Encryptor(password)
            return encryptor.decrypt(salt, iv, ciphertext)

        except Exception as e:
            print(f"加载数据库失败: {e}")
            return None

    def save_data(self, password: str, data: Dict[str, Any]) -> bool:
        """
        使用提供的密码加密并保存数据

        :param password: 用于加密的密码
        :param data: 要保存的数据
        :return: 是否保存成功
        """
        try:
            # 使用密码创建加密器并加密
            encryptor = Encryptor(password)
            salt, iv, ciphertext = encryptor.encrypt(data)

            # 写入加密数据
            with open(self.db_path, 'wb') as f:
                f.write(salt)
                f.write(iv)
                f.write(ciphertext)

            return True

        except Exception as e:
            print(f"保存数据库失败: {e}")
            return False

    def initialize_database(self, password: str) -> bool:
        """
        初始化数据库（如果不存在）

        :param password: 用于加密的密码
        :return: 是否初始化成功
        """
        if os.path.exists(self.db_path):
            return True

        return self.save_data(password, {})

    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        更改数据库密码

        :param old_password: 旧密码
        :param new_password: 新密码
        :return: 是否更改成功
        """
        # 先尝试加载数据
        data = self.load_data(old_password)
        if data is None:
            print("旧密码错误，无法更改密码")
            return False

        # 使用新密码保存数据
        return self.save_data(new_password, data)


def test_password_db():
    """测试密码数据库功能"""
    import tempfile

    # 使用临时文件进行测试
    temp_db_path = tempfile.mktemp()

    try:
        # 创建数据库实例
        db = PasswordDB(temp_db_path)

        # 初始化数据库
        initial_success = db.initialize_database("test_password")
        print(f"数据库初始化: {'成功' if initial_success else '失败'}")

        # 保存一些测试数据
        test_data = {
            "Gmail": {
                "account": "user@gmail.com",
                "password": "pass1",
                "email": "user@gmail.com",
                "phone": "13800138000",
                "remark": "测试产品"
            }
        }
        save_success = db.save_data("test_password", test_data)
        print(f"数据保存: {'成功' if save_success else '失败'}")

        # 读取数据
        loaded_data = db.load_data("test_password")
        print(f"数据读取: {'成功' if loaded_data is not None else '失败'}")
        if loaded_data:
            print(f"读取的数据: {loaded_data}")

        # 尝试用错误密码读取
        failed_load = db.load_data("wrong_password")
        print(f"错误密码读取: {'失败成功' if failed_load is None else '意外成功'}")

    finally:
        # 清理测试文件
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


if __name__ == "__main__":
    test_password_db()