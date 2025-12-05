# modes
MODE_IDLE = "IDLE"
MODE_ADD_CHANNEL = "ADD_CHANNEL"
MODE_COLLECT_POST = "COLLECT_POST"
MODE_ADD_URL_BUTTON = "ADD_URL_BUTTON"

# user_states[chat_id] = {
#   "mode": ...,
#   "channel_id": str,
#   "panel_id": int,
#   "buffer": [message_ids],
#   "buttons": [{"text": str, "url": str}]
# }

user_states = {}


def set_state(chat_id, mode, channel_id=None, panel_id=None, buffer=None, buttons=None):
    if buffer is None:
        buffer = []
    if buttons is None:
        buttons = []
    user_states[chat_id] = {
        "mode": mode,
        "channel_id": channel_id,
        "panel_id": panel_id,
        "buffer": buffer,
        "buttons": buttons,
    }


def get_state(chat_id):
    return user_states.get(chat_id)


def clear_state(chat_id):
    user_states.pop(chat_id, None)
