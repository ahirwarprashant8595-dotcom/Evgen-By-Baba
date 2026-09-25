"""
Основной модуль генерации токенов Discord (Lord Vault Generator Core).
Включает интеграцию с почтовыми провайдерами (CyberTemp, CrowMail, DuckMail, TempMailLol, Hotmail, Zeus, Mailcow),
решение капчи через NopeCHA (Request API и расширение браузера),
эмуляцию сетевых отпечатков (JA3/TLS/HTTP2), WebSocket KeepAlive и валидацию токенов.
Все консольные логи и вывод в терминал осуществляются на английском языке.
"""

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
import primp
from colorama import Fore, Style
from PIL import Image
import asyncio
import websockets

import requests
from stealth_requests import StealthSession
import base64
import json
import os
import platform
import random
import re
import string
import threading
import time
import uuid
import websocket
import subprocess
import ctypes
import sys
import imaplib
import email
from datetime import datetime
from urllib.parse import urlparse
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = "\033[38;2;121;3;255m"     
C = "\033[38;2;3;248;252m"     
G = "\033[38;2;68;255;0m"      
D = "\033[38;2;92;94;91m"      
R = "\033[0m"                  
Y = "\033[38;2;255;200;50m"    
RD = "\033[38;2;255;80;80m"    
W = "\033[97m"    


class DEVSMailApi:
    """
    Клиент почтового сервиса CyberTemp API для автоматического создания
    временных почтовых ящиков и получения ссылок/кодов верификации Discord.
    """
    BASE_URL = "https://api.cybertemp.xyz"
    def __init__(self, logger=None, forced_domain: str = None, api_key: str = None):
        self.created_emails = {}
        self.logger = logger
        self.forced_domain = forced_domain
        self.api_key = (api_key or os.getenv("CYBERTEMP_API_KEY", "")).strip()
        if not self.api_key:
            self.api_key = self._read_api_key_from_config()
        self.headers = {"X-API-KEY": self.api_key} if self.api_key else {}
    def _build_proxies(self, proxy: str = None):
        if proxy and "://" not in proxy:
            proxy = f"http://{proxy}"
        return {"http": proxy, "https": proxy} if proxy else None
    def _log(self, message: str):
        pass
    def _read_api_key_from_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return (cfg.get("mail_services", {}).get("cybertemp", {}).get("api_key") or "").strip()
        except Exception:
            return ""
    def get_domains(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cybertemp_cfg = cfg.get("mail_services", {}).get("cybertemp", {})
            if "domains" in cybertemp_cfg and isinstance(cybertemp_cfg["domains"], list) and len(cybertemp_cfg["domains"]) > 0:
                return cybertemp_cfg["domains"]
        except Exception:
            pass

        try:
            resp = requests.get(f"{self.BASE_URL}/getDomains", params={"type": "discord"}, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "domains" in data:
                    domains_list = data["domains"]
                elif isinstance(data, list):
                    domains_list = data
                else:
                    return []
                return [d.get("domain", d) if isinstance(d, dict) else d for d in domains_list]
        except:
            pass
        return []
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if email and '@' in email:
            created_email = email
        elif self.forced_domain:
            local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{local}@{self.forced_domain}"
        else:
            domains = self.get_domains()
            if not domains:
                domains = ["randommail.com"] 
            target_domain = random.choice(domains)
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{username}@{target_domain}"
        if not created_email:
            self._log("DEVSMail could not create an email")
            return None
        self.created_emails[created_email] = password or ""
        self._log(f"Prepared email: {created_email}")
        return created_email
    def get_verify_url(self, email: str, poll_interval: int = 3, timeout: int = 120, proxy: str = None):
        start_time = time.time()
        used_message_ids = set()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.BASE_URL}/getMail", params={"email": email}, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    messages = resp.json()
                    if isinstance(messages, list) and messages:
                        for msg in messages:
                            msg_id = msg.get("id")
                            if msg_id in used_message_ids:
                                continue
                            subject = msg.get("subject", "")
                            if "discord" in subject.lower() or "verify" in subject.lower() or "verif" in subject.lower():
                                html_body = msg.get("html", "") or msg.get("text", "") or ""
                                text_body = msg.get("text", "") or ""
                                combined = html_body + text_body
                                all_links = re.findall(r'https?://[^\s"\'<>]+', combined)
                                target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l and "blog." not in l]
                                if target_links:
                                    url = None
                                    if len(target_links) >= 2:
                                        second_url = target_links[1]
                                        if "verify" in second_url.lower() or "token=" in second_url.lower() or "click.discord.com" in second_url:
                                            url = second_url
                                    if not url:
                                        url = max(target_links, key=len)
                                    if "click.discord.com" in url:
                                        resolved = self._resolve_url(url, proxy=proxy)
                                        if resolved:
                                            return resolved
                                    return url
                                used_message_ids.add(msg_id)
            except Exception as e:
                self._log(f"Error reading inbox: {e}")
            time.sleep(poll_interval)
        self._log(f"Timeout waiting for verify URL in {email}")
        return None
    def _resolve_url(self, url: str, proxy: str = None) -> str:
        proxies = self._build_proxies(proxy)
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, proxies=proxies)
            final_url = resp.url
            if "discord.com/verify" in final_url:
                return final_url
        except Exception:
            pass
        return None
class CrowMailAPI:
    BASE_URL = "https://api.crowmail.sbs"
    def __init__(self, password: str = ""):
        self.password = password or ''.join(random.choices(string.ascii_letters + string.digits, k=14))
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json"})
        self._bearer = None
        self._email = None
    def _domain(self) -> str:
        for _ in range(3):
            try:
                r = self.s.get(f"{self.BASE_URL}/domains", timeout=10)
                if r.status_code == 200:
                    for m in r.json().get("hydra:member", []):
                        if m.get("ownerId") is None:
                            return m["domain"]
            except Exception:
                time.sleep(1.0)
        return "crowmail.sbs"
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        for attempt in range(3):
            try:
                domain = self._domain()
                addr = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}@{domain}"
                pw = self.password
                r = self.s.post(f"{self.BASE_URL}/accounts", json={"address": addr, "password": pw, "expiresIn": 0}, timeout=10)
                if r.status_code != 201:
                    time.sleep(1.5)
                    continue
                token_r = self.s.post(f"{self.BASE_URL}/token", json={"address": addr, "password": pw}, timeout=10)
                if token_r.status_code != 200:
                    time.sleep(1.5)
                    continue
                self._bearer = token_r.json().get("token")
                self._email = addr
                return addr
            except Exception:
                time.sleep(2.0)
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._bearer:
            return None
        headers = {"Authorization": f"Bearer {self._bearer}"}
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = self.s.get(f"{self.BASE_URL}/messages", headers=headers, timeout=10)
                if r.status_code == 200:
                    for msg in r.json().get("hydra:member", []):
                        subj = (msg.get("subject", "") or "").lower()
                        sender = (msg.get("from", {}) or {}).get("address", "").lower()
                        if "verify" in subj or "discord" in sender or "noreply@discord" in sender:
                            detail = self.s.get(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers, timeout=10).json()
                            body = detail.get("text", "") or " ".join(detail.get("html", ""))
                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+',
                                        r'https://discord\.com/verify\?token=[^\s"\'<>]+',
                                        r'https://click\.discord\.com/[^\s"\'<>]+']:
                                m = re.search(pat, body, re.IGNORECASE)
                                if m:
                                    link = m.group(0).replace("&amp;", "&")
                                    self.s.delete(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers)
                                    return link
            except:
                pass
            time.sleep(poll_interval)
        return None

class DuckMailAPI:
    BASE_URL = "https://api.duckmail.sbs"
    def __init__(self, password: str = ""):
        self.password = password or ''.join(random.choices(string.ascii_letters + string.digits, k=14))
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json"})
        self._bearer = None
        self._email = None
    def _domain(self) -> str:
        for _ in range(3):
            try:
                r = self.s.get(f"{self.BASE_URL}/domains", timeout=10)
                if r.status_code == 200:
                    for m in r.json().get("hydra:member", []):
                        if m.get("ownerId") is None:
                            return m["domain"]
            except Exception:
                time.sleep(1.0)
        return "duckmail.sbs"
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        for attempt in range(3):
            try:
                domain = self._domain()
                addr = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}@{domain}"
                pw = self.password
                r = self.s.post(f"{self.BASE_URL}/accounts", json={"address": addr, "password": pw, "expiresIn": 0}, timeout=10)
                if r.status_code != 201:
                    time.sleep(1.5)
                    continue
                token_r = self.s.post(f"{self.BASE_URL}/token", json={"address": addr, "password": pw}, timeout=10)
                if token_r.status_code != 200:
                    time.sleep(1.5)
                    continue
                self._bearer = token_r.json().get("token")
                self._email = addr
                return addr
            except Exception:
                time.sleep(2.0)
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._bearer:
            return None
        headers = {"Authorization": f"Bearer {self._bearer}"}
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = self.s.get(f"{self.BASE_URL}/messages", headers=headers, timeout=10)
                if r.status_code == 200:
                    for msg in r.json().get("hydra:member", []):
                        subj = (msg.get("subject", "") or "").lower()
                        sender = (msg.get("from", {}) or {}).get("address", "").lower()
                        if "verify" in subj or "discord" in sender or "noreply@discord" in sender:
                            detail = self.s.get(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers, timeout=10).json()
                            body = detail.get("text", "") or " ".join(detail.get("html", ""))
                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+',
                                        r'https://discord\.com/verify\?token=[^\s"\'<>]+',
                                        r'https://click\.discord\.com/[^\s"\'<>]+']:
                                m = re.search(pat, body, re.IGNORECASE)
                                if m:
                                    link = m.group(0).replace("&amp;", "&")
                                    self.s.delete(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers)
                                    return link
            except:
                pass
            time.sleep(poll_interval)
        return None

class TempMailLolAPI:
    BASE_URL = "https://api.tempmail.lol"
    def __init__(self):
        self._token = None
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        try:
            r = requests.get(f"{self.BASE_URL}/generate", timeout=10)
            if r.status_code == 200:
                data = r.json()
                self._token = data.get("token", "")
                return data.get("address", "")
        except:
            pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._token:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(f"{self.BASE_URL}/auth/{self._token}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for msg in data.get("email", []):
                        subject = msg.get("subject", "")
                        body = msg.get("body", "") or msg.get("html", "")
                        if "discord" in subject.lower() or "verify" in subject.lower():
                            all_links = re.findall(r'https?://[^\s"\'<>]+', body)
                            target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l]
                            if target_links:
                                return max(target_links, key=len)
            except:
                pass
            time.sleep(poll_interval)
        return None

