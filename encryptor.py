"""
加密/解密模块，用于安全地存储密码数据
使用AES加密算法和PBKDF2密钥派生
"""

import os
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from typing import Tuple, Optional


class Encryptor:
    """
    加密/解密类，用于处理密码数据的加密和解密
    """

    def __init__(self, password: str):
        """
        初始化加密器

        :param password: 用户提供的密码，用于派生加密密钥
        """
        self.password = password.encode('utf-8')

    def _derive_key(self, salt: bytes) -> bytes:
        """
        从用户密码和盐值派生加密密钥

        :param salt: 盐值
        :return: 派生的密钥
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.password)

    def encrypt(self, data: dict) -> Tuple[bytes, bytes, bytes]:
        """
        加密数据

        :param data: 要加密的数据（字典）
        :return: (salt, iv, ciphertext)
        """
        # 将数据转换为JSON字符串并编码为字节
        json_data = json.dumps(data).encode('utf-8')

        # 生成随机盐值和IV
        salt = os.urandom(16)
        iv = os.urandom(16)

        # 派生密钥
        key = self._derive_key(salt)

        # 创建加密器
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()

        # 添加PKCS7填充
        json_length = len(json_data)
        padding_length = 16 - (json_length % 16)
        padded_data = json_data + bytes([padding_length] * padding_length)

        # 执行加密
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return salt, iv, ciphertext

    def decrypt(self, salt: bytes, iv: bytes, ciphertext: bytes) -> Optional[dict]:
        """
        解密数据

        :param salt: 盐值
        :param iv: 初始化向量
        :param ciphertext: 密文
        :return: 解密后的数据（字典）或None
        """
        try:
            # 派生密钥
            key = self._derive_key(salt)

            # 创建解密器
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()

            # 解密
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # 移除PKCS7填充
            padding_length = padded_plaintext[-1]
            plaintext = padded_plaintext[:-padding_length]

            # 解析JSON数据
            data = json.loads(plaintext.decode('utf-8'))
            return data
        except Exception as e:
            print(f"解密失败: {e}")
            return None


def test_encryption():
    """测试加密和解密功能"""
    encryptor = Encryptor("my_secure_password")
    original_data = {"username": "test_user", "password": "test_password"}

    # 加密数据
    salt, iv, ciphertext = encryptor.encrypt(original_data)
    print("加密成功")

    # 解密数据
    decrypted_data = encryptor.decrypt(salt, iv, ciphertext)
    print(f"解密结果: {decrypted_data}")

    assert original_data == decrypted_data
    print("加密/解密测试通过")


if __name__ == "__main__":
    test_encryption()