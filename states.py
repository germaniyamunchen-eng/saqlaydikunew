from aiogram.fsm.state import State, StatesGroup


class MusicStates(StatesGroup):
    waiting_for_query = State()


class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    confirming = State()
