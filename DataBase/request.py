from .models import *
from sqlalchemy import select,update,delete

async def return_group(col:int|str):
    async with SESSION() as db: 
        if type(col)==int:
            stmt=select(Group).where(Group.id==col)
        else:
            stmt=select(Group).where(Group.name==col)
        cols=await db.scalars(stmt)
    logging.debug(cols)
    cols=[col for col in cols]
    return cols[-1] if cols else None

async def return_student(col:int|str):
    async with SESSION() as db: 
        if type(col)==int:
            stmt=select(Student).where(Student.telegram_id==col)
        else:
            stmt=select(Student).where(Student.name==col)
        cols=await db.scalars(stmt)
    logging.debug(cols)
    return [col for col in cols]

async def return_discipline(col:int|str,**kwargs):
    if kwargs:
        if "id_group" in kwargs:
            stmt=select(Discipline).where(Discipline.id_group==kwargs["id_group"])
    else:
        if type(col)==int:
            stmt=select(Discipline).where(Discipline.id==col)
        else:
            stmt=select(Discipline).where(Discipline.name==col)
    async with SESSION() as db:
        cols=await db.scalars(stmt)
    logging.debug(cols)
    return [col for col in cols]

async def return_work(id:int,**kwargs):
    if kwargs:
        if "id_discipline" in kwargs:
            stmt=select(Works).where(Works.id_discipline==kwargs["id_discipline"])
        elif "name" in kwargs:
            stmt=select(Works).where(Works.name==kwargs["name"])
    else:
        stmt=select(Works).where(Works.id==id)
            
    async with SESSION() as db:
        cols=await db.scalars(stmt)
    logging.debug(cols)
    return [col for col in cols]
async def return_works_student(col:int|Student):
    async with SESSION() as db:
        if type(col)==int:
            stmt=select(WorksStudent).where(WorksStudent.id==col)
        else:
            stmt=select(WorksStudent).where(WorksStudent.id_student==Student.telegram_id)
        cols=await db.scalars(stmt)
    logging.debug(cols)
    return [col for col in cols]
async def check_work(id_student:int,id_work:int):
    async with SESSION() as db:
        stmt=select(WorksStudent).where(WorksStudent.id_student==id_student and WorksStudent.id_work==id_work)
        cols=await db.scalars(stmt)
    logging.debug(cols)
    return [col for col in cols]

async def add(table:str,data:list[tuple]):  
    """
    Group: id,name,yeat_study
    Student: telegram_id,name,id_group
    Discipline: name,id_group
    Works: name,id_discipline
    WorksStudent: id_student,id_work,date_of_delivery,path,accept
    """
    cols=[]
    if table=="student":               
            cols=[Student(telegram_id=telegram_id,name=name,id_group=id_group) for telegram_id,name,id_group in data if not await return_student(telegram_id)]
    elif table=="group":
        cols=[Group(name=name) for name in data if not await return_group(name)]
    elif table=="discipline":
        cols=[Discipline(name=name,id_group=id_group) for name,id_group in data if not await return_discipline(name)]
    elif table=="works":
        cols=[Works(id_discipline=id_discipline,name=name,path=path) for name,id_discipline,path in data]
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
async def delete_col(table:str,ids:int|list[int]):
    if table=="student":
        if type(ids)==int:
            stmts=[delete(Student).where(Student.id==ids)]  
        else: 
            stmts=[delete(Student).where(Student.id==id) for id in ids]
    elif table=="group":
        if type(ids)==int:
            stmts=[delete(Group).where(Group.id==ids)]   
        else: 
            stmts=[delete(Group).where(Group.id==id) for id in ids]
    elif table=="discipline":
        if type(ids)==int:
            stmts=[delete(Discipline).where(Discipline.id==ids)]   
        else: 
            stmts=[delete(Discipline).where(Discipline.id==id) for id in ids]
    elif table=="works":
        if type(ids)==int:
            stmts=[delete(Works).where(Works.id==ids)]  
        else: 
            stmts=[delete(Works).where(Works.id==id) for id in ids]
    elif table=="works_student":
        if type(ids)==int:
            stmts=[delete(WorksStudent).where(WorksStudent.id==ids)]   
        else:
            stmts=[delete(WorksStudent).where(WorksStudent.id==id) for id in ids]
    async with SESSION() as db:
        for stmt in stmts:
            db.execute(stmt) 
            await db.commit()
async def update_col(table:str,data:tuple):
    """
    Group: id,name
    Student: id,telegram_id,name,id_group
    Discipline:id, name,id_group
    Works: id,name,id_discipline
    WorksStudent: id,id_student,id_work,date_of_delivery,path,accept
    """
    cols=[]
    if table=="student":
        id,telegram_id,name,id_group=data
        stmt=update(Student).where(Student.id==id).values(telegram_id=telegram_id,name=name,id_group=id_group)
    elif table=="group":
        id,name=data
        stmt=update(Group).where(Group.id==id).values(name=name)
    elif table=="discipline":
        id,name,id_group=data
        stmt=update(Discipline).where(Discipline.id==id).values(name=name, id_group=id_group)
    elif table=="works":
        id,name,id_discipline,path=data
        stmt=update(Works).where(Works.id==id).values(name=name, id_discipline=id_discipline, path=path)
    elif table=="works_student":
        stmt=update(WorksStudent).where(WorksStudent.id==data[0]).values(id_student=data[1],id_work=data[2],date_of_delivery=data[3],path=data[4],accept=data[5])
    else:
        logging.INFO("Такой таблицы не существует!")
    async with SESSION() as db:
            logging.debug(cols)
            await db.execute(stmt)
            logging.info("Обновлен!")
            await db.commit()
async def return_all(table:str):
    if table=="student":
        stmt=select(Student)
    elif table=="group":
        stmt=select(Group)
    elif table=="discipline":
        stmt=select(Discipline)
    elif table=="works":
        stmt=select(Works)
    elif table=="works_student":
        stmt=select(WorksStudent)
    async with SESSION() as db:
        return await db.scalars(stmt)

if __name__=="__main__":
    with SESSION() as db:
        print(db.query(Student).all())