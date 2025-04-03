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
    get_work=State()
class AddWork(StatesGroup):
    choice_discipline=State()
    choice_work=State()
    document=State()
class CheckWork(StatesGroup):
    choice_discipline=State()
    choice_student=State()
    choice_work=State()
    check_work=State()
class Report(StatesGroup):
    choice_discipline=State()
    choice_group=State()
