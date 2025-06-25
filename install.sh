#!/bin/bash

echo "Sayer Tool Installer"
echo "================="

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "[!] Python3 غير مثبت. الرجاء تثبيت Python3 أولاً."
    exit 1
fi

# التحقق من وجود pip
if ! command -v pip3 &> /dev/null; then
    echo "[!] pip3 غير مثبت. الرجاء تثبيت pip3 أولاً."
    exit 1
fi

# تثبيت المتطلبات
echo "[*] جاري تثبيت المتطلبات..."
pip3 install -r requirements.txt

# التحقق من وجود nmap
if ! command -v nmap &> /dev/null; then
    echo "[!] nmap غير مثبت. جاري محاولة التثبيت..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y nmap
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y nmap
    elif command -v yum &> /dev/null; then
        sudo yum install -y nmap
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm nmap
    else
        echo "[!] لم نتمكن من تثبيت nmap تلقائياً. الرجاء تثبيته يدوياً."
    fi
fi

# جعل ملفات التشغيل قابلة للتنفيذ
chmod +x run.sh

echo "[✓] تم تثبيت Sayer بنجاح!"
echo "[*] لتشغيل الأداة، استخدم: ./run.sh"