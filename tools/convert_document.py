import os
import sys
import pypandoc
import logging
import io
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET

"""
Здесь хранятся функции для конвертации Markdown в DOCX и PDF с сохранением подсветки кода.
Для корректной работы требуется установленный системный пакет 'pandoc'.
Для конвертации в PDF также требуется установленный движок рендеринга (например, typst).
Чтобы использовать этот скрипт, убедитесь, что у вас установлены все необходимые зависимости.

Чтобы конвертировать Markdown в DOCX используйте функцию convert_to_docx(input_file, output_file).
Чтобы конвертировать Markdown в PDF используйте функцию convert_to_pdf(input_file, output_file).

"""

def _read_markdown(input_file: str) -> str:
    with open(input_file, encoding="utf-8") as markdown_file:
        markdown = markdown_file.read()
    return re.sub(r"(^```\s*)kv(\s*$)", r"\1yaml\2", markdown, flags=re.MULTILINE)


def _enable_docx_code_wrapping(output_file: str) -> None:
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    namespace_map = {"w": namespace}
    temporary_file = None

    try:
        with zipfile.ZipFile(output_file) as source_docx:
            styles_xml = source_docx.read("word/styles.xml")
            for _, (prefix, uri) in ET.iterparse(
                io.BytesIO(styles_xml), events=("start-ns",)
            ):
                ET.register_namespace(prefix or "", uri)

            styles = ET.fromstring(styles_xml)
            source_code_style = styles.find(
                ".//w:style[@w:styleId='SourceCode']", namespace_map
            )
            if source_code_style is not None:
                word_wrap = source_code_style.find("w:pPr/w:wordWrap", namespace_map)
                if word_wrap is not None:
                    source_code_style.find("w:pPr", namespace_map).remove(word_wrap)
                updated_styles = ET.tostring(styles, encoding="utf-8", xml_declaration=True)

                with tempfile.NamedTemporaryFile(
                    suffix=".docx", dir=os.path.dirname(output_file) or ".", delete=False
                ) as temporary:
                    temporary_file = temporary.name

                with zipfile.ZipFile(temporary_file, "w") as updated_docx:
                    for item in source_docx.infolist():
                        content = updated_styles if item.filename == "word/styles.xml" else source_docx.read(item.filename)
                        updated_docx.writestr(item, content)

        if temporary_file:
            os.replace(temporary_file, output_file)
    finally:
        if temporary_file and os.path.exists(temporary_file):
            os.remove(temporary_file)

def check_dependencies():
    
    """Проверяет наличие необходимых инструментов в системе."""
    try:
        # Проверяем, установлен ли системный Pandoc
        version = pypandoc.get_pandoc_version()
        logging.info(f"✅ Pandoc найден, версия: {version}")
        return True
    except OSError:
        logging.error("❌ Ошибка: Системный пакет 'pandoc' не установлен.")
        if sys.platform == "darwin":
            logging.info("💡 Решение: откройте терминал и выполните 'brew install pandoc'")
        elif sys.platform.startswith("linux"):
            logging.info("💡 Решение: откройте терминал и выполните 'sudo apt install pandoc' или используйте пакетный менеджер вашей системы.")
        elif sys.platform == "win64":
            logging.info("💡 Решение: скачайте установщик с https://pandoc.org/installing.html и установите Pandoc.")
        sys.exit(1)
        return False
def convert_to_docx(input_file: str, output_file: str):
    """
    Конвертирует Markdown в формат DOCX с сохранением подсветки кода.
    Примечание: Для этого требуется установленный системный пакет 'pandoc'.
    """
    if not check_dependencies():
        return  # Проверяем зависимости перед конвертацией
    if not os.path.exists(input_file):
        logging.error(f"❌ Файл '{input_file}' не найден.")
        return

    logging.info(f"🔄 Конвертация в DOCX: {input_file} -> {output_file}")
    try:
        pypandoc.convert_text(
            _read_markdown(input_file),
            'docx',
            format='markdown',
            outputfile=output_file,
            extra_args=[
                '--standalone',             # Создаёт полноценный документ с заголовком
                '--syntax-highlighting=breezedark', # Контрастный фон и цвета подсветки кода
            ]
        )
        _enable_docx_code_wrapping(output_file)
        logging.info(f"✅ Успешно создано: {os.path.abspath(output_file)}\n")
    except Exception as e:
        logging.error(f"⚠️ Ошибка при создании DOCX: {e}\n")

def convert_to_pdf(input_file: str, output_file: str):
    """
    Конвертирует Markdown в PDF. 
    Примечание: Для этого требуется установленный движок рендеринга (например, wkhtmltopdf или xelatex).
    """
    if not check_dependencies():
        return  # Проверяем зависимости перед конвертацией
    if not os.path.exists(input_file):
        logging.error(f"❌ Файл '{input_file}' не найден.")
        return

    logging.info(f"🔄 Конвертация в PDF: {input_file} -> {output_file}")
    try:
        pypandoc.convert_text(
            _read_markdown(input_file),
            'pdf',
            format='markdown',
            outputfile=output_file,
            extra_args=[
                '--standalone',
                '--syntax-highlighting=breezedark',
                '--pdf-engine=typst', # Используем typst как наиболее простой движок
                '-V', 'mainfont=Arial',     # Шрифт для корректного отображения кириллицы
                '-V', 'monofont=Menlo',      # Моноширинный шрифт для блоков кода
                '-V', 'geometry:margin=1in'  # Поля документа
            ]
        )
        logging.info(f"✅ Успешно создано: {os.path.abspath(output_file)}\n")
    except RuntimeError as e:
        logging.error(f"⚠️ Не удалось создать PDF. Возможно, не установлен 'typst'.")
        if sys.platform == "darwin":
            logging.info(f"💡 Решение: выполните 'brew install typst'")
        elif sys.platform.startswith("linux"):
            logging.info(f"💡 Решение: выполните 'sudo apt install typst' или используйте пакетный менеджер вашей системы.")
        else:
            logging.info(f"💡 Решение: скачайте установщик с https://wkhtmltopdf.org/downloads.html и установите wkhtmltopdf.")
        logging.error(f"Техническая деталь: {e}\n")

if __name__ == '__main__':
    # Задаем имена файлов (измените 'lab5.md' на имя вашего файла с отчетом)
    INPUT_MD = 'lab5.md'       
    OUTPUT_DOCX = 'Отчет_Лабораторная_5.docx'
    OUTPUT_PDF = 'Отчет_Лабораторная_5.pdf'
    
    convert_to_docx(INPUT_MD, OUTPUT_DOCX)
    convert_to_pdf(INPUT_MD, OUTPUT_PDF)
    