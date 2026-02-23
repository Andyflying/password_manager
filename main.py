"""
主应用程序，提供命令行界面来管理密码
"""

import getpass
import sys
from password_manager import PasswordManager
from exporter import CSVExporter


def print_menu():
    """打印主菜单"""
    print("\n" + "="*50)
    print("           密码管理器")
    print("="*50)
    print("1. 添加密码")
    print("2. 查看密码")
    print("3. 更新密码")
    print("4. 删除密码")
    print("5. 列出所有产品")
    print("6. 导出到CSV")
    print("7. 更改主密码")
    print("8. 退出")
    print("="*50)


DEFAULT_MASTER_PASSWORD = "000000"


def main():
    """主程序入口"""
    print("欢迎使用安全密码管理器！")

    # 创建密码管理器实例
    pm = PasswordManager()

    # 首次运行自动初始化数据库（使用默认密码）
    pm.db.initialize_database(DEFAULT_MASTER_PASSWORD)

    print("\n请输入主密码以访问密码数据库：")
    master_password = getpass.getpass("主密码: ")

    # 尝试认证
    if not pm.authenticate(master_password):
        print("密码错误，程序退出。")
        print(f"提示：初始密码为 '{DEFAULT_MASTER_PASSWORD}'，登录后可使用'更改主密码'功能修改")
        return

    print("认证成功！")

    while True:
        print_menu()
        choice = input("\n请选择操作 (1-8): ").strip()

        if choice == '1':
            # 添加密码
            print("\n--- 添加新密码 ---")
            product_name = input("产品名称: ").strip()
            account = input("账号: ").strip()
            password = getpass.getpass("密码: ")
            email = input("邮箱 (可选，直接回车跳过): ").strip()
            phone = input("手机号 (可选，直接回车跳过): ").strip()
            remark = input("备注 (可选，直接回车跳过): ").strip()

            if pm.add_password(product_name, account, password, email, phone, remark):
                print("密码添加成功！")
            else:
                print("密码添加失败！")

        elif choice == '2':
            # 查看密码
            print("\n--- 查看密码 ---")
            product_name = input("请输入产品名称: ").strip()

            product_info = pm.get_password(product_name)
            if product_info:
                print(f"\n产品名称: {product_name}")
                print(f"账号: {product_info['account']}")
                print(f"密码: {product_info['password']}")
                if product_info.get('email'):
                    print(f"邮箱: {product_info['email']}")
                if product_info.get('phone'):
                    print(f"手机号: {product_info['phone']}")
                if product_info.get('remark'):
                    print(f"备注: {product_info['remark']}")
            else:
                print("产品不存在或获取失败！")

        elif choice == '3':
            # 更新密码
            print("\n--- 更新密码 ---")
            product_name = input("请输入要更新的产品名称: ").strip()

            # 检查产品是否存在
            if not pm.get_password(product_name):
                print("产品不存在！")
                continue

            print("留空表示不更改该项")
            account_input = input("新账号 (留空则不变): ").strip()
            password_input = getpass.getpass("新密码 (留空则不变): ")
            email_input = input("新邮箱 (留空则不变): ").strip()
            phone_input = input("新手机号 (留空则不变): ").strip()
            remark_input = input("新备注 (留空则不变): ").strip()

            # 只传递非空值
            update_data = {}
            if account_input:
                update_data['account'] = account_input
            if password_input:
                update_data['password'] = password_input
            if email_input:
                update_data['email'] = email_input
            if phone_input:
                update_data['phone'] = phone_input
            if remark_input:
                update_data['remark'] = remark_input

            if update_data:
                if pm.update_password(product_name, **update_data):
                    print("密码更新成功！")
                else:
                    print("密码更新失败！")
            else:
                print("没有更改任何内容。")

        elif choice == '4':
            # 删除密码
            print("\n--- 删除密码 ---")
            product_name = input("请输入要删除的产品名称: ").strip()

            confirm = input(f"确认删除产品 '{product_name}' 吗？(y/n): ").lower()
            if confirm == 'y':
                if pm.delete_password(product_name):
                    print("密码删除成功！")
                else:
                    print("密码删除失败！")
            else:
                print("取消删除操作。")

        elif choice == '5':
            # 列出所有产品
            print("\n--- 所有产品 ---")
            products = pm.list_products()
            if products:
                print("产品列表:")
                for i, product in enumerate(products, 1):
                    print(f"{i}. {product}")
            else:
                print("暂无产品。")

        elif choice == '6':
            # 导出到CSV
            print("\n--- 导出到CSV ---")
            csv_path = input("请输入CSV文件保存路径 (例如: passwords.csv): ").strip()

            if not csv_path:
                print("未指定路径，使用默认路径 'passwords.csv'")
                csv_path = "passwords.csv"

            # 创建导出器并导出
            exporter = CSVExporter(pm)
            if exporter.export_to_csv(csv_path):
                print(f"成功导出到: {csv_path}")
            else:
                print("导出失败！")

        elif choice == '7':
            # 更改主密码
            print("\n--- 更改主密码 ---")
            current_password = getpass.getpass("请输入当前主密码: ")

            # 验证当前密码
            if not pm.authenticate(current_password):
                print("当前密码错误！")
                continue

            new_password = getpass.getpass("请输入新主密码: ")
            confirm_password = getpass.getpass("请再次输入新主密码: ")

            if new_password != confirm_password:
                print("两次输入的密码不一致！")
                continue

            if pm.change_master_password(new_password):
                print("主密码更改成功！")
                # 更新当前会话的密码
                master_password = new_password
            else:
                print("主密码更改失败！")

        elif choice == '8':
            # 退出
            print("感谢使用密码管理器，再见！")
            break

        else:
            print("无效选择，请重新输入！")

        # 按任意键继续
        input("\n按回车键继续...")


def quick_add():
    """快速添加密码的命令行接口"""
    # 支持: python main.py add <product_name> <account> <password> [email] [phone] [remark]
    if len(sys.argv) < 5:
        print("用法: python main.py add <产品名称> <账号> <密码> [邮箱] [手机号] [备注]")
        print("示例: python main.py add Gmail user@gmail.com mypassword")
        print("示例: python main.py add Gmail user@gmail.com mypassword user@gmail.com 13800138000 个人邮箱")
        return

    product_name = sys.argv[2]
    account = sys.argv[3]
    password = sys.argv[4]
    email = sys.argv[5] if len(sys.argv) > 5 else ""
    phone = sys.argv[6] if len(sys.argv) > 6 else ""
    remark = sys.argv[7] if len(sys.argv) > 7 else ""

    pm = PasswordManager()
    master_password = getpass.getpass("请输入主密码: ")

    if not pm.authenticate(master_password):
        print("主密码错误！")
        return

    if pm.add_password(product_name, account, password, email, phone, remark):
        print("密码添加成功！")
    else:
        print("密码添加失败！")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        quick_add()
    else:
        main()