class Hotmail007API:
    BASE_URL = "https://api.hotmail007.com"
    def __init__(self, client_key: str = ""):
        self.client_key = client_key
        self._email_data = None
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.client_key:
            return None
        for mail_type in ["outlook", "hotmail"]:
            try:
                r = requests.get(f"{self.BASE_URL}/api/mail/getMail",
                    params={"clientKey": self.client_key, "mailType": mail_type, "quantity": 1}, timeout=15, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("code") == 0 and data.get("data"):
                        parts = data["data"][0].split(":")
                        if len(parts) >= 2:
                            self._email_data = {"email": parts[0], "password": parts[1]}
                            return parts[0]
            except:
                pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        return None

class ZeusProvider:
    BASE_URL = "https://api.zeus-x.ru"
    def __init__(self, api_key: str = "", mail_type: str = "new", mailcode: str = ""):
        self.api_key = api_key
        if mailcode:
            self.account_codes = [mailcode]
        else:
            self.account_codes = ["HOTMAIL_TRUSTED_GRAPH_API", "OUTLOOK_TRUSTED_GRAPH_API"] if mail_type == "uhq" else ["HOTMAIL", "OUTLOOK"]
        self._email_data = None
        self._last_error = None

    def check_balance(self):
        try:
            r = requests.get(f"{self.BASE_URL}/balance", params={"apikey": self.api_key}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # Try multiple possible response formats
                if isinstance(data, dict):
                    for key in ["Balance", "balance", "data", "Data"]:
                        val = data.get(key)
                        if val is not None:
                            if isinstance(val, dict):
                                for k2 in ["Balance", "balance", "Amount", "amount"]:
                                    v2 = val.get(k2)
                                    if v2 is not None:
                                        return v2
                            else:
                                return val
                return data  # Return raw response if nothing matched
        except:
            pass
        return None

    def check_stock(self):
        try:
            r = requests.get(f"{self.BASE_URL}/instock", timeout=10)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return None
        
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.api_key:
            self._last_error = "no_api_key"
            return None
        self._last_error = None
        for code in self.account_codes:
            try:
                r = requests.get(f"{self.BASE_URL}/purchase",
                    params={"apikey": self.api_key, "accountcode": code, "quantity": 1}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("Code") == 0 and data.get("Data"):
                        accounts = data["Data"].get("Accounts", [])
                        if accounts:
                            item = accounts[0]
                            self._email_data = {
                                "email": item.get("Email", ""), 
                                "password": item.get("Password", ""),
                                "token": item.get("RefreshToken", ""),
                                "uuid": item.get("ClientId", "")
                            }
                            return item.get("Email", "")
                    # Store the error reason
                    msg = data.get("Message", data.get("message", ""))
                    err_code = data.get("Code", "")
                    self._last_error = msg or f"code={err_code}"
            except:
                self._last_error = "request_failed"
        return None
        
    def get_access_token(self, refresh_token: str, client_id: str = None) -> str:
        try:
            cid = client_id or "d8fbe69d-15be-43fa-b204-5c5bc5a73ad7"
            if refresh_token.endswith("$"): 
                refresh_token = refresh_token[:-1]
            response = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": cid,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=30, verify=False,
            )
            return response.json().get("access_token")
        except:
            return None

    def get_verify_url(self, email_str: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._email_data:
            return None
            
        refresh_token = self._email_data.get("token", "")
        client_id = self._email_data.get("uuid", "")
        
        if refresh_token:
            access_token = self.get_access_token(refresh_token, client_id)
            if access_token:
                session = requests.Session()
                start_time = time.time()
                while time.time() - start_time < timeout:
                    for folder in ["inbox", "junkemail"]:
                        try:
                            response = session.get(
                                f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages",
                                headers={"Authorization": f"Bearer {access_token}"},
                                params={"$top": 10, "$orderby": "receivedDateTime desc", "$select": "subject,body,from"},
                                timeout=15, verify=False,
                            )
                            if response.status_code == 200:
                                emails = response.json().get("value", [])
                                for eml in emails:
                                    subject = eml.get("subject", "").lower()
                                    from_addr = eml.get("from", {}).get("emailAddress", {}).get("address", "").lower()
                                    is_verify = ("verify" in subject or "confirm" in subject or "email" in subject) and ("discord" in from_addr or "noreply@discord.com" in from_addr)
                                    if is_verify:
                                        body_html = eml.get("body", {}).get("content", "")
                                        direct_match = re.search(r'https://discord\.com/verify\?token=[^"\'\>\s]+', body_html)
                                        if direct_match:
                                            return direct_match.group(0).replace("&amp;", "&")
                                        for pat in [r'https://click\.discord\.com/ls/click\?[^"\'\>\s]+', r'https://links\.discord\.com[^"\'\>\s]+']:
                                            for m in re.finditer(pat, body_html):
                                                url = m.group(0).replace("&amp;", "&")
                                                try:
                                                    r2 = session.get(url, allow_redirects=True, verify=False, timeout=10)
                                                    if "discord.com/verify" in r2.url:
                                                        return r2.url
                                                    found = re.search(r'https://discord\.com/verify\?token=[^"\'\>\s]+', r2.text)
                                                    if found:
                                                        return found.group(0).replace("&amp;", "&")
                                                except:
                                                    pass
                        except Exception:
                            pass
                    time.sleep(poll_interval)
                return None
                
        # Fallback to standard IMAP if no refresh token
        password = self._email_data.get("password")
        if not password:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout / 2: # Give it limited time for fallback
            try:
                mail = imaplib.IMAP4_SSL('outlook.office365.com')
                mail.login(email_str, password)
                for folder in ['inbox', 'Junk', '"Junk Email"']:
                    try:
                        status, count = mail.select(folder)
                        if status != 'OK': continue
                        status, messages = mail.search(None, '(ALL)')
                        if status == 'OK' and messages[0]:
                            for num in reversed(messages[0].split()):
                                res, msg_data = mail.fetch(num, '(RFC822)')
                                if res == 'OK':
                                    msg = email.message_from_bytes(msg_data[0][1])
                                    subject = str(msg.get("Subject", "")).lower()
                                    from_addr = str(msg.get("From", "")).lower()
                                    if "discord" in subject or "verify" in subject or "discord" in from_addr:
                                        body = ""
                                        if msg.is_multipart():
                                            for part in msg.walk():
                                                if part.get_content_type() in ["text/plain", "text/html"]:
                                                    try: body += part.get_payload(decode=True).decode(errors='ignore')
                                                    except: pass
                                        else:
                                            try: body = msg.get_payload(decode=True).decode(errors='ignore')
                                            except: pass
                                        if body:
                                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+', r'https://discord\.com/verify\?token=[^\s"\'<>]+', r'https://click\.discord\.com/[^\s"\'<>]+']:
                                                m = re.search(pat, body, re.IGNORECASE)
                                                if m: return m.group(0).replace("&amp;", "&")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[IMAP LOGIN FAILED] {e}", flush=True)
            time.sleep(poll_interval)
        return None

class DraxonoAPI:
    BASE_URL = "https://mail.draxono.in/api"
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key else {}
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        try:
            r = requests.get(f"{self.BASE_URL}/domains", headers=self.headers, timeout=10, verify=False)
            if r.status_code == 200:
                domains = r.json()
                if isinstance(domains, list) and domains:
                    domain = random.choice(domains)
                    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                    return f"{local}@{domain}"
        except:
            pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        return None

class MailcowProvider:
    def __init__(self, mc_config: dict):
        self.config = mc_config
        self.base_url = mc_config.get("host", "")
        self.api_key = mc_config.get("api_key", "")
        self.headers = {"X-API-Key": self.api_key}
        self.tm_api = TempMailLolAPI()
        self.temp_email = None

    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.base_url or not self.api_key:
            return None
        
        # 1. Generate tempmail target
        self.temp_email = self.tm_api.create_account()
        if not self.temp_email:
            return None
            
        try:
            # 2. Create Mailcow Alias forwarding to tempmail
            domain = self.config.get("domain", "")
            if not domain:
                return None
            alias = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@{domain}"
            data = {"address": alias, "goto": self.temp_email, "active": "1"}
            
            # format base url just in case user forgot https://
            url = self.base_url
            if not url.startswith('http'):
                url = f"https://{url}"
            if url.endswith('/'):
                url = url[:-1]
                
            r = requests.post(f"{url}/api/v1/add/alias", json=data, headers=self.headers, timeout=10)
            if r.status_code == 200:
                return alias
        except:
            pass
        return None

    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self.temp_email:
            return None
        # Simply poll the mail.tm inbox we just created!
        return self.tm_api.get_verify_url(self.temp_email, poll_interval, timeout, proxy)

class LutionAPI(ZeusProvider):
    BASE_URL = "https://api.lution.ee/v2"
    def __init__(self, api_key: str = "", category: str = "Microsoft"):
        self.api_key = api_key
        self.category = category
        self._email_data = None
        
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.api_key:
            return None
        headers = {"accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {"category": self.category, "quantity": 1}
        for _ in range(5):
            try:
                r = requests.post(f"{self.BASE_URL}/email/buy", json=payload, headers=headers, timeout=10)
                if r.status_code == 200:
                    j = r.json()
                    data = j.get("data") or {}
                    emails = data.get("emails") or []
                    if emails:
                        e = emails[0]
                        self._email_data = {
                            "email": e.get("email", ""), 
                            "password": e.get("password", ""),
                            "token": e.get("graph_refresh_token", ""),
                            "uuid": e.get("thunderbird_client_id", "")
                        }
                        return e.get("email", "").lower()
            except:
                pass
            time.sleep(3)
        return None

def get_mail_provider():
    services = config.get("mail_services", {})
    if not services:
        devs_cfg = config.get("devs_mail", {})
        if devs_cfg.get("api_key"):
            return DEVSMailApi(logger=print, api_key=devs_cfg["api_key"]), "cybertemp"
        return None, None

    provider_order = ["crowmail", "duckmail", "cybertemp", "lution", "tempmail_lol", "hotmail007", "zeus", "draxono", "mailcow"]
    for name in provider_order:
        svc = services.get(name, {})
        if not svc.get("enabled", False):
            continue
        if name == "crowmail":
            return CrowMailAPI(password=svc.get("password", "")), name
        elif name == "duckmail":
            return DuckMailAPI(password=svc.get("password", "")), name
        elif name == "cybertemp":
            return DEVSMailApi(logger=print, api_key=svc.get("api_key", "")), name
        elif name == "lution":
            return LutionAPI(api_key=svc.get("api_key", ""), category=svc.get("mailcode", "")), name
        elif name == "tempmail_lol":
            return TempMailLolAPI(), name
        elif name == "hotmail007":
            return Hotmail007API(client_key=svc.get("client_key", "")), name
        elif name == "zeus":
            return ZeusProvider(api_key=svc.get("api_key", ""), mailcode=svc.get("mailcode", "")), name
        elif name == "draxono":
            return DraxonoAPI(api_key=svc.get("api_key", "")), name
        elif name == "mailcow":
            return MailcowProvider(svc), name
    return None, None

class Solver:
    VPS_URL  = ""                
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    
    def __init__(self, url, sitekey, rqdata="", user_agent="", proxy=None, api_key="",
                 session_profile=None, discord_fingerprint=None, cookies=None,
                 super_props=None, captcha_rqtoken=None, captcha_session_id=None):
        self.url        = url
        self.sitekey    = sitekey
        self.rqdata     = rqdata
        self.user_agent = user_agent
        self.proxy      = proxy
        self.api_key    = api_key
        self.session_profile      = session_profile
        self.discord_fingerprint  = discord_fingerprint
        self.cookies              = cookies if isinstance(cookies, dict) else {}
        self.super_props           = super_props
        self.captcha_rqtoken       = captcha_rqtoken
        self.captcha_session_id    = captcha_session_id
        cap_cfg = config.get("nopecha") or config.get("solver", {})
        has_req = cap_cfg.get("req_solver")
        has_ext = cap_cfg.get("extension_solver")
        mode = str(cap_cfg.get("solver_mode", "")).strip().lower()

        if has_req is True and has_ext is False:
            self.use_req = True
            self.use_extension = False
        elif has_ext is True and has_req is False:
            self.use_extension = True
            self.use_req = False
        elif mode in ("request", "req", "api"):
            self.use_req = True
            self.use_extension = False
        elif mode in ("extension", "ext", "browser"):
            self.use_extension = True
            self.use_req = False
        else:
            self.use_req = bool(has_req)
            self.use_extension = bool(has_ext if has_ext is not None else not self.use_req)
            if not self.use_req and not self.use_extension:
                self.use_extension = True

        self.use_vps       = self.use_req
        self.solver_url    = cap_cfg.get("url", "").strip() or "https://api.nopecha.com"
        bd_cfg = config.get("bright_data", {})
        self.use_brightdata = bd_cfg.get("enabled", False)
        self.bd_api_key     = bd_cfg.get("api_key", "")
        self.bd_zone        = bd_cfg.get("zone", "web_unlocker1")

    def _format_proxy(self):
        if self.proxy:
            return self.proxy
        return ""
    def _solve_extension(self, timeout=90):
        
        try:
            from engine.extension_browser import get_browser
            browser = get_browser()
            _file_log("[EXT] Solving via local browser + extension")
            token = browser.solve(
                sitekey=self.sitekey,
                url=self.url,
                rqdata=self.rqdata,
                user_agent=self.user_agent,
                timeout=timeout,
                proxy=self.proxy,
            )
            if token:
                return token, {}
            _file_log("[EXT] Extension solver returned no token")
            return None, None
        except ImportError:
            _file_log("[EXT] extension_browser.py not found or nodriver not installed")
            return None, None
        except Exception as e:
            _file_log(f"[EXT] Error: {e}")
            return None, None

    def _solve_nopecha_token_api(self, timeout=120, poll_interval=2):
        import urllib.request, urllib.error, json, time
        
        base_api = self.solver_url.rstrip("/") if self.solver_url else "https://api.nopecha.com"
        token_endpoint = f"{base_api}/token" if not base_api.endswith("/token") else base_api
        
        payload = {
            "key": self.api_key,
            "type": "hcaptcha",
            "sitekey": self.sitekey,
            "url": self.url,
            "data": {
                "rqdata": self.rqdata or ""
            }
        }
        if self.proxy:
            payload["proxy"] = self._format_proxy()
        if self.user_agent:
            payload["useragent"] = self.user_agent
            
        _file_log(f"[NOPECHA-REQ] Submitting token job to {token_endpoint} (sitekey={self.sitekey[:10]}...)...")
        
        task_id = None
        try:
            req = urllib.request.Request(
                token_endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'User-Agent': self.UA}
            )
            resp = urllib.request.urlopen(req, timeout=20)
            resp_text = resp.read().decode('utf-8')
            data = json.loads(resp_text)
            
            if "data" in data:
                res_data = data["data"]
                if isinstance(res_data, list) and len(res_data) > 0:
                    _file_log(f"[NOPECHA-REQ] Token received directly ({len(res_data[0])} chars)")
                    return res_data[0], {}
                elif isinstance(res_data, str) and (len(res_data) > 50 or "P1_" in res_data or "P0_" in res_data):
                    _file_log(f"[NOPECHA-REQ] Token received directly ({len(res_data)} chars)")
                    return res_data, {}
                task_id = str(res_data)
            elif "id" in data:
                task_id = str(data["id"])
            elif "token" in data:
                return data["token"], {}
            else:
                _file_log(f"[NOPECHA-REQ] Unexpected response: {resp_text[:200]}")
                return None, None
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode('utf-8')
                err_json = json.loads(err_body)
                _file_log(f"[NOPECHA-REQ] HTTP {e.code}: {err_json.get('message', err_body)}")
                if e.code == 402:
                    _file_log("[NOPECHA-REQ] Token API requires a paid plan with token access (Reviewer plan unsupported)")
                    try:
                        Log.error("NopeCHA Token API [HTTP 402]: Feature unavailable for current plan.")
                        Log._log("[NOPECHA]", "Your key is on 'Reviewer' plan which does NOT support Request Token API.", D, Y)
                        Log._log("[NOPECHA]", "Switch to Extension mode ('solver_mode': 'extension') in config.json to solve via browser.", D, Y)
                    except Exception:
                        pass
            except Exception:
                _file_log(f"[NOPECHA-REQ] HTTP error {e.code}: {e.reason}")
            return None, None
        except Exception as e:
            _file_log(f"[NOPECHA-REQ] Connection error: {e}")
            return None, None

        _file_log(f"[NOPECHA-REQ] Task {task_id} queued, polling for solution...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            try:
                poll_url = f"{base_api}/token?key={self.api_key}&id={task_id}"
                poll_req = urllib.request.Request(poll_url, headers={'User-Agent': self.UA})
                poll_resp = urllib.request.urlopen(poll_req, timeout=15)
                poll_text = poll_resp.read().decode('utf-8')
                poll_data = json.loads(poll_text)

                if "data" in poll_data:
                    solution = poll_data["data"]
                    if isinstance(solution, list) and len(solution) > 0:
                        _file_log(f"[NOPECHA-REQ] Solved successfully in {round(time.time() - start_time, 1)}s")
                        return solution[0], {}
                    elif isinstance(solution, str) and (len(solution) > 50 or "P1_" in solution or "P0_" in solution):
                        _file_log(f"[NOPECHA-REQ] Solved successfully in {round(time.time() - start_time, 1)}s")
                        return solution, {}
                elif "token" in poll_data:
                    _file_log(f"[NOPECHA-REQ] Solved successfully in {round(time.time() - start_time, 1)}s")
                    return poll_data["token"], {}

                error_msg = poll_data.get("message") or poll_data.get("error")
                if error_msg:
                    _file_log(f"[NOPECHA-REQ] API message: {error_msg}")
                    if "incomplete" in str(error_msg).lower():
                        continue
                    return None, None
            except urllib.error.HTTPError as e:
                if e.code in (409, 404):
                    continue
                _file_log(f"[NOPECHA-REQ] Polling HTTP error {e.code}: {e.reason}")
            except Exception as e:
                _file_log(f"[NOPECHA-REQ] Polling error: {e}")

        _file_log("[NOPECHA-REQ] Task timed out")
        return None, None

    def _solve_vps(self, timeout=120, poll_interval=2):
        import urllib.request, urllib.error, json, time
        
        vps_base = (self.solver_url or self.VPS_URL or "").rstrip("/")
        if not vps_base:
            return None, None
            
        payload = {
            "key": self.api_key,
            "type": "hcaptcha_basic",
            "data": {
                "sitekey": self.sitekey,
                "siteurl": self.url.replace("https://", "").replace("http://", "").split("/")[0],
                "proxy": self._format_proxy(),
                "rqdata": self.rqdata,
                "useragent": self.user_agent
            }
        }
        
        _file_log(f"[VPS] Creating task on {vps_base}...")
        
        req = urllib.request.Request(
            f"{vps_base}/api/create_task",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': self.UA}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            resp_text = resp.read().decode('utf-8')
            data = json.loads(resp_text)
            if data.get("status") != "success":
                _file_log(f"[VPS] Task creation failed: {data.get('message')}")
                return None, None
            task_id = data.get("task_id")
        except Exception as e:
            _file_log(f"[VPS] API connection error: {e}")
            return None, None
            
        _file_log(f"[VPS] Task {task_id} created, polling...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            try:
                poll_url = f"{vps_base}/api/get_result/{task_id}?key={self.api_key}"
                poll_req = urllib.request.Request(poll_url, headers={'User-Agent': self.UA})
                poll_resp = urllib.request.urlopen(poll_req, timeout=15)
                poll_data = json.loads(poll_resp.read().decode('utf-8'))
                
                status = poll_data.get("status")
                if status == "solved":
                    _file_log(f"[VPS] Solved successfully in {round(time.time() - start_time, 1)}s")
                    return poll_data.get("solution"), {}
                elif status == "error":
                    err_msg = poll_data.get("error", "Unknown error")
                    _file_log(f"[VPS] Solver API returned error: {err_msg}")
                    if "rate limit" in str(err_msg).lower() or "429" in str(err_msg):
                        return "ERROR_RATELIMIT", None
                    if "ip" in str(err_msg).lower() or "proxy" in str(err_msg).lower() or "reject" in str(err_msg).lower():
                        return "ERROR_IP_REJECTED", None
                    return None, None
                elif status == "solving":
                    continue
            except Exception as e:
                _file_log(f"[VPS] Polling error: {e}")
        
        _file_log("[VPS] Task timed out")
        return None, None

    def _solve_req(self, timeout=120, poll_interval=2):
        api_url = (self.solver_url or "").strip().lower()
        if not api_url or "nopecha.com" in api_url:
            return self._solve_nopecha_token_api(timeout=timeout, poll_interval=poll_interval)
        else:
            return self._solve_vps(timeout=timeout, poll_interval=poll_interval)

    def _solve_brightdata(self, timeout=120):
        """Solve hCaptcha via Bright Data Web Unlocker API.
        Supports both VPN mode (no proxy, traffic goes through VPN tunnel)
        and proxy mode (traffic goes through external proxy)."""
        import urllib.request, urllib.error, json, time, re

        is_vpn_mode = not self.proxy
        mode_str = "VPN Tunnel" if is_vpn_mode else f"Proxy: {self.proxy}"
        _file_log(f"[BRIGHTDATA] Solving captcha via Web Unlocker API ({mode_str})")

        # Bright Data Web Unlocker proxy endpoint
        proxy_host = "brd.superproxy.io"
        proxy_port = 33335
        # Extract customer ID from config or use default
        bd_cfg = config.get("bright_data", {})
        customer_id = bd_cfg.get("customer_id", "hl_2c1fdd5f")
        proxy_user = f"brd-customer-{customer_id}-zone-{self.bd_zone}"
        proxy_pass = self.bd_api_key

        bd_proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"

        target_url = self.url if self.url else "https://discord.com/register"

        _file_log(f"[BRIGHTDATA] Target: {target_url}")
        _file_log(f"[BRIGHTDATA] Zone: {self.bd_zone}")
        _file_log(f"[BRIGHTDATA] Mode: {mode_str}")

        # In VPN mode:  local traffic -> VPN tunnel -> Bright Data proxy -> target
        # In Proxy mode: local traffic -> Bright Data proxy -> target
        # Both modes connect to Bright Data proxy the same way;
        # in VPN mode the OS-level VPN tunnel handles the outer hop automatically.

        # --- Try with requests library first ---
        try:
            import requests as _requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            proxies = {
                "http": bd_proxy_url,
                "https": bd_proxy_url,
            }

            _file_log(f"[BRIGHTDATA] Sending request through Web Unlocker proxy...")

            # When VPN is active, the connection to brd.superproxy.io
            # goes through the VPN tunnel automatically (OS-level routing).
            # This means Bright Data sees the VPN exit IP, not the real IP.
            resp = _requests.get(
                target_url,
                proxies=proxies,
                headers={
                    'User-Agent': self.user_agent or self.UA,
                },
                timeout=timeout,
                verify=False,
            )

            _file_log(f"[BRIGHTDATA] Response status: {resp.status_code}")

            if resp.status_code == 429:
                _file_log("[BRIGHTDATA] Rate limited (429)")
                return "ERROR_RATELIMIT", None

            if resp.status_code == 403:
                _file_log("[BRIGHTDATA] IP rejected (403)")
                return "ERROR_IP_REJECTED", None

            resp_text = resp.text

            # Look for hCaptcha response token in the page
            token_match = re.search(r'h-captcha-response["\s:=]+([a-zA-Z0-9_\-\.]{20,})', resp_text)
            if token_match:
                token = token_match.group(1)
                _file_log(f"[BRIGHTDATA] Captcha token extracted ({len(token)} chars)")
                return token, {}

            # Check response headers for captcha solution
            if 'x-captcha-solution' in resp.headers:
                token = resp.headers['x-captcha-solution']
                _file_log(f"[BRIGHTDATA] Token from header ({len(token)} chars)")
                return token, {}

            # Check for token in JSON response body
            try:
                resp_json = resp.json()
                if resp_json.get("token"):
                    token = resp_json["token"]
                    _file_log(f"[BRIGHTDATA] Token from JSON ({len(token)} chars)")
                    return token, {}
                if resp_json.get("solution"):
                    token = resp_json["solution"]
                    _file_log(f"[BRIGHTDATA] Token from solution ({len(token)} chars)")
                    return token, {}
            except Exception:
                pass

            _file_log(f"[BRIGHTDATA] No captcha token found in response (len={len(resp_text)})")
            return None, None

        except ImportError:
            _file_log("[BRIGHTDATA] 'requests' library not available, using urllib fallback")
        except Exception as e:
            err_str = str(e).lower()
            _file_log(f"[BRIGHTDATA] Error: {e}")
            if "rate limit" in err_str or "429" in err_str:
                return "ERROR_RATELIMIT", None
            if "timeout" in err_str or "timed out" in err_str:
                if is_vpn_mode:
                    _file_log("[BRIGHTDATA] Timeout in VPN mode — VPN tunnel may be slow or disconnected")
                return None, None
            if "10013" in err_str or "permission" in err_str:
                _file_log("[BRIGHTDATA] WinError 10013 — VPN socket not ready, wait and retry")
                return None, None
            return None, None

        # --- Fallback: Use urllib with proxy handler ---
        try:
            proxy_handler = urllib.request.ProxyHandler({
                'http': bd_proxy_url,
                'https': bd_proxy_url,
            })
            opener = urllib.request.build_opener(proxy_handler)

            req = urllib.request.Request(target_url, headers={
                'User-Agent': self.user_agent or self.UA,
            })

            _file_log(f"[BRIGHTDATA] urllib fallback ({mode_str})...")
            resp = opener.open(req, timeout=timeout)
            resp_text = resp.read().decode('utf-8')

            token_match = re.search(r'h-captcha-response["\s:=]+([a-zA-Z0-9_\-\.]{20,})', resp_text)
            if token_match:
                token = token_match.group(1)
                _file_log(f"[BRIGHTDATA] urllib: Token extracted ({len(token)} chars)")
                return token, {}

            _file_log("[BRIGHTDATA] urllib: No captcha token in response")
            return None, None
        except Exception as e:
            err_str = str(e).lower()
            _file_log(f"[BRIGHTDATA] urllib fallback error: {e}")
            if "10013" in err_str:
                _file_log("[BRIGHTDATA] VPN socket blocked (WinError 10013) — network not ready yet")
            return None, None

    def solve(self, timeout=120, poll_interval=2):
        _file_log(f"Using Proxy: {self.proxy or 'None (Local IP)'}")
        _file_log(f"Solver config: ext={self.use_extension}, req={self.use_req}, brightdata={self.use_brightdata}")
        
        # When request solver is enabled / prioritized
        if self.use_req:
            _file_log("[REQ] Using NopeCHA Request Solver (API mode)")
            try:
                result = self._solve_req(timeout, poll_interval)
                if result and result[0]:
                    return result
                _file_log("[REQ] Request solver returned no solution")
            except Exception as e:
                _file_log(f"[REQ] Error: {e}")

            return None, None
        else:
            # When extension solver is enabled / prioritized
            _file_log("[EXT] Using NopeCHA Extension Solver (Browser mode)")
            try:
                result = self._solve_extension(timeout)
                if result and result[0]:
                    return result
                _file_log("[EXT] Extension solver failed")
            except Exception as e:
                _file_log(f"[EXT] Error: {e}")

            # Fallback to request solver if enabled
            if self.use_req:
                _file_log("[EXT->REQ] Trying request solver fallback...")
                try:
                    result = self._solve_req(timeout, poll_interval)
                    if result and result[0]:
                        return result
                    _file_log("[REQ] Fallback failed")
                except Exception as e:
                    _file_log(f"[REQ] Fallback error: {e}")

        # Priority 3: Bright Data Web Unlocker (experimental fallback)
        if self.use_brightdata and self.bd_api_key:
            _file_log("[BRIGHTDATA] Trying Bright Data Web Unlocker as last resort...")
            try:
                result = self._solve_brightdata(timeout)
                if result and result[0]:
                    return result
                _file_log("[BRIGHTDATA] Failed")
            except Exception as e:
                _file_log(f"[BRIGHTDATA] Error: {e}")

        _file_log("[WARN] All solvers failed or none enabled!")
        return None, None
config = {}
try:
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"Error loading config.json: {e}")

_logs_enabled = config.get("logs", False)
def _file_log(msg):
    if not _logs_enabled:
        return
    try:
        with open(os.path.join(os.path.dirname(__file__), "logs.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

verification_enabled = config.get("verification", {}).get("enabled", True)
gen_count = 0
gen_lock = threading.Lock()
stats_lock = threading.Lock()
stats = {
    'generated': 0,
    'verified': 0,
    'captcha_failed': 0,
    'captcha_solved': 0,
    'locked': 0,
    'valid': 0,
    'total': 0
}
from engine.vpn import VPNManager, DEFAULT_COUNTRIES

vpn_manager = VPNManager(config)
# Backward compat alias
proxy_manager = vpn_manager
from colorama import Fore, Style, init
from pystyle import Colors, Colorate, Center, Anime, System
init(autoreset=True)
class Log:
    lock = threading.Lock()
    @staticmethod
    def _log(badge, text, color=R, badge_color=None):
        with Log.lock:
            ts = datetime.now().strftime("%H:%M:%S")
            b_col = badge_color or color
            print(f"  {D}[{ts}]{R} {b_col}{badge:<9}{R} {color}{text}{R}")
    @staticmethod
    def proxy_header(num, proxy):
        """Show VPN IP info instead of proxy. Kept name for backward compat."""
        if vpn_manager and vpn_manager.enabled:
            ip = vpn_manager._current_ip or vpn_manager.get_current_ip() or "Active"
            vpn_name = vpn_manager.get_vpn_name()
            Log._log("[VPN]", f"#{num} {vpn_name} · IP: {ip}", D, C)
        elif proxy:
            Log._log("[PROXY]", f"#{num} {proxy[:10]}***", D, C)
    @staticmethod
    def generated(token):
        with Log.lock:
            ts = datetime.now().strftime("%H:%M:%S")
            parts = token.split(".")
            if len(parts) == 3:
                censored_token = f"{parts[0][:6]}******.{parts[1]}.*******{parts[2][-6:]}"
            else:
                censored_token = token[:15] + "******"
            print(f"  {D}[{ts}]{R} {G}[GEN]{R}     {G}Generated:{R} {C}{censored_token}{R}")
        with stats_lock:
            stats['generated'] += 1
            stats['total'] += 1
    @staticmethod
    def captcha_solved(time_n, token=""):
        token_str = f" → {token[:35]}..." if token else ""
        Log._log("[SOLVED]", f"Captcha solved in {time_n:.1f}s{token_str}", C, C)
        with stats_lock:
            stats['captcha_solved'] += 1
    @staticmethod
    def solving(email):
        Log._log("[SOLVE]", "Solving hCaptcha via Browser Extension...", Y, Y)
    @staticmethod
    def captcha_failed():
        Log._log("[FAILED]", "Captcha failed due to ratelimit / timeout", RD, RD)
        with stats_lock:
            stats['captcha_failed'] += 1
            stats['total'] += 1
    @staticmethod
    def status(status_text):
        st = str(status_text).strip()
        if not st:
            return
        Log._log("[INFO]", st, W, P)
    @staticmethod
    def error(text):
        Log._log("[ERROR]", text, RD, RD)
    @staticmethod
    def waiting(text):
        Log._log("[WAIT]", text, Y, Y)
    @staticmethod
    def verified(token):
        with Log.lock:
            ts = datetime.now().strftime("%H:%M:%S")
            parts = token.split(".")
            if len(parts) == 3:
                censored_token = f"{parts[0][:6]}******.{parts[1]}.*******{parts[2][-6:]}"
            else:
                censored_token = token[:15] + "******"
            print(f"  {D}[{ts}]{R} {G}[VERIF]{R}   {G}Verified:{R}  {C}{censored_token}{R}")
        with stats_lock:
            stats['verified'] += 1
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6897.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.127 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.142 Safari/537.36",
]

# ── Browser Fingerprint Profiles ─────────────────────────────────────────────
# Each profile matches a real machine: UA + GPU + screen + memory + timezone.
# Discord correlates x-super-properties with WebGL/GPU data — mismatches trigger flags.
BROWSER_PROFILES = {
    "Windows Chrome 148 1080p NVIDIA": {
        "name": "Windows Chrome 148 1080p NVIDIA",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 12, "memory": 8,
    },
    "Windows Chrome 148 1440p AMD": {
        "name": "Windows Chrome 148 1440p AMD",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Google Chrome", "version": "148"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (AMD)",
        "gpu_renderer": "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 2560, "screen_h": 1440,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Chicago", "tz_offset": -360,
        "cores": 16, "memory": 16,
    },
    "Windows Chrome 148 1080p Intel": {
        "name": "Windows Chrome 148 1080p Intel",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "148"},
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (Intel)",
        "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Denver", "tz_offset": -420,
        "cores": 8, "memory": 16,
    },
    "Windows Chrome 147 1366x768 Laptop": {
        "name": "Windows Chrome 147 1366x768 Laptop",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "147"},
            {"brand": "Chromium", "version": "147"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (Intel)",
        "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1366, "screen_h": 768,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Los_Angeles", "tz_offset": -480,
        "cores": 4, "memory": 8,
    },
    "Windows Chrome 148 1080p RTX4060": {
        "name": "Windows Chrome 148 1080p RTX4060",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Chromium", "version": "148"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Los_Angeles", "tz_offset": -480,
        "cores": 8, "memory": 16,
    },
    "Windows 11 Chrome 148 4K": {
        "name": "Windows 11 Chrome 148 4K",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "11",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 3840, "screen_h": 2160,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 24, "memory": 16,
    },
    "macOS Chrome 148 Retina": {
        "name": "macOS Chrome 148 Retina",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "macOS", "mobile": False, "os_version": "10.15.7",
        "gpu_vendor": "Google Inc. (Apple)",
        "gpu_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)",
        "screen_w": 1728, "screen_h": 1117,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Los_Angeles", "tz_offset": -480,
        "cores": 8, "memory": 8,
    },
    "macOS Chrome 147 MBA": {
        "name": "macOS Chrome 147 MBA",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "147"},
            {"brand": "Google Chrome", "version": "147"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "macOS", "mobile": False, "os_version": "10.15.7",
        "gpu_vendor": "Google Inc. (Apple)",
        "gpu_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)",
        "screen_w": 1440, "screen_h": 900,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Chicago", "tz_offset": -360,
        "cores": 8, "memory": 8,
    },
    "Linux Chrome 148 1080p": {
        "name": "Linux Chrome 148 1080p",
        "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Linux", "mobile": False, "os_version": "",
        "gpu_vendor": "Mesa", "gpu_renderer": "Mesa Intel(R) UHD Graphics 630 (CFL GT2)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "Europe/London", "tz_offset": 0,
        "cores": 8, "memory": 16,
    },
    "Windows Chrome 147 1080p RTX2070": {
        "name": "Windows Chrome 147 1080p RTX2070",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "147"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Google Chrome", "version": "147"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 SUPER Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "Europe/Berlin", "tz_offset": 60,
        "cores": 8, "memory": 16,
    },
    "Windows Chrome 148 Ultrawide": {
        "name": "Windows Chrome 148 Ultrawide",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "148"},
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "11",
        "gpu_vendor": "Google Inc. (AMD)",
        "gpu_renderer": "ANGLE (AMD, AMD Radeon RX 7900 XT Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 3440, "screen_h": 1440,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 16, "memory": 32,
    },
    "macOS Chrome 148 iMac": {
        "name": "macOS Chrome 148 iMac",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Chromium", "version": "148"},
        ],
        "platform": "macOS", "mobile": False, "os_version": "10.15.7",
        "gpu_vendor": "Google Inc. (Apple)",
        "gpu_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M3, Unspecified Version)",
        "screen_w": 2560, "screen_h": 1440,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 12, "memory": 16,
    },
}

def resolve_session_profile(profile_name=None):
    """Pick a browser profile and build session-level metadata from it."""
    if profile_name and profile_name in BROWSER_PROFILES:
        prof = BROWSER_PROFILES[profile_name]
    else:
        prof = random.choice(list(BROWSER_PROFILES.values()))
    ua = prof["userAgent"]
    m = re.search(r"Chrome/(\d+)", ua)
    chrome_major = int(m.group(1)) if m else 148
    brands = prof.get("brands", [])
    sec_ch_ua = ", ".join(f'"{b["brand"]}";v="{b["version"]}"' for b in brands)
    plat = prof.get("platform", "Windows")
    os_version = prof.get("os_version", "10")
    if plat == "macOS":
        sp_os, sp_browser, sp_device = "Mac OS X", "Chrome", ""
    elif plat == "Linux":
        sp_os, sp_browser, sp_device = "Linux", "Chrome", ""
    else:
        sp_os, sp_browser, sp_device = "Windows", "Chrome", ""
    return {
        "ua": ua,
        "chrome_version": chrome_major,
        "sec_ch_ua": sec_ch_ua,
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": f'"{plat}"',
        "platform": plat,
        "os_version": os_version,
        "lang": prof.get("lang", "en-US"),
        "timezone": prof.get("timezone", "America/Los_Angeles"),
        "sp_os": sp_os,
        "sp_browser": sp_browser,
        "sp_device": sp_device,
        "raw_profile": prof,
        "name": prof.get("name", "Unknown"),
    }

# ── Custom fingerprint loading ───────────────────────────────────────────────
_CUSTOM_FINGERPRINTS = []
_FINGERPRINTS_LOADED = False
_FINGERPRINTS_LOCK = threading.Lock()

def load_custom_fingerprints():
    global _CUSTOM_FINGERPRINTS, _FINGERPRINTS_LOADED
    with _FINGERPRINTS_LOCK:
        if _FINGERPRINTS_LOADED:
            return
        _FINGERPRINTS_LOADED = True
        fp_path = os.path.join(os.path.dirname(__file__), "input", "fingerprints.txt")
        if not os.path.exists(fp_path):
            return
        with open(fp_path, "r", encoding="utf-8") as f:
            _CUSTOM_FINGERPRINTS.extend(line.strip() for line in f if line.strip())

def pop_custom_fingerprint():
    """Return a pre-harvested Discord fingerprint if available."""
    with _FINGERPRINTS_LOCK:
        if _CUSTOM_FINGERPRINTS:
            return _CUSTOM_FINGERPRINTS.pop(0)
    return None

_FIRST_NAMES = [
    'james', 'mary', 'john', 'patricia', 'robert', 'jennifer', 'michael', 'linda', 'william', 'elizabeth',
    'david', 'barbara', 'richard', 'susan', 'joseph', 'jessica', 'thomas', 'sarah', 'charles', 'karen',
    'christopher', 'lisa', 'daniel', 'nancy', 'matthew', 'betty', 'anthony', 'margaret', 'mark', 'sandra',
    'donald', 'ashley', 'steven', 'kimberly', 'paul', 'emily', 'andrew', 'donna', 'joshua', 'michelle',
    'kenneth', 'carol', 'kevin', 'amanda', 'brian', 'dorothy', 'george', 'melissa', 'timothy', 'deborah',
    'ronald', 'stephanie', 'edward', 'rebecca', 'jason', 'sharon', 'jeffrey', 'laura', 'ryan', 'cynthia',
    'jacob', 'kathleen', 'gary', 'amy', 'nicholas', 'angela', 'eric', 'shirley', 'jonathan', 'anna',
    'stephen', 'brenda', 'larry', 'pamela', 'justin', 'emma', 'scott', 'nicole', 'brandon', 'helen',
    'alex', 'sam', 'jay', 'riley', 'max', 'charlie', 'taylor', 'jordan', 'casey', 'drew', 'oliver', 'lucas',
    'mason', 'logan', 'ethan', 'aiden', 'jackson', 'liam', 'noah', 'elijah', 'mia', 'chloe', 'zoey', 'lily'
]

_LAST_NAMES = [
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller', 'davis', 'rodriguez', 'martinez',
    'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson', 'thomas', 'taylor', 'moore', 'jackson', 'martin',
    'lee', 'perez', 'thompson', 'white', 'harris', 'sanchez', 'clark', 'ramirez', 'lewis', 'robinson',
    'walker', 'young', 'allen', 'king', 'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores', 'green',
    'adams', 'nelson', 'baker', 'hall', 'rivera', 'campbell', 'mitchell', 'carter', 'roberts', 'gomez',
    'phillips', 'evans', 'turner', 'diaz', 'parker', 'cruz', 'edwards', 'collins', 'reyes', 'stewart',
    'morris', 'morales', 'murphy', 'cook', 'rogers', 'gutierrez', 'ortiz', 'morgan', 'cooper', 'peterson',
    'bailey', 'reed', 'kelly', 'howard', 'ramos', 'kim', 'cox', 'ward', 'richardson', 'watson', 'brooks',
    'chavez', 'wood', 'james', 'bennett', 'gray', 'mendoza', 'ruiz', 'hughes', 'price', 'alvarez', 'castillo'
]

_ADJECTIVES = [
    'cool', 'dark', 'wild', 'fast', 'chill', 'epic', 'real', 'true', 'fire', 'ice',
    'neon', 'void', 'zen', 'pro', 'ace', 'rad', 'dope', 'lit', 'raw', 'hype', 'super',
    'mega', 'ultra', 'hyper', 'quantum', 'cyber', 'retro', 'crypto', 'meta', 'stealth',
    'shadow', 'ghost', 'phantom', 'ninja', 'vortex', 'solar', 'lunar', 'cosmic', 'astral',
    'mystic', 'magic', 'lucky', 'happy', 'mad', 'crazy', 'lazy', 'sleepy', 'angry', 'sad',
    'good', 'bad', 'evil', 'holy', 'pure', 'dirty', 'clean', 'fresh', 'stale', 'sweet'
]

def _random_username() -> str:
    suf = lambda: str(random.randint(1000, 99999))
    patterns = [
        lambda: f"{random.choice(_FIRST_NAMES)}_{random.choice(_LAST_NAMES)}{suf()}",
        lambda: f"{random.choice(_FIRST_NAMES)}{random.choice(_LAST_NAMES)}_{suf()}",
        lambda: f"{random.choice(_ADJECTIVES)}_{random.choice(_FIRST_NAMES)}{suf()}",
        lambda: f"{random.choice(_FIRST_NAMES)}.{random.choice(_LAST_NAMES)}{suf()}",
        lambda: f"{random.choice(_FIRST_NAMES)}_{''.join(random.choices(string.ascii_lowercase, k=3))}{suf()}",
        lambda: f"{random.choice(_ADJECTIVES)}_{random.choice(_LAST_NAMES)}{suf()}",
        lambda: f"{random.choice(_LAST_NAMES)}_{random.choice(_FIRST_NAMES)}_{suf()}",
    ]
    return random.choice(patterns)()
def _random_password() -> str:
    
    base = ''.join(random.choices(string.ascii_letters, k=random.randint(6, 10)))
    digits = ''.join(random.choices(string.digits, k=random.randint(2, 4)))
    special = random.choice('!@#$%&*')
    pwd = base + digits + special
    return pwd
def _random_dob() -> str:
    
    year = random.randint(1994, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  
    return f"{year}-{month:02d}-{day:02d}"
# ── Build number caching (6-hour TTL) ────────────────────────────────────────
_BUILD_CACHE = {"value": None, "ts": 0.0}
_BUILD_LOCK = threading.Lock()
_BUILD_TTL = 6 * 3600
_BUILD_FALLBACK = 502645

def robust_request(session, method, url, max_retries=3, delay=1.5, **kwargs):
    """Executes an HTTP request with automatic retry on h2 connection reset or socket drops."""
    timeout = kwargs.pop("timeout", 15)
    last_err = None
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                return session.get(url, timeout=timeout, **kwargs)
            elif method.upper() == "POST":
                return session.post(url, timeout=timeout, **kwargs)
            elif method.upper() == "HEAD":
                return session.head(url, timeout=timeout, **kwargs)
            else:
                return session.request(method, url, timeout=timeout, **kwargs)
        except Exception as e:
            last_err = e
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["connection reset", "h2", "(56)", "(28)", "protocol_error", "broken pipe", "stream 0"]):
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
            raise e
    raise last_err

def get_build_number(proxy=None):
    now = time.time()
    with _BUILD_LOCK:
        if _BUILD_CACHE["value"] and now - _BUILD_CACHE["ts"] < _BUILD_TTL:
            return _BUILD_CACHE["value"]
    try:
        sess = StealthSession()
        if proxy:
            proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
            sess.proxies = {"http": proxy_url, "https": proxy_url}
        page = robust_request(sess, "GET", "https://discord.com/app", timeout=15).text
        assets = re.findall(r'src="/assets/([^"]+)"', page)
        for asset in reversed(assets):
            try:
                js = robust_request(sess, "GET", f"https://discord.com/assets/{asset}", timeout=15).text
            except Exception:
                continue
            if "buildNumber:" in js:
                bn = int(js.split('buildNumber:"')[1].split('"')[0])
                with _BUILD_LOCK:
                    _BUILD_CACHE["value"] = bn
                    _BUILD_CACHE["ts"] = now
                return bn
    except Exception:
        pass
    return _BUILD_FALLBACK
def build_super_properties(build_number, session_profile):
    """Build x-super-properties using the full session profile."""
    ua = session_profile["ua"]
    chrome_match = re.search(r"Chrome/([\d.]+)", ua)
    browser_version = chrome_match.group(1) if chrome_match else f"{session_profile['chrome_version']}.0.0.0"
    payload = {
        "os": session_profile["sp_os"],
        "browser": session_profile["sp_browser"],
        "device": session_profile["sp_device"],
        "system_locale": session_profile["lang"],
        "browser_user_agent": ua,
        "browser_version": browser_version,
        "os_version": session_profile.get("os_version", ""),
        "referrer": "https://discord.com/",
        "referring_domain": "discord.com",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": build_number,
        "client_event_source": None,
        "design_id": 0,
        "has_client_mods": False,
        "client_launch_id": str(uuid.uuid4()),
        "launch_signature": str(uuid.uuid4()),
        "client_heartbeat_session_id": str(uuid.uuid4()),
        "client_app_state": "focused",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()
def _build_sec_ch_ua(chrome_version):
    if chrome_version >= 133:
        return f'"Not:A-Brand";v="24", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
    return f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
def acquire_discord_cookies(session):
    robust_request(session, "GET", "https://discord.com", timeout=15)
    cookies = session.cookies.get_dict()
    dcfduid = cookies.get("__dcfduid")
    sdcfduid = cookies.get("__sdcfduid")
    return dcfduid, sdcfduid
def fetch_discord_fingerprint(session, dcfduid, sdcfduid, session_profile):
    """Fetch Discord x-fingerprint from /experiments, or use a pre-harvested one."""
    # Try pre-harvested fingerprint first
    load_custom_fingerprints()
    custom_fp = pop_custom_fingerprint()
    if custom_fp:
        _file_log(f"[FP] Using custom fingerprint: {custom_fp[:36]}...")
        return custom_fp
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": f"{session_profile['lang']},en;q=0.9",
        "sec-ch-ua": session_profile["sec_ch_ua"],
        "sec-ch-ua-mobile": session_profile["sec_ch_ua_mobile"],
        "sec-ch-ua-platform": session_profile["sec_ch_ua_platform"],
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": session_profile["ua"]
    }
    session.headers.update(headers)
    data = robust_request(session, "GET", "https://discord.com/api/v9/experiments", timeout=15)
    payload = data.json()
    fp = payload.get("fingerprint") if isinstance(payload, dict) else None
    if not fp:
        raise RuntimeError(f"experiments missing fingerprint [{data.status_code}]: {str(payload)[:200]}")
    return fp
def build_headers(fingerprint, super_props, session_profile):
    """Build Discord API headers using profile-specific values."""
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": f"{session_profile['lang']},en;q=0.9",
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/",
        "priority": "u=1, i",
        "sec-ch-ua": session_profile["sec_ch_ua"],
        "sec-ch-ua-mobile": session_profile["sec_ch_ua_mobile"],
        "sec-ch-ua-platform": session_profile["sec_ch_ua_platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": session_profile["ua"],
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": session_profile["lang"],
        "x-discord-timezone": session_profile["timezone"],
        "x-fingerprint": fingerprint,
        "x-super-properties": super_props,
    }
def context_properties(location="Register"):
    """Build x-context-properties header value."""
    raw = json.dumps({"location": location}, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()
def verify_token_integrity(session):
    try:
        r = robust_request(session, "GET", "https://discord.com/api/v9/users/@me")
        if r.status_code != 200:
            return "invalid"
        user_data = r.json() if r.text else {}
        r2 = robust_request(session, "GET", "https://discord.com/api/v9/users/@me/settings")
        if r2.status_code == 200:
            if user_data.get("verified") is False:
                return "unverified"
            return "Valid"
        elif r2.status_code in (401, 403):
            return "locked"
    except Exception:
        pass
    return "invalid"
_EXPORT_LOCK = threading.Lock()
_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Экспорт учетных данных аккаунта в соответствующий файл результатов
def export_credential(email, password, token, token_status, is_verified=False):
    with _EXPORT_LOCK:
        if not os.path.exists(_OUTPUT_DIR):
            try:
                os.makedirs(_OUTPUT_DIR, exist_ok=True)
            except Exception:
                pass
        status_lower = token_status.lower() if token_status else ""
        if "locked" in status_lower:
            target_name = "locked.txt"
        elif "invalid" in status_lower:
            target_name = "invalid.txt"
        elif is_verified:
            target_name = "email_verified.txt"
        else:
            target_name = "tokens.txt"
        filename = os.path.join(_OUTPUT_DIR, target_name)
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(f"{email}:{password}:{token}\n")
        except PermissionError:
            # Fallback to project root if output directory has restricted Windows permissions
            fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), target_name)
            try:
                with open(fallback, "a", encoding="utf-8") as f:
                    f.write(f"{email}:{password}:{token}\n")
            except Exception:
                pass
        with stats_lock:
            if "locked" in status_lower:
                stats['locked'] += 1
            elif "valid" in status_lower or is_verified:
                stats['valid'] += 1
class WebSocketClientKeepAlive:
    
    def __init__(self, token):
        self.token = token
        self._stop = threading.Event()
        self._thread = None
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    def stop(self):
        self._stop.set()
    def _run(self):
        try:
            ws = websocket.WebSocket()
            ws.settimeout(10)
            ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
            hello = json.loads(ws.recv())
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000
            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Windows",
                        "browser": "Chrome",
                        "device": "",
                        "system_locale": "en-US",
                        "browser_user_agent": random.choice(USER_AGENTS),
                        "browser_version": "136.0.0.0",
                        "os_version": "10",
                        "referrer": "https://discord.com/",
                        "referring_domain": "discord.com",
                        "referrer_current": "",
                        "referring_domain_current": "",
                        "release_channel": "stable",
                        "client_build_number": get_build_number(),
                        "client_event_source": None,
                    },
                    "presence": {
                        "status": "online",
                        "since": 0,
                        "activities": [],
                        "afk": False
                    },
                    "compress": False,
                    "client_state": {
                        "guild_versions": {},
                        "highest_last_message_id": "0",
                        "read_state_version": 0,
                        "user_guild_settings_version": -1,
                        "user_settings_version": -1,
                        "private_channels_version": "0",
                        "api_code_version": 0
                    }
                },
            }
            ws.send(json.dumps(identify))
            ready = False
            for _ in range(10):
                resp = json.loads(ws.recv())
                if resp.get("t") == "READY":
                    ready = True
                    break
                if resp.get("op") == 9:  
                    ws.close()
                    return
            if not ready:
                ws.close()
                return
            while not self._stop.is_set():
                ws.send(json.dumps({"op": 1, "d": None}))
                self._stop.wait(heartbeat_interval)
            ws.close()
        except Exception:
            pass
