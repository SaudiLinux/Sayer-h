#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة فحص تطبيقات الويب لبرنامج Sayer
"""

import requests
import concurrent.futures
import re
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from tqdm import tqdm

from .utils import normalize_url, get_random_user_agent, is_valid_url


class WebScanner:
    """فئة فحص تطبيقات الويب"""
    
    def __init__(self, target, threads=5, timeout=30, logger=None):
        """تهيئة الفئة"""
        self.target = normalize_url(target) if is_valid_url(target) else f"http://{target}"
        self.threads = threads
        self.timeout = timeout
        self.logger = logger
        self.results = {}
        self.visited_urls = set()
        self.urls_to_scan = set([self.target])
        self.forms = []
        self.headers = []
        self.cookies = []
        self.common_files = [
            "robots.txt", "sitemap.xml", "crossdomain.xml", "clientaccesspolicy.xml",
            "phpinfo.php", "info.php", "admin/", "administrator/", "login/", "wp-login.php",
            "wp-admin/", "admin.php", "login.php", "administrator.php", "backup/", "backup.zip",
            "backup.tar.gz", "backup.sql", ".git/", ".svn/", ".htaccess", ".env", "config.php"
        ]
        
        # قائمة الثغرات الشائعة للفحص
        self.vulnerabilities = {
            "xss": {
                "patterns": [
                    "<script>alert('XSS')</script>",
                    "<img src=x onerror=alert('XSS')>",
                    "javascript:alert('XSS')"
                ],
                "description": "Cross-Site Scripting (XSS)"
            },
            "sqli": {
                "patterns": [
                    "' OR '1'='1",
                    "' OR 1=1 --",
                    "\" OR 1=1 --"
                ],
                "description": "SQL Injection"
            },
            "lfi": {
                "patterns": [
                    "../../../etc/passwd",
                    "..\\..\\..\\windows\\win.ini",
                    "/etc/passwd"
                ],
                "description": "Local File Inclusion (LFI)"
            }
        }
    
    def scan(self):
        """تنفيذ عملية فحص تطبيق الويب"""
        if self.logger:
            self.logger.info(f"[+] بدء فحص تطبيق الويب: {self.target}")
        
        # فحص الملفات الشائعة
        self._scan_common_files()
        
        # زحف الموقع واستخراج الروابط والنماذج
        self._crawl_website()
        
        # فحص الثغرات في النماذج
        self._scan_forms()
        
        # فحص ترويسات HTTP
        self._scan_headers()
        
        # فحص ملفات تكوين الموقع
        self._scan_misconfigurations()
        
        return self.results
    
    def _scan_common_files(self):
        """فحص الملفات والمسارات الشائعة"""
        common_files_results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            future_to_file = {}
            
            for file in self.common_files:
                url = urljoin(self.target, file)
                future = executor.submit(self._check_url_exists, url)
                future_to_file[future] = file
            
            for future in tqdm(concurrent.futures.as_completed(future_to_file), 
                              total=len(future_to_file), 
                              desc="فحص الملفات الشائعة", 
                              disable=self.logger is None):
                file = future_to_file[future]
                try:
                    exists, status_code, content_type, content_length = future.result()
                    if exists:
                        common_files_results[file] = {
                            "url": urljoin(self.target, file),
                            "status_code": status_code,
                            "content_type": content_type,
                            "content_length": content_length
                        }
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"[!] خطأ في فحص الملف {file}: {str(e)}")
        
        self.results["common_files"] = common_files_results
    
    def _check_url_exists(self, url):
        """التحقق من وجود عنوان URL"""
        try:
            headers = {"User-Agent": get_random_user_agent()}
            response = requests.head(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            
            # إذا كان الرد HEAD غير مدعوم، جرب GET
            if response.status_code >= 400:
                response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            
            content_type = response.headers.get("Content-Type", "")
            content_length = response.headers.get("Content-Length", "0")
            
            return (response.status_code < 400, response.status_code, content_type, content_length)
        except Exception:
            return (False, 0, "", "0")
    
    def _crawl_website(self, max_urls=100):
        """زحف الموقع واستخراج الروابط والنماذج"""
        if self.logger:
            self.logger.info(f"[+] بدء زحف الموقع: {self.target}")
        
        crawl_results = {
            "pages": {},
            "forms": [],
            "links": []
        }
        
        while self.urls_to_scan and len(self.visited_urls) < max_urls:
            url = self.urls_to_scan.pop()
            
            if url in self.visited_urls:
                continue
            
            self.visited_urls.add(url)
            
            try:
                headers = {"User-Agent": get_random_user_agent()}
                response = requests.get(url, headers=headers, timeout=self.timeout)
                
                if response.status_code >= 400:
                    continue
                
                # تخزين معلومات الصفحة
                crawl_results["pages"][url] = {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": len(response.content)
                }
                
                # تحليل محتوى HTML
                if "text/html" in response.headers.get("Content-Type", ""):
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # استخراج الروابط
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        absolute_url = urljoin(url, href)
                        
                        # تجاهل الروابط الخارجية والبريد الإلكتروني والهاشتاج
                        if not absolute_url.startswith(self.target) or "mailto:" in href or href.startswith("#"):
                            continue
                        
                        if absolute_url not in self.visited_urls and absolute_url not in self.urls_to_scan:
                            self.urls_to_scan.add(absolute_url)
                            crawl_results["links"].append({
                                "url": absolute_url,
                                "text": a_tag.get_text(strip=True)
                            })
                    
                    # استخراج النماذج
                    for form in soup.find_all("form"):
                        form_data = {
                            "action": urljoin(url, form.get("action", "")),
                            "method": form.get("method", "get").upper(),
                            "inputs": []
                        }
                        
                        for input_tag in form.find_all(["input", "textarea", "select"]):
                            input_type = input_tag.get("type", "text")
                            input_name = input_tag.get("name", "")
                            
                            if input_name and input_type not in ["submit", "button", "reset", "image"]:
                                form_data["inputs"].append({
                                    "name": input_name,
                                    "type": input_type
                                })
                        
                        if form_data["inputs"]:
                            self.forms.append(form_data)
                            crawl_results["forms"].append(form_data)
                
                # تخزين الكوكيز والترويسات
                if response.cookies:
                    for cookie in response.cookies:
                        self.cookies.append({
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": cookie.domain,
                            "path": cookie.path,
                            "secure": cookie.secure,
                            "expires": cookie.expires
                        })
                
                if response.headers:
                    self.headers.append({
                        "url": url,
                        "headers": dict(response.headers)
                    })
            
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[!] خطأ في زحف الصفحة {url}: {str(e)}")
        
        self.results["crawl"] = crawl_results
    
    def _scan_forms(self):
        """فحص النماذج للكشف عن الثغرات"""
        if not self.forms:
            self.results["forms_vulnerabilities"] = {"error": "لم يتم العثور على نماذج للفحص"}
            return
        
        forms_vulnerabilities = []
        
        for form in self.forms:
            form_vulnerabilities = {
                "form": form,
                "vulnerabilities": []
            }
            
            # فحص كل نوع من أنواع الثغرات
            for vuln_type, vuln_info in self.vulnerabilities.items():
                for pattern in vuln_info["patterns"]:
                    # إنشاء بيانات النموذج للاختبار
                    form_data = {}
                    for input_field in form["inputs"]:
                        if input_field["type"] in ["text", "search", "url", "tel", "email", "password"]:
                            form_data[input_field["name"]] = pattern
                        else:
                            form_data[input_field["name"]] = "test"
                    
                    try:
                        headers = {"User-Agent": get_random_user_agent()}
                        
                        if form["method"] == "GET":
                            response = requests.get(
                                form["action"],
                                params=form_data,
                                headers=headers,
                                timeout=self.timeout,
                                allow_redirects=False
                            )
                        else:  # POST
                            response = requests.post(
                                form["action"],
                                data=form_data,
                                headers=headers,
                                timeout=self.timeout,
                                allow_redirects=False
                            )
                        
                        # التحقق من وجود الثغرة في الاستجابة
                        if pattern in response.text:
                            form_vulnerabilities["vulnerabilities"].append({
                                "type": vuln_type,
                                "description": vuln_info["description"],
                                "pattern": pattern,
                                "status_code": response.status_code
                            })
                    
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"[!] خطأ في فحص النموذج {form['action']}: {str(e)}")
            
            if form_vulnerabilities["vulnerabilities"]:
                forms_vulnerabilities.append(form_vulnerabilities)
        
        self.results["forms_vulnerabilities"] = forms_vulnerabilities
    
    def _scan_headers(self):
        """فحص ترويسات HTTP للكشف عن المشكلات الأمنية"""
        if not self.headers:
            self.results["headers_issues"] = {"error": "لم يتم العثور على ترويسات للفحص"}
            return
        
        headers_issues = []
        
        # قائمة الترويسات الأمنية المهمة
        security_headers = {
            "Strict-Transport-Security": "يحدد استخدام HTTPS بدلاً من HTTP",
            "Content-Security-Policy": "يحدد مصادر المحتوى المسموح بها",
            "X-Content-Type-Options": "يمنع تخمين نوع MIME",
            "X-Frame-Options": "يحمي من هجمات clickjacking",
            "X-XSS-Protection": "يحمي من هجمات XSS",
            "Referrer-Policy": "يتحكم في معلومات الإحالة المرسلة",
            "Feature-Policy": "يتحكم في الميزات والواجهات البرمجية المتاحة",
            "Permissions-Policy": "يتحكم في الميزات والواجهات البرمجية المتاحة (بديل Feature-Policy)"
        }
        
        for header_info in self.headers:
            url = header_info["url"]
            headers = header_info["headers"]
            
            header_issues = {
                "url": url,
                "missing_headers": [],
                "insecure_headers": []
            }
            
            # التحقق من الترويسات الأمنية المفقودة
            for header, description in security_headers.items():
                if header not in headers:
                    header_issues["missing_headers"].append({
                        "header": header,
                        "description": description
                    })
            
            # التحقق من الترويسات غير الآمنة
            if "Set-Cookie" in headers:
                cookies = headers["Set-Cookie"].split(",")
                for cookie in cookies:
                    if "secure" not in cookie.lower() or "httponly" not in cookie.lower():
                        header_issues["insecure_headers"].append({
                            "header": "Set-Cookie",
                            "value": cookie,
                            "issue": "الكوكي غير آمن (يفتقد إلى secure أو httponly)"
                        })
            
            if "Server" in headers and headers["Server"]:
                server = headers["Server"]
                if re.search(r"(apache|nginx|iis|tomcat).*?([0-9]+\.[0-9]+\.[0-9]+)", server, re.I):
                    header_issues["insecure_headers"].append({
                        "header": "Server",
                        "value": server,
                        "issue": "يكشف عن إصدار الخادم"
                    })
            
            if header_issues["missing_headers"] or header_issues["insecure_headers"]:
                headers_issues.append(header_issues)
        
        self.results["headers_issues"] = headers_issues
    
    def _scan_misconfigurations(self):
        """فحص سوء التكوين في الموقع"""
        misconfigurations = []
        
        # فحص ملف robots.txt
        robots_url = urljoin(self.target, "robots.txt")
        try:
            response = requests.get(robots_url, timeout=self.timeout)
            if response.status_code == 200:
                disallowed_paths = re.findall(r"Disallow:\s*(.+)", response.text)
                if disallowed_paths:
                    misconfigurations.append({
                        "type": "robots.txt",
                        "url": robots_url,
                        "description": "تم العثور على مسارات محظورة في ملف robots.txt",
                        "details": disallowed_paths
                    })
        except Exception:
            pass
        
        # فحص ملف .env
        env_url = urljoin(self.target, ".env")
        try:
            response = requests.get(env_url, timeout=self.timeout)
            if response.status_code == 200 and "DB_" in response.text:
                misconfigurations.append({
                    "type": ".env",
                    "url": env_url,
                    "description": "تم العثور على ملف .env يحتوي على معلومات حساسة",
                    "details": "يحتوي على متغيرات بيئية حساسة"
                })
        except Exception:
            pass
        
        # فحص مجلد .git
        git_url = urljoin(self.target, ".git/config")
        try:
            response = requests.get(git_url, timeout=self.timeout)
            if response.status_code == 200 and "[core]" in response.text:
                misconfigurations.append({
                    "type": ".git",
                    "url": git_url,
                    "description": "تم العثور على مجلد .git مكشوف",
                    "details": "يمكن الوصول إلى مستودع Git"
                })
        except Exception:
            pass
        
        # فحص phpinfo
        phpinfo_urls = ["phpinfo.php", "info.php", "php_info.php", "test.php"]
        for phpinfo_path in phpinfo_urls:
            phpinfo_url = urljoin(self.target, phpinfo_path)
            try:
                response = requests.get(phpinfo_url, timeout=self.timeout)
                if response.status_code == 200 and ("<title>phpinfo()</title>" in response.text or "PHP Version" in response.text):
                    misconfigurations.append({
                        "type": "phpinfo",
                        "url": phpinfo_url,
                        "description": "تم العثور على صفحة phpinfo مكشوفة",
                        "details": "تكشف عن معلومات حساسة حول تكوين PHP"
                    })
                    break
            except Exception:
                pass
        
        self.results["misconfigurations"] = misconfigurations