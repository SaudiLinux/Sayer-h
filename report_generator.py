#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة إنشاء التقارير لبرنامج Sayer
"""

import os
import json
import datetime
import jinja2
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class ReportGenerator:
    """فئة إنشاء التقارير"""
    
    def __init__(self, target, scan_type, results, output_dir="reports"):
        """تهيئة الفئة"""
        self.target = target
        self.scan_type = scan_type
        self.results = results
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_dir = output_dir
        self.console = Console()
        
        # إنشاء مجلد التقارير إذا لم يكن موجودًا
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def generate_report(self, format_type="all"):
        """إنشاء التقرير بالتنسيق المطلوب"""
        report_files = {}
        
        if format_type == "all" or format_type == "console":
            self.generate_console_report()
        
        if format_type == "all" or format_type == "json":
            json_file = self.generate_json_report()
            report_files["json"] = json_file
        
        if format_type == "all" or format_type == "html":
            html_file = self.generate_html_report()
            report_files["html"] = html_file
            
        return report_files
    
    def generate_console_report(self):
        """إنشاء تقرير في واجهة سطر الأوامر"""
        self.console.print("\n")
        self.console.print(Panel.fit(f"[bold cyan]تقرير فحص Sayer للهدف: {self.target}[/bold cyan]", border_style="cyan"))
        self.console.print(f"[bold]نوع الفحص:[/bold] {self.scan_type}")
        self.console.print(f"[bold]تاريخ الفحص:[/bold] {self.timestamp.replace('_', ' ')}")
        self.console.print("\n")
        
        # عرض ملخص النتائج
        if "risk_assessment" in self.results:
            risk_level = self.results["risk_assessment"]["risk_level"]
            risk_color = self._get_risk_color(risk_level)
            
            self.console.print(Panel.fit(
                f"[bold]مستوى الخطورة الإجمالي:[/bold] [{risk_color}]{risk_level}[/{risk_color}]", 
                border_style=risk_color
            ))
            
            # عرض ملخص الثغرات
            summary = self.results["risk_assessment"]["summary"]
            summary_table = Table(title="ملخص الثغرات", show_header=True, header_style="bold")
            summary_table.add_column("مستوى الخطورة", style="bold")
            summary_table.add_column("العدد")
            
            summary_table.add_row("Critical", f"[red]{summary['critical']}[/red]")
            summary_table.add_row("High", f"[orange3]{summary['high']}[/orange3]")
            summary_table.add_row("Medium", f"[yellow]{summary['medium']}[/yellow]")
            summary_table.add_row("Low", f"[green]{summary['low']}[/green]")
            summary_table.add_row("Info", f"[blue]{summary['info']}[/blue]")
            
            self.console.print(summary_table)
            self.console.print("\n")
        
        # عرض معلومات الهدف
        if "target_info" in self.results:
            target_info = self.results["target_info"]
            self.console.print(Panel.fit("[bold]معلومات الهدف[/bold]", border_style="blue"))
            
            if "error" in target_info:
                self.console.print(f"[red]خطأ: {target_info['error']}[/red]")
            else:
                info_table = Table(show_header=False)
                info_table.add_column("الخاصية", style="bold")
                info_table.add_column("القيمة")
                
                for key, value in target_info.items():
                    if key not in ["forms", "technologies"]:
                        info_table.add_row(key, str(value))
                
                self.console.print(info_table)
                
                # عرض التقنيات المكتشفة
                if "technologies" in target_info and target_info["technologies"]:
                    self.console.print("\n[bold]التقنيات المكتشفة:[/bold]")
                    for tech in target_info["technologies"]:
                        self.console.print(f"  • {tech}")
            
            self.console.print("\n")
        
        # عرض نتائج الفحص المفصلة
        for key, value in self.results.items():
            if key not in ["risk_assessment", "target_info"] and isinstance(value, dict) and "vulnerabilities" in value:
                vuln_name = value.get("name", key)
                severity = value.get("severity", "Info")
                status = value.get("status", "Unknown")
                description = value.get("description", "")
                vulnerabilities = value.get("vulnerabilities", [])
                
                # تحديد لون مستوى الخطورة
                severity_color = self._get_risk_color(severity)
                status_color = "green" if status == "Not Vulnerable" else ("red" if status == "Vulnerable" else "yellow")
                
                # عنوان القسم
                self.console.print(Panel.fit(
                    f"[bold]{vuln_name}[/bold] - [{severity_color}]{severity}[/{severity_color}] - [{status_color}]{status}[/{status_color}]", 
                    border_style=severity_color
                ))
                
                if description:
                    self.console.print(f"[bold]الوصف:[/bold] {description}")
                
                # عرض الثغرات المكتشفة
                if vulnerabilities:
                    self.console.print("\n[bold]الثغرات المكتشفة:[/bold]")
                    
                    for i, vuln in enumerate(vulnerabilities, 1):
                        vuln_panel = Panel.fit(
                            self._format_vulnerability(vuln),
                            title=f"[bold]ثغرة #{i}[/bold]",
                            border_style=severity_color
                        )
                        self.console.print(vuln_panel)
                else:
                    self.console.print("\n[green]لم يتم اكتشاف ثغرات.[/green]")
                
                self.console.print("\n")
        
        # عرض معلومات إضافية عن التقرير
        self.console.print(Panel.fit(
            "[bold]تم إنشاء هذا التقرير بواسطة أداة Sayer[/bold]\n" +
            "المطور: Saudi Linux\n" +
            "البريد الإلكتروني: SaudiLinux1@gmail.com",
            border_style="cyan"
        ))
        
        self.console.print(f"\n[bold green]تم حفظ التقرير بتنسيق JSON في:[/bold green] {self._get_output_filename('json')}")
        self.console.print(f"[bold green]تم حفظ التقرير بتنسيق HTML في:[/bold green] {self._get_output_filename('html')}")
    
    def generate_json_report(self):
        """إنشاء تقرير بتنسيق JSON"""
        report_data = {
            "target": self.target,
            "scan_type": self.scan_type,
            "timestamp": self.timestamp,
            "results": self.results
        }
        
        output_file = self._get_output_filename("json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
        
        return output_file
    
    def generate_html_report(self):
        """إنشاء تقرير بتنسيق HTML"""
        # قالب HTML
        template_str = '''
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>تقرير فحص Sayer - {{ target }}</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    direction: rtl;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: #fff;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    border-radius: 5px;
                }
                h1, h2, h3 {
                    color: #2c3e50;
                }
                .header {
                    background-color: #3498db;
                    color: white;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                    text-align: center;
                }
                .section {
                    margin-bottom: 30px;
                    padding: 15px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
                    border-right: 5px solid #3498db;
                }
                .vulnerability {
                    margin-bottom: 15px;
                    padding: 15px;
                    background-color: #fff;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: right;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #f2f2f2;
                    font-weight: bold;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                .risk-critical {
                    color: #e74c3c;
                    border-color: #e74c3c;
                }
                .risk-high {
                    color: #e67e22;
                    border-color: #e67e22;
                }
                .risk-medium {
                    color: #f39c12;
                    border-color: #f39c12;
                }
                .risk-low {
                    color: #27ae60;
                    border-color: #27ae60;
                }
                .risk-info {
                    color: #3498db;
                    border-color: #3498db;
                }
                .status-vulnerable {
                    color: #e74c3c;
                }
                .status-not-vulnerable {
                    color: #27ae60;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #7f8c8d;
                }
                .summary-box {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }
                .summary-item {
                    flex: 1;
                    text-align: center;
                    padding: 15px;
                    margin: 0 5px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }
                .summary-item h3 {
                    margin-top: 0;
                }
                .bg-critical { background-color: rgba(231, 76, 60, 0.1); }
                .bg-high { background-color: rgba(230, 126, 34, 0.1); }
                .bg-medium { background-color: rgba(243, 156, 18, 0.1); }
                .bg-low { background-color: rgba(39, 174, 96, 0.1); }
                .bg-info { background-color: rgba(52, 152, 219, 0.1); }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>تقرير فحص Sayer</h1>
                    <p>الهدف: {{ target }}</p>
                    <p>نوع الفحص: {{ scan_type }}</p>
                    <p>تاريخ الفحص: {{ timestamp }}</p>
                </div>
                
                {% if results.risk_assessment %}
                <div class="section">
                    <h2>تقييم المخاطر</h2>
                    <p><strong>مستوى الخطورة الإجمالي: </strong>
                        <span class="risk-{{ results.risk_assessment.risk_level|lower }}">{{ results.risk_assessment.risk_level }}</span>
                    </p>
                    
                    <div class="summary-box">
                        <div class="summary-item bg-critical">
                            <h3 class="risk-critical">Critical</h3>
                            <p>{{ results.risk_assessment.summary.critical }}</p>
                        </div>
                        <div class="summary-item bg-high">
                            <h3 class="risk-high">High</h3>
                            <p>{{ results.risk_assessment.summary.high }}</p>
                        </div>
                        <div class="summary-item bg-medium">
                            <h3 class="risk-medium">Medium</h3>
                            <p>{{ results.risk_assessment.summary.medium }}</p>
                        </div>
                        <div class="summary-item bg-low">
                            <h3 class="risk-low">Low</h3>
                            <p>{{ results.risk_assessment.summary.low }}</p>
                        </div>
                        <div class="summary-item bg-info">
                            <h3 class="risk-info">Info</h3>
                            <p>{{ results.risk_assessment.summary.info }}</p>
                        </div>
                    </div>
                    
                    {% if results.risk_assessment.vulnerable_components %}
                    <h3>المكونات المعرضة للخطر</h3>
                    <table>
                        <tr>
                            <th>المكون</th>
                            <th>مستوى الخطورة</th>
                            <th>عدد الثغرات</th>
                        </tr>
                        {% for component in results.risk_assessment.vulnerable_components %}
                        <tr>
                            <td>{{ component.name }}</td>
                            <td class="risk-{{ component.severity|lower }}">{{ component.severity }}</td>
                            <td>{{ component.count }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                    {% endif %}
                </div>
                {% endif %}
                
                {% if results.target_info %}
                <div class="section">
                    <h2>معلومات الهدف</h2>
                    {% if results.target_info.error %}
                    <p class="status-vulnerable">خطأ: {{ results.target_info.error }}</p>
                    {% else %}
                    <table>
                        {% for key, value in results.target_info.items() %}
                            {% if key not in ['forms', 'technologies'] %}
                            <tr>
                                <th>{{ key }}</th>
                                <td>{{ value }}</td>
                            </tr>
                            {% endif %}
                        {% endfor %}
                    </table>
                    
                    {% if results.target_info.technologies %}
                    <h3>التقنيات المكتشفة</h3>
                    <ul>
                        {% for tech in results.target_info.technologies %}
                        <li>{{ tech }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                    {% endif %}
                </div>
                {% endif %}
                
                {% for key, value in results.items() %}
                    {% if key not in ['risk_assessment', 'target_info'] and value.vulnerabilities is defined %}
                    <div class="section" style="border-right-color: {{ get_color(value.severity) }}">
                        <h2>{{ value.name|default(key) }}</h2>
                        <p>
                            <strong>مستوى الخطورة: </strong>
                            <span class="risk-{{ value.severity|lower }}">{{ value.severity }}</span>
                        </p>
                        <p>
                            <strong>الحالة: </strong>
                            <span class="status-{{ value.status|lower|replace(' ', '-') }}">{{ value.status }}</span>
                        </p>
                        {% if value.description %}
                        <p><strong>الوصف: </strong>{{ value.description }}</p>
                        {% endif %}
                        
                        {% if value.vulnerabilities %}
                        <h3>الثغرات المكتشفة</h3>
                        {% for vuln in value.vulnerabilities %}
                        <div class="vulnerability">
                            <h4>ثغرة #{{ loop.index }}</h4>
                            <table>
                                {% for k, v in vuln.items() %}
                                <tr>
                                    <th>{{ k }}</th>
                                    <td>{{ v }}</td>
                                </tr>
                                {% endfor %}
                            </table>
                        </div>
                        {% endfor %}
                        {% else %}
                        <p class="status-not-vulnerable">لم يتم اكتشاف ثغرات.</p>
                        {% endif %}
                    </div>
                    {% endif %}
                {% endfor %}
                
                <div class="footer">
                    <p>تم إنشاء هذا التقرير بواسطة أداة Sayer</p>
                    <p>المطور: Saudi Linux</p>
                    <p>البريد الإلكتروني: SaudiLinux1@gmail.com</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # إنشاء محرك قوالب Jinja2
        template = jinja2.Template(template_str)
        
        # تحديد دالة للحصول على لون مستوى الخطورة
        def get_color(severity):
            severity = severity.lower()
            if severity == "critical":
                return "#e74c3c"
            elif severity == "high":
                return "#e67e22"
            elif severity == "medium":
                return "#f39c12"
            elif severity == "low":
                return "#27ae60"
            else:  # info
                return "#3498db"
        
        # إنشاء HTML
        html_content = template.render(
            target=self.target,
            scan_type=self.scan_type,
            timestamp=self.timestamp.replace("_", " "),
            results=self.results,
            get_color=get_color
        )
        
        # حفظ الملف
        output_file = self._get_output_filename("html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return output_file
    
    def _get_output_filename(self, extension):
        """الحصول على اسم ملف المخرجات"""
        target_name = self.target.replace("http://", "").replace("https://", "").replace("/", "_")
        return os.path.join(self.output_dir, f"sayer_{target_name}_{self.scan_type}_{self.timestamp}.{extension}")
    
    def _get_risk_color(self, risk_level):
        """الحصول على لون مستوى الخطورة"""
        risk_level = risk_level.lower()
        if risk_level == "critical":
            return "red"
        elif risk_level == "high":
            return "orange3"
        elif risk_level == "medium":
            return "yellow"
        elif risk_level == "low":
            return "green"
        else:  # info
            return "blue"
    
    def _format_vulnerability(self, vuln):
        """تنسيق معلومات الثغرة للعرض في واجهة سطر الأوامر"""
        text = Text()
        
        for key, value in vuln.items():
            if isinstance(value, dict):
                text.append(f"[bold]{key}:[/bold]\n")
                for k, v in value.items():
                    text.append(f"  [bold]{k}:[/bold] {v}\n")
            else:
                text.append(f"[bold]{key}:[/bold] {value}\n")
        
        return text