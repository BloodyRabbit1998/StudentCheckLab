"""
Router для админ панели
Основные функции:
- Просмотр и редактирование таблиц:
    - Добавление, удаление и изменение дисциплин
    - Добавление, удаление и изменение групп
    - Добавление, удаление и изменение работ
- Просмотр и проверка работ студентов

"""

from aiogram.types import ( InlineKeyboardButton, 
                            InlineKeyboardMarkup, 
                            KeyboardButton, 
                            ReplyKeyboardMarkup, 
                            ReplyKeyboardRemove,
                            Message
                            )
from aiogram import F, Router, types,Bot
from aiogram.types.input_file import FSInputFile 
from aiogram.filters import Command,CommandStart,BaseFilter
from config import ADMINS
import DataBase.request as db
from aiogram.fsm.context import FSMContext 
from states import *
from pathlib import Path
from .keyboard import *
import logging
import os
import asyncio
import datetime
import shutil
from config import UPDATE_DATE,URL_SQL,BASE_DIR
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
router=Router()
edit_table=False

class AdminFilter(BaseFilter):
    def __init__(self):
        super().__init__()

    async def __call__(self, message: Message) -> bool:
        result=message.from_user.id in ADMINS
        return result
@router.message(AdminFilter(),CommandStart())
@router.message(AdminFilter(),Command('start'))
async def start_handler(msg:Message,state:FSMContext):
    await msg.answer_sticker(r"CAACAgQAAxkBAAED3Q1l5EuHETdkCgz_OEPKmjcPJXwyxQACAwYAAgtetBq169NzfwFttTQE")#,reply_markup=kb)
    await msg.answer(f"Вы админ",reply_markup=kb_admin_main) 
    await msg.answer(msg_admin_start)  
@router.message(AdminFilter(),Command('menu'))
@router.message(AdminFilter(),F.text=="menu")
async def menu(msg:Message,state:State):
    global edit_table
    await state.clear() 
    await msg.answer(f"Админ панель",reply_markup=kb_admin_main) 
    edit_table=False
@router.message(Command('id'))
@router.message(F.text=="id")
async def massage_id(msg:Message):
    await msg.answer(f"Ваш ID: {msg.from_user.id}")

@router.message(AdminFilter(),Command('edit'))
@router.message(AdminFilter(),F.text.in_(["edit","Edit","Редактирование таблиц 🧾"]))
async def edir_table_status(msg:Message,state:FSMContext):
    global edit_table
    edit_table=not edit_table
    if edit_table:
        await msg.answer("Вы перешли в режим изменения базы данных",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[   
            [KeyboardButton(text="Работы"),KeyboardButton(text="Группы")],
            [KeyboardButton(text="Дисциплины"),KeyboardButton(text="Назад")],
            [KeyboardButton(text="Архивация базы данных")]
        ]),resize_keyboard=True)
        await state.set_state(Table.choice_table)
    else:
        await msg.answer("Вы вышли из режима изменения базы данных")
        await state.clear()
        await menu(msg,state)
@router.message(AdminFilter(),Table.choice_table, ~F.text=="Архивация базы данных")
async def table(msg:Message,state:FSMContext):
    await state.update_data(choice_table=msg.text)
    kbs={"Работы":kb_admin_works,
         "Группы":kb_admin_group,
         "Дисциплины":kb_admin_discipline}
    if msg.text=="Назад":
        await msg.answer("Вы вышли из режима изменения базы данных")
        await state.clear()
        await menu(msg,state)
    elif msg.text in kbs:
        await msg.answer(f"""
    Вы выбрали таблицу "{msg.text}"
    Выберите что хотите сделать с таблицей в клавиатуре ниже!
                              """, reply_markup= kbs[msg.text])
        await state.set_state(Table.choice_operation)

