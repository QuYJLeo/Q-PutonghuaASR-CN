import logging
import platform

_log = logging.getLogger(__name__)
system = platform.system()
isWindows = system == "Windows"
isLinux = system == "Linux"
isDarwin = system == "Darwin"  # macOS

print("使用的平台是：%s" % system)
