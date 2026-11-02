"""
WordCraft Python API — кроссплатформенный генератор документов.
Работает на macOS, Linux и Windows.
"""

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class WordCraftError(Exception):
    """Базовое исключение для ошибок WordCraft."""
    pass


class WordCraftNotFoundError(WordCraftError):
    """Не удалось найти wordcraft-cli в системе."""
    pass


class WordCraft:
    """
    Кроссплатформенный интерфейс для работы с WordCraft.
    
    Пример использования:
        wc = WordCraft()
        wc.heading("Лабораторная работа №1", level=1)
        wc.paragraph("Цель работы: ...")
        wc.save("lab1.docx")
        wc.build()
    """
    
    def __init__(
        self,
        cli_path: Optional[str] = None,
        auto_detect: bool = True,
        timeout: float = 30.0,
    ):
        """
        Инициализация WordCraft.
        
        Args:
            cli_path: Путь к wordcraft-cli. Если None — ищет автоматически.
            auto_detect: Автоматически искать wordcraft-cli в PATH.
            timeout: Таймаут для операций с control-каналом (секунды).
        """
        self.cli_path = cli_path
        self.timeout = timeout
        self.commands: List[Dict[str, Any]] = []
        self._live_socket: Optional[socket.socket] = None
        self._live_host = "127.0.0.1"
        self._live_port = 7981
        
        # Автоопределение платформы
        self.platform = platform.system()  # 'Windows', 'Darwin', 'Linux'
        
        if auto_detect and not self.cli_path:
            self.cli_path = self._find_wordcraft_cli()
    
    def _find_wordcraft_cli(self) -> str:
        """Ищет wordcraft-cli в системе."""
        # Сначала пробуем найти через shutil.which (работает на всех ОС)
        cli_name = "wordcraft-cli"
        if self.platform == "Windows":
            cli_name = "wordcraft-cli.exe"
        
        found = shutil.which(cli_name)
        if found:
            return found
        
        # Пробуем стандартные пути установки
        search_paths = []
        
        if self.platform == "Windows":
            search_paths = [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "WordCraft",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "WordCraft",
                Path.home() / "AppData" / "Local" / "Programs" / "WordCraft",
            ]
        elif self.platform == "Darwin":  # macOS
            search_paths = [
                Path("/Applications/WordCraft.app/Contents/MacOS"),
                Path.home() / "Applications" / "WordCraft.app" / "Contents" / "MacOS",
                Path("/usr/local/bin"),
                Path.home() / ".local" / "bin",
            ]
        else:  # Linux
            search_paths = [
                Path("/usr/bin"),
                Path("/usr/local/bin"),
                Path.home() / ".local" / "bin",
                Path("/opt/wordcraft"),
            ]
        
        for path in search_paths:
            candidate = path / cli_name
            if candidate.exists() and os.access(candidate, os.X_OK):
                return str(candidate)
        
        raise WordCraftNotFoundError(
            f"Не удалось найти {cli_name} в системе.\n"
            f"Установите WordCraft: https://github.com/storytold/wordcraft/releases\n"
            f"Или укажите путь вручную: WordCraft(cli_path='/path/to/wordcraft-cli')"
        )
    
    # === Методы для работы с содержимым документа ===
    
    def heading(self, text: str, level: int = 1) -> "WordCraft":
        """Добавить заголовок (level 1..9)."""
        if not 1 <= level <= 9:
            raise ValueError("Уровень заголовка должен быть от 1 до 9")
        
        self.commands.append({
            "cmd": "type_text",
            "text": text
        })
        self.commands.append({
            "cmd": "style.apply",
            "style": f"Heading{level}"
        })
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def paragraph(self, text: str, style: Optional[str] = None) -> "WordCraft":
        """Добавить обычный параграф."""
        if style:
            self.commands.append({"cmd": "style.apply", "style": style})
        self.commands.append({"cmd": "type_text", "text": text})
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def bold(self, text: str) -> "WordCraft":
        """Добавить жирный текст."""
        self.commands.append({"cmd": "format.bold.on"})
        self.commands.append({"cmd": "type_text", "text": text})
        self.commands.append({"cmd": "format.bold.off"})
        return self
    
    def italic(self, text: str) -> "WordCraft":
        """Добавить курсив."""
        self.commands.append({"cmd": "format.italic.on"})
        self.commands.append({"cmd": "type_text", "text": text})
        self.commands.append({"cmd": "format.italic.off"})
        return self
    
    def bold_paragraph(self, text: str) -> "WordCraft":
        """Добавить параграф жирным шрифтом."""
        self.bold(text)
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def bullet_list(self, items: List[str]) -> "WordCraft":
        """Добавить маркированный список."""
        for item in items:
            self.commands.append({"cmd": "list.bullet.start"})
            self.commands.append({"cmd": "type_text", "text": item})
            self.commands.append({"cmd": "list.end"})
        return self
    
    def numbered_list(self, items: List[str]) -> "WordCraft":
        """Добавить нумерованный список."""
        for item in items:
            self.commands.append({"cmd": "list.number.start"})
            self.commands.append({"cmd": "type_text", "text": item})
            self.commands.append({"cmd": "list.end"})
        return self
    
    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        style: Optional[str] = None
    ) -> "WordCraft":
        """
        Добавить таблицу.
        
        Args:
            headers: Список заголовков столбцов.
            rows: Список строк (каждая строка — список ячеек).
            style: Опциональный стиль таблицы.
        """
        num_rows = len(rows) + 1  # +1 для заголовков
        num_cols = len(headers)
        
        self.commands.append({
            "cmd": "insert.table",
            "rows": num_rows,
            "cols": num_cols
        })
        
        # Заголовки
        for header in headers:
            self.commands.append({"cmd": "format.bold.on"})
            self.commands.append({"cmd": "type_text", "text": header})
            self.commands.append({"cmd": "format.bold.off"})
            self.commands.append({"cmd": "cursor.right"})
        
        # Строки
        for row in rows:
            for cell in row:
                self.commands.append({"cmd": "type_text", "text": str(cell)})
                self.commands.append({"cmd": "cursor.right"})
        
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def image(self, path: Union[str, Path], width: Optional[float] = None) -> "WordCraft":
        """
        Вставить изображение.
        
        Args:
            path: Путь к файлу изображения.
            width: Ширина в сантиметрах (опционально).
        """
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Изображение не найдено: {path}")
        
        cmd = {"cmd": "insert.picture", "path": str(path)}
        if width:
            cmd["width_cm"] = width
        
        self.commands.append(cmd)
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def page_break(self) -> "WordCraft":
        """Вставить разрыв страницы."""
        self.commands.append({"cmd": "insert.page_break"})
        return self
    
    def toc(self) -> "WordCraft":
        """Вставить оглавление."""
        self.commands.append({"cmd": "insert.toc"})
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def footnote(self, text: str) -> "WordCraft":
        """Вставить сноску."""
        self.commands.append({"cmd": "insert.footnote", "text": text})
        return self
    
    def formula(self, latex: str) -> "WordCraft":
        """
        Вставить формулу (если поддерживается).
        
        Args:
            latex: LaTeX-представление формулы.
        """
        self.commands.append({"cmd": "insert.equation", "latex": latex})
        self.commands.append({"cmd": "insert.paragraph_break"})
        return self
    
    def header_footer(
        self,
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
        first_page_different: bool = False
    ) -> "WordCraft":
        """
        Настроить колонтитулы.
        
        Args:
            header_text: Текст верхнего колонтитула.
            footer_text: Текст нижнего колонтитула.
            first_page_different: Отличный колонтитул для первой страницы.
        """
        if header_text:
            self.commands.append({
                "cmd": "header.set",
                "text": header_text,
                "first_page_different": first_page_different
            })
        if footer_text:
            self.commands.append({
                "cmd": "footer.set",
                "text": footer_text,
                "first_page_different": first_page_different
            })
        return self
    
    def page_setup(
        self,
        margins: Optional[Dict[str, float]] = None,
        orientation: Optional[str] = None,
        size: Optional[str] = None
    ) -> "WordCraft":
        """
        Настроить параметры страницы.
        
        Args:
            margins: Словарь {top, bottom, left, right} в сантиметрах.
            orientation: 'portrait' или 'landscape'.
            size: Размер страницы (A4, Letter и т.д.).
        """
        if margins:
            self.commands.append({"cmd": "page.margins", **margins})
        if orientation:
            self.commands.append({"cmd": "page.orientation", "orientation": orientation})
        if size:
            self.commands.append({"cmd": "page.size", "size": size})
        return self
    
    def save(self, filename: Union[str, Path]) -> "WordCraft":
        """Сохранить документ."""
        filename = Path(filename).resolve()
        self.commands.append({"cmd": "save_document", "path": str(filename)})
        return self
    
    # === Методы для выполнения ===
    
    def build(self, output_file: Optional[Union[str, Path]] = None) -> Path:
        """
        Сгенерировать JSON-скрипт и выполнить его через wordcraft-cli.
        
        Args:
            output_file: Если указан, сохраняет JSON-скрипт в этот файл.
        
        Returns:
            Путь к созданному документу (из последней команды save).
        """
        if not self.commands:
            raise WordCraftError("Нет команд для выполнения")
        
        # Извлекаем путь сохранения из последней команды
        output_path = None
        for cmd in reversed(self.commands):
            if cmd.get("cmd") == "save_document":
                output_path = Path(cmd["path"])
                break
        
        if not output_path:
            raise WordCraftError("Не указана команда save(). Добавьте wc.save('file.docx')")
        
        # Формируем JSON
        script = {"commands": self.commands}
        json_content = json.dumps(script, ensure_ascii=False, indent=2)
        
        # Сохраняем JSON во временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(json_content)
            temp_json = f.name
        
        try:
            # Запускаем wordcraft-cli
            cmd = [self.cli_path, "run", "--script", temp_json]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )
            
            print(f"✅ Документ создан: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            raise WordCraftError(
                f"Ошибка выполнения wordcraft-cli:\n"
                f"stdout: {e.stdout}\n"
                f"stderr: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise WordCraftError(f"Таймаут выполнения ({self.timeout}с)")
        finally:
            # Удаляем временный JSON
            try:
                os.unlink(temp_json)
            except:
                pass
    
    def connect(self, host: str = "127.0.0.1", port: int = 7981) -> "WordCraft":
        """
        Подключиться к работающему WordCraft через control-канал.
        
        WordCraft должен быть запущен с флагом --control:
            wordcraft --control 7981
        
        Args:
            host: Хост control-канала.
            port: Порт control-канала.
        """
        self._live_host = host
        self._live_port = port
        
        try:
            self._live_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._live_socket.settimeout(self.timeout)
            self._live_socket.connect((host, port))
            print(f"✅ Подключено к WordCraft на {host}:{port}")
            return self
        except Exception as e:
            raise WordCraftError(
                f"Не удалось подключиться к WordCraft на {host}:{port}\n"
                f"Убедитесь, что WordCraft запущен с флагом --control {port}\n"
                f"Ошибка: {e}"
            )
    
    def send_live(self) -> "WordCraft":
        """Отправить команды в работающий WordCraft."""
        if not self._live_socket:
            raise WordCraftError("Сначала вызовите connect()")
        
        for cmd in self.commands:
            try:
                self._live_socket.sendall((json.dumps(cmd) + "\n").encode('utf-8'))
                response = self._live_socket.recv(4096)
                print(f"Ответ: {response.decode('utf-8')}")
            except Exception as e:
                raise WordCraftError(f"Ошибка отправки команды: {e}")
        
        return self
    
    def disconnect(self) -> "WordCraft":
        """Отключиться от работающего WordCraft."""
        if self._live_socket:
            self._live_socket.close()
            self._live_socket = None
            print("✅ Отключено от WordCraft")
        return self
    
    def clear(self) -> "WordCraft":
        """Очистить список команд."""
        self.commands.clear()
        return self
    
    def __enter__(self):
        """Поддержка контекстного менеджера для live-режима."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое отключение при выходе из контекста."""
        self.disconnect()
    
    def __repr__(self) -> str:
        return (
            f"WordCraft(platform={self.platform}, "
            f"cli_path={self.cli_path}, "
            f"commands={len(self.commands)})"
        )


# === Пример использования ===

if __name__ == "__main__":
    print("=== Пример генерации лабораторной работы ===\n")
    
    # Создаем документ
    wc = WordCraft()
    
    # Титульный лист
    wc.heading("Лабораторная работа №3", level=1)
    wc.paragraph("Дисциплина: Цифровая обработка сигналов")
    wc.paragraph("Студент: Иванов И.И., группа ПИ-21")
    wc.paragraph("Преподаватель: Петров П.П.")
    wc.page_break()
    
    # Цель работы
    wc.heading("1. Цель работы", level=2)
    wc.paragraph("Изучить методы цифровой фильтрации сигналов.")
    wc.paragraph("Научиться проектировать БИХ- и КИХ-фильтры.")
    
    # Теоретические сведения
    wc.heading("2. Теоретические сведения", level=2)
    wc.paragraph("Цифровой фильтр — это система, преобразующая дискретный сигнал...")
    wc.bold_paragraph("Определение: Передаточная функция БИХ-фильтра:")
    wc.formula("H(z) = \\frac{\\sum_{k=0}^{M} b_k z^{-k}}{1 + \\sum_{k=1}^{N} a_k z^{-k}}")
    
    # Задание
    wc.heading("3. Задание", level=2)
    wc.paragraph("Спроектировать фильтр нижних частот со следующими параметрами:")
    wc.table(
        headers=["Параметр", "Значение", "Единицы"],
        rows=[
            ["Частота дискретизации", "44100", "Гц"],
            ["Частота среза", "1000", "Гц"],
            ["Порядок фильтра", "8", "-"],
            ["Тип", "Баттерворта", "-"]
        ]
    )
    
    # Ход работы
    wc.heading("4. Ход работы", level=2)
    wc.numbered_list([
        "Загрузить тестовый сигнал из файла signal.wav",
        "Применить разработанный фильтр",
        "Построить АЧХ и ФЧХ фильтра",
        "Сравнить исходный и отфильтрованный сигналы"
    ])
    
    # Контрольные вопросы
    wc.heading("5. Контрольные вопросы", level=2)
    wc.bullet_list([
        "Что такое АЧХ и ФЧХ фильтра?",
        "Чем БИХ-фильтр отличается от КИХ-фильтра?",
        "Какие методы проектирования цифровых фильтров вы знаете?",
        "Что такое частота Найквиста?"
    ])
    
    # Выводы
    wc.heading("6. Выводы", level=2)
    wc.paragraph("В ходе лабораторной работы были изучены методы цифровой фильтрации...")
    
    # Сохраняем
    wc.save("lab3.docx")
    
    # Генерируем документ
    try:
        output = wc.build()
        print(f"\n🎉 Готово! Файл сохранен: {output}")
    except WordCraftNotFoundError as e:
        print(f"\n❌ {e}")
    except WordCraftError as e:
        print(f"\n❌ Ошибка: {e}")