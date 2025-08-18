import asyncio
from bleak import BleakClient
from Crypto.Hash import CMAC
from Crypto.Cipher import AES
from enum import Enum

# BluetoothでSESAMI5を制御するサンプルプログラム

class OP_CODE(Enum):
    RESPONSE = 0x07
    PUBLISH = 0x08

class ITEM_CODE(Enum):
    NONE = 0
    REGISTRATION = 1
    LOGIN = 2
    HISTORY = 4
    VERSION_DETAIL = 5
    TIME = 8
    AUTOLOCK = 11
    INITIAL = 14
    IRER = 15
    MAGNET = 17
    MECH_SETTING = 80
    MECH_STATUS = 81
    LOCK = 82
    UNLOCK = 83

class SsmBleClient:
    def __init__(self, config):
        self.__isWait = False
        self._config = config
        self._random_code = None
        self._token = None
        self._buff = None
        self._op_code = None
        self._item_code = None
        self._notify_uuid = None
        self._write_uuid = None
        self._decrypt_counter = 0
        self._encrypt_counter = 0
        self.isLogin = False
        
        self._client = BleakClient(self._config['mac_addr'], address_type="random")
    
    async def connect(self):
        await self._client.connect()
        if self._client.is_connected:
            print(f"connection OK! MAC Address: {self._config['mac_addr']}")
        else:
            print("connection error!")
         
        for service in self._client.services:
            for char in service.characteristics:
                if self._notify_uuid is None and 'read' in char.properties and 'notify' in char.properties:
                    print(f" notify UUID: {char.uuid}")
                    self._notify_uuid = char.uuid
                elif self._write_uuid is None and 'write' in char.properties and 'write-without-response' in char.properties:
                    print(f" write UUID: {char.uuid}")
                    self._write_uuid = char.uuid

    async def disconnect(self):
        await self._client.disconnect()
        print("disconnected!")

    async def start_notify(self):
        print("notify start!")
        self.__isWait = True
        await self._client.start_notify(self._notify_uuid, self.__handleNotification)
        await self._wait()
    
    async def stop_notify(self):
        print("notify stop!")
        await self._client.stop_notify(self._notify_uuid)
    
    async def login(self):
        self.__isWait = True
        command = bytes([0x02]) + self._token
        print(f"cmd send login data: [{command}] encrypt: {False}")
        await self._send(command, False)
        await self._wait()
    
    async def history(self):
        self.__isWait = True
        command = bytes([ITEM_CODE.HISTORY.value]) + bytes([0x01])
        print(f"cmd send history data: [{command}] encrypt: {True}")
        await self._send(command, True)
        await self._wait()
    
    async def unlock(self):
        self.__isWait = True
        tag = 'SampleUnlock'.encode()
        command = bytes([ITEM_CODE.UNLOCK.value, len(tag)]) + tag
        print(f"cmd send unlock data: [{command}] encrypt: {True}")
        await self._send(command, True)
        await self._wait()
    
    def __handleNotification(self, handle, data):
        print(f"handle: {handle}, data: {data}")

        packetHead = data[0]
        if packetHead == 0x01 or packetHead == 0x03 or packetHead == 0x05:
            # 開始パケット
            self._buff = bytes()
        self._buff += data[1:]
        if packetHead == 0x00 or packetHead == 0x01:
            # 次パケットあり
            return
        if packetHead == 0x02 or packetHead == 0x03:
            # 終了パケット(平文)
            data = self._buff
        elif packetHead == 0x04 or packetHead == 0x05:
            # 終了パケット(暗号文)
            data = self._decrypt(self._buff)
        else:
            print(f"packet error!")
            return
        
        print(f"Notify data: {data}")
        self._op_code = data[0]
        self._item_code = data[1]
        if self._op_code == OP_CODE.RESPONSE.value:
            if self._item_code == ITEM_CODE.LOGIN.value:
                # ログイン結果受信
                if data[2] == 0x00:
                    print(f"Login OK!")
                    self.isLogin = True
                else:
                    print(f"Login NG!")
                    self.isLogin = False
            elif self._item_code == ITEM_CODE.UNLOCK.value:
                #解錠結果受信
                if data[2] == 0x00:
                    print(f"unlocked!")
                else:
                    print(f"unlock error!")
            elif self._item_code == ITEM_CODE.HISTORY.value:
                print(f"history!")
        elif self._op_code == OP_CODE.PUBLISH.value:
            if self._item_code == ITEM_CODE.INITIAL.value:
                # ランダムコード受信
                self._random_code = bytes([data[2], data[3], data[4], data[5]])
                cobj = CMAC.new(bytes.fromhex(self._config['private_key']), ciphermod=AES)
                cobj.update(self._random_code)
                self._token = cobj.digest()
                print(f"Random Code: {self._random_code}")
                print(f"Token: {self._token}")
                self._decrypt_counter = 0
                self._encrypt_counter = 0
        else:
            print('response error!')
        
        self.__isWait = False
    
    async def _wait(self):
        retry_count = 0
        while self.__isWait or retry_count > self._config['max_retry_count']:
            print(f"wait... {retry_count}")
            retry_count += 1
            await asyncio.sleep(self._config['notify_interval']) 
    
    async def _send(self, send_data, is_encrypt):
        if is_encrypt:
            send_data = self._encrypt(send_data)

        remain = len(send_data)
        offset = 0
        while remain != 0:
            header = 0
            if offset == 0:
                header += 1

            if remain <= 19:
                buffer = send_data[offset:]
                remain = 0
                if is_encrypt:
                    header += 4
                else:
                    header += 2
            else:
                buffer = send_data[offset:(offset+20)]
                offset += 19
                remain -= 19

            buffer = bytes([header]) + buffer
            await self._client.write_gatt_char(self._write_uuid, buffer)
    
    def _encrypt(self, data):
        nouse = bytes([0x00])
        ccm_iv = self._encrypt_counter.to_bytes(8, "little") + nouse + self._random_code
        cobj = AES.new(self._token, AES.MODE_CCM, ccm_iv, mac_len=4,msg_len=len(data), assoc_len=1)
        cobj.update(bytes([0x00]))
        enc_data, tag = cobj.encrypt_and_digest(data)
        tag4 = tag[0:4]
        self._encrypt_counter += 1
        return enc_data + tag4

    def _decrypt(self, data):
        nouse = bytes([0x00])
        ccm_iv = self._decrypt_counter.to_bytes(8, "little") + nouse + self._random_code
        cobj = AES.new(self._token, AES.MODE_CCM, nonce=ccm_iv, mac_len=4)
        cobj.update(bytes([0x00]))
        decode_data = cobj.decrypt(data[:-4])
        self._decrypt_counter += 1
        return decode_data

