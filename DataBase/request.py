"""
Утилиты для работы с базой данных
содержит функции для получения, добавления, удаления и обновления данных в базе данных.
Структура таблиц:
    Group: 
        id,
        name,
        year_study
    Student: 
        telegram_id,
        name,id_group
    Discipline: 
        name,
        id_group
    Works:
        name,
        id_discipline
    WorksStudent:
        id_student,
        id_work,
        date_of_delivery,
        path,
        accept
"""

from .models import *
from sqlalchemy import select,update,delete,func

async def return_group(row:int|str)->Group:
    """
    Возвращает объект группы по идентификатору или названию.

    Args:
        row: Идентификатор группы (int) или её название (str).

    Returns:
        Group | None: Объект группы или None, если группа не найдена.
    """
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
    """
    Возвращает список студентов по telegram_id или имени.

    Args:
        row: Telegram ID студента (int) или его имя (str).

    Returns:
        list[Student]: Список объектов студентов (может быть пустым).
    """
    async with SESSION() as db: 
        if type(row)==int:
            stmt=select(Student).where(Student.telegram_id==row)
        else:
            stmt=select(Student).where(Student.name==row)
        rows=await db.scalars(stmt)
    logging.debug(rows)
    return [row for row in rows]

async def return_discipline(row:int|str,**kwargs)->list[Discipline]:
    '''
    Возвращает список дисциплин по id, названию или id группы.

    Args:
        row: Идентификатор дисциплины (int) или её название (str).
        **kwargs: Дополнительные фильтры. Поддерживается "id_group" (int) —
            вернуть все дисциплины указанной группы.

    Returns:
        list[Discipline]: Список объектов дисциплин (может быть пустым).
    '''
    if kwargs:
        if "id_group" in kwargs:
            stmt=select(Discipline).where(Discipline.id_group==kwargs["id_group"])
        else:
            return []
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
    '''
    Возвращает работу или список работ.

    Args:
        id: Идентификатор работы (используется, если kwargs пусты).
        **kwargs: Дополнительные фильтры. Поддерживаются:
            - "id_discipline" (int) — вернуть все работы дисциплины;
            - "name" (str) — вернуть работу по названию.

    Returns:
        list[Works]: Список объектов работ. При поиске по id возвращается
        список с одним последним найденным объектом (или пустой список).
    '''
    if kwargs:
        if "id_discipline" in kwargs:
            stmt=select(Works).where(Works.id_discipline==kwargs["id_discipline"])
        elif "name" in kwargs:
            stmt=select(Works).where(Works.name==kwargs["name"])
        else:
            return []
    else:
        stmt=select(Works).where(Works.id==id)
            
    async with SESSION() as db:
        rows=await db.scalars(stmt)
    logging.debug(rows)
    result=[row for row in rows]
    return result if kwargs else (result[-1:] if result else [])

async def check_work(id_student:int,id_work:int)->list[WorksStudent]:
    '''
    Возвращает записи работы студента по id студента и id работы.

    Args:
        id_student: Telegram ID студента.
        id_work: Идентификатор работы.

    Returns:
        list[WorksStudent]: Список объектов WorksStudent (может быть пустым).
    '''
    async with SESSION() as db:
        stmt=select(WorksStudent).where(WorksStudent.id_student==id_student).where(WorksStudent.id_work==id_work)
        rows=await db.scalars(stmt)
    logging.debug(rows)
    return [row for row in rows]

async def add(table:str,data:list[tuple])->list:  
    """
    Добавляет записи в указанную таблицу (если duplicates отсутствуют).

    Args:
        table: Название таблицы ("student", "group", "discipline",
            "works", "works_student").
        data: Список кортежей с данными для вставки. Состав кортежа зависит
            от таблицы:

            Group:          (name,)
            Student:        (telegram_id, name, id_group)
            Discipline:     (name, id_group)
            Works:          (name, id_discipline, path)
            WorksStudent:   (id_student, id_work, date_of_delivery, path, accept)

    Returns:
        list: Список созданных ORM-объектов (может быть пустым, если все
            записи уже существовали).

    Структура таблиц:
        Group: id, name, year_study
        Student: telegram_id, name, id_group
        Discipline: name, id_group
        Works: name, id_discipline
        WorksStudent: id_student, id_work, date_of_delivery, path, accept
    """
    rows=[]
    if table=="student":               
        rows=[Student(telegram_id=telegram_id,name=name,id_group=id_group) for telegram_id,name,id_group in data if not await return_student(telegram_id)]
    elif table=="group":
        rows=[Group(name=name) for (name,) in data if not await return_group(name)]
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
                await update_col("works_student",(work[0].id,id_student,id_work,date_of_delivery,path,True if work[0].accept else None))
                rows.append(work[0])
    async with SESSION() as db:  
        try:
            if rows:
                db.add_all(rows)
                await db.commit()
        except Exception:
            await db.rollback()
            raise
    return rows
async def delete_col(table:str,ids:int|list[int])->None:
    """
    Удаляет записи из указанной таблицы по одному или нескольким id.

    Args:
        table: Название таблицы ("student", "group", "discipline",
            "works", "works_student").
        ids: Один идентификатор (int) или список идентификаторов (list[int])
            для удаления.

    Returns:
        None
    """
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
        try:
            for stmt in stmts:
                await db.execute(stmt) 
            await db.commit()
        except Exception:
            await db.rollback()
            raise
async def update_col(table:str,data:tuple)->None:
    """
    Обновляет запись в указанной таблице.

    Args:
        table: Название таблицы ("student", "group", "discipline",
            "works", "works_student").
        data: Кортеж со значениями для обновления. Состав кортежа зависит
            от таблицы:

            Group:          (id, name)
            Student:        (telegram_id, name, id_group)
            Discipline:     (id, name, id_group)
            Works:          (id, name, id_discipline, path)
            WorksStudent:   (id, id_student, id_work, date_of_delivery, path, accept)

    Returns:
        None

    Структура таблиц:
        Group: id, name
        Student: telegram_id, name, id_group
        Discipline: id, name, id_group
        Works: id, name, id_discipline
        WorksStudent: id, id_student, id_work, date_of_delivery, path, accept
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
        logging.info("Такой таблицы не существует!")
        return
    async with SESSION() as db:
        try:
            logging.debug(f"Обновление данных таблицы: {table}")
            await db.execute(stmt)
            logging.info("Обновлен!")
            await db.commit()
        except Exception:
            await db.rollback()
            raise
async def accept_work(id:int, accept:bool):
    """
    Отмечает работу студента как принятую или не принятую.

    Args:
        id: Идентификатор записи WorksStudent.
        accept: Флаг принятия работы (True/False).

    Returns:
        None
    """
    stmt=update(WorksStudent).where(WorksStudent.id==id).values(accept=accept)
    async with SESSION() as db:
        try:
            await db.execute(stmt)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
async def return_work_accept(id):
    """
    Возвращает данные работы студента по id записи WorksStudent.

    Args:
        id: Идентификатор записи WorksStudent.

    Returns:
        Row: Строка с полями work_name, discipline_name, path.
        None, если запись не найдена.
    """
    stmt=select(Works.name.label("work_name"),
                Discipline.name.label("discipline_name"),
                WorksStudent.path.label("path")
                ).join(Discipline,Works.id_discipline==Discipline.id
                ).join(WorksStudent,Works.id==WorksStudent.id_work
    ).where(WorksStudent.id==id)
    async with SESSION() as db:
        rows=await db.execute(stmt)
    logging.debug("получены данные работы студента!")
    result=[row for row in rows]
    return result[-1] if result else None
async def return_all(table:str)->list:
    """
    Возвращает все записи из указанной таблицы.

    Args:
        table: Название таблицы ("student", "group", "discipline",
            "works", "works_student").

    Returns:
        list: Список всех объектов таблицы.
    """
    if table=="student":
        stmt=select(Student).order_by(Student.name)
    elif table=="group":
        stmt=select(Group).order_by(Group.name)
    elif table=="discipline":
        stmt=select(Discipline)
    elif table=="works":
        stmt=select(Works).order_by(Works.name)
    elif table=="works_student":
        stmt=select(WorksStudent)
    async with SESSION() as db:
        return [row for row in await db.scalars(stmt)]

async def return_student_work_none(id_discipline:int,id_student:int=None)->list:
    """
    Возвращает не принятые работы студентов по дисциплине.

    Args:
        discipline_id: Идентификатор дисциплины.
        id_student: Telegram ID студента (опционально). Если указан, возвращаются
            только работы этого студента; иначе — все не принятые работы по дисциплине.

    Returns:
        list | dict:
            - при указанном id_student: список словарей с полями id, id_work, path,
              id_student, name_work;
            - при отсутствии id_student: словарь, где ключ — id_student, значение —
              results = [
                          {
                              "id_student": row.id_student,
                              "name": row.name_student,
                              "group": row.group_name,
                              "count": row.count,
                          }
    """
    
    if id_student:
        stmt = select(
            WorksStudent.id.label("id"),
            WorksStudent.id_work.label("id_work"),
            WorksStudent.path.label("path"),
            WorksStudent.id_student.label("id_student"),
            Works.name.label("name_work"), 
                ).join(Works, WorksStudent.id_work == Works.id
                ).where(WorksStudent.id_student == id_student and WorksStudent.accept == None and Works.id_discipline == id_discipline,
                ).order_by(Works.name)
    else:
        stmt = select(
            WorksStudent.id_student.label("id_student"),
            Student.name.label("name_student"),
            Group.name.label("group_name"),
            func.count(WorksStudent.id_student).label('count')
                ).join(WorksStudent, Student.telegram_id==WorksStudent.id_student
                ).join(Works, WorksStudent.id_work == Works.id
                ).join(Group, Student.id_group==Group.id
                ).where(WorksStudent.accept == None,Works.id_discipline == id_discipline
                ).group_by( 
                    Student.telegram_id,
                    Student.name,
                    Group.name,
                    WorksStudent.id_student
                ).order_by(Student.name)
    async with SESSION() as db:
        rows=await db.execute(stmt)
    logging.debug("Данные работ студентов успешно получены!")
    if id_student:
        results=[
            {
                "id":row.id,
                "name_work":row.name_work,
                "path":row.path,
                "id_student":row.id_student,
                "name_work":row.name_work}
        for row in rows]
    else:
        results = [
            {
                "id_student": row.id_student,
                "name": row.name_student,
                "group": row.group_name,
                "count": row.count,
            }
            for row in rows
]
    return results
async def return_work_student(id_work:int)-> dict:
    '''
    return {
            'id':rows.id,
            'id_student':rows.id_student,
            'id_work':rows.id_work,
            'date_of_delivery':rows.date_of_delivery,
            'path':rows.path,
            'accept':rows.accept
            }
    '''
    
    stmt=select(
            WorksStudent.id.label("id_work"),
            WorksStudent.id_student.label("id_student"),
            Student.name.label("name_student"),
            Works.name.label("work_name"),
            Group.name.label("group_name"),
            Discipline.name.label("discipline_name")
                ).join(WorksStudent, Student.telegram_id==WorksStudent.id_student
                ).join(Works, WorksStudent.id_work == Works.id
                ).join(Group, Student.id_group==Group.id
                ).join(Discipline,Works.id_discipline==Discipline.id
                ).where(WorksStudent.id == id_work
                )
    async with SESSION() as db:
        row=await db.execute(stmt)
    return {
        'id_work':rows.id_work,
        'id_student':rows.id_student,
        'name_student':rows.name_student,
        'group_name':rows.group_name,
        'discipline_name':rows.discipline_name,
        'work_name':rows.work_name
        }
        
async def return_submitted_works(discipline_id:int, group_id:int=None)->list:
    """
    Возвращает все сданные работы по дисциплине (опционально по группе).

    Args:
        discipline_id: Идентификатор дисциплины.
        group_id: Идентификатор группы (опционально).

    Returns:
        list: Список строк с полями student_name, group_name, discipline_name,
              work_name, date, accept, path.
    """
    stmt = select(
        Student.name.label("student_name"),
        Group.name.label("group_name"),
        Discipline.name.label("discipline_name"),
        Works.name.label("work_name"),
        WorksStudent.date_of_delivery.label("date"),
        WorksStudent.accept.label("accept"),
        WorksStudent.path.label("path"),
    ).join(WorksStudent, Student.telegram_id == WorksStudent.id_student
    ).join(Works, WorksStudent.id_work == Works.id
    ).join(Group, Student.id_group == Group.id
    ).join(Discipline, Works.id_discipline == Discipline.id
    ).where(Works.id_discipline == discipline_id)

    if group_id:
        stmt = stmt.where(Student.id_group == group_id)

    stmt = stmt.order_by(Student.name, Works.name)

    async with SESSION() as db:
        rows = await db.execute(stmt)
    return rows.all()


if __name__=="__main__":
    import asyncio

    async def main():
        async with SESSION() as db:
            result = await db.execute(select(Student))
            print(result.scalars().all())

    asyncio.run(main())