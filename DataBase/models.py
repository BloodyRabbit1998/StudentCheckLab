from sqlalchemy import (
                        String,
                        Date,
                        Boolean,
                        Integer,
                        BigInteger,
                        ForeignKey)
from sqlalchemy.orm import (DeclarativeBase,
                            Mapped,
                            mapped_column,
                            relationship)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine 
from config import URL_SQL
import logging

ENGINE = create_async_engine(URL_SQL, echo=True)
SESSION = async_sessionmaker(ENGINE)

class Base(AsyncAttrs,DeclarativeBase): pass
class Group(Base):
    __tablename__ = "Группы"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    name:Mapped[str] = mapped_column(String, unique=True)
    def __str__(self):
        return f"{self.id} \t|\t{self.name}"
class Student(Base):
    __tablename__ = "Студенты"
    
    telegram_id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name:Mapped[str] = mapped_column(String)
    id_group:Mapped[int] = mapped_column(ForeignKey("Группы.id"))
    year_study:Mapped[int] = mapped_column(Integer)
    def __str__(self):
        return f"{self.telegram_id} \t|\t{self.name} \t|\t{self.id_group} \t|\t{self.year_study}"
class Discipline(Base):
    __tablename__ = "Дисциплины"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    name:Mapped[str] = mapped_column(String, unique=True)
    id_group:Mapped[int] = mapped_column(ForeignKey("Группы.id"))
    def __str__(self):
        return f"{self.id} \t|\t{self.name} \t|\t{self.id_group}"
class Works(Base):
    __tablename__ = "Работы"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    name:Mapped[str] = mapped_column(String)
    id_discipline:Mapped[int] = mapped_column(ForeignKey("Дисциплины.id"))
    def __str__(self):
        return f"{self.id} \t|\t{self.name} \t|\t{self.id_discipline}"
class WorksStudent(Base):
    __tablename__ = "Работы_Студентов"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    id_student:Mapped[int] = mapped_column(ForeignKey("Студенты.telegram_id"))
    id_work:Mapped[int] = mapped_column(ForeignKey("Работы.id"))
    date_of_delivery:Mapped[Date] = mapped_column(Date)
    path:Mapped[str] = mapped_column(String)
    accept:Mapped[bool] = mapped_column(Boolean,)   
    def __str__(self):
        return f"{self.id} \t|\t{self.id_student} \t|\t{self.id_work} \t|\t{self.date_of_delivery} \t|\t{self.path} \t|\t{self.accept}"

async def create_db():
    async with ENGINE.begin() as conn:
        #if input(":::Удалить БД?::: (y/n): ") == "y":
        #    await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        logging.info(" > База данных успешно создана!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(create_db())
    