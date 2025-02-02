from .models import *
from sqlalchemy import select
from datetime import datetime

def f_date(date:str):
    return datetime.strptime(date,"%d-%m-%Y")
def f_time(time:str):
    return datetime.strptime(time,"%H:%M")

async def return_group(col:int|str):
    async with SESSION() as db: 
        if type(col)==int:
            stmt=select(Group).where(Group.id==col)
        else:
            stmt=select(Group).where(Group.name==col)
        cols=await db.scalars(stmt)
    logging.DEBUG(cols)
    return [col for col in cols]

async def return_student(col:int|str):
    async with SESSION() as db: 
        if type(col)==int:
            stmt=select(Student).where(Student.telegram_id==col)
        else:
            stmt=select(Student).where(Student.name==col)
        cols=await db.scalars(stmt)
    logging.DEBUG(cols)
    return [col for col in cols]

async def return_discipline(col:int|str):
    async with SESSION() as db:    
        if type(col)==int:
            stmt=select(Discipline).where(Discipline.id==col)
        else:
            stmt=select(Discipline).where(Discipline.name==col)
        cols=await db.scalars(stmt)
    logging.DEBUG(cols)
    return [col for col in cols]

async def return_work(id:int):
    async with SESSION() as db:
        stmt=select(Works).where(Works.id==id)
        cols=await db.scalars(stmt)
    logging.DEBUG(cols)
    return [col for col in cols]
async def return_works_student(col:int|Student):
    async with SESSION() as db:
        if type(col)==int:
            stmt=select(WorksStudent).where(WorksStudent.id==col)
        else:
            stmt=select(WorksStudent).where(WorksStudent.id_student==Student.telegram_id)
        cols=await db.scalars(stmt)
    logging.DEBUG(cols)
    return [col for col in cols]
async def check_work(id_student:int,id_work:int):
    async with SESSION() as db:
        stmt=select(WorksStudent).where(WorksStudent.id_student==id_student and WorksStudent.id_work==id_work)
        cols=await db.scalars(stmt)
    logging.DEBUG(cols)
    return [col for col in cols]

async def add(table:str,data:list[tuple]):  
    cols=[]
    if table=="student":               
            cols=[Student(telegram_id=telegram_id,name=name,id_group=id_group,year_study=year_study) for telegram_id,name,id_group,year_study in data if not await return_student(telegram_id)]
    elif table=="group":
        cols=[Group(name=name) for name in data if not await return_group(name)]
    elif table=="discipline":
        cols=[Discipline(name=name,id_group=id_group) for name,id_group in data if not await return_discipline(name)]
    elif table=="works":
        cols=[Works(id_discipline=id_discipline,name=name) for name,id_discipline in data if not await return_work(name)]
    elif table=="works_student":
        cols=[]
        for id_student,id_work,date_of_delivery,path,accept in data:
            work=await check_work(id_student,id_work)
            if not work:
                cols.append(WorksStudent(id_student=id_student,id_work=id_work,date_of_delivery=date_of_delivery,path=path,accept=accept))
            else:
                await update("works_student",[(work[0].id,id_student,id_work,date_of_delivery,path,accept)])
    async with SESSION() as db:  
        if cols:
            db.add_all(cols)
            await db.commit()
    return cols
async def delete(table:str,ids:list[tuple]):
    cols=[]
    if table=="student":
        cols=[await return_student(telegram_id) for telegram_id in ids]
    elif table=="group":
        cols=[await return_group(id) for id in ids]
    elif table=="discipline":
        cols=[await return_discipline(id) for id in ids]
    elif table=="works":
        cols=[await return_work(id) for id in ids]
    elif table=="works_student":
        cols=[await return_works_student(id) for id in ids]
    async with SESSION() as db:
        if cols:
            db.delete(cols)
            await db.commit()
    return cols
async def update(table:str,data:list[tuple]):
    cols=[]
    if table=="student":
        cols=[await return_student(telegram_id) for telegram_id,_,_,_, in data]
        for student,data in zip(cols,data):
            if student.name != data[1]      : student.name=data[1] 
            if student.id_group!=data[2]    : student.id_group=data[2]    
            if student.year_study!=data[3]  : student.year_study=data[3]

    elif table=="group":
        cols=[await return_group(id) for id,_ in data]
        for group,data in zip(cols,data):
            if group.name!=data[1]          : group.name=data[1]
    elif table=="discipline":
        cols=[await return_discipline(id) for id in data]
        for discipline,data in zip(cols,data):
            if discipline.name!=data[1]     : discipline.name=data[1]
            if discipline.id_group!=data[2] : discipline.id_group=data[2]
    elif table=="works":
        cols=[await return_work(id) for id in data]
        for work,data in zip(cols,data):
            if work.name!=data[1]           : work.name=data[1]
            if work.id_discipline!=data[2]  : work.id_discipline=data[2]   
    elif table=="works_student":
        cols=[await return_works_student(id) for id in data]
        for work_student,data in zip(cols,data):
            if work_student.id_student!=data[1]         : work_student.id_student=data[1]
            if work_student.id_work!=data[2]            : work_student.id_work=data[2]
            if work_student.date_of_delivery!=data[3]   : work_student.date_of_delivery=data[3]
            if work_student.path!=data[4]               : work_student.path=data[4]
            if work_student.accept!=data[5]             : work_student.accept=data[5]
    else:
        logging.INFO("Такой таблицы не существует!")
    async with SESSION() as db:
        if cols:
            logging.debug(cols)
            logging.info("Обновлен!")
            await db.commit()
    return cols
if __name__=="__main__":
    with SESSION() as db:
        print(db.query(Student).all())