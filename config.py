import os
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = dotenv_values(os.path.join(BASE_DIR, '.env'))

URL_SQL=env["SQL_URL"]
AI_TOKEN=env["AI_TOKEN"]
BOT_TOKEN=env["BOT_TOKEN"]
FONT_NAME=env["FONT_NAME"]
UPDATE_DATE=eval(env["UPDATE_DATE"])

def _parse_admins(raw: str | None) -> list[int]:
    """Разбирает ADMINS_ID: допускает пробелы, запятые и точки с запятой."""
    result = []
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip().strip('"').strip("'")
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            raise ValueError(
                f"Некорректный ID администратора в ADMINS_ID: {part!r}. "
                "Ожидается число или несколько чисел через запятую."
            ) from None

    if not result:
        raise ValueError(
            "ADMINS_ID не задан или пуст. Укажите свой Telegram ID в .env "
            "(его можно узнать командой /id в боте)."
        )
    return result


ADMINS = _parse_admins(env.get("ADMINS_ID"))