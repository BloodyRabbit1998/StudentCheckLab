import os
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = dotenv_values(os.path.join(BASE_DIR, '.env'))

URL_SQL=env["SQL_URL"]
AI_TOKEN=env["AI_TOKEN"]
BOT_TOKEN=env["BOT_TOKEN"]
FONT_NAME=env["FONT_NAME"]

admins=env["ADMINS_ID"]
if "," in admins:
    ADMINS=list(map(int,admins.split(",")))
else:
    ADMINS=[int(admins)]