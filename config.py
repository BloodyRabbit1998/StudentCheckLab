from dotenv import dotenv_values

env=dotenv_values(".env")

URL_SQL=env["SQL_URL"]

BOT_TOKEN=env["TOKEN"]

ADMINS=env["ADMINS_ID"]