def process_hcaptcha(sitekey, rqdata, user_agent, proxy=None,
                     session_profile=None, discord_fingerprint=None,
                     cookies=None, super_props=None,
                     captcha_rqtoken=None, captcha_session_id=None,
                     url="https://discord.com/register"):
    solver_key = (config.get("nopecha") or config.get("solver", {})).get("api_key", "")
    solver = Solver(
        url=url,
        sitekey=sitekey,
        rqdata=rqdata,
        user_agent=user_agent,
        proxy=proxy,
        api_key=solver_key,
        session_profile=session_profile,
        discord_fingerprint=discord_fingerprint,
        cookies=cookies,
        super_props=super_props,
        captcha_rqtoken=captcha_rqtoken,
        captcha_session_id=captcha_session_id,
    )
    return solver.solve()

def register_discord_account_via_requests(email, username, password, proxy=None, mail_api=None):
    start_time = time.time()
    session = StealthSession()
    if proxy:
        proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
        session.proxies = {"http": proxy_url, "https": proxy_url}

    try:
        session_profile = resolve_session_profile()
        build_number = get_build_number(proxy)
        super_props = build_super_properties(build_number, session_profile)
        dcfduid, sdcfduid = acquire_discord_cookies(session)
        fingerprint = fetch_discord_fingerprint(session, dcfduid, sdcfduid, session_profile)
        headers = build_headers(fingerprint, super_props, session_profile)
        headers["x-context-properties"] = context_properties("Register")

        dob = _random_dob()
        reg_payload = {
            "consent": True,
            "fingerprint": fingerprint,
            "email": email,
            "username": username,
            "password": password,
            "date_of_birth": dob,
            "gift_code_sku_id": None,
            "invite": None,
            "promotional_email_opt_in": False
        }

        _file_log("[REQUEST] Submitting initial registration request to Discord API...")
        resp = robust_request(session, "POST", "https://discord.com/api/v9/auth/register", json=reg_payload, headers=headers, timeout=20)
        auth_token = None
        solve_time = 0.0

        if resp.status_code in (200, 201):
            auth_token = resp.json().get("token")
        elif resp.status_code == 400:
            data = resp.json() if resp.text else {}
            if data.get("errors", {}).get("username"):
                new_username = _random_username()
                Log._log("[TARGET]", f"Username was taken, retrying with: {new_username}", Y, D)
                reg_payload["username"] = new_username
                resp = robust_request(session, "POST", "https://discord.com/api/v9/auth/register", json=reg_payload, headers=headers, timeout=20)
                if resp.status_code in (200, 201):
                    return resp.json().get("token"), 0.0
                data = resp.json() if resp.text else {}

            captcha_key = data.get("captcha_key")
            sitekey = data.get("captcha_sitekey")
            rqdata = data.get("captcha_rqdata", "")
            rqtoken = data.get("captcha_rqtoken", "")
            cap_session_id = data.get("captcha_session_id", "")

            if sitekey or (isinstance(captcha_key, list) and "captcha-required" in captcha_key):
                sitekey = sitekey or "4c672d35-0701-42b2-88c3-78380b0db560"
                Log._log("[CAPTCHA]", "hCaptcha challenge detected, solving via NopeCHA Request API...", D, C)
                start_solve = time.time()
                captcha_solution, _ = process_hcaptcha(
                    sitekey=sitekey,
                    rqdata=rqdata,
                    user_agent=session_profile["ua"],
                    proxy=proxy,
                    session_profile=session_profile,
                    discord_fingerprint=fingerprint,
                    cookies=session.cookies.get_dict(),
                    super_props=super_props,
                    captcha_rqtoken=rqtoken,
                    captcha_session_id=cap_session_id,
                    url="https://discord.com/register"
                )
                solve_time = round(time.time() - start_solve, 1)

                if not captcha_solution or captcha_solution in ("ERROR_RATELIMIT", "ERROR_IP_REJECTED"):
                    Log.error(f"Captcha solving failed: {captcha_solution or 'No solution'}")
                    return None, 0.0

                Log._log("[CAPTCHA]", f"Captcha solved in {solve_time}s! Resubmitting registration...", G, C)
                reg_payload["captcha_key"] = captcha_solution
                if rqtoken:
                    reg_payload["captcha_rqtoken"] = rqtoken
                headers["x-captcha-key"] = captcha_solution
                if rqtoken:
                    headers["x-captcha-rqtoken"] = rqtoken

                resp2 = robust_request(session, "POST", "https://discord.com/api/v9/auth/register", json=reg_payload, headers=headers, timeout=20)
                if resp2.status_code in (200, 201):
                    auth_token = resp2.json().get("token")
                else:
                    Log.error(f"Registration failed after captcha [{resp2.status_code}]: {resp2.text[:200]}")
                    return None, solve_time
            else:
                Log.error(f"Registration rejected [{resp.status_code}]: {resp.text[:200]}")
                return None, 0.0
        else:
            Log.error(f"Registration request error [{resp.status_code}]: {resp.text[:200]}")
            return None, 0.0

        if not auth_token:
            Log.error("Could not extract token from registration response")
            return None, solve_time

        # Email verification via HTTP request (no browser)
        if mail_api:
            Log._log("[VERIFY]", "Waiting for verification email...", D, Y)
            verify_url = mail_api.get_verify_url(email, 3, 180, proxy)
            if verify_url:
                Log._log("[VERIFY]", "Verification link received! Verifying via requests...", D, G)
                try:
                    ver_resp = session.get(verify_url, timeout=20, allow_redirects=True)
                    final_url = str(ver_resp.url) if hasattr(ver_resp, "url") else verify_url
                    if "token=" in final_url:
                        token_code = final_url.split("token=")[1].split("&")[0]
                        v_post = session.post(
                            "https://discord.com/api/v9/auth/verify",
                            json={"token": token_code},
                            headers={
                                "authorization": auth_token,
                                "content-type": "application/json",
                                "user-agent": session_profile["ua"],
                                "x-fingerprint": fingerprint,
                                "x-super-properties": super_props
                            },
                            timeout=15
                        )
                        if v_post.status_code == 200:
                            new_tok = v_post.json().get("token")
                            if new_tok:
                                auth_token = new_tok
                                Log._log("[VERIFY]", "Email verified successfully!", G, C)
                except Exception as ve:
                    Log._log("[VERIFY]", f"Verification notice: {ve}", D, Y)

        return auth_token, solve_time
    except Exception as e:
        Log.error(f"Request registration error: {e}")
        return None, 0.0

