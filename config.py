#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة الإعدادات لبرنامج Sayer
"""

import os
import json
import logging

# إعدادات افتراضية
DEFAULT_CONFIG = {
    "general": {
        "threads": 5,
        "timeout": 30,
        "user_agent": "Sayer Security Scanner",
        "log_level": "INFO"
    },
    "info_gathering": {
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "whois_timeout": 10,
        "ssl_check": True
    },
    "web_scanner": {
        "crawl_depth": 2,
        "max_urls": 100,
        "exclude_extensions": [".jpg", ".jpeg", ".png", ".gif", ".css", ".js"],
        "exclude_urls": ["logout", "signout", "exit"],
        "respect_robots": True
    },
    "network_scanner": {
        "port_scan_type": "SYN",
        "port_range": "1-1000",
        "service_detection": True,
        "os_detection": True
    },
    "vulnerability_scanner": {
        "xss_scan": True,
        "sqli_scan": True,
        "lfi_scan": True,
        "rfi_scan": True,
        "open_redirect_scan": True,
        "csrf_scan": True,
        "clickjacking_scan": True,
        "cors_scan": True,
        "ssl_tls_scan": True,
        "cve_scan": True
    },
    "report": {
        "output_dir": "reports",
        "formats": ["console", "json", "html"]
    }
}


class Config:
    """فئة إدارة الإعدادات"""
    
    def __init__(self, config_file="config.json"):
        """تهيئة الفئة"""
        self.config_file = config_file
        self.config = DEFAULT_CONFIG.copy()
        
        # تحميل الإعدادات من الملف إذا كان موجودًا
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    self._merge_config(user_config)
            except Exception as e:
                logging.warning(f"خطأ في تحميل ملف الإعدادات: {str(e)}")
    
    def _merge_config(self, user_config):
        """دمج الإعدادات المخصصة مع الإعدادات الافتراضية"""
        for section, options in user_config.items():
            if section in self.config:
                if isinstance(options, dict):
                    self.config[section].update(options)
                else:
                    self.config[section] = options
            else:
                self.config[section] = options
    
    def get(self, section, option=None, default=None):
        """الحصول على قيمة الإعداد"""
        if section not in self.config:
            return default
        
        if option is None:
            return self.config[section]
        
        return self.config[section].get(option, default)
    
    def set(self, section, option, value):
        """تعيين قيمة الإعداد"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][option] = value
    
    def save(self):
        """حفظ الإعدادات في ملف"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"خطأ في حفظ ملف الإعدادات: {str(e)}")
            return False
    
    def reset_to_default(self):
        """إعادة تعيين الإعدادات إلى القيم الافتراضية"""
        self.config = DEFAULT_CONFIG.copy()
        return self.save()
    
    def get_all(self):
        """الحصول على جميع الإعدادات"""
        return self.config.copy()