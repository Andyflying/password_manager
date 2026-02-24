"""
加密/解密模块，用于安全地存储密码数据
使用AES-GCM加密算法（带完整性验证）和PBKDF2密钥派生
"""

import os
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from typing import Tuple, Optional


class Encryptor:
    """
    加密/解密类，用于处理密码数据的加密和解密
    使用 AES-GCM 模式提供加密和完整性验证
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

    def encrypt(self, data: dict) -> Tuple[bytes, bytes, bytes, bytes]:
        """
        加密数据

        :param data: 要加密的数据（字典）
        :return: (salt, iv, ciphertext, auth_tag)
        """
        json_data = json.dumps(data).encode('utf-8')

        salt = os.urandom(16)
        iv = os.urandom(12)

        key = self._derive_key(salt)

        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(json_data) + encryptor.finalize()
        auth_tag = encryptor.tag

        return salt, iv, ciphertext, auth_tag

    def decrypt(self, salt: bytes, iv: bytes, ciphertext: bytes, auth_tag: bytes) -> Optional[dict]:
        """
        解密数据（GCM模式，带完整性验证）

        :param salt: 盐值
        :param iv: 初始化向量
        :param ciphertext: 密文
        :param auth_tag: 认证标签
        :return: 解密后的数据（字典）或None
        """
        try:
            key = self._derive_key(salt)

            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, auth_tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            data = json.loads(plaintext.decode('utf-8'))
            return data
        except Exception as e:
            print(f"解密失败: {e}")
            return None


def test_encryption():
    """测试加密和解密功能"""
    encryptor = Encryptor("my_secure_password")
    original_data = {"username": "test_user", "password": "test_password"}

    salt, iv, ciphertext, auth_tag = encryptor.encrypt(original_data)
    print("加密成功")
    print(f"salt: {len(salt)} bytes, iv: {len(iv)} bytes, auth_tag: {len(auth_tag)} bytes")

    decrypted_data = encryptor.decrypt(salt, iv, ciphertext, auth_tag)
    print(f"解密结果: {decrypted_data}")

    assert original_data == decrypted_data
    print("加密/解密测试通过")


if __name__ == "__main__":
    test_encryption()
