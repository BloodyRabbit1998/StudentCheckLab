from dotenv import dotenv_values

env=dotenv_values(".env")

URL_SQL=env["SQL_URL"]

BOT_TOKEN=env["TOKEN"]
admins=env["ADMINS_ID"]
if "," in admins:
    ADMINS=list(map(int,admins.split(",")))
else:
    ADMINS=[int(admins)]