def generate_lord_vault_token(email, username, password, proxy=None, current_num=1, mail_api=None, mail_provider_name=None):
    Log.proxy_header(current_num, proxy)
    email = email.lower()
    masked_mail = f"{email[:4]}***@{email.split('@')[1]}" if '@' in email else email
    Log._log("[TARGET]", f"User: {username} · Mail: {masked_mail}", W, C)
    
    if not mail_api:
        mail_api, mail_provider_name = get_mail_provider()
        if not mail_api:
            mail_api = DEVSMailApi(logger=print)
            mail_provider_name = "cybertemp (fallback)"

    cap_cfg = config.get("nopecha") or config.get("solver", {})
    has_req = cap_cfg.get("req_solver")
    has_ext = cap_cfg.get("extension_solver")
    mode = str(cap_cfg.get("solver_mode", "")).strip().lower()
    is_req = (has_req is True and has_ext is False) or (mode in ("request", "req", "api")) or (has_req and not has_ext)

    if is_req:
        Log._log("[REQUEST]", "Running pure request-based registration (No browser)...", D, C)
        auth_token, solve_time = register_discord_account_via_requests(
            email=email,
            username=username,
            password=password,
            proxy=proxy,
            mail_api=mail_api if verification_enabled else None
        )
    else:
        from engine.extension_browser import create_discord_account
        Log._log("[BROWSER]", "Launching stealth browser solver...", D, C)
        auth_token, solve_time = create_discord_account(
            email=email,
            username=username,
            password=password,
            proxy=proxy,
            mail_api=mail_api if verification_enabled else None,
            logger=Log.status
        )
    if not auth_token:
        Log.error("Registration failed to obtain token")
        return False

    Log.captcha_solved(solve_time, auth_token)
    Log.generated(auth_token)

    keepalive = WebSocketClientKeepAlive(auth_token)
    keepalive.start()

    # Сессия для проверки валидности созданного токена
    session = StealthSession()
    if proxy:
        proxy_url = f"http://{proxy}" if "://" not in proxy else proxy
        session.proxies = {"http": proxy_url, "https": proxy_url}
    session.headers.update({"authorization": auth_token})

    # Проверка целостности и статуса токена в Discord
    token_status = verify_token_integrity(session)
    is_verified = (token_status.lower() == "valid")
    if is_verified:
        Log.verified(auth_token)
    else:
        Log.error(f"Token status: {token_status.upper()}")

    # Экспорт учетных данных аккаунта
    export_credential(email, password, auth_token, token_status, is_verified=is_verified)
    keepalive.stop()
    return True
