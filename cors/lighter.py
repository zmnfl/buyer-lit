import ctypes
import platform
import os
import aiohttp
import urllib.parse
import time
import random
import json

import logging


class Lighter:
    ORDER_TYPE_LIMIT = 0
    ORDER_TYPE_MARKET = 1
    ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL = 0
    ORDER_TIME_IN_FORCE_GOOD_TILL_TIME = 1
    DEFAULT_IOC_EXPIRY = 0
    NIL_TRIGGER_PRICE = 0
    DEFAULT_28_DAY_ORDER_EXPIRY = -1
    TX_TYPE_CREATE_ORDER = 14

    def __init__(self, config):
        self.logger = logging.getLogger("core lighter")
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler("logs/lighter.log", mode="a")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)
            self.logger.propagate = False

        self.config = config

        self.session: aiohttp.ClientSession | None = None
        self.chain_id = 304
        if self.config.API_KEY_PRIVATE_KEY.startswith("0x"):
            self.private_key = self.config.API_KEY_PRIVATE_KEY[2:]
        else:
            self.private_key = self.config.API_KEY_PRIVATE_KEY
        self.api_key_dict = { self.config.API_KEY_INDEX: self.private_key }
        self.signer = self._initialize_signer()
        self.create_client()
        self.nonce = -1

    def create_client(self):
        self.signer.CreateClient.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_longlong,
        ]
        self.signer.CreateClient.restype = ctypes.c_char_p
        err = self.signer.CreateClient(
            self.config.BASE_URL.encode("utf-8"),
            self.config.API_KEY_PRIVATE_KEY.encode("utf-8"),
            self.chain_id,
            self.config.API_KEY_INDEX,
            self.config.ACCOUNT_INDEX,
        )

        if err is None:
            return

        err_str = err.decode("utf-8")
        raise Exception(err_str)

    def sign_create_order(
        self,
        market_id,
        base_amount,
        is_ask,
        nonce: bool = False
    ):
        self.signer.SignCreateOrder.argtypes = [ctypes.c_int, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                            ctypes.c_int, ctypes.c_int, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_int, ctypes.c_longlong]
        
        class SignedTxResponse(ctypes.Structure):
            _fields_ = [
                ("txType", ctypes.c_uint8),
                ("txInfo", ctypes.c_char_p),
                ("txHash", ctypes.c_char_p),
                ("messageToSign", ctypes.c_char_p),
                ("err", ctypes.c_char_p),
            ]

        self.signer.SignCreateOrder.restype = SignedTxResponse

        result = self.signer.SignCreateOrder(
            market_id,
            0,
            base_amount,
            1 if is_ask else 99999999,
            int(is_ask),
            self.ORDER_TYPE_MARKET,
            self.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
            0,
            self.NIL_TRIGGER_PRICE,
            self.DEFAULT_IOC_EXPIRY,
            self.nonce if (not nonce) else (self.nonce + 1),
            self.config.API_KEY_INDEX,
            self.config.ACCOUNT_INDEX
        )

        if result.err:
            error = result.err.decode("utf-8")
            return None, error

        tx_type = result.txType
        tx_info_str = result.txInfo.decode("utf-8") if result.txInfo else None
        tx_hash_str = result.txHash.decode("utf-8") if result.txHash else None

        return tx_type, tx_info_str, tx_hash_str, None
    
    async def create_order(
        self,
        market_id,
        amount,
        long,
        decimal_amount
    ):
        try:
            start = time.time()
            base_amount = int(amount * 10**decimal_amount)
            _, tx_info, _, error = self.sign_create_order(
                market_id,
                base_amount,
                int(not long)
            )
            if error is not None:
                return None, None, error

            status, api_response = await self.send_tx(tx_info)

            if (status == 200):
                self.nonce += 1
            else:
                await self.get_nonce()

            end = time.time()
            return "lighter", status, end - start, api_response
        except Exception as e:
            return "lighter", 404, end - start, f"lighter create order error: {e}"

    def create_order_ws(
        self,
        market_id,
        amount,
        long,
        decimal_amount
    ):
        base_amount = int(amount * 10**decimal_amount)
        _, tx_info, _, error = self.sign_create_order(
            market_id,
            base_amount,
            int(not long)
        )
        if error is not None:
            return None, None, error
        
        id = str(random.randint(1, 10**76))
        msg = {
            "type": "jsonapi/sendtx",
            "data": {
                "id": id,
                "tx_type": self.TX_TYPE_CREATE_ORDER,
                "tx_info": json.loads(tx_info)
            }
        }
        return msg, id
    
    def create_order_for_batch_ws(
        self,
        market_id,
        amount,
        long,
        decimal_amount,
        nonce: bool = False
    ):
        base_amount = int(amount * 10**decimal_amount)
        _, tx_info, _, error = self.sign_create_order(
            market_id,
            base_amount,
            int(not long),
            nonce
        )
        if error is not None:
            return error
        
        return tx_info

    def sign_create_limit_order(
        self,
        market_id,
        base_amount,
        price,
        is_ask
    ):
        self.signer.SignCreateOrder.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_longlong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_longlong,
        ]

        class StrOrErr(ctypes.Structure):
            _fields_ = [("str", ctypes.c_char_p), ("err", ctypes.c_char_p)]

        self.signer.SignCreateOrder.restype = StrOrErr

        result = self.signer.SignCreateOrder(
            market_id,
            0,
            base_amount,
            price,
            int(is_ask),
            self.ORDER_TYPE_LIMIT,
            self.ORDER_TIME_IN_FORCE_GOOD_TILL_TIME,
            0,
            self.NIL_TRIGGER_PRICE,
            self.DEFAULT_28_DAY_ORDER_EXPIRY,
            self.nonce,
        )

        tx_info = result.str.decode("utf-8") if result.str else None
        error = result.err.decode("utf-8") if result.err else None

        return tx_info, error
    
    async def create_limit_order(
        self,
        market_id,
        amount,
        price,
        long,
        decimal_amount,
        decimal_price
    ):
        try:
            start = time.time()
            base_amount = int(amount * 10**decimal_amount)
            base_price = int(price * 10**decimal_price)
            tx_info, error = self.sign_create_limit_order(
                market_id,
                base_amount,
                base_price,
                int(not long)
            )
            if error is not None:
                return None, None, error
            
            status, api_response = await self.send_tx(tx_info)

            if (status == 200):
                self.nonce += 1
            else:
                await self.get_nonce()

            end = time.time()
            return "lighter limit", status, end - start, api_response
        except Exception as e:
            return "lighter limit", 404, end - start, f"lighter create order error: {e}"

    def create_limit_order_for_barch_ws(
        self,
        market_id,
        amount,
        price,
        long,
        decimal_amount,
        decimal_price,
        nonce: bool = False
    ):
        try:
            base_amount = int(amount * 10**decimal_amount)
            base_price = int(price * 10**decimal_price)
            tx_info, error = self.sign_create_limit_order(
                market_id,
                base_amount,
                base_price,
                int(not long)
            )
            if error is not None:
                return error
            
            return json.loads(tx_info)
        except Exception as e:
            return f"create_limit_order_for_barch_ws: {e}"


    # sub

    def _initialize_signer(self):
        is_linux = platform.system() == "Linux"
        is_mac = platform.system() == "Darwin"
        is_windows = platform.system() == "Windows"
        is_x64 = platform.machine().lower() in ("amd64", "x86_64")
        is_arm = platform.machine().lower() == "arm64"

        current_file_directory = os.path.dirname(os.path.abspath(__file__))
        path_to_signer_folders = os.path.join(current_file_directory, "signers")

        if is_arm and is_mac:
            return ctypes.CDLL(os.path.join(path_to_signer_folders, "lighter-signer-darwin-arm64.dylib"))
        elif is_linux and is_x64:
            return ctypes.CDLL(os.path.join(path_to_signer_folders, "lighter-signer-linux-amd64.so"))
        elif is_linux and is_arm:
            return ctypes.CDLL(os.path.join(path_to_signer_folders, "lighter-signer-linux-arm64.so"))
        elif is_windows and is_x64:
            return ctypes.CDLL(os.path.join(path_to_signer_folders, "lighter-signer-windows-amd64.dll"))
        else:
            raise Exception(
                f"Unsupported platform/architecture: {platform.system()}/{platform.machine()}. "
                "Currently supported: Linux(x86_64), macOS(arm64), and Windows(x86_64)."
            )

        # is_linux = platform.system() == "Linux"
        # is_mac = platform.system() == "Darwin"
        # is_windows = platform.system() == "Windows"
        # is_x64 = platform.machine().lower() in ("amd64", "x86_64")
        # is_arm = platform.machine().lower() == "arm64"

        # current_file_directory = os.path.dirname(os.path.abspath(__file__))
        # path_to_signer_folders = os.path.join(current_file_directory, "signers")

        # if is_arm and is_mac:
        #     return ctypes.CDLL(os.path.join(path_to_signer_folders, "signer-arm64.dylib"))
        # elif is_linux and is_x64:
        #     return ctypes.CDLL(os.path.join(path_to_signer_folders, "signer-amd64.so"))
        # elif is_windows and is_x64:
        #     return ctypes.CDLL(os.path.join(path_to_signer_folders, "signer-amd64.dll"))
        # else:
        #     raise Exception(
        #         f"Unsupported platform/architecture: {platform.system()}/{platform.machine()}. "
        #         "Currently supported: Linux(x86_64), macOS(arm64), and Windows(x86_64)."
        #     )

    # api

    async def init_session(self):
        try:
            if self.session is None or self.session.closed:

                # ssl_context = ssl._create_unverified_context()
                self.session = aiohttp.ClientSession(
                    # connector=aiohttp.TCPConnector(ssl=ssl_context),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
                    }
                )
                await self.get_nonce()
        except Exception as e:
            raise Exception(f"init session error: {e}")

    async def send_tx(self, tx_info: str):
        try:
            await self.init_session()
            url = self.config.BASE_URL + "/api/v1/sendTx"
            tx_info_encoded = urllib.parse.quote(tx_info, safe="")
            data_raw = f"tx_type=14&tx_info={tx_info_encoded}"
            async with self.session.post(url, data=data_raw) as resp:
                text = await resp.text()
                return resp.status, text
        except Exception as e:
            raise Exception(f"send tx error: {e}")
        
    async def send_tx_batch(self, data_raw):
        try:
            await self.init_session()
            url = self.config.BASE_URL + "/api/v1/sendTxBatch"
            async with self.session.post(url, data=data_raw) as resp:
                text = await resp.text()
                return resp.status, text
        except Exception as e:
            raise Exception(f"send tx error: {e}")
        
    async def get_nonce(self) -> int:
        try:
            await self.init_session()
            url = self.config.BASE_URL + "/api/v1/nextNonce"
            params={"account_index": self.config.ACCOUNT_INDEX, "api_key_index": self.config.API_KEY_INDEX}
            async with self.session.get(url, params=params) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"couldn't get nonce {text}")
                self.nonce = (await resp.json())['nonce']
                return self.nonce
        except Exception as e:
            raise Exception(f"get nonce error: {e}")
        
    async def get_positions(self, account: int = None):
        try:
            await self.init_session()
            account = account if account else self.config.ACCOUNT_INDEX
            url = self.config.BASE_URL + "/api/v1/account"
            params={"by": "index", "value": account}
            async with self.session.get(url, params=params) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"couldn't get nonce {text}")
                res = await resp.json()
                account = next((x for x in res["accounts"] if x["index"] == account), None)
                return account["positions"], account["assets"]
        except Exception as e:
            raise Exception(f"get position error: {e}")
        
    async def get_positions_by_address(self, address: str, account: int = None):
        try:
            await self.init_session()
            account = account if account else self.config.ACCOUNT_INDEX
            url = self.config.BASE_URL + "/api/v1/account"
            params={"by": "l1_address", "value": address}
            print(0)
            async with self.session.get(url, params=params) as resp:
                print(1)
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"couldn't get nonce {text}")
                res = await resp.json()
                account = next((x for x in res["accounts"] if x["index"] == account), None)
                return account["positions"], account["assets"]
        except Exception as e:
            raise Exception(f"get position error: {e}")

    async def get_orderBook(self):
        try:
            await self.init_session()
            url = self.config.BASE_URL + "/api/v1/orderBookDetails"
            params={"account_index": self.config.ACCOUNT_INDEX, "api_key_index": self.config.API_KEY_INDEX}
            async with self.session.get(url, params=params) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise Exception(f"couldn't get nonce {text}")
                res_json = await resp.json()
                return res_json["order_book_details"], res_json["spot_order_book_details"]
        except Exception as e:
            raise Exception(f"get nonce error: {e}")
           

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
