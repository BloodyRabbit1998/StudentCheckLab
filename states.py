from aiogram.fsm.state import State, StatesGroup

class Student(StatesGroup):
    choice_Name=State()
    choice_Group=State()

class Lab(StatesGroup):
    choice_semester=State()
    choice_discipline=State()
    choice_number_state=State()