generate_9DEVS_token = generate_lord_vault_token


def stats_updater():
    while True:
        time.sleep(2)
        with stats_lock:
            total = stats['total']
            gen = stats['generated']
            ver = stats['verified']
            cap_fail = stats['captcha_failed']
            cap_solved = stats['captcha_solved']
            locked = stats['locked']
            valid = stats['valid']
        gen_pct = (gen / total * 100) if total else 0
        ver_pct = (ver / total * 100) if total else 0
        cap_fail_pct = (cap_fail / total * 100) if total else 0
        cap_solved_pct = (cap_solved / total * 100) if total else 0
        locked_pct = (locked / total * 100) if total else 0
        valid_pct = (valid / total * 100) if total else 0
        current_time = datetime.now().strftime('%H:%M')
        title = f"⚡ Lord Vault v4.2 PRO | Gen: {gen} | EV: {ver} | Solved: {cap_solved} | Failed: {cap_fail} | Total: {total} | {current_time}"
        ctypes.windll.kernel32.SetConsoleTitleW(title)
        import os
        if os.environ.get("GUI_MODE") == "1":
            print(f"GUI_STAT:{gen},{ver},{cap_solved},{cap_fail},{locked},{valid},{total}")
P = "\033[38;2;121;3;255m"     
C = "\033[38;2;3;248;252m"     
G = "\033[38;2;68;255;0m"      
D = "\033[38;2;92;94;91m"      
R = "\033[0m"                  
Y = "\033[38;2;255;200;50m"
RD = "\033[38;2;255;80;80m"
W = "\033[97m"
def display_banner(force_animate=False):
    import os
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if os.environ.get("GUI_MODE") == "1":
        return
    if os.name == "nt":
        os.system("")
    os.system("cls" if os.name == "nt" else "clear")
    from engine.banner import display_animated_banner
    display_animated_banner(force_animate=force_animate)