@router.message(AdminFilter(),Table.choice_operation)
async def set_operation(msg:Message, state:FSMContext):
    await state.update_data(choice_operation=msg.text)
    if msg.text=="Назад":
        await menu(msg,state)
    elif msg.text in ["Добавить работу","Просмотреть работы","Изменить работу"]:
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Выберите дисциплину:",reply_markup=await kb_return_discipline("discipline sel work"))
        await load.delete()
    elif msg.text=="Удалить работу":
        await msg.answer("В разработке...")
    elif msg.text=="Добавить группу":
        await msg.answer("Введите название группы:",reply_markup=ReplyKeyboardRemove())
        await state.set_state(Table.set_data)
    elif msg.text=="Просмотреть группы":
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Список групп:",reply_markup=await kb_return_group("info group"))
        await load.delete()
        state.set_state(Table.choice_operation)
    elif msg.text=="Изменить группу":
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Выберите группу и введите измененное имя",
                         reply_markup=await kb_return_group("group"))  
        await load.delete()
    elif msg.text=="Удалить группу":
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Нажмите группу для удаления:",reply_markup=await kb_return_group("group del"))
        await load.delete()
    elif msg.text=="Добавить дисциплину":
        await msg.answer("Введите название дисциплины:",reply_markup=ReplyKeyboardRemove())
        await state.set_state(Table.set_data)
    elif msg.text=="Просмотреть дисциплины":
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Список дисциплин:",reply_markup=await kb_return_discipline("info discipline"))
        await load.delete()
    elif msg.text=="Изменить дисциплину":
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Список дисциплин:",reply_markup=await kb_return_discipline("update discipline"))
        await load.delete()
    elif msg.text=="Удалить дисциплину":
        load=await msg.answer("Загрузка ...",reply_markup=ReplyKeyboardRemove())
        await msg.answer("Нажмите дисциплину для удаления:",reply_markup=InlineKeyboardMarkup(inline_keyboard=await kb_return_discipline("discipline del")))
        await load.delete()
    else:
        await msg.answer("Неверная команда!")
        await state.set_state(Table.choice_operation)
@router.message(Table.set_data,F.text.in_(["Название","Файл","Отмена"]))
async def update_work(msg:Message, state:FSMContext):
    await state.update_data(set_col=msg.text)
    if msg.text=="Название":
        await msg.answer("Введите обновленное название работы:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Table.set_data)
    elif msg.text=="Файл":
        await msg.answer("Отправьте документ:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Table.document)
    elif msg.text=="Отмена":
        await msg.answer("Операция отменена",reply_markup=ReplyKeyboardMarkup(
            keyboard=[[]]
        ))
@router.message(Table.set_data)
async def set_data(msg:Message, state:FSMContext):
    operation = await state.get_data()
    if operation is None:
        pass
    if operation['choice_operation']=="Добавить работу":
        await state.update_data(set_data=msg.text)
        await msg.answer("Добавить документ?",reply_markup=ReplyKeyboardMarkup(keyboard=
                            [
                                [KeyboardButton(text="Добавить документ"),KeyboardButton(text="Не добавлять документ")]
                                                      ],resize_keyboard=True)
                        )
        await state.set_state(Table.document)
    elif operation['choice_operation']=="Добавить группу":    
        await db.add("group",[(msg.text)])
        await msg.answer("Группа добавлена!\nЖелаете добавит еще?",reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Добавить еще группу"),KeyboardButton(text="Назад")]],resize_keyboard=True))    
        await state.set_state(Table.repite)
    elif operation['choice_operation']=="Добавить дисциплину":
        await state.update_data(set_data=msg.text)
        await msg.answer("Выберите группу:",reply_markup=await kb_return_group("discipline group"))
    elif operation['choice_operation']=="Изменить группу":
        await db.update_col("group", (operation['group_id'],(msg.text)))
        await msg.answer("Группа изменена!",reply_markup=kb_admin_group)
        await state.set_state(Table.choice_operation)
    elif operation['choice_operation']=="Изменить дисциплину":
        await db.update_col("discipline", (operation['discipline_id'], (msg.text)))
        await msg.answer("Дисциплина изменена!",reply_markup=kb_admin_discipline)
        await state.clear()
        await state.set_state(Table.choice_operation)
    elif operation['choice_operation']=="Изменить работу" and "set_col" in operation:
        if operation["set_col"]=="Название":
            work=await db.return_work(operation["work_id"])
            await db.update_col("works", (operation['work_id'], msg.text,operation["discipline_id"],work.path))
        elif operation["set_col"]=="Документ":
            await msg.answer("Отправьте документ:", reply_markup="")
            await state.set_state(Table.document)
        await msg.answer("Работа обновлена!",reply_markup=kb_admin_works)
        await state.clear()
        await state.set_state(Table.choice_operation)
    else:
        await msg.answer("Неверная команда!")
        await state.set_state(Table.set_data)
@router.message(Table.repite)
async def repite(msg:Message, state:FSMContext):
    if msg.text=="Добавить еще группу":
        await msg.answer("Введите название группы:",reply_markup=ReplyKeyboardRemove())    
        await state.set_state(Table.set_data)
    elif msg.text=="Добавить еще дисциплину":
        await msg.answer("Введите название дисциплины:",reply_markup=ReplyKeyboardRemove()) 
        await state.set_state(Table.set_data)
    elif msg.text=="Добавить еще работу":
        await msg.answer("Введите название работы:")
        await state.set_state(Table.set_data)
    elif msg.text=="Назад":
        await edir_table_status(msg, state)
    
    else:
        await msg.answer("Неверная команда!")
        await state.set_state(Table.repite)
@router.callback_query(F.data.regexp(r"discipline \d+"))
async def callback_group(call:types.CallbackQuery, state:FSMContext):
    await call.message.edit_text("Введите название дисциплины:",reply_markup=ReplyKeyboardRemove())
    await state.update_data(group_id=call.data.split()[1])
    await state.set_state(Table.set_data)
@router.callback_query(F.data.regexp(r"group \d+"))
async def callback_info_group(call:types.CallbackQuery,state:FSMContext):
    group_id=int(call.data.split()[-1])
    await state.update_data(group_id=group_id) 
    await call.message.edit_text(f"Введите обновленное название группы:",reply_markup=ReplyKeyboardRemove())
    await state.set_state(Table.set_data)
@router.callback_query(F.data.regexp(r'group del \d+'))
async def callback_del_group(call:types.CallbackQuery,state:FSMContext):
    group_id=int(call.data.split()[-1])
    await state.update_data(group_id=group_id)
    await call.message.edit_text("Уверены что хотите удалить?",reply_markup=InlineKeyboardMarkup(inline_keyboard=
                            [
                                [InlineKeyboardButton(text="Да ✅", callback_data=f"choice yes"),InlineKeyboardButton(text="Нет ❌", callback_data=f"choice no") ] ])
                        )
@router.callback_query(F.data.regexp(r'choice (yes|no)'))
async def callback_del_group(call:types.CallbackQuery, state:FSMContext):
    if call.data.split()[-1]=="yes":
        operation=await state.get_data()
        if operation["choice_operation"]=="Удалить группу":
            await db.delete_col("group", operation['group_id'])
            await call.message.edit_text("Группа удалена!",reply_markup=None)
        elif operation["choice_operation"]=="Удалить дисциплину":
            await db.delete_col("discipline", operation['discipline_id'])
            await call.message.edit_text("Дисциплина удалена!",reply_markup=None)
        elif operation["choice_operation"]=="Удалить работу":
            await db.delete_col("works", operation['work_id'])
            await call.message.edit_text("Работа удалена!",reply_markup=None)
        elif operation["choice_operation"]=="Удалить работу студента":
            await db.delete_col("works_student", operation['works_student_id'])
            await call.message.edit_text("Работа студента удалена!",reply_markup=None)
    else:
        await call.message.edit_text("Группа не удалена!",reply_markup=None)
    await state.clear()
@router.callback_query(F.data.regexp(r'discipline group \d+'))
async def callback_discipline(call:types.CallbackQuery,state:FSMContext):
    group_id=int(call.data.split()[-1])
    data=await state.get_data()
    group=await db.return_group(group_id)
    await state.update_data(group_id=group_id)
    await call.message.edit_text(f"""
    Дисциплина:{data["set_data"]}
    Группа:{group.name}
    """,reply_markup=None)
    await db.add("discipline", [(data['set_data'], group_id)])
    await call.message.answer("Дисциплина добавлена!\nЖелаете добавит еще?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Добавить еще дисциплину"), KeyboardButton(text="Назад")]], resize_keyboard=True))
    await state.set_state(Table.repite)
@router.callback_query(F.data.regexp(r"discipline del \d+")) 
async def callback_del_discipline(call:types.CallbackQuery,state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.edit_text("Уверены что хотите удалить?",reply_markup=InlineKeyboardMarkup(inline_keyboard=
                            [
                                [InlineKeyboardButton(text="Да ✅", callback_data=f"choice yes"),InlineKeyboardButton(text="Нет ❌", callback_data=f"choice no") ] ])
                        )
@router.callback_query(F.data.regexp(r"discipline sel work \d+"))
async def callback_work(call:types.CallbackQuery,state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    data=await state.get_data()
    if data["choice_operation"]=="Просмотреть работы":
        await call.message.edit_text("Список работ:",
                         reply_markup=await kb_return_works(discipline_id,"student get work")
                        )
        await state.set_state(Table.get_work)
    elif data["choice_operation"]=="Добавить работу":
        await call.message.edit_text("Введите название работы:",reply_markup= None)
        await state.set_state(Table.set_data)
    elif data["choice_operation"]=="Изменить работу":
        await call.message.edit_text("Выберите работу для изменения:", reply_markup= await kb_return_works(discipline_id, "work update"))

@router.message(Table.document,F.text.in_(["Добавить документ","Не добавлять документ"]))
async def add_work(msg:Message,state:FSMContext):
    data=await state.get_data()
    if msg.text=="Добавить документ":
        await msg.answer("Отправьте документ:")
        await state.set_state(Table.document)
    else:
        await db.add("works", [(data['set_data'], data['discipline_id'],None)])
        await msg.answer("Работа добавлена!\nЖелаете добавит еще?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Добавить еще работу"), KeyboardButton(text="Назад")]], resize_keyboard=True))
        await state.set_state(Table.repite)

@router.message(Table.document, F.document)
async def add_document(msg:Message,state:FSMContext,bot:Bot):
    data=await state.get_data()
    disc=await db.return_discipline(data['discipline_id'])
    path= Path(__file__).parent.parent / "files"/"documents"/disc[-1].name 
    path=path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    path/=msg.document.file_name 
    path=path.resolve()
    await bot.download(file=msg.document, destination=path)
    if "set_col" in data:
        work=await db.return_work(data['work_id'])
        await db.update_col("works", (data['work_id'], work.name, data['discipline_id'],str(path)))
        await msg.answer("Работа обновлена!",reply_markup=kb_admin_works)
        await state.clear()
        await state.set_state(Table.choice_operation)
    else:
        await db.add("works", [(data['set_data'], data['discipline_id'],str(path))])
        await msg.answer("Работа добавлена!\nЖелаете добавит еще?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Добавить еще работу"), KeyboardButton(text="Назад")]], resize_keyboard=True))
        await state.set_state(Table.repite)

@router.callback_query(F.data.regexp(r"work del \d+"))
async def callback_del_work(call:types.CallbackQuery, state:FSMContext):
    work_id=int(call.data.split()[-1])
    await state.update_data(work_id=work_id)
    await call.message.edit_text("Уверены что хотите удалить?",reply_markup=InlineKeyboardMarkup(inline_keyboard=
                            [
                                [InlineKeyboardButton(text="Да ✅", callback_data=f"choice yes"),InlineKeyboardButton(text="Нет ❌", callback_data=f"choice no") ] ])
                        )
    await state.set_state(Table.set_data)
@router.callback_query(F.data.regexp(r"work update \d+"))
async def callback_update_work(call:types.CallbackQuery, state:FSMContext):
    work_id=int(call.data.split()[-1])
    await state.update_data(work_id=work_id)
    await call.message.delete()
    await call.message.answer("Выберите что хотите изменить",reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Название"),KeyboardButton(text="Файл")],
                   [KeyboardButton(text="Отмена")]],
        resize_keyboard=True))
    await state.set_state(Table.set_data)
@router.callback_query(F.data.regexp(r"update discipline \d+"))
async def update_disc(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.edit_text("Введите обновленное название дисциплины:", reply_markup=None)
    await state.set_state(Table.set_data)


@router.message(AdminFilter(),F.text=="Архивация базы данных")
async def archive_database(msg:Message):    
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    # SQL_URL вида sqlite+aiosqlite:///files/db.sqlite3 -> путь к файлу БД
    db_rel_path = URL_SQL.split("///")[-1]
    database_path = os.path.join(BASE_DIR, db_rel_path)
    archive_dir = os.path.join(os.path.dirname(database_path), "db_archive")
    archive_path = os.path.join(archive_dir, f"database_{timestamp}.db")

    try:
        os.makedirs(archive_dir, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, database_path, archive_path)
    except Exception as e:
        logging.exception("Не удалось архивировать базу данных")
        await msg.answer(f"Не удалось архивировать базу данных: {e}")
        return

    display_path = os.path.relpath(archive_path, BASE_DIR)
    msg_info=await msg.answer(f"База данных успешно архивирована в {display_path}\nОчищаем базу данных для следующего года...")
    await db.clean_for_next_year(datetime.datetime(year=now.year, 
                                                   month=UPDATE_DATE["month"], 
                                                   day=UPDATE_DATE["day"]))
    await msg_info.edit_text(f"База данных успешно архивирована в {display_path}\nБаза данных очищена для следующего года.")
    

"""-------------------Проверка работ студентов------------------"""

@router.message(AdminFilter(),F.text=='Просмотреть работы 🔎')
async def view_works(msg:Message, state:FSMContext):
    await msg.answer("Выберите дисциплину:", reply_markup=await kb_return_discipline("discipline check work"))
    await state.update_data(choice_operation="Просмотреть работы")
    await state.set_state(CheckWork.choice_discipline)
@router.callback_query(CheckWork.choice_discipline,F.data.regexp(r"discipline check work \d+"))
async def callback_work(call:types.CallbackQuery, state:FSMContext, bot:Bot):
    discipline_id=int(call.data.split()[-1])
    kb=await kb_retutn_students_work( discipline_id,"student check work")
    
    await state.update_data(discipline_id=discipline_id)
    await call.message.edit_text("Работы по дисциплине", reply_markup=kb )
    await state.set_state(CheckWork.choice_student)
@router.callback_query(CheckWork.choice_student, F.data.regexp(r"student check work \d+"))
async def callback_work(call:types.CallbackQuery, state:FSMContext,bot:Bot):
    id_student=int(call.data.split()[-1])
    data=await state.get_data()
    id_discipline=data["discipline_id"]
    student = await db.return_student(id_student)
    student=student[-1]
    await call.message.delete()
    await call.message.answer(f"Работы студента {student.name}:")
    for row in await db.return_student_work_none(id_discipline=id_discipline, id_student=id_student):
        file_input = FSInputFile(row["path"])
        await bot.send_document(call.message.chat.id,file_input ,
                caption=f"{row['name_work']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept {row['id']}"),
        InlineKeyboardButton(text="❌ Не принять", callback_data=f"reject {row['id']}")]
    ]))
    logging.debug("Отправлены работы!")
@router.callback_query(F.data.regexp(r"accept \d+"))
async def callback_accept(call:types.CallbackQuery, state:FSMContext,bot:Bot):
    id_work=int(call.data.split()[-1])
    data=await state.get_data()
    await db.accept_work(id_work,True)
    await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
       [InlineKeyboardButton(text="✅ Принято", callback_data="None")]]))
    work=await db.return_work_student(id_work=id_work)
    await bot.send_message(chat_id=work['id_student'], text=f"Дисциплина: {work['discipline_name']}\nРабота: {work['work_name']}\nСтатус: ✅ Принята")
    await call.answer()
@router.callback_query(F.data.regexp(r"reject \d+"))
async def callback_reject(call:types.CallbackQuery, state:FSMContext, bot:Bot):
    id_work=int(call.data.split()[-1])
    work=await db.return_work_student(id_work=id_work)
    id_student=work["id_student"]
    await state.update_data(id_work=id_work,id_student=id_student)
    await db.accept_work(id_work, False)
    msg_request = await call.message.answer("Введите комменторий к работе:")
    await state.update_data(request_comment_msg_id=msg_request.message_id)
    await state.set_state(CheckWork.check_work)
@router.message(AdminFilter(),CheckWork.check_work)
async def msg_reject(msg:Message, state:FSMContext, bot:Bot):
    state_data=await state.get_data()
    id_work,id_student=state_data["id_work"],state_data["id_student"]
    request_msg_id = state_data.get("request_comment_msg_id")

    work_data=await db.return_work_accept(id_work)
    work_name,discipline_name,path=work_data
    await bot.send_document(chat_id=id_student, document=FSInputFile(path), 
        caption=f"""
Дисциплина: {discipline_name}
Работа: {work_name}
Статус: ❌ Не принята
Комментарий {msg.text}""")

    # Удаляем сообщение администратора "Введите комментарий к работе:" после отправки нового
    if request_msg_id:
        try:
            await bot.delete_message(chat_id=msg.chat.id, message_id=request_msg_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение: {e}")

    await state.clear()

@router.message(AdminFilter(),F.text=="Отчет 📠")
async def report(msg:Message, state:FSMContext):
    await state.clear()
    await msg.answer("Выберите дисциплину:", reply_markup=await kb_return_discipline("discipline report"))
    await state.set_state(Report.choice_discipline)
@router.callback_query(F.data.regexp(r"discipline report \d+"))
async def callback_discipline(call:types.CallbackQuery, state:FSMContext, bot:Bot):
    discipline_id=int(call.data.split()[-1])
    disciplines=await db.return_discipline(discipline_id)
    if not disciplines:
        await call.answer("Дисциплина не найдена", show_alert=True)
        return

    discipline=disciplines[-1]
    await state.update_data(discipline_id=discipline_id, group_id=discipline.id_group)
    await call.answer("Формирую отчёт...")
    try:
        await call.message.edit_text(f"Формирую отчёт по дисциплине «{discipline.name}»...")
    except Exception:
        pass

    # Дисциплина привязана к конкретной группе, поэтому отчёт формируем сразу
    await _send_report(call, state, bot, discipline_id, discipline.id_group)


STATUS_MARK = {True: "✅", False: "❌", None: "🕖"}


def _safe_sheet_title(title: str) -> str:
    """Убирает символы, недопустимые в имени листа Excel, и ограничивает длину."""
    for ch in ':\\/?*[]':
        title = title.replace(ch, "-")
    return (title.strip() or "Отчёт")[:31]


async def generate_excel_report(discipline_id: int, group_id: int | None, data: list) -> str | None:
    """
    Генерирует Excel-отчёт по сданным работам в виде матрицы:
        {Группа} — {Дисциплина}
        № | ФИО | группа | 1 | 2 | 3 | ... | Сдано | Принято

    В ячейках: ✅ — принята, ❌ — не принята, 🕖 — на рассмотрении,
    пусто — работа не сдана.

    Returns:
        str | None: Путь к созданному файлу или None, если данных нет.
    """
    if not data:
        return None

    # Уникальные названия работ по дисциплине, отсортированные
    work_names = sorted({row.work_name for row in data})

    # Уникальные студенты: ключ (группа, имя), значение — {work_name: accept}
    students_map: dict[tuple[str, str], dict[str, bool | None]] = {}
    for row in data:
        key = (row.group_name, row.student_name)
        students_map.setdefault(key, {})[row.work_name] = row.accept

    # Название группы и дисциплины (берем из первой строки)
    group_name = data[0].group_name
    discipline_name = data[0].discipline_name

    wb = Workbook()
    ws = wb.active
    # Имя листа в Excel ограничено 31 символом и не должно содержать спецсимволов
    ws.title = _safe_sheet_title(f"{group_name} {discipline_name}")

    first_work_col = 4
    submitted_col = first_work_col + len(work_names)
    accepted_col = submitted_col + 1
    last_col = accepted_col

    # Заголовок отчёта
    title_row = 1
    ws.merge_cells(start_row=title_row, start_column=1, end_row=title_row, end_column=last_col)
    title_cell = ws.cell(row=title_row, column=1, value=f"{group_name} — {discipline_name}")
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = Alignment(horizontal="center")

    # Заголовок таблицы
    header_row = 3
    headers = ["№", "ФИО", "группа"]
    headers += [str(i + 1) for i in range(len(work_names))]
    headers += ["Сдано", "Принято"]
    for col_idx, value in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=value)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Расшифровка номеров работ
    names_row = header_row + 1
    for col_idx, work_name in enumerate(work_names, start=first_work_col):
        cell = ws.cell(row=names_row, column=col_idx, value=work_name)
        cell.font = Font(italic=True, size=9)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Обозначения статусов
    legend_row = names_row + 1
    ws.merge_cells(start_row=legend_row, start_column=1, end_row=legend_row, end_column=last_col)
    legend_cell = ws.cell(
        row=legend_row, column=1,
        value="Обозначения: ✅ принята, ❌ не принята, 🕖 на рассмотрении, пусто — работа не сдана",
    )
    legend_cell.font = Font(italic=True, size=9)
    legend_cell.alignment = Alignment(horizontal="left")

    # Данные по студентам
    first_data_row = legend_row + 1
    for row_idx, ((student_group, student_name), works_dict) in enumerate(
        students_map.items(), start=first_data_row
    ):
        ws.cell(row=row_idx, column=1, value=row_idx - first_data_row + 1)   # №
        ws.cell(row=row_idx, column=2, value=student_name)                   # ФИО
        ws.cell(row=row_idx, column=3, value=student_group)                  # группа
        for col_idx, work_name in enumerate(work_names, start=first_work_col):
            if work_name in works_dict:
                cell = ws.cell(row=row_idx, column=col_idx,
                               value=STATUS_MARK[works_dict[work_name]])
                cell.alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=submitted_col, value=len(works_dict))
        ws.cell(row=row_idx, column=accepted_col,
                value=sum(1 for accept in works_dict.values() if accept is True))

    # Автоширина столбцов
    for col_idx in range(1, last_col + 1):
        max_length = 0
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=True):
            value = row[0]
            if value is not None:
                max_length = max(max_length, len(str(value)))
        adjusted_width = min(max(max_length + 2, 8), 40)
        ws.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

    # Сохраняем файл
    reports_dir = Path(__file__).parent.parent / "files" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_group = str(group_id) if group_id else "all"
    filepath = reports_dir / f"report_discipline_{discipline_id}_group_{safe_group}.xlsx"
    await asyncio.to_thread(wb.save, filepath)
    return str(filepath)


async def _send_report(call: types.CallbackQuery, state: FSMContext, bot: Bot,
                       discipline_id: int, group_id: int | None):
    """Формирует Excel-отчёт и отправляет его админу в чат."""
    # Получаем данные из БД
    works_data = await db.return_submitted_works(discipline_id, group_id)

    if not works_data:
        await call.message.answer("Нет сданных работ по выбранным критериям.")
        await state.clear()
        return

    # Генерируем Excel
    try:
        filepath = await generate_excel_report(discipline_id, group_id, works_data)
    except Exception:
        logging.exception("Ошибка генерации Excel")
        await call.message.answer("Ошибка при генерации отчёта.")
        await state.clear()
        return

    if not filepath:
        await call.message.answer("Нет данных для формирования отчёта.")
        await state.clear()
        return

    group_name = works_data[0].group_name
    discipline_name = works_data[0].discipline_name

    # Отправляем файл админу
    try:
        await bot.send_document(
            chat_id=call.message.chat.id,
            document=FSInputFile(filepath),
            caption=f"Отчёт: {discipline_name}, группа {group_name}",
        )
    finally:
        # Удаляем временный файл в любом случае
        try:
            os.remove(filepath)
        except Exception as e:
            logging.warning(f"Не удалось удалить временный файл отчёта: {e}")

    await state.clear()


@router.callback_query(F.data.regexp(r"group report \d+"))
async def callback_report_group(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    # Оставлено для совместимости со старыми сообщениями с выбором группы
    group_id = int(call.data.split()[-1])
    state_data = await state.get_data()
    discipline_id = state_data.get("discipline_id")

    if not discipline_id:
        await call.answer("Ошибка: дисциплина не выбрана", show_alert=True)
        return

    await call.answer("Формирую отчёт...")
    await _send_report(call, state, bot, discipline_id, group_id)