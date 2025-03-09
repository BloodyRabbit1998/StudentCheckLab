import asyncio
import logging
import DataBase.models as models
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import config
from handlers.student_panel import router as student_router
from handlers.admin_panel import router as admin_router
from aiogram.client.default import DefaultBotProperties
"""
TODO: 
-не работает удаление данных из базы данных. Надо доработать функцию delete_col
-проверять наличие имени у студента по регулярным выражениям
"""
async def main():
    await models.create_db()
    bot = Bot(token=config.BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp=Dispatcher(storege=MemoryStorage())
    dp.include_routers(admin_router,student_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.DEBUG("Программа завершена принудительно!")
    finally:
        logging.info(" > Bot прекратил свою работу!!!!!!")