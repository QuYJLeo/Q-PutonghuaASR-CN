import base64
import datetime
import json
import logging
import os
import random
import string

import pyDes
from utils.Config import AUTHS
from utils.MMPlatform import isWindows, isLinux

_log = logging.getLogger(__name__)


class TestUtil:
    """
    Test utility class for authorization verification.
    
    This class provides methods for license verification, including token-based
    and license-based authentication. It validates authorization codes against
    hardware information (UUID and MAC addresses).
    
    Attributes:
        _uuid (str): System UUID
        _mac (list): List of MAC addresses
        _current_auth (dict): Currently validated authorization object
        Des_Key (str): DES encryption key
        Des_IV (str): DES initialization vector
    """

    def __init__(self):
        """Initialize the test utility and collect hardware information."""
        super().__init__()
        self._uuid = self.getUD()
        self._mac = self.getMC()
        self._current_auth = None

    Des_Key = "hs8yc8dx"
    Des_IV = "bj6hd6hs"

    def desEncrypt(self, string):
        """
        Encrypt string using DES algorithm.
        
        Args:
            string (str): String to encrypt
            
        Returns:
            bytes: Base64 encoded encrypted string
        """
        k = pyDes.des(self.Des_Key, pyDes.CBC, self.Des_IV, pad=None, padmode=pyDes.PAD_PKCS5)
        encryptStr = k.encrypt(string)
        encodeStr = base64.b64encode(encryptStr)
        return encodeStr

    def desDecrypt(self, string):
        """
        Decrypt string using DES algorithm.
        
        Args:
            string (bytes): Base64 encoded encrypted string
            
        Returns:
            bytes: Decrypted string
        """
        decodeStr = base64.b64decode(string)
        k = pyDes.des(self.Des_Key, pyDes.CBC, self.Des_IV, pad=None, padmode=pyDes.PAD_PKCS5)
        decryptStr = k.decrypt(decodeStr)
        return decryptStr

    def check(self):
        """
        Verify authorization information.
        
        First attempts to use previously validated authorization. If that fails,
        iterates through the authorization list to find a valid match.
        
        Returns:
            bool: True if valid authorization exists, False otherwise
        """
        if self._current_auth:
            if self._verify_single_auth(self._current_auth):
                return True
            else:
                _log.info("Previous valid authorization has expired, attempting to re-match...")
                self._current_auth = None
        for AUTH in AUTHS:
            if self._verify_single_auth(AUTH):
                self._current_auth = AUTH
                return True

        return False

    def get_current_limit(self):
        """
        Get the concurrent session limit from the current authorization.
        
        Returns:
            int: Session limit, 0 if no valid authorization
        """
        if self._current_auth:
            return self._current_auth.get("session", 0)
        return 0

    def _verify_single_auth(self, AUTH):
        """
        Verify a single authorization dictionary.
        
        Args:
            AUTH (dict): Authorization dictionary containing user, session, valid, token, and code
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            dAuthCode = self.desDecrypt(AUTH.get("code"))
            jsonStr = json.loads(dAuthCode)
            AUTH_USER = AUTH.get("user")
            AUTH_SESSION = AUTH.get("session")
            AUTH_VALID = AUTH.get("valid")
            AUTH_TOKEN = AUTH.get("token")

            if jsonStr['user'] != str(AUTH_USER):
                _log.warning(f"Authorization failed, user mismatch:{jsonStr['user']}, AUTH_USER={AUTH_USER}")
                return False
            if jsonStr['session'] != str(AUTH_SESSION):
                _log.warning(f"{AUTH_USER} authorization failed, session count mismatch:{jsonStr['session']}, AUTH_SESSION={AUTH_SESSION}")
                return False
            if jsonStr['valid'] != AUTH_VALID.strftime("%Y-%m-%d"):
                _log.warning(f"{AUTH_USER} authorization failed, validity mismatch:{jsonStr['valid']}, AUTH_VALID={AUTH_VALID.strftime('%Y-%m-%d')}")
                return False
            if jsonStr['token'] != AUTH_TOKEN:
                _log.warning(f"{AUTH_USER} authorization failed, TOKEN mismatch:{jsonStr['token']}, AUTH_TOKEN={AUTH_TOKEN}")
                return False
            if jsonStr['valid'] < datetime.date.today().strftime("%Y-%m-%d"):
                _log.warning(f"{AUTH_USER} authorization failed, expired:{jsonStr['valid']}")
                return False
            if jsonStr['uuid'] != self._uuid:
                _log.warning(f"{AUTH_USER} authorization failed, UUID mismatch:{jsonStr['uuid']}, self.getUD()={self._uuid}")
                return False
            if self._mac and jsonStr['mac'] not in self._mac:
                _log.warning(f"{AUTH_USER} authorization failed, MAC mismatch:{jsonStr['mac']}, self.getMC()={self._mac}")
                return False
            return True
        except Exception as e:
            _log.error(f"Verification exception: {e}")
            return False

    def getUD(self):
        """
        Get the system UUID.
        
        Returns:
            str: System UUID
        """
        if isWindows:
            cmd = base64.decodebytes(b'd21pYyBjc3Byb2R1Y3QgZ2V0IFVVSUQ =\n').decode()
        if isLinux:
            cmd = base64.decodebytes(b'dXVpZD0kKHN1ZG8gZG1pZGVjb2RlIC1zIHN5c3RlbS11dWlkIDI+L2Rldi9udWxsKSAmJiBbIC1uICIkdXVpZCIgXSAmJiBlY2hvICIkdXVpZCIgfHwgY2F0IC9ldGMvbWFjaGluZS1pZA==').decode()
        f = os.popen(cmd)
        d = f.read()
        uuid = d.split()[-1]
        f.close()
        return uuid

    def getMC(self):
        """
        Get all MAC addresses from network interfaces.
        
        Returns:
            list: List of MAC addresses with separators removed
        """
        from psutil import net_if_addrs
        mcArray = []
        try:
            for k, v in net_if_addrs().items():
                for item in v:
                    address = item[1]
                    if '-' in address and len(address) == 17 and isWindows:
                        mcArray.append(address.replace('-', ''))
                    if ':' in address and len(address) == 17 and isLinux:
                        mc = address.replace(':', '')
                        if mc == "000000000000":
                            continue
                        mcArray.append(address.replace(':', ''))
        except Exception as ex:
            print(f"getMC exception:{ex}")
        return mcArray

    def getRD(self):
        """
        Generate a random 32-character string.
        
        Returns:
            str: Random string containing letters and digits
        """
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(32))
        return random_string


testUtil = TestUtil()