if __name__ == "__main__":
    _root = os.path.dirname(os.path.abspath(__file__))
    if "--menu" in sys.argv or "--cli" in sys.argv:
        cli_path = os.path.join(_root, "launchers", "start.py")
        subprocess.run([sys.executable, cli_path], cwd=_root)
        sys.exit(0)
    elif "--auth-joiner" in sys.argv:
        auth_path = os.path.join(_root, "engine", "auth_joiner.py")
        args = [a for a in sys.argv[1:] if a != "--auth-joiner"]
        subprocess.run([sys.executable, auth_path] + args, cwd=_root)
        sys.exit(0)
    elif "--joiner" in sys.argv:
        joiner_path = os.path.join(_root, "engine", "joiner.py")
        args = [a for a in sys.argv[1:] if a != "--joiner"]
        subprocess.run([sys.executable, joiner_path] + args, cwd=_root)
        sys.exit(0)

    display_banner()
    cap_cfg = config.get("nopecha") or config.get("solver", {})
    api_key = cap_cfg.get("api_key", "").strip()
    if not api_key:
        api_key = config.get("solver", {}).get("api_key", "").strip()
    if not api_key:
        print(f"  {Fore.RED}⚠ No NopeCHA API key set!{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}  Get your key at: https://nopecha.com{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}  Set it in config.json under nopecha.api_key.{Style.RESET_ALL}")
        sys.exit(1)
    has_req = cap_cfg.get("req_solver")
    has_ext = cap_cfg.get("extension_solver")
    mode = str(cap_cfg.get("solver_mode", "")).strip().lower()
    is_req = (has_req is True and has_ext is False) or (mode in ("request", "req", "api")) or (has_req and not has_ext)

    if is_req:
        print(f"  {D}[STARTUP]{R} {C}Solver Mode:{R} {G}Pure Request (NopeCHA API / VPS){R}")
        print(f"  {D}[STARTUP]{R} {C}Validating NopeCHA API Key...{R}")
        import urllib.request, json
        try:
            r = urllib.request.urlopen(f"https://api.nopecha.com/status?key={api_key}", timeout=10)
            data = json.loads(r.read().decode("utf-8"))
            plan = data.get("plan", "Unknown")
            credits_left = data.get("credit", 0)
            if plan.lower() == "reviewer":
                print(f"  {D}[STARTUP]{R} {Fore.YELLOW}⚠ Notice: Key is on 'Reviewer' plan ({credits_left} credits left).{R}")
                print(f"  {D}[STARTUP]{R} {Fore.YELLOW}  Reviewer plan does NOT allow Request Token API (HTTP 402).{R}")
                print(f"  {D}[STARTUP]{R} {Fore.YELLOW}  Tip: Switch to Browser Extension mode (Option [8] in start.py) to solve captchas.{R}")
            else:
                print(f"  {D}[STARTUP]{R} {G}✓ NopeCHA API key verified (Plan: {plan}, Credits: {credits_left}){R}")
        except Exception as e:
            print(f"  {D}[STARTUP]{R} {Fore.YELLOW}⚠ Warning verifying NopeCHA status: {e}{R}")
    else:
        print(f"  {D}[STARTUP]{R} {C}Solver Mode:{R} {G}Browser Extension (NopeCHA){R}")
        try:
            from engine.extension_browser import get_browser, sync_api_key
            print(f"  {D}[STARTUP]{R} {C}Validating NopeCHA API Key...{R}")
            api_key_valid = sync_api_key()
            if api_key_valid == "SERVER_ERROR":
                print(f"  {D}[STARTUP]{R} {Fore.YELLOW}⚠ Server error! The NopeCHA API might be down. Please check again in 3-4 minutes.{R}")
                sys.exit(1)
            elif not api_key_valid:
                print(f"  {D}[STARTUP]{R} {Fore.RED}⚠ FATAL: Invalid NopeCHA API Key. Generator explicitly aborted!{R}")
                sys.exit(1)
            print(f"  {D}[STARTUP]{R} {G}✓ NopeCHA extension ready (Browser Solver Active){R}")
        except SystemExit:
            raise
        except ImportError as e:
            print(f"  {D}[STARTUP]{R} {Fore.YELLOW}⚠ Extension browser unavailable: {e}{R}")
            print(f"  {D}[STARTUP]{R} {D}  pip install nodriver{R}")
        
    import atexit
    def cleanup_browser():
        try: get_browser().stop()
        except: pass
    atexit.register(cleanup_browser)
            
    print()
    
    if vpn_manager.is_enabled():
        print(f"  {D}[STARTUP]{R} {G}Network Mode: VPN Auto-Rotation (Active){R}")
        vpn_manager.startup_check()
    else:
        print(f"  {D}[STARTUP]{R} {G}Network Mode: Direct / Local IP{R}")

    NUM_THREADS = int(config.get("threading", {}).get("generator", config.get("threads", 1)))
    if vpn_manager.is_enabled() and vpn_manager.rotate_every_account:
        NUM_THREADS = 1

    semaphore = threading.Semaphore(NUM_THREADS)
    _stop_event = threading.Event()
    def _signal_handler(sig, frame):
        if not _stop_event.is_set():
            _stop_event.set()
            print(f"\n  {Fore.YELLOW}⚠ Halting generator immediately...{R}")
            os._exit(0)
    import signal
    signal.signal(signal.SIGINT, _signal_handler)
    
    if os.environ.get("GUI_MODE") != "1":
        try:
            import keyboard
            keyboard.add_hotkey('ctrl+x', lambda: _signal_handler(None, None))
        except Exception:
            pass
            
    stats_thread = threading.Thread(target=stats_updater, daemon=True)
    stats_thread.start()
    def worker(current_num):
        proxy = None  # VPN mode — no proxy needed
        acc_created = False
        rotated = False
        try:
            mail_api_temp, mail_provider_name_temp = get_mail_provider()
            if not mail_api_temp:
                mail_api_temp = DEVSMailApi(logger=print)
            email = mail_api_temp.create_account(proxy=proxy)
            if not email:
                if isinstance(mail_api_temp, ZeusProvider):
                    reason = getattr(mail_api_temp, '_last_error', '') or 'unknown_error'
                    bal = mail_api_temp.check_balance()
                    try:
                        no_bal = bal is not None and float(bal) <= 0
                    except (ValueError, TypeError):
                        no_bal = False
                        
                    if no_bal:
                        Log.error(f"No Balance (Zeus: {bal})")
                    else:
                        reason_lower = str(reason).lower()
                        if "stock" in reason_lower or "quantity" in reason_lower or "enough" in reason_lower or "empty" in reason_lower:
                            Log.error(f"No Stock ({reason}) — waiting 30s...")
                            time.sleep(30)
                            email = mail_api_temp.create_account(proxy=proxy)
                            if not email:
                                new_reason = getattr(mail_api_temp, '_last_error', '') or reason
                                Log.error(f"Still No Stock ({new_reason}) — skipping")
                                return
                        else:
                            Log.error(f"Zeus Failed: {reason} (Bal: {bal})")
                            return
                else:
                    Log.error("emails are not available")
                    return
            if not email:
                return
            username = _random_username()
            mail_pass = None
            if hasattr(mail_api_temp, '_email_data') and isinstance(mail_api_temp._email_data, dict):
                mail_pass = mail_api_temp._email_data.get("password")
            elif hasattr(mail_api_temp, 'password') and mail_api_temp.password:
                mail_pass = mail_api_temp.password
            password = mail_pass if mail_pass else _random_password()
            acc_created = bool(generate_lord_vault_token(email, username, password, proxy, current_num, mail_api_temp, mail_provider_name_temp))
        except Exception as e:
            err_msg = str(e)
            Log.error(f"Worker exception: {err_msg}")
            if vpn_manager and vpn_manager.is_enabled() and vpn_manager.rotate_on_flag and vpn_manager.reconnect_command:
                err_lower = err_msg.lower()
                if "10013" in err_lower or "forbidden by its access permissions" in err_lower:
                    # Windows socket blocked while VPN is establishing; give network stack time to unblock
                    time.sleep(2.5)
                elif any(k in err_lower for k in ("timed out", "curl: (28)", "connection", "rate", "429")):
                    vpn_manager.rotate_ip(reason="Rate limit / connection timeout")
                    rotated = True
        finally:
            if vpn_manager and vpn_manager.is_enabled() and not _stop_event.is_set() and not rotated:
                if acc_created:
                    if vpn_manager.rotate_every_account:
                        vpn_manager.rotate_ip(reason="Post-account rotation")
                else:
                    # Account failed or error occurred -> Rotate VPN IP so next attempt has a fresh IP
                    vpn_manager.rotate_ip(reason="Account creation failed / error")
            semaphore.release()

    while not _stop_event.is_set():
        semaphore.acquire()
        if _stop_event.is_set():
            semaphore.release()
            break
        
        with gen_lock:
            gen_count += 1
            current_num = gen_count
        t = threading.Thread(target=worker, args=(current_num,), daemon=True)
        t.start()
    print(f"  {G}✓ Generator stopped cleanly.{R}")
