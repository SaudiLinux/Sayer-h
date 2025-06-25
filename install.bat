@echo off
echo Sayer Tool Installer
echo =================

:: التحقق من وجود Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python غير مثبت. الرجاء تثبيت Python أولاً.
    echo [!] يمكنك تحميله من https://www.python.org/downloads/
    pause
    exit /b 1
)

:: التحقق من وجود pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] pip غير مثبت. الرجاء تثبيت pip أولاً.
    pause
    exit /b 1
)

:: تثبيت المتطلبات
echo [*] جاري تثبيت المتطلبات...
pip install -r requirements.txt

:: التحقق من وجود nmap
nmap --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] nmap غير مثبت. الرجاء تثبيت nmap يدوياً.
    echo [!] يمكنك تحميله من https://nmap.org/download.html
)

echo [✓] تم تثبيت Sayer بنجاح!
echo [*] لتشغيل الأداة، استخدم: run.bat

pause