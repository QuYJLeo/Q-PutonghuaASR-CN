import json

from utils.TestUtil import TestUtil

if __name__ == '__main__':
    authTool = TestUtil()
    # print(authTool.check())

    print(authTool.getUD())
    print(authTool.getMC())
    print(authTool.getRD())

    data = {
        "uuid": input("UUID："),
        "mac": input("MAC："),
        "user": input("USER："),
        "session": input("输入会话个数："),
        "token": authTool.getRD(),
        "valid": input("输入有效期：")
    }
    print("--------------------------------\n\n")
    print("auths: ")
    print("  - user:", data["user"])
    print("    session:", data["session"])
    print("    valid:", data["valid"])
    print("    token:", data["token"])
    print("    code:", authTool.desEncrypt(json.dumps(data)).decode('utf-8'))
