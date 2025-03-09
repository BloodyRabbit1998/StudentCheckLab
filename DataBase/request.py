from .models import *
from sqlalchemy import select,update,delete
from sqlalchemy.sql.expression import func
async def return_group(row:int|str)->Group:
    async with SESSION() as db: 
        if type(row)==int:
            stmt=select(Group).where(Group.id==row)
        else:
            stmt=select(Group).where(Group.name==row)
        rows=await db.scalars(stmt)
    logging.debug(rows)
    rows=[row for row in rows]
    return rows[-1] if rows else None

async def return_student(row:int|str)->list[Student]:
    async with SESSION() as db: 
        if type(row)==int:
            stmt=select(Student).where(Student.telegram_id==row)
        else:
            stmt=select(Student).where(Student.name==row)
        rows=await db.scalars(stmt)
    logging.debug(rows)
    return [row for row in rows]

async def return_discipline(row:int|str,**kwargs)->list[Discipline]:
    if kwargs:
        if "id_group" in kwargs:
            stmt=select(Discipline).where(Discipline.id_group==kwargs["id_group"])
    else:
        if type(row)==int:
            stmt=select(Discipline).where(Discipline.id==row)
        else:
            stmt=select(Discipline).where(Discipline.name==row)
    async with SESSION() as db:
        rows=await db.scalars(stmt)
    logging.debug(rows)
    return [row for row in rows]

async def return_work(id:int,**kwargs)->list[Works]:
    if kwargs:
        if "id_discipline" in kwargs:
            stmt=select(Works).where(Works.id_discipline==kwargs["id_discipline"])
        elif "name" in kwargs:
            stmt=select(Works).where(Works.name==kwargs["name"])
    else:
        stmt=select(Works).where(Works.id==id)
            
    async with SESSION() as db:
        rows=await db.scalars(stmt)
    logging.debug(rows)
    return [row for row in rows]

async def check_work(id_student:int,id_work:int)->list[WorksStudent]:
    async with SESSION() as db:
        stmt=select(WorksStudent).where(WorksStudent.id_student==id_student).where(WorksStudent.id_work==id_work)
        rows=await db.scalars(stmt)
    logging.debug(rows)
    return [row for row in rows]

async def add(table:str,data:list[tuple])->list:  
    """
    Group: id,name,yeat_study
    Student: telegram_id,name,id_group
    Discipline: name,id_group
    Works: name,id_discipline
    WorksStudent: id_student,id_work,date_of_delivery,path,accept
    """
    rows=[]
    if table=="student":               
            rows=[Student(telegram_id=telegram_id,name=name,id_group=id_group) for telegram_id,name,id_group in data if not await return_student(telegram_id)]
    elif table=="group":
        rows=[Group(name=name) for name in data if not await return_group(name)]
    elif table=="discipline":
        rows=[Discipline(name=name,id_group=id_group) for name,id_group in data if not await return_discipline(name)]
    elif table=="works":
        rows=[Works(id_discipline=id_discipline,name=name,path=path) for name,id_discipline,path in data]
    elif table=="works_student":
        rows=[]
        for id_student,id_work,date_of_delivery,path,accept in data:
            work=await check_work(id_student,id_work)
            if not work:
                rows.append(WorksStudent(id_student=id_student,id_work=id_work,date_of_delivery=date_of_delivery,path=path,accept=accept))
            else:
                await update_col("works_student",(work[0].id,id_student,id_work,date_of_delivery,path,accept))
    async with SESSION() as db:  
        if rows:
            db.add_all(rows)
            await db.commit()
    return rows
async def delete_col(table:str,ids:int|list[int])->None:
    if table=="student":
        if type(ids)==int:
            stmts=[delete(Student).where(Student.telegram_id==ids)]  
        else: 
            stmts=[delete(Student).where(Student.telegram_id==id) for id in ids]
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
async def update_col(table:str,data:tuple)->None:
    """
    Group: id,name
    Student: telegram_id,name,id_group
    Discipline:id, name,id_group
    Works: id,name,id_discipline
    WorksStudent: id,id_student,id_work,date_of_delivery,path,accept
    """
    if table=="student":
        telegram_id,name,id_group=data
        stmt=update(Student).where(Student.telegram_id==telegram_id).values(telegram_id=telegram_id,name=name,id_group=id_group)
    elif table=="group":
        id,name=data
        stmt=update(Group).where(Group.id==id).values(name=name)
    elif table=="discipline":
        id,name=data
        stmt=update(Discipline).where(Discipline.id==id).values(name=name)
    elif table=="works":
        id,name,id_discipline,path=data
        stmt=update(Works).where(Works.id==id).values(name=name, id_discipline=id_discipline, path=path)
    elif table=="works_student":
        stmt=update(WorksStudent).where(WorksStudent.id==data[0]).values(id_student=data[1],id_work=data[2],date_of_delivery=data[3],path=data[4],accept=data[5])
    else:
        logging.INFO("Такой таблицы не существует!")
    async with SESSION() as db:
            logging.debug(f"Обновление данных таблицы: {table}")
            await db.execute(stmt)
            logging.info("Обновлен!")
            await db.commit()
async def return_all(table:str)->list:
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
        return [row for row in await db.scalars(stmt)]
async def retutn_works_student_all(id_student:int, id_discipline:int=None)->list:
    if id_discipline:
        stmt=select(
            WorksStudent.id,Works.name,WorksStudent.accept
            ).join(Works,WorksStudent.id_work==Works.id
            ).where(WorksStudent.id_student==id_student,Works.id_discipline==id_discipline)
    else:
        stmt=select(WorksStudent.id).where(WorksStudent.id_student==id_student)
    async with SESSION() as db:
        rows=await db.execute(stmt)
    logging.debug("получены данные работ студентов!")
    return [row for row in rows]

async def return_student_work_none(discipline_id:int,id_student:int=None)->list:
    """ if id_student:  
            return id_work,name_student,group.name,count
        else:
            return """
    if id_student:
        stmt = select(
            WorksStudent.id_work.label("id_work"),
            Works.name.label("name_work"), 
                ).join(WorksStudent, WorksStudent.id_student == Student.telegram_id
                ).join(Works, WorksStudent.id_work == Works.id
                ).join(Group, Student.id_group==Group.id
                ).where(Works.id_discipline == discipline_id,
                        WorksStudent.accept == None,
                        Student.telegram_id == id_student
                ).group_by(Student.name, WorksStudent.id_work
                ).order_by(Student.name)

    else:
        stmt = select(
            WorksStudent.id_work.label("id_work"),
            Student.name.label("name_student"),
            Group.name.label("group_name"),
            func.count(WorksStudent.id_work).label("count")
                ).join(WorksStudent, WorksStudent.id_student == Student.telegram_id
                ).join(Works, WorksStudent.id_work == Works.id
                ).join(Group, Student.id_group==Group.id
                ).where(WorksStudent.accept == None
                ).where(Works.id_discipline == discipline_id
                ).order_by(Student.name)

    async with SESSION() as db:
        rows=await db.execute(stmt)
    logging.debug("получены данные работ студентов!")
    return [row for row in rows]

if __name__=="__main__":
    with SESSION() as db:
        print(db.query(Student).all())