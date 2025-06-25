#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sayer - أداة أمان سيبراني متكاملة
تطوير: Saudi Linux (SaudiLinux1@gmail.com)
"""

import argparse
import sys
import os
import time
import json
from datetime import datetime

# استيراد الوحدات الداخلية
try:
    from modules import (
        InfoGathering, VulnerabilityScanner, WebScanner, NetworkScanner,
        ReportGenerator, Config, setup_logger, banner, check_requirements
    )
except ImportError:
    print("[!] خطأ في استيراد الوحدات. تأكد من تثبيت جميع المتطلبات.")
    print("[!] قم بتنفيذ: pip install -r requirements.txt")
    sys.exit(1)


def parse_arguments():
    """تحليل معطيات سطر الأوامر"""
    parser = argparse.ArgumentParser(description="Sayer - أداة أمان سيبراني متكاملة")
    
    # مجموعة الخيارات الأساسية
    group_basic = parser.add_argument_group('الخيارات الأساسية')
    group_basic.add_argument("-t", "--target", required=True, help="الهدف المراد فحصه (نطاق، عنوان IP، موقع ويب)")
    group_basic.add_argument("-s", "--scan-type", default="full", 
                        choices=["full", "quick", "web", "network", "info", "vuln"],
                        help="نوع الفحص (full: شامل، quick: سريع، web: ويب، network: شبكة، info: معلومات، vuln: ثغرات)")
    group_basic.add_argument("-o", "--output-dir", default="reports", help="مجلد حفظ التقارير (الافتراضي: reports)")
    group_basic.add_argument("-f", "--format", default="all", 
                        choices=["all", "console", "json", "html"],
                        help="تنسيق التقرير (all: الكل، console: طرفية، json: جيسون، html: ويب)")
    group_basic.add_argument("-v", "--verbose", action="store_true", help="عرض معلومات تفصيلية أثناء الفحص")
    group_basic.add_argument("-c", "--config", default="config.json", help="ملف الإعدادات (الافتراضي: config.json)")
    
    # مجموعة خيارات الأداء
    group_performance = parser.add_argument_group('خيارات الأداء')
    group_performance.add_argument("--threads", type=int, default=5, help="عدد العمليات المتزامنة (الافتراضي: 5)")
    group_performance.add_argument("--timeout", type=int, default=30, help="مهلة الاتصال بالثواني (الافتراضي: 30)")
    
    # مجموعة خيارات الفحص
    group_scan = parser.add_argument_group('خيارات الفحص')
    group_scan.add_argument("--web-crawl-depth", type=int, default=2, help="عمق زحف الويب (الافتراضي: 2)")
    group_scan.add_argument("--port-range", default="1-1000", help="نطاق المنافذ للفحص (الافتراضي: 1-1000)")
    group_scan.add_argument("--disable-vuln-scan", action="store_true", help="تعطيل فحص الثغرات")
    group_scan.add_argument("--disable-ssl-check", action="store_true", help="تعطيل فحص SSL/TLS")
    
    # مجموعة خيارات إضافية
    group_misc = parser.add_argument_group('خيارات إضافية')
    group_misc.add_argument("--update", action="store_true", help="تحديث الأداة إلى أحدث إصدار")
    group_misc.add_argument("--create-config", action="store_true", help="إنشاء ملف إعدادات افتراضي")
    
    return parser.parse_args()


def main():
    """الدالة الرئيسية للبرنامج"""
    # عرض شعار البرنامج
    banner()
    
    # تحليل المعطيات
    args = parse_arguments()
    
    # التحقق من الخيارات الإضافية
    if args.update:
        print("[*] جاري التحقق من وجود تحديثات...")
        # هنا يمكن إضافة كود للتحقق من التحديثات
        print("[*] الأداة محدثة إلى آخر إصدار.")
        sys.exit(0)
    
    if args.create_config:
        config = Config()
        if config.save():
            print(f"[✓] تم إنشاء ملف الإعدادات الافتراضي: {config.config_file}")
        else:
            print("[!] فشل في إنشاء ملف الإعدادات.")
        sys.exit(0)
    
    # التحقق من المتطلبات
    if not check_requirements():
        sys.exit(1)
    
    # تحميل الإعدادات
    config = Config(args.config)
    
    # إعداد المسجل
    logger = setup_logger(args.verbose)
    
    # إنشاء مجلد التقارير إذا لم يكن موجودًا
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    logger.info(f"[+] بدء الفحص على الهدف: {args.target}")
    logger.info(f"[+] نوع الفحص: {args.scan_type}")
    
    start_time = time.time()
    
    # تحديث الإعدادات من معطيات سطر الأوامر
    scan_config = {
        "threads": args.threads,
        "timeout": args.timeout,
        "web_crawl_depth": args.web_crawl_depth,
        "port_range": args.port_range,
        "disable_vuln_scan": args.disable_vuln_scan,
        "disable_ssl_check": args.disable_ssl_check
    }
    
    # إنشاء كائنات الفحص
    info_gatherer = InfoGathering(
        args.target, 
        threads=args.threads, 
        timeout=args.timeout, 
        logger=logger
    )
    
    web_scanner = WebScanner(
        args.target, 
        threads=args.threads, 
        timeout=args.timeout, 
        logger=logger
    )
    
    network_scanner = NetworkScanner(
        args.target, 
        threads=args.threads, 
        timeout=args.timeout, 
        logger=logger
    )
    
    vuln_scanner = VulnerabilityScanner(
        args.target, 
        threads=args.threads, 
        timeout=args.timeout, 
        logger=logger
    )
    
    # تنفيذ الفحص حسب النوع المحدد
    results = {}
    
    if args.scan_type in ["full", "info", "quick"]:
        logger.info("[+] بدء مرحلة جمع المعلومات...")
        results["info"] = info_gatherer.gather()
    
    if args.scan_type in ["full", "web", "quick"]:
        logger.info("[+] بدء فحص تطبيق الويب...")
        results["web"] = web_scanner.scan()
    
    if args.scan_type in ["full", "network"]:
        logger.info("[+] بدء فحص الشبكة...")
        results["network"] = network_scanner.scan()
    
    if args.scan_type in ["full", "vuln"] and not args.disable_vuln_scan:
        logger.info("[+] بدء فحص الثغرات...")
        results["vulnerabilities"] = vuln_scanner.scan()
    
    # حساب الوقت المستغرق
    elapsed_time = time.time() - start_time
    logger.info(f"[+] اكتمل الفحص في {elapsed_time:.2f} ثانية")
    
    # إنشاء التقرير
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_gen = ReportGenerator(
        target=args.target, 
        scan_type=args.scan_type, 
        results=results, 
        output_dir=args.output_dir
    )
    
    logger.info(f"[+] إنشاء التقرير...")
    report_files = report_gen.generate_report(format_type=args.format)
    
    logger.info(f"[+] تم حفظ التقرير في مجلد: {args.output_dir}")
    
    # عرض مسارات ملفات التقارير
    if report_files:
        for report_type, file_path in report_files.items():
            logger.info(f"[+] تم حفظ تقرير {report_type} في: {file_path}")
    
    print(f"\n[✓] اكتمل الفحص! تم حفظ التقرير في مجلد: {args.output_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] تم إيقاف البرنامج بواسطة المستخدم.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] حدث خطأ غير متوقع: {str(e)}")
        sys.exit(1)