# ---- 以下テストコード ----

async def open_sesame_bt():
    config = {
        'mac_addr': 'DF:FD:0D:D3:43:8D', # SESAME5のMACアドレス
        'private_key': '6ec38d24f0c9b88467116ae69b3c6104', # アプリから取得した鍵
        'max_retry_count': 5, # notify通知待機最大回数
        'notify_interval': 1.0 # notify通知待機時間
    }
    sbc = SsmBleClient(config)
    await sbc.connect()
    await sbc.start_notify()
    await sbc.login()
    if sbc.isLogin:
        await sbc.unlock()
    await sbc.stop_notify()
    await sbc.disconnect()

if __name__ == "__main__":
    asyncio.run(open_sesame_bt())

# Service: 00001800-0000-1000-8000-00805f9b34fb
#  Characteristic: 00002a00-0000-1000-8000-00805f9b34fb
#  Properties: ['write', 'read']
#  Characteristic: 00002a01-0000-1000-8000-00805f9b34fb
#  Properties: ['read']
#  Characteristic: 00002a04-0000-1000-8000-00805f9b34fb
#  Properties: ['read']
# Service: 0000fd81-0000-1000-8000-00805f9b34fb
#  Characteristic: 16860002-a5ae-9856-b6d3-dbb4c676993e
#  Properties: ['write', 'write-without-response']
#  Characteristic: 16860003-a5ae-9856-b6d3-dbb4c676993e
#  Properties: ['read', 'notify']
# Service: 0000fe59-0000-1000-8000-00805f9b34fb
#  Characteristic: 8ec90001-f315-4f60-9fb8-838830daea50
#  Properties: ['write', 'notify']
#  Characteristic: 8ec90002-f315-4f60-9fb8-838830daea50
#  Properties: ['read', 'write-without-response']
#  Characteristic: 00000003-0000-1000-8000-00805f9b34fb
#  Properties: ['write', 'read', 'notify']
