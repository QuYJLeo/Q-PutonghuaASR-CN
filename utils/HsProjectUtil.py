import base64
import logging
import os
import re
import time
from binascii import a2b_hex

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

from utils.MMPlatform import isWindows, isLinux

_log = logging.getLogger(__name__)


class HsLicenseUtil:
    """
    License utility class for hardware-based license validation.
    
    This class provides methods for license verification, encryption/decryption,
    and hardware information collection. It supports both UUID and MAC address
    based license validation.
    
    Attributes:
        Des_Key (bytes): Triple DES encryption key
        Des_IV (bytes): Initialization vector for DES encryption
        wlist (list): Whitelist of valid license codes
        uuid (str): System UUID
        mc (list): List of MAC addresses
    """

    Des_Key = b'hs8yc8dx'
    Des_IV = b'bj6hd6hs'
    wlist = [b"MEI3MDAxNEMtMkMxMS0xMUIyLUE4NUMtRUE1NTdBOTkzREQ1",
             b"NEM0QzQ1NDQtMDAzNi01OTEwLTgwNTItQjhDMDRGNDgzMzMz",
             b"RTk3ODRENTYtQTgzQi04REUwLTc1NDktMzlENzJEOTk5RkEz",
             b"Q0M1NkEzRjYtNkRDMi0zQkZBLUUxODUtQjRBOUZDQkFFN0U0",
             b"OTM0QkI5QjgtM0VEOC0xMUVCLTlGODQtNzQzM0FEOENGRjAw",
             b"QkRBMjk2Q0MtMzQ2My0xMUIyLUE4NUMtODQxMkE2OUEwNkRD",
             b"NEE2MUIzQ0MtMjNENC0xMUIyLUE4NUMtQzgzOUVGRTY1MjE1",
             b"MzY0NUJFQ0YtMEQxOS0xMUVCLTgxMDctN0M4QUUxNTM3OUU3",
             b"RDJENkU0MDAtOUJCRi0xMUVDLTk3QzItOEE0NEEzODczNzAw",
             b"MUQwQzkyMjAtQzhGMC0xMUVCLUI3MUEtNUM1NDIwQjY1RDAw",
             b"QzEwNzQzQ0MtMzQ5RS0xMUIyLUE4NUMtQTAwNjNBRjYxQzJC",
             b"RkFBRjc2NEMtMkFCRS0xMUIyLUE4NUMtQTVEMUU4RDhCRDMy",
             b"QTc5OUUyNEMtMzUwNi0xMUIyLUE4NUMtRDc4N0NCMDZFQkJD",
             b"RTJBNDEyNjktNUIyRC0zMUFDLTJGMTMtMUM2OTdBRjRENUJE",
             b"RDk3N0FGQ0MtMkQ3NC0xMUIyLUE4NUMtODA5MjlGQkE4MDJD",
             b"MDZGRkNGODAtNkE5QS0xMUVFLUFCMDItMzcxQzZENEYzRTAw",
             b"OTg1ZjRmMDctNWY2Yy0yMDI0LTAzMTEtMDkwNDA1MDAwMDAw",
             b"OTg1ZjRmMGEtMjc1ZC0yMDI1LTA1MjMtMTEzNzU0MDAwMDAw",
             b"YWVjODczYmItODRhYy00NzA4LWIyNDEtNTVkZDRhMDJiMjY1",
             b"NURGQjI4Q0MtMkU3MC0xMUIyLUE4NUMtRDAzMkU5OTI1OEFG",
             ]

    def __init__(self):
        """Initialize the license utility and collect hardware information."""
        self.uuid = self.getUD()
        self.mc = self.getMC()

    def desEncrypt(self, plaintext):
        """
        Encrypt data using Triple DES algorithm.
        
        Args:
            plaintext (bytes): Data to encrypt
            
        Returns:
            bytes: Base64 encoded encrypted data
        """
        cipher = Cipher(algorithms.TripleDES(self.Des_Key), modes.CBC(self.Des_IV), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(64).padder()
        padded_plaintext = padder.update(plaintext) + padder.finalize()

        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        encodeStr = base64.b64encode(ciphertext)
        return encodeStr

    def desDecrypt(self, ciphertext):
        """
        Decrypt data using Triple DES algorithm.
        
        Args:
            ciphertext (bytes): Base64 encoded encrypted data
            
        Returns:
            bytes: Decrypted plaintext
        """
        ciphertext = base64.b64decode(ciphertext)
        cipher = Cipher(algorithms.TripleDES(self.Des_Key), modes.CBC(self.Des_IV), backend=default_backend())
        decryptor = cipher.decryptor()

        decrypted_padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(64).unpadder()
        decrypted_plaintext = unpadder.update(decrypted_padded_plaintext) + unpadder.finalize()

        return decrypted_plaintext

    def check(self, code):
        """
        Validate a license code.
        
        Checks if the provided license code is valid by comparing against whitelist
        or decrypting and verifying hardware information.
        
        Args:
            code (str): License code to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if code in self.wlist:
            return True
        try:
            sNumber = self.uuid
            mcArray = self.mc
            encryptStr = a2b_hex(code)
            decryptStr = self.desDecrypt(encryptStr).decode('utf8')
            strArray = decryptStr.split('/')

            if len(strArray) < 4 or (int(strArray[2]) - time.time()) < 0:
                return False
            elif strArray[1] == sNumber or strArray[3] in mcArray:
                return True
            else:
                return False
        except Exception as e:
            _log.warning(f"check_license error:{e}")
            return False

    def is_valid_uuid(self, uuid_str):
        """
        Check if a string is a valid UUID format.
        
        Args:
            uuid_str (str): String to validate
            
        Returns:
            bool: True if valid UUID, False otherwise
        """
        uuid_pattern = re.compile(
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        )
        return bool(uuid_pattern.match(uuid_str))

    def getUD(self):
        """
        Get the system UUID.
        
        Returns the system UUID on both Windows and Linux systems.
        
        Returns:
            str: System UUID
        """
        uuid = None
        if isWindows:
            import wmi
            c = wmi.WMI()
            system_info = c.Win32_ComputerSystemProduct()[0]
            uuid = system_info.UUID
        if isLinux:
            cmd = base64.decodebytes(b'cGtleGVjIGRtaWRlY29kZSAtcyBzeXN0ZW0tdXVpZA==\n').decode()
            f = os.popen(cmd)
            d = f.read()
            if d == '':
                cmd = base64.decodebytes(b'bHNodyAtQyBzeXN0ZW0gfCBncmVwIC1pIHNlcmlhbA==').decode()
                f = os.popen(cmd)
                serial = f.read()
                d = serial.split(':', 1)[1].strip()
                trimmed = d[:32]
                zeros_needed = 32 - len(trimmed)
                filled = '0' * zeros_needed + trimmed
                uuid = f"{filled[:8]}-{filled[8:12]}-{filled[12:16]}-{filled[16:20]}-{filled[20:]}"
            else:
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
        for k, v in net_if_addrs().items():
            for item in v:
                address = item[1]
                if ('-' in address or ":" in address) and len(address) == 17:
                    mcArray.append(address.replace('-', ''))
                    mcArray.append(address.replace(':', ''))
        return mcArray