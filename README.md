# Телеграм бот для проверки лабораторных работ студентас

## Установка
Для того, чтобы запустит бота нужно установить [Python3.11](https://www.python.org/downloads/release/python-3119/)

### Для операционной системы MacOS нужно дополнительно установить  ```pandoс```
```brew install pandoc```

## Проверка работ на плагиат
Модуль `tools/ap_tools.py` сравнивает текст (шинглы) и скриншоты (перцептивные хеши) документа с другими работами.

```python
from tools.ap_tools import check_plagiarism, format_report

report = check_plagiarism(
    "files/documents/works students/ПИ-21/Иванов/Лабораторная 1.docx",
    "files/documents/works students/ПИ-21",  # папка или список файлов
    threshold=0.6,
)
print(format_report(report))
```

В боте используется асинхронная версия, чтобы не блокировать event loop:

```python
from tools.ap_tools import check_plagiarism_async, format_report

report = await check_plagiarism_async(file_path, works_folder, threshold=0.6)
await message.answer(format_report(report, html_safe=True))
```

Запуск из терминала:

```bash
python -m tools.ap_tools "работа.docx" "папка_с_работами" --threshold 0.6
```