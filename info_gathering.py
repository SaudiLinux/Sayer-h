#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة جمع المعلومات لبرنامج Sayer
"""

import socket
import whois as python_whois
import dns.resolver
import requests
import ssl
import OpenSSL
import concurrent.futures
import json
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm

from .utils import is_valid_domain, is_valid_ip, is_valid_url, normalize_url, get_random_user_agent


class InfoGathering:
    """فئة جمع المعلومات عن الهدف"""
    
    def __init__(self, target, threads=5, timeout=30, logger=None):
        """تهيئة الفئة"""
        self.target = target
        self.threads = threads
        self.timeout = timeout
        self.logger = logger
        self.results = {}
        
        # تحديد نوع الهدف
        if is_valid_ip(target):
            self.target_type = "ip"
        elif is_valid_domain(target):
            self.target_type = "domain"
        elif is_valid_url(target):
            self.target_type = "url"
            self.target = normalize_url(target)
        else:
            self.target_type = "unknown"
    
    def gather(self):
        """تنفيذ عملية جمع المعلومات"""
        if self.target_type == "unknown":
            if self.logger:
                self.logger.error(f"[!] نوع الهدف غير معروف: {self.target}")
            return {"error": f"نوع الهدف غير معروف: {self.target}"}
        
        # جمع المعلومات الأساسية
        self.results["basic_info"] = {
            "target": self.target,
            "target_type": self.target_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # تنفيذ عمليات جمع المعلومات المختلفة
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            tasks = {
                executor.submit(self._get_dns_info): "dns_info",
                executor.submit(self._get_whois_info): "whois_info",
                executor.submit(self._get_ip_info): "ip_info",
                executor.submit(self._get_headers): "headers",
                executor.submit(self._get_ssl_info): "ssl_info",
                executor.submit(self._get_technologies): "technologies"
            }
            
            for future in tqdm(concurrent.futures.as_completed(tasks), 
                              total=len(tasks), 
                              desc="جمع المعلومات", 
                              disable=self.logger is None):
                task_name = tasks[future]
                try:
                    self.results[task_name] = future.result()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"[!] خطأ في {task_name}: {str(e)}")
                    self.results[task_name] = {"error": str(e)}
        
        return self.results
    
    def _get_dns_info(self):
        """الحصول على معلومات DNS"""
        if self.target_type not in ["domain", "url"]:
            return {"error": "الهدف ليس نطاقًا أو عنوان URL"}
        
        domain = self.target
        if self.target_type == "url":
            domain = self.target.split("//")[-1].split("/")[0]
        
        dns_info = {}
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]
        
        for record_type in record_types:
            try:
                answers = dns.resolver.resolve(domain, record_type)
                dns_info[record_type] = [str(answer) for answer in answers]
            except Exception:
                dns_info[record_type] = []
        
        return dns_info
    
    def _get_whois_info(self):
        """الحصول على معلومات WHOIS"""
        if self.target_type not in ["domain", "url", "ip"]:
            return {"error": "الهدف ليس نطاقًا أو عنوان URL أو عنوان IP"}
        
        domain_or_ip = self.target
        if self.target_type == "url":
            domain_or_ip = self.target.split("//")[-1].split("/")[0]
        
        try:
            w = python_whois.whois(domain_or_ip)
            whois_info = {}
            
            # تحويل كائن WHOIS إلى قاموس
            for key, value in w.items():
                if isinstance(value, list):
                    whois_info[key] = [str(item) for item in value]
                elif isinstance(value, datetime):
                    whois_info[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    whois_info[key] = str(value) if value is not None else None
            
            return whois_info
        except Exception as e:
            return {"error": str(e)}
    
    def _get_ip_info(self):
        """الحصول على معلومات عنوان IP"""
        ip = self.target if self.target_type == "ip" else None
        
        if self.target_type in ["domain", "url"]:
            domain = self.target
            if self.target_type == "url":
                domain = self.target.split("//")[-1].split("/")[0]
            
            try:
                ip = socket.gethostbyname(domain)
            except socket.gaierror:
                return {"error": f"لا يمكن الحصول على عنوان IP للنطاق: {domain}"}
        
        if not ip:
            return {"error": "لا يمكن الحصول على عنوان IP"}
        
        # الحصول على معلومات الموقع الجغرافي لعنوان IP
        try:
            response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"فشل الاستعلام عن معلومات IP: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _get_headers(self):
        """الحصول على ترويسات HTTP"""
        if self.target_type not in ["url", "domain"]:
            return {"error": "الهدف ليس عنوان URL أو نطاقًا"}
        
        url = self.target
        if self.target_type == "domain":
            url = f"http://{self.target}"
        
        try:
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            
            # تحويل ترويسات الاستجابة إلى قاموس
            response_headers = {}
            for key, value in response.headers.items():
                response_headers[key] = value
            
            return {
                "status_code": response.status_code,
                "headers": response_headers,
                "final_url": response.url
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_ssl_info(self):
        """الحصول على معلومات شهادة SSL"""
        if self.target_type not in ["url", "domain"]:
            return {"error": "الهدف ليس عنوان URL أو نطاقًا"}
        
        hostname = self.target
        if self.target_type == "url":
            hostname = self.target.split("//")[-1].split("/")[0]
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # تحويل شهادة SSL إلى معلومات مفهومة
                    cert_info = {
                        "subject": dict(x[0] for x in cert["subject"]),
                        "issuer": dict(x[0] for x in cert["issuer"]),
                        "version": cert["version"],
                        "serialNumber": cert["serialNumber"],
                        "notBefore": cert["notBefore"],
                        "notAfter": cert["notAfter"]
                    }
                    
                    # الحصول على معلومات إضافية باستخدام OpenSSL
                    cert_bin = ssock.getpeercert(True)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_bin)
                    cert_info["signature_algorithm"] = x509.get_signature_algorithm().decode()
                    
                    return cert_info
        except ssl.SSLError as e:
            return {"error": f"خطأ SSL: {str(e)}"}
        except socket.error as e:
            return {"error": f"خطأ اتصال: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _get_technologies(self):
        """الكشف عن التقنيات المستخدمة في الموقع"""
        if self.target_type not in ["url", "domain"]:
            return {"error": "الهدف ليس عنوان URL أو نطاقًا"}
        
        url = self.target
        if self.target_type == "domain":
            url = f"http://{self.target}"
        
        try:
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            soup = BeautifulSoup(response.text, "html.parser")
            
            technologies = {
                "server": response.headers.get("Server", "Unknown"),
                "technologies": [],
                "meta_tags": {},
                "javascript_libraries": []
            }
            
            # البحث عن وسوم meta
            for meta in soup.find_all("meta"):
                name = meta.get("name", meta.get("property", ""))
                content = meta.get("content", "")
                if name and content:
                    technologies["meta_tags"][name] = content
            
            # البحث عن مكتبات JavaScript
            js_libraries = [
                "jQuery", "React", "Vue", "Angular", "Bootstrap", "Modernizr",
                "Backbone", "Ember", "Knockout", "Prototype", "MooTools"
            ]
            
            for script in soup.find_all("script"):
                src = script.get("src", "")
                content = script.string if script.string else ""
                
                for lib in js_libraries:
                    if (src and lib.lower() in src.lower()) or (content and lib.lower() in content.lower()):
                        if lib not in technologies["javascript_libraries"]:
                            technologies["javascript_libraries"].append(lib)
            
            # البحث عن أطر العمل والتقنيات الشائعة
            common_technologies = [
                "WordPress", "Joomla", "Drupal", "Magento", "Shopify",
                "Laravel", "Django", "Flask", "Express", "Ruby on Rails",
                "ASP.NET", "PHP", "Node.js", "Apache", "Nginx", "IIS"
            ]
            
            for tech in common_technologies:
                if tech.lower() in response.text.lower() or tech.lower() in str(response.headers).lower():
                    technologies["technologies"].append(tech)
            
            return technologies
        except Exception as e:
            return {"error": str(e)}