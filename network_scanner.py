#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة فحص الشبكة لبرنامج Sayer
"""

import socket
import ipaddress
import concurrent.futures
import nmap
import subprocess
import re
import platform
from tqdm import tqdm

from .utils import is_valid_ip, is_valid_domain, is_valid_url


class NetworkScanner:
    """فئة فحص الشبكة"""
    
    def __init__(self, target, threads=5, timeout=30, logger=None):
        """تهيئة الفئة"""
        self.target = target
        self.threads = threads
        self.timeout = timeout
        self.logger = logger
        self.results = {}
        
        # تحديد نوع الهدف وتحويله إلى عنوان IP أو نطاق IP إذا لزم الأمر
        if is_valid_ip(target):
            self.target_type = "ip"
            self.ip = target
        elif is_valid_domain(target) or is_valid_url(target):
            self.target_type = "domain"
            try:
                domain = target
                if is_valid_url(target):
                    domain = target.split("//")[-1].split("/")[0]
                self.ip = socket.gethostbyname(domain)
            except socket.gaierror:
                self.ip = None
                if self.logger:
                    self.logger.error(f"[!] لا يمكن الحصول على عنوان IP للنطاق: {domain}")
        elif "/" in target:  # نطاق CIDR
            self.target_type = "cidr"
            self.ip = target
        elif "-" in target:  # نطاق IP
            self.target_type = "range"
            self.ip = target
        else:
            self.target_type = "unknown"
            self.ip = None
            if self.logger:
                self.logger.error(f"[!] نوع الهدف غير معروف: {target}")
    
    def scan(self):
        """تنفيذ عملية فحص الشبكة"""
        if self.ip is None:
            return {"error": f"لا يمكن الحصول على عنوان IP للهدف: {self.target}"}
        
        if self.logger:
            self.logger.info(f"[+] بدء فحص الشبكة للهدف: {self.target} ({self.ip})")
        
        # فحص المنافذ المفتوحة
        self.results["port_scan"] = self._scan_ports()
        
        # فحص الخدمات
        self.results["service_scan"] = self._scan_services()
        
        # فحص نظام التشغيل
        self.results["os_detection"] = self._detect_os()
        
        # تتبع المسار
        self.results["traceroute"] = self._traceroute()
        
        return self.results
    
    def _scan_ports(self, common_ports=True):
        """فحص المنافذ المفتوحة"""
        if self.logger:
            self.logger.info("[+] بدء فحص المنافذ...")
        
        # تحديد المنافذ للفحص
        if common_ports:
            # المنافذ الشائعة
            ports = [
                21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
                1723, 3306, 3389, 5900, 8080, 8443
            ]
        else:
            # فحص المنافذ من 1 إلى 1024
            ports = range(1, 1025)
        
        open_ports = {}
        
        # استخدام nmap لفحص المنافذ
        try:
            nm = nmap.PortScanner()
            target = self.ip
            
            # تحويل نطاق IP إلى صيغة مناسبة لـ nmap
            if self.target_type == "range":
                start_ip, end_ip = self.ip.split("-")
                target = f"{start_ip}-{end_ip}"
            
            # تحديد المنافذ للفحص
            ports_str = ",".join(map(str, ports))
            
            # تنفيذ الفحص
            nm.scan(hosts=target, ports=ports_str, arguments=f"-T4 --max-retries 1 --host-timeout {self.timeout}s")
            
            # معالجة النتائج
            for host in nm.all_hosts():
                if host not in open_ports:
                    open_ports[host] = []
                
                for proto in nm[host].all_protocols():
                    for port in nm[host][proto].keys():
                        port_info = nm[host][proto][port]
                        if port_info["state"] == "open":
                            open_ports[host].append({
                                "port": port,
                                "protocol": proto,
                                "service": port_info["name"],
                                "state": port_info["state"]
                            })
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"[!] خطأ في فحص المنافذ: {str(e)}")
            
            # استخدام طريقة بديلة باستخدام socket
            if self.target_type in ["ip", "domain"]:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
                    future_to_port = {executor.submit(self._check_port, self.ip, port): port for port in ports}
                    
                    for future in tqdm(concurrent.futures.as_completed(future_to_port), 
                                      total=len(future_to_port), 
                                      desc="فحص المنافذ", 
                                      disable=self.logger is None):
                        port = future_to_port[future]
                        try:
                            is_open, service = future.result()
                            if is_open:
                                if self.ip not in open_ports:
                                    open_ports[self.ip] = []
                                
                                open_ports[self.ip].append({
                                    "port": port,
                                    "protocol": "tcp",
                                    "service": service,
                                    "state": "open"
                                })
                        except Exception as e:
                            if self.logger:
                                self.logger.error(f"[!] خطأ في فحص المنفذ {port}: {str(e)}")
        
        return open_ports
    
    def _check_port(self, ip, port):
        """التحقق من حالة منفذ معين"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        
        try:
            sock.connect((ip, port))
            service = socket.getservbyport(port, "tcp") if port < 1024 else "unknown"
            return True, service
        except (socket.timeout, socket.error):
            return False, ""
        finally:
            sock.close()
    
    def _scan_services(self):
        """فحص الخدمات على المنافذ المفتوحة"""
        if self.logger:
            self.logger.info("[+] بدء فحص الخدمات...")
        
        services = {}
        
        # التحقق من وجود نتائج فحص المنافذ
        if "port_scan" not in self.results or not self.results["port_scan"]:
            return {"error": "لم يتم العثور على منافذ مفتوحة للفحص"}
        
        # استخدام nmap لفحص الخدمات
        try:
            nm = nmap.PortScanner()
            
            for host, ports in self.results["port_scan"].items():
                if not ports:
                    continue
                
                services[host] = []
                
                # تجميع المنافذ المفتوحة
                open_ports = [str(p["port"]) for p in ports]
                ports_str = ",".join(open_ports)
                
                # تنفيذ الفحص مع تحديد الخدمات والإصدارات
                nm.scan(hosts=host, ports=ports_str, arguments=f"-sV -T4 --max-retries 1 --host-timeout {self.timeout}s")
                
                # معالجة النتائج
                if host in nm.all_hosts():
                    for proto in nm[host].all_protocols():
                        for port in nm[host][proto].keys():
                            port_info = nm[host][proto][port]
                            services[host].append({
                                "port": port,
                                "protocol": proto,
                                "service": port_info["name"],
                                "product": port_info.get("product", ""),
                                "version": port_info.get("version", ""),
                                "extrainfo": port_info.get("extrainfo", "")
                            })
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"[!] خطأ في فحص الخدمات: {str(e)}")
            
            # استخدام المعلومات المتوفرة من فحص المنافذ
            for host, ports in self.results["port_scan"].items():
                services[host] = [{
                    "port": p["port"],
                    "protocol": p["protocol"],
                    "service": p["service"],
                    "product": "",
                    "version": "",
                    "extrainfo": "معلومات محدودة (فشل فحص الخدمات)"
                } for p in ports]
        
        return services
    
    def _detect_os(self):
        """الكشف عن نظام التشغيل"""
        if self.logger:
            self.logger.info("[+] بدء الكشف عن نظام التشغيل...")
        
        os_info = {}
        
        # استخدام nmap للكشف عن نظام التشغيل
        try:
            nm = nmap.PortScanner()
            target = self.ip
            
            # تحويل نطاق IP إلى صيغة مناسبة لـ nmap
            if self.target_type == "range":
                start_ip, end_ip = self.ip.split("-")
                target = f"{start_ip}-{end_ip}"
            
            # تنفيذ الفحص
            nm.scan(hosts=target, arguments=f"-O --osscan-guess --max-os-tries 1 --host-timeout {self.timeout}s")
            
            # معالجة النتائج
            for host in nm.all_hosts():
                if "osmatch" in nm[host]:
                    os_matches = nm[host]["osmatch"]
                    os_info[host] = [{
                        "name": match["name"],
                        "accuracy": match["accuracy"],
                        "line": match.get("line", "")
                    } for match in os_matches]
                else:
                    os_info[host] = [{"error": "لم يتم التعرف على نظام التشغيل"}]
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"[!] خطأ في الكشف عن نظام التشغيل: {str(e)}")
            
            # استخدام طريقة بديلة باستخدام TTL
            if self.target_type in ["ip", "domain"]:
                try:
                    os_name = self._detect_os_by_ttl(self.ip)
                    os_info[self.ip] = [{
                        "name": os_name,
                        "accuracy": "50",
                        "method": "TTL"
                    }]
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"[!] خطأ في الكشف عن نظام التشغيل باستخدام TTL: {str(e)}")
                    os_info[self.ip] = [{"error": "فشل الكشف عن نظام التشغيل"}]
        
        return os_info
    
    def _detect_os_by_ttl(self, ip):
        """الكشف عن نظام التشغيل باستخدام قيمة TTL"""
        os_name = "Unknown"
        
        try:
            # استخدام ping للحصول على قيمة TTL
            if platform.system().lower() == "windows":
                ping_cmd = ["ping", "-n", "1", ip]
            else:
                ping_cmd = ["ping", "-c", "1", ip]
            
            output = subprocess.check_output(ping_cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            
            # استخراج قيمة TTL
            ttl_match = re.search(r"TTL=([0-9]+)", output, re.IGNORECASE)
            if ttl_match:
                ttl = int(ttl_match.group(1))
                
                # تحديد نظام التشغيل بناءً على قيمة TTL
                if ttl <= 64:
                    os_name = "Linux/Unix"
                elif ttl <= 128:
                    os_name = "Windows"
                elif ttl <= 255:
                    os_name = "Cisco/Network Device"
        
        except Exception:
            pass
        
        return os_name
    
    def _traceroute(self):
        """تتبع المسار إلى الهدف"""
        if self.logger:
            self.logger.info("[+] بدء تتبع المسار...")
        
        traceroute_info = []
        
        if self.target_type not in ["ip", "domain"]:
            return {"error": "تتبع المسار متاح فقط للأهداف من نوع IP أو نطاق"}
        
        try:
            # استخدام nmap لتتبع المسار
            nm = nmap.PortScanner()
            nm.scan(hosts=self.ip, arguments=f"--traceroute --max-retries 1 --host-timeout {self.timeout}s")
            
            # معالجة النتائج
            if self.ip in nm.all_hosts() and "trace" in nm[self.ip] and "hops" in nm[self.ip]["trace"]:
                hops = nm[self.ip]["trace"]["hops"]
                for hop in sorted(hops.keys()):
                    traceroute_info.append({
                        "hop": hop,
                        "ip": hops[hop]["ipaddr"],
                        "hostname": hops[hop].get("host", ""),
                        "rtt": hops[hop].get("rtt", "")
                    })
            else:
                # استخدام طريقة بديلة
                traceroute_info = self._traceroute_alternative()
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"[!] خطأ في تتبع المسار: {str(e)}")
            
            # استخدام طريقة بديلة
            traceroute_info = self._traceroute_alternative()
        
        return traceroute_info
    
    def _traceroute_alternative(self):
        """طريقة بديلة لتتبع المسار"""
        traceroute_info = []
        
        try:
            # تحديد الأمر المناسب حسب نظام التشغيل
            if platform.system().lower() == "windows":
                cmd = ["tracert", "-d", "-w", "500", self.ip]
            else:
                cmd = ["traceroute", "-n", "-w", "1", self.ip]
            
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            
            # تحليل النتائج
            lines = output.strip().split("\n")[1:]  # تجاهل السطر الأول
            
            for line in lines:
                if "*" in line and line.count("*") >= 3:
                    continue  # تجاهل الخطوات التي تجاوزت المهلة
                
                # استخراج معلومات الخطوة
                if platform.system().lower() == "windows":
                    match = re.search(r"\s*(\d+)\s+(?:\d+\s+ms\s+){1,3}\s*([\d\.]+)", line)
                else:
                    match = re.search(r"\s*(\d+)\s+([\d\.]+)\s+(?:\d+\.\d+\s+ms\s+){1,3}", line)
                
                if match:
                    hop = match.group(1)
                    ip = match.group(2)
                    
                    traceroute_info.append({
                        "hop": hop,
                        "ip": ip,
                        "hostname": "",
                        "rtt": ""
                    })
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"[!] خطأ في تتبع المسار البديل: {str(e)}")
        
        return traceroute_info