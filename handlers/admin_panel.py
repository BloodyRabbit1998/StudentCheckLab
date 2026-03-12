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
            [KeyboardButton(text="Дисциплины"),KeyboardButton(text="Назад")]
        ]),resize_keyboard=True)
        await state.set_state(Table.choice_table)
    else:
        await msg.answer("Вы вышли из режима изменения базы данных")
        await state.clear()
        await menu(msg,state)
@router.message(AdminFilter(),Table.choice_table)
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
        await msg.answer("Выберите дисциплину:",reply_markup=await kb_return_discipline("discipline sel work"))
        await msg.answer("",reply_markup=ReplyKeyboardRemove())
    elif msg.text=="Удалить работу":
        await msg.answer("В разработке...")
    elif msg.text=="Добавить группу":
        await msg.answer("Введите название группы:",reply_markup=ReplyKeyboardRemove())
        await state.set_state(Table.set_data)
    elif msg.text=="Просмотреть группы":
        await msg.answer("Список групп:",reply_markup=await kb_return_group("info group"))
        state.set_state(Table.choice_operation)
    elif msg.text=="Изменить группу":
        await msg.answer("Выберите группу и введите измененное имя",
                         reply_markup=await kb_return_group("group"))  
    elif msg.text=="Удалить группу":
        await msg.answer("Нажмите группу для удаления:",reply_markup=await kb_return_group("group del"))
    elif msg.text=="Добавить дисциплину":
        await msg.answer("Введите название дисциплины:",reply_markup=ReplyKeyboardRemove())
        await state.set_state(Table.set_data)
    elif msg.text=="Просмотреть дисциплины":
        await msg.answer("Список дисциплин:",reply_markup=await kb_return_discipline("info discipline"))
    elif msg.text=="Изменить дисциплину":
        await msg.answer("Список дисциплин:",reply_markup=await kb_return_discipline("update discipline"))
    elif msg.text=="Удалить дисциплину":
        await msg.answer("Нажмите дисциплину для удаления:",reply_markup=InlineKeyboardMarkup(inline_keyboard=await kb_return_discipline("discipline del")))
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
            await call.message.edit_text("Группа удалена!",reply_markup=ReplyKeyboardRemove())
        elif operation["choice_operation"]=="Удалить дисциплину":
            await db.delete_col("discipline", operation['discipline_id'])
            await call.message.edit_text("Дисциплина удалена!",reply_markup=ReplyKeyboardRemove())
        elif operation["choice_operation"]=="Удалить работу":
            await db.delete_col("works", operation['work_id'])
            await call.message.edit_text("Работа удалена!",reply_markup=ReplyKeyboardRemove())
        elif operation["choice_operation"]=="Удалить работу студента":
            await db.delete_col("works_student", operation['works_student_id'])
            await call.message.edit_text("Работа студента удалена!",reply_markup=ReplyKeyboardRemove())
    else:
        await call.message.edit_text("Группа не удалена!",reply_markup=ReplyKeyboardRemove())
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
    """,reply_markup=ReplyKeyboardRemove())
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
        await call.message.text_edit("Список работ:",
                         reply_markup=await kb_return_works(discipline_id,"student get work")
                        )
        await state.set_state(Table.get_work)
    elif data["choice_operation"]=="Добавить работу":
        await call.message.edit_text("Введите название работы:",reply_markup= ReplyKeyboardRemove())
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
    await call.message.edit_text("Выберите что хотите изменить",reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Название"),KeyboardButton(text="Файл")],
                   [KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    ))
    await state.set_state(Table.set_data)
@router.callback_query(F.data.regexp(r"update discipline \d+"))
async def update_disc(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.edit_text("Введите обновленное название дисциплины:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Table.set_data)

"""-------------------Проверка работ студентов------------------"""

@router.message(AdminFilter(),F.text=='Просмотреть работы 🔎')
async def view_works(msg:Message, state:FSMContext):
    await msg.answer("Выберите дисциплину:", reply_markup=await kb_return_discipline("discipline check work"))
    await state.update_data(choice_operation="Просмотреть работы")
    await state.set_state(CheckWork.choice_discipline)
@router.callback_query(CheckWork.choice_discipline,F.data.regexp(r"discipline check work \d+"))
async def callback_work(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    kb,data=await kb_retutn_students_work( discipline_id,"student check work")
    await state.update_data(discipline_id=discipline_id,student=data)
    await call.message.edit_text("Работы по дисциплине", reply_markup=kb )
    await state.set_state(CheckWork.choice_student)
@router.callback_query(CheckWork.choice_student, F.data.regexp(r"student check work \d+"))
async def callback_work(call:types.CallbackQuery, state:FSMContext,bot:Bot):
    id_student=int(call.data.split()[-1])
    data=await state.get_data()
    id_disciplite=data["discipline_id"]
    data=data["student"]
    await call.message.answer(f"Работы студента {data[id_student]['name']}({data[id_student]['group']}):")
    for work in data[id_student]["works"]:
        row=await db.return_student_work_none(id_disciplite,work)
        row=row[-1]
        file_input = FSInputFile(row["path"])
        await bot.send_document(call.message.chat.id,file_input ,
                caption=f"{row['name_work']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept {row['id']} {row['id_student']}"),
        InlineKeyboardButton(text="❌ Не принять", callback_data=f"reject {row['id']} {row['id_student']}")]
    ]))
    logging.debug("Отправлены работы!")
@router.callback_query(F.data.regexp(r"accept \d+ \d+"))
async def callback_accept(call:types.CallbackQuery, state:FSMContext,bot:Bot):
    id_work,id_student=map(int,call.data.split()[1:])
    await db.accept_work(id_work,True)
    #await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    #    [InlineKeyboardButton(text="✅ Принято", callback_data=f"")]]))
    data=await db.return_work_accept(id_work)
    work_name,discipline_name,path=data
    await bot.send_message(chat_id=id_student, text=f"Дисциплина: {discipline_name}\nРабота: {work_name}\nСтатус: ✅ Принята")
    await call.answer()
@router.callback_query(F.data.regexp(r"reject \d+ \d+"))
async def callback_reject(call:types.CallbackQuery, state:FSMContext, bot:Bot):
    id_work,id_student=map(int, call.data.split()[1:])
    await state.update_data(id_work=id_work,id_student=id_student)
    await db.accept_work(id_work, False)
    await call.message.answer("Введите комменторий к работе:")
    await state.set_state(CheckWork.check_work)
@router.message(AdminFilter(),CheckWork.check_work)
async def msg_reject(msg:Message, state:FSMContext, bot:Bot):
    data=await state.get_data()
    id_work,id_student=data["id_work"],data["id_student"]    
    data=await db.return_work_accept(id_work)
    work_name,discipline_name,path=data
    await bot.send_document(chat_id=id_student, document=FSInputFile(path), 
        caption=f"""
Дисциплина: {discipline_name}
Работа: {work_name}
Статус: ❌ Не принята
Комментарий {msg.text}""")
    msg.answer()

@router.message(AdminFilter(),F.text=="Отчет 📠")
async def report(msg:Message, state:FSMContext):
    await msg.answer("Выберите дисциплину:", reply_markup=await kb_return_discipline("discipline report"))
    await state.set_state(Report.choice_discipline)
@router.callback_query(F.data.regexp(r"discipline report \d+"))
async def callback_discipline(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.answer("Выберите группу:", reply_markup=await kb_return_group("group report"))
    await state.set_state(Report.choice_group)
