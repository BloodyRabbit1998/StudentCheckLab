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
                                [KeyboardButton(text="Редактирование таблиц 🧾"), KeyboardButton(text="Просмотреть работы 🔎")],
                                [ KeyboardButton(text="Отчет 📠"), KeyboardButton(text="Список услуг 🧾")],
                                [ KeyboardButton(text="Список услуг 🧾")]],
                                resize_keyboard=True)                    
kb_student_main=ReplyKeyboardMarkup(keyboard=[
                                [KeyboardButton(text="Сдать работу🧾"), KeyboardButton(text="Список моих работ")],
                                [ KeyboardButton(text="Получить работу👁‍🗨"),KeyboardButton(text="Получить шаблон📝")]],
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
async def kb_return_group(call_text:str,discipline_id:int=None):
    if discipline_id:
        pass
    else:
        kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=group.name, callback_data=f"{call_text} {group.id}")] for group in await db.return_all("group")])
    return kb
async def kb_return_disciplin_id(call_text:str,id_student:int):
    student=await db.return_student(id_student)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=student.name, callback_data=f"{call_text} {student.id}")] for student in await db.return_discipline("",id_group=student[-1].id_group)])
    return kb
async def kb_return_student_works(id_student,id_discipline,call_text:str):
    data=await db.retutn_works_student_all(id_student, id_discipline)
    status={True:"✅",False:"❌",None:"🕖"}
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{name} {status[accept]}", callback_data=f"{call_text} {id}")] for id,name,accept in data])
    return kb
async def kb_retutn_students_work(id_discipline:int,call_text:str):
    data=await db.return_student_work_none(id_discipline)
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{shorten_name(data[id_student]["name"])}({data[id_student]["group"]})-{len(data[id_student]["works"])}', callback_data=f"{call_text} {id_student}")] for id_student in data])
    return kb,data

def shorten_name(full_name):
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    last_name = parts[-1]
    initials = [f"{part[0]}." for part in parts[:-1]]
    return f"{' '.join(initials)} {last_name}"