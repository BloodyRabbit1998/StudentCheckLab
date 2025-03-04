from aiogram import types, F, Router,Bot
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile
from aiogram.filters import Command,CommandStart
from aiogram.fsm.context import FSMContext 
from states import *
from config import *
from .keyboard import *
import DataBase.request as db
from aiogram.types import ( InlineKeyboardButton, 
                            InlineKeyboardMarkup, 
                            KeyboardButton, 
                            ReplyKeyboardMarkup, 
                            ReplyKeyboardRemove,
                            )
from pathlib import Path
from datetime import datetime
router=Router()
@router.message(CommandStart())
@router.message(Command('start'),F.text.in_(["start","Start","Старт"]))
async def start(msg:Message,state:FSMContext):
    await msg.answer(msg_student_start) 
    if not await db.return_student(msg.from_user.id):
        await msg.answer("Вы не зарегестрированы! Необходимо пройти регистрацию.")
        await msg.answer("Введите вашу фамилию и имя полностью:",reply_markup=ReplyKeyboardRemove())
        await state.set_state(Student.choice_Name)
@router.message(Student.choice_Name)
async def set_name(msg:Message, state:FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Выберите вашу группу:", reply_markup=await kb_return_group("student sel group"))
    await state.set_state(Student.choice_Group)
@router.message(Command('menu'))
async def menu(msg:Message):
    await msg.answer("Панель управления", reply_markup=kb_student_main)
@router.callback_query(F.data.regexp(r"student sel group \d+"),Student.choice_Group)
async def callback_group(call:types.CallbackQuery, state:FSMContext):
    group_id=int(call.data.split()[-1])
    await state.update_data(group_id=group_id)
    data=await state.get_data()
    if await db.return_student(call.from_user.id):
        await db.update_col("student", (call.from_user.id, data['name'], group_id))
        await call.message.answer("Вы успешно обновили данные!")
    else:  
        await db.add("student", [(call.from_user.id,data['name'], data['group_id'] )])
        await call.message.answer("Вы успешно зарегестрированы!")
    await state.clear()
    await menu(call.message)
@router.message(Command("registration"))
async def registration(msg:Message,state:FSMContext):
    await msg.answer("Введите вашу фамилию и имя полностью:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Student.choice_Name)
@router.message(F.text=="Сдать работу🧾")
async def send_work(msg:Message, state:FSMContext):
    await state.clear()
    await msg.answer("Выберите дисциплину:",reply_markup=await kb_return_disciplin_id("discipline sel student",msg.from_user.id))
    await state.set_state(AddWork.choice_discipline)
@router.callback_query(F.data.regexp(r"discipline sel student \d+"),AddWork.choice_discipline)
async def callback_discipline(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.answer("Выберите работу:", reply_markup=await kb_return_works(discipline_id,"student sel work"))
    await state.set_state(AddWork.choice_work)
@router.callback_query(F.data.regexp(r"student sel work \d+"),AddWork.choice_work)
async def callback_discipline(call:types.CallbackQuery, state:FSMContext):
    work_id=int(call.data.split()[-1])
    await state.update_data(work_id=work_id)
    await call.message.answer("Отправьте файл:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отменить отправку❌")]],resize_keyboard=True))
    await state.set_state(AddWork.document)
@router.message(AddWork.document, F.text.in_(["Отменить отправку❌"]))
async def cancel_send(msg:Message, state:FSMContext):
    await msg.answer("Отменено!", reply_markup=kb_student_main)
    await state.clear()
@router.message(AddWork.document, F.document)
async def add_document(msg:Message,state:FSMContext,bot:Bot):
    data=await state.get_data()
    student=await db.return_student(msg.from_user.id)
    group=await db.return_group(student[-1].id_group)
    work=await db.return_work(data['work_id'])
    disc=await db.return_discipline(data['discipline_id'])
    path= Path(__file__).parent.parent /"files"/"documents"/"works students"/f"{group.name}"/disc[-1].name/student[-1].name
    path=path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    path/=f'{work[-1].name}.{msg.document.file_name.split(".")[-1] if "." in msg.document.file_name else "file"}'
    path=path.resolve()
    await bot.download(file=msg.document, destination=path)
    await db.add("works_student", [(msg.from_user.id, data['work_id'],datetime.now(),str(path),None)])
    await msg.answer("Работа отправлена!")
    await menu(msg)
    await state.clear()
@router.message(F.text=="Получить работу👁‍🗨")
async def get_work(msg:Message, state:FSMContext):
    await state.clear()
    await msg.answer("Выберите дисциплину:", reply_markup=await kb_return_disciplin_id("discipline sel get work",msg.from_user.id))
    await state.set_state(AddWork.choice_discipline)

@router.callback_query(F.data.regexp(r"discipline sel get work \d+"),AddWork.choice_discipline)
async def callback_discipline(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.answer("Выберите работу:", reply_markup=await kb_return_works(discipline_id, "student get work"))
    await state.set_state(AddWork.choice_work)
@router.callback_query(F.data.regexp(r"student get work \d+"), AddWork.choice_work)
async def callback_document(call:types.CallbackQuery, state:FSMContext,bot:Bot):
    work_id=int(call.data.split()[-1])
    await state.update_data(work_id=work_id)
    data=await state.get_data()
    work=await db.return_work(data['work_id'])
    if work[-1].path:
        file_input = FSInputFile(work[-1].path)
        await bot.send_document(
            call.message.chat.id, file_input,
            caption=f'{work[-1].name}')
    else:
        await call.message.answer("Файл не загружен!")

@router.message(F.text=="Список моих работ")
async def get_work(msg:Message, state:FSMContext):
    await state.clear()
    await msg.answer("Выберите дисциплину:", reply_markup=await kb_return_disciplin_id("discipline sel student for works", msg.from_user.id))
    await state.set_state(AddWork.choice_discipline)
@router.callback_query(F.data.regexp(r"discipline sel student for works \d+"), AddWork.choice_discipline)
async def callback_discipline(call:types.CallbackQuery, state:FSMContext):
    discipline_id=int(call.data.split()[-1])
    await state.update_data(discipline_id=discipline_id)
    await call.message.answer("✅ - работа принята\n❌-работа не принята\n🕖-работа на расмотрении\nСписок работ:", 
                              reply_markup=await kb_return_student_works(call.from_user.id, discipline_id,"work student"))
    await state.clear()
    await menu(call.message)