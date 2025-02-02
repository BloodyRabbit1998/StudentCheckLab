from sqlalchemy import (CheckConstraint,
                        String,
                        Date,
                        Time,
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

class Client(Base):
    __tablename__ = "Студенты"
    
    telegram_id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name:Mapped[str] = mapped_column(String)
    group:Mapped[str] = mapped_column(String)
    year_study:Mapped[int] = mapped_column(Integer)

class Discipline(Base):
    __tablename__ = "Дисциплины"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    name:Mapped[str] = mapped_column(String, unique=True)
class Works(Base):
    __tablename__ = "Работы"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    id_discipline:Mapped[int] = mapped_column(ForeignKey("Дисциплины.id"))
    name:Mapped[str] = mapped_column(String)
class WorksStudent(Base):
    __tablename__ = "Работы_Студентов"
    id:Mapped[int] = mapped_column(primary_key=True, index=True)
    id_student:Mapped[int] = mapped_column(ForeignKey("Студенты.telegram_id"))
    id_work:Mapped[int] = mapped_column(ForeignKey("Работы.id"))
    date_of_delivery:Mapped[Date] = mapped_column(Date)
    path:Mapped[str] = mapped_column(String)
    accept:Mapped[bool] = mapped_column(Boolean,)   


async def create_db():
    async with ENGINE.begin() as conn:
        #if input(":::Удалить БД?::: (y/n): ") == "y":
        #    await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
if __name__ == "__main__":
    import asyncio
    asyncio.run(create_db())
    