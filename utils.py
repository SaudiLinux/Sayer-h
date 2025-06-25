#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة الأدوات المساعدة لبرنامج Sayer
"""

import os
import sys
import logging
import platform
import subprocess
import pkg_resources
from colorama import init, Fore, Style
from datetime import datetime

# تهيئة colorama للألوان
init(autoreset=True)

# تعريف الألوان
COLORS = {
    "INFO": Fore.BLUE,
    "SUCCESS": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT,
    "RESET": Style.RESET_ALL
}


def banner():
    """عرض شعار البرنامج"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.GREEN + r"""
    ███████╗ █████╗ ██╗   ██╗███████╗██████╗ 
    ██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗
    ███████╗███████║ ╚████╔╝ █████╗  ██████╔╝
    ╚════██║██╔══██║  ╚██╔╝  ██╔══╝  ██╔══██╗
    ███████║██║  ██║   ██║   ███████╗██║  ██║
    ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    """ + Style.RESET_ALL)
    print(Fore.CYAN + "    أداة أمان سيبراني متكاملة | الإصدار 1.0.0" + Style.RESET_ALL)
    print(Fore.CYAN + "    تطوير: Saudi Linux (SaudiLinux1@gmail.com)" + Style.RESET_ALL)
    print("\n" + "="*60 + "\n")


def setup_logger(verbose=False):
    """إعداد المسجل للبرنامج"""
    logger = logging.getLogger("sayer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # إزالة المعالجات السابقة إن وجدت
    if logger.handlers:
        logger.handlers.clear()
    
    # معالج لعرض السجلات في وحدة التحكم
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # تنسيق السجلات
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # إضافة معالج وحدة التحكم
    logger.addHandler(console_handler)
    
    # إنشاء مجلد للسجلات إذا لم يكن موجودًا
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # معالج لحفظ السجلات في ملف
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"sayer_{timestamp}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # إضافة معالج الملف
    logger.addHandler(file_handler)
    
    return logger


def check_requirements():
    """التحقق من توفر المتطلبات"""
    print("[*] التحقق من المتطلبات...")
    
    # التحقق من إصدار Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print(f"{COLORS['ERROR']}[!] يجب استخدام Python 3.8 أو أحدث. الإصدار الحالي: {python_version.major}.{python_version.minor}.{python_version.micro}{COLORS['RESET']}")
        return False
    
    # التحقق من المكتبات المطلوبة
    requirements_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requirements.txt")
    
    if not os.path.exists(requirements_file):
        print(f"{COLORS['ERROR']}[!] ملف المتطلبات غير موجود: {requirements_file}{COLORS['RESET']}")
        return False
    
    # قراءة المتطلبات من الملف
    with open(requirements_file, 'r') as f:
        requirements = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # استخراج اسم المكتبة فقط (بدون رقم الإصدار)
                package_name = line.split('>=')[0].split('==')[0].strip()
                requirements.append(package_name)
    
    # التحقق من تثبيت المكتبات
    missing_packages = []
    for package in requirements:
        try:
            pkg_resources.get_distribution(package)
        except pkg_resources.DistributionNotFound:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"{COLORS['ERROR']}[!] المكتبات التالية غير مثبتة:{COLORS['RESET']}")
        for package in missing_packages:
            print(f"   - {package}")
        print(f"\n{COLORS['INFO']}[i] قم بتثبيت المكتبات المطلوبة باستخدام:{COLORS['RESET']}")
        print(f"    pip install -r {requirements_file}")
        return False
    
    # التحقق من توفر الأدوات الخارجية المطلوبة
    external_tools = {
        "nmap": "nmap --version",
    }
    
    missing_tools = []
    for tool, command in external_tools.items():
        try:
            subprocess.run(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"{COLORS['ERROR']}[!] الأدوات الخارجية التالية غير مثبتة:{COLORS['RESET']}")
        for tool in missing_tools:
            print(f"   - {tool}")
        
        # إرشادات التثبيت حسب نظام التشغيل
        os_name = platform.system().lower()
        if os_name == "linux":
            print(f"\n{COLORS['INFO']}[i] قم بتثبيت الأدوات المطلوبة باستخدام:{COLORS['RESET']}")
            print("    sudo apt-get update && sudo apt-get install nmap")
        elif os_name == "darwin":  # macOS
            print(f"\n{COLORS['INFO']}[i] قم بتثبيت الأدوات المطلوبة باستخدام:{COLORS['RESET']}")
            print("    brew install nmap")
        elif os_name == "windows":
            print(f"\n{COLORS['INFO']}[i] قم بتثبيت الأدوات المطلوبة من المواقع الرسمية:{COLORS['RESET']}")
            print("    Nmap: https://nmap.org/download.html")
        
        return False
    
    print(f"{COLORS['SUCCESS']}[✓] جميع المتطلبات متوفرة.{COLORS['RESET']}")
    return True


def is_valid_ip(ip):
    """التحقق من صحة عنوان IP"""
    import re
    pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(pattern, ip))


def is_valid_domain(domain):
    """التحقق من صحة اسم النطاق"""
    import re
    pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))


def is_valid_url(url):
    """التحقق من صحة عنوان URL"""
    import re
    pattern = r'^(https?:\/\/)?([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(\/[\w\-\.\/?\&=]*)?$'
    return bool(re.match(pattern, url))


def normalize_url(url):
    """تنسيق عنوان URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url


def get_random_user_agent():
    """الحصول على عميل مستخدم عشوائي"""
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
    except:
        # قائمة عملاء المستخدم الاحتياطية
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]
        import random
        return random.choice(user_agents)