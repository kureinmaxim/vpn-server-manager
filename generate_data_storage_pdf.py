#!/usr/bin/env python3
"""
Генератор PDF документации по хранению данных VPN Server Manager
"""

import os
import sys
from pathlib import Path

# Добавляем путь к проекту для импорта модулей
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, darkblue, darkgreen, darkred
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("❌ Ошибка: Необходимо установить reportlab")
    print("Установка: pip install reportlab")
    sys.exit(1)

def create_data_storage_pdf():
    """Создает PDF документацию по хранению данных"""
    
    # Создаем PDF файл
    pdf_path = project_root / "docs" / "DATA_STORAGE_GUIDE.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Стили
    styles = getSampleStyleSheet()
    
    # Кастомные стили
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#2c3e50')
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        spaceBefore=20,
        textColor=HexColor('#34495e')
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=12,
        textColor=HexColor('#7f8c8d')
    )
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Code'],
        fontSize=9,
        fontName='Courier',
        leftIndent=20,
        rightIndent=20,
        spaceAfter=6,
        spaceBefore=6,
        backgroundColor=HexColor('#f8f9fa'),
        borderColor=HexColor('#dee2e6'),
        borderWidth=1,
        borderPadding=8
    )
    
    warning_style = ParagraphStyle(
        'WarningStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#e74c3c'),
        leftIndent=20,
        spaceAfter=6,
        spaceBefore=6
    )
    
    # Содержимое документа
    story = []
    
    # Заголовок
    story.append(Paragraph("📁 Руководство по хранению данных", title_style))
    story.append(Paragraph("VPN Server Manager v3.5.4", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Обзор
    story.append(Paragraph("🎯 Обзор", heading1_style))
    story.append(Paragraph(
        "VPN Server Manager использует <b>зашифрованное хранение данных</b> для обеспечения "
        "безопасности информации о серверах, паролях и настройках. Все данные защищены "
        "криптографическим шифрованием и хранятся в специальных директориях в зависимости "
        "от операционной системы.",
        styles['Normal']
    ))
    story.append(Spacer(1, 12))
    
    # Структура хранения данных
    story.append(Paragraph("🏠 Структура хранения данных", heading1_style))
    
    # В режиме разработки
    story.append(Paragraph("📂 В режиме разработки (текущий проект)", heading2_style))
    
    dev_structure = """
/Users/olgazaharova/Project/ProjectPython/VPNserverManage/
├── data/                          # 📊 Локальные данные разработки
│   ├── servers.json.enc          # 🔐 Основной файл с серверами (зашифрован)
│   ├── hints.json                # 📝 Шпаргалка команд
│   └── merged_*.enc              # 📦 Временные файлы импорта
├── uploads/                       # 📎 Пользовательские файлы
│   ├── icon_*.png                # 🖼️ Иконки серверов
│   └── *_Invoice-*.pdf           # 📄 Чеки об оплате
├── config.json                   # ⚙️ Настройки приложения
├── .env                          # 🔑 Секретный ключ шифрования
└── memory-bank/                  # 🧠 Система управления задачами
    ├── tasks.md
    ├── activeContext.md
    └── archive/
    """
    
    story.append(Paragraph(dev_structure, code_style))
    story.append(Spacer(1, 12))
    
    # В установленном приложении
    story.append(Paragraph("📂 В установленном приложении", heading2_style))
    
    # Таблица с путями для разных ОС
    os_data = [
        ['ОС', 'Путь к данным'],
        ['macOS', '~/Library/Application Support/VPNServerManager/'],
        ['Windows', '%APPDATA%\\VPNServerManager\\'],
        ['Linux', '~/.local/share/VPNServerManager/']
    ]
    
    os_table = Table(os_data, colWidths=[1.5*inch, 4*inch])
    os_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(os_table)
    story.append(Spacer(1, 20))
    
    # Критически важные файлы
    story.append(Paragraph("🔐 Критически важные файлы", heading1_style))
    
    # servers.json.enc
    story.append(Paragraph("1. servers.json.enc - Главная база данных", heading2_style))
    story.append(Paragraph(
        "<b>Назначение:</b> Содержит всю информацию о серверах в зашифрованном виде<br/>"
        "<b>Содержимое:</b> IP-адреса, логины, пароли, настройки, заметки<br/>"
        "<b>Безопасность:</b> Зашифрован алгоритмом Fernet (AES 128)<br/>"
        "<b>Ключ:</b> Хранится в .env файле как SECRET_KEY",
        styles['Normal']
    ))
    story.append(Spacer(1, 8))
    
    # .env
    story.append(Paragraph("2. .env - Секретный ключ шифрования", heading2_style))
    story.append(Paragraph(
        "<b>Назначение:</b> Содержит ключ для расшифровки данных<br/>"
        "<b>Содержимое:</b> SECRET_KEY=gAAAAABh...32-байтовый_base64_ключ<br/>"
        "<b>Критичность:</b> КРИТИЧЕСКИ ВАЖЕН - без этого файла данные НЕ расшифруются",
        styles['Normal']
    ))
    story.append(Spacer(1, 8))
    
    # config.json
    story.append(Paragraph("3. config.json - Настройки приложения", heading2_style))
    story.append(Paragraph(
        "<b>Назначение:</b> Содержит конфигурацию приложения<br/>"
        "<b>Содержимое:</b> Версия, URL сервисов, активный файл данных",
        styles['Normal']
    ))
    story.append(Spacer(1, 8))
    
    # hints.json
    story.append(Paragraph("4. hints.json - Шпаргалка команд", heading2_style))
    story.append(Paragraph(
        "<b>Назначение:</b> Содержит команды для быстрого доступа<br/>"
        "<b>Содержимое:</b> JSON массив с командами",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))
    
    # Структура данных серверов
    story.append(Paragraph("📊 Структура данных серверов", heading1_style))
    
    # Таблица полей данных
    fields_data = [
        ['Поле', 'Тип', 'Описание', 'Шифрование'],
        ['id', 'String', 'Уникальный идентификатор', '❌'],
        ['name', 'String', 'Название сервера', '❌'],
        ['ip_address', 'String', 'IP-адрес сервера', '❌'],
        ['username', 'String', 'SSH пользователь', '❌'],
        ['password', 'String', 'SSH пароль', '✅'],
        ['hoster_credentials.user', 'String', 'Пользователь панели хостера', '✅'],
        ['hoster_credentials.password', 'String', 'Пароль панели хостера', '✅'],
        ['docker_info', 'String', 'Информация о Docker', '❌'],
        ['software_info', 'String', 'Установленное ПО', '❌'],
        ['notes', 'String', 'Заметки пользователя', '❌']
    ]
    
    fields_table = Table(fields_data, colWidths=[1.2*inch, 0.8*inch, 2*inch, 0.8*inch])
    fields_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    story.append(fields_table)
    story.append(Spacer(1, 20))
    
    # Безопасность данных
    story.append(Paragraph("🛡️ Безопасность данных", heading1_style))
    
    story.append(Paragraph(
        "<b>Алгоритм шифрования:</b> Fernet (AES 128 в режиме CBC)<br/>"
        "<b>Ключ:</b> 32-байтовый base64-кодированный ключ<br/>"
        "<b>Аутентификация:</b> HMAC-SHA256<br/>"
        "<b>Случайность:</b> Использует криптографически стойкий генератор",
        styles['Normal']
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Уровни защиты:", heading2_style))
    story.append(Paragraph("1. <b>Файловое шифрование:</b> Весь файл servers.json.enc зашифрован", styles['Normal']))
    story.append(Paragraph("2. <b>Полевое шифрование:</b> Пароли зашифрованы дополнительно", styles['Normal']))
    story.append(Paragraph("3. <b>Двойное шифрование:</b> Пароли хостера шифруются отдельно", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Утилиты для работы с данными
    story.append(Paragraph("🔧 Утилиты для работы с данными", heading1_style))
    
    story.append(Paragraph("1. decrypt_tool.py - Просмотр данных", heading2_style))
    story.append(Paragraph(
        "<b>Назначение:</b> Просмотр расшифрованных данных без запуска GUI<br/>"
        "<b>Использование:</b> python3 decrypt_tool.py",
        styles['Normal']
    ))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("2. generate_key.py - Создание нового ключа", heading2_style))
    story.append(Paragraph(
        "<b>Назначение:</b> Генерация нового SECRET_KEY<br/>"
        "<b>Использование:</b> python3 generate_key.py",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))
    
    # Важные моменты
    story.append(Paragraph("⚠️ Важные моменты и рекомендации", heading1_style))
    
    story.append(Paragraph("Резервное копирование:", heading2_style))
    story.append(Paragraph(
        "<b>Критически важные файлы для резервирования:</b><br/>"
        "1. servers.json.enc - основная база данных<br/>"
        "2. .env - ключ шифрования<br/>"
        "3. config.json - настройки приложения<br/>"
        "4. uploads/ - пользовательские файлы",
        styles['Normal']
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Безопасность:", heading2_style))
    story.append(Paragraph("Никогда не делайте:", warning_style))
    story.append(Paragraph("• Не делитесь файлом .env", styles['Normal']))
    story.append(Paragraph("• Не загружайте .env в Git", styles['Normal']))
    story.append(Paragraph("• Не передавайте ключи по незащищенным каналам", styles['Normal']))
    story.append(Paragraph("• Не храните незашифрованные пароли", styles['Normal']))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("Всегда делайте:", styles['Normal']))
    story.append(Paragraph("• Регулярные резервные копии", styles['Normal']))
    story.append(Paragraph("• Проверку целостности данных", styles['Normal']))
    story.append(Paragraph("• Обновления приложения", styles['Normal']))
    story.append(Paragraph("• Безопасное хранение ключей", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Заключение
    story.append(Paragraph("🎯 Заключение", heading1_style))
    story.append(Paragraph(
        "VPN Server Manager использует <b>многоуровневую систему защиты данных</b> с зашифрованным "
        "хранением, автоматическим управлением ключами и безопасным импортом/экспортом. "
        "Все данные защищены криптографическим шифрованием и хранятся в специальных "
        "директориях операционной системы.",
        styles['Normal']
    ))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Ключевые принципы:", heading2_style))
    story.append(Paragraph("🔐 <b>Безопасность</b> - все пароли зашифрованы", styles['Normal']))
    story.append(Paragraph("🏠 <b>Портативность</b> - данные легко переносятся", styles['Normal']))
    story.append(Paragraph("🔄 <b>Совместимость</b> - поддержка импорта/экспорта", styles['Normal']))
    story.append(Paragraph("🛡️ <b>Надежность</b> - резервное копирование и восстановление", styles['Normal']))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph(
        "Следуйте рекомендациям по безопасности и регулярно делайте резервные копии "
        "для обеспечения сохранности ваших данных! 🚀",
        styles['Normal']
    ))
    
    # Создаем PDF
    doc.build(story)
    print(f"✅ PDF документация создана: {pdf_path}")
    
    return pdf_path

if __name__ == "__main__":
    try:
        pdf_path = create_data_storage_pdf()
        print(f"📄 Документация по хранению данных создана:")
        print(f"   MD: docs/DATA_STORAGE_GUIDE.md")
        print(f"   PDF: {pdf_path}")
    except Exception as e:
        print(f"❌ Ошибка при создании PDF: {e}")
        sys.exit(1)
