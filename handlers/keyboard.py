import DataBase.request as db
from aiogram.types import ( InlineKeyboardButton, 
                            InlineKeyboardMarkup, 
                            KeyboardButton, 
                            ReplyKeyboardMarkup)
msg_admin_start="""
        Доступны следующие команды:
    /start          - запуск бота
    /status         - проверка статуса админа 
    /edit           - начать измененик данных     
    /works          - просмотреть работы студентов
    /menu           -вызов панели администратора
"""
msg_student_start="""
        У вас статус "Студент"!.
        Доступны следующие команды:
    /start          - запуск бота
    /registration   - регистрация студента
    /menu           - вызов меню
        """
kb_admin_main=ReplyKeyboardMarkup(keyboard=[
                                [KeyboardButton(text="Редактирование таблиц 🧾"), KeyboardButton(text="Просмотреть работы 🧾")],
                                [ KeyboardButton(text="Список услуг 🧾"), KeyboardButton(text="Список услуг 🧾")],
                                [ KeyboardButton(text="Список услуг 🧾")]],
                                resize_keyboard=True)                    
kb_student_main=ReplyKeyboardMarkup(keyboard=[
                                [KeyboardButton(text="Сдать работу🧾"), KeyboardButton(text="Список моих работ")],
                                [ KeyboardButton(text="Получить работу👁‍🗨")]],
                                resize_keyboard=True)
kb_admin_works=ReplyKeyboardMarkup(keyboard=[
                                [KeyboardButton(text="Добавить работу"),KeyboardButton(text="Просмотреть работы")],
                                [KeyboardButton(text="Изменить работу"),KeyboardButton(text="Удалить работу")],
                                [KeyboardButton(text="Назад")]],
                                resize_keyboard=True)
kb_admin_group=ReplyKeyboardMarkup(keyboard=[
                                [KeyboardButton(text="Добавить группу"),KeyboardButton(text="Просмотреть группы")],
                                [KeyboardButton(text="Изменить группу"),KeyboardButton(text="Удалить группу")],
                                [KeyboardButton(text="Назад")]],
                                resize_keyboard=True)
kb_admin_discipline=ReplyKeyboardMarkup(keyboard=[
                                [KeyboardButton(text="Добавить дисциплину"),KeyboardButton(text="Просмотреть дисциплины")],
                                [KeyboardButton(text="Изменить дисциплину"),KeyboardButton(text="Удалить дисциплину")],
                                [KeyboardButton(text="Назад")]],
                                resize_keyboard=True)
async def kb_return_works(discipline_id:int, call_text:str=None):
    works=await db.return_work("works",id_discipline=discipline_id)
    kb=InlineKeyboardMarkup(inline_keyboard=
                            [
                                [InlineKeyboardButton(text=f"{work.name}📄{'✅'if work.path else '❌'}",
                                                      callback_data=f"{call_text if call_text else ''} {work.id}")]
                                                      for work in works])
    return kb
async def kb_return_discipline(call_text:str):
    kb=InlineKeyboardMarkup(inline_keyboard=
                            [
                                [InlineKeyboardButton(text=discipline.name, 
                                                      callback_data=f"{call_text} {discipline.id}")] 
                                                      for discipline in await db.return_all("discipline")])
    return kb 
async def kb_return_group(call_text:str):
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=group.name, callback_data=f"{call_text} {group.id}")] for group in await db.return_all("group")])
    return kb
async def kb_return_disciplin_id(call_text:str,id_student:int):
    student=await db.return_student(id_student)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=student.name, callback_data=f"{call_text} {student.id}")] for student in await db.return_discipline("",id_group=student[-1].id_group)])
    return kb