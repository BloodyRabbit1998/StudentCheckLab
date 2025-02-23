from aiogram.fsm.state import State, StatesGroup

class Student(StatesGroup):
    choice_Name=State()
    choice_Group=State()

class Table(StatesGroup):
    choice_table=State()
    choice_operation=State()
    set_data=State()
    repite=State()
    document=State()
class AddWork(StatesGroup):
    choice_discipline=State()
    choice_work=State()
    document=State()