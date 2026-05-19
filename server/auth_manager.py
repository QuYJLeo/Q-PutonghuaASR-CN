from utils.Config import IS_SERVER, AUTHS
from utils.HsProjectUtil import HsLicenseUtil
from utils.TestUtil import testUtil


class AuthManager:
    def __init__(self):
        self.is_server = IS_SERVER
        self.hs_license = testUtil if IS_SERVER else HsLicenseUtil()
        self.token_limits = {auth.get("token"): auth.get("session", 0) for auth in AUTHS}

    def check_access(self, config, current_ready_count):
        """验证 License, Token 和 并发数"""
        if self.is_server:
            # 1. 首先验证硬件指纹和授权码是否有效
            success = self.hs_license.check()
            if not success:
                return False, "服务端认证失败：授权码无效或硬件不匹配"
            # 2. 获取当前匹配到的授权对象的并发限制
            limit = self.hs_license.get_current_limit()  # 这里的 hs_license 实际上就是 testUtil

            # 3. 校验实时并发数
            if current_ready_count >= limit:
                return False, f"服务端连接数超限：当前{current_ready_count}，限制{limit}"
            return True, "server服务认证成功"
        else:
            token = config.get("token")
            license_data = config.get("licenseData")
            # 1. License 优先
            if license_data and self.hs_license.check(license_data):
                return True, "License 认证成功"

            # 2. Token 检查
            if token not in self.token_limits:
                return False, f"Token 验证失败: {token}"

            # 3. 并发限制
            limit = self.token_limits.get(token, 0)
            if current_ready_count >= limit:
                return False, f"连接数超限 ({current_ready_count}/{limit})"

            return True, "Token 验证成功"
