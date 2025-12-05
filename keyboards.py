from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import load_channels


def add_channel_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("+ Add Channel", callback_data="add_channel"))
    return kb


def main_menu_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("Create Post", callback_data="create_post"))
    kb.row(
        InlineKeyboardButton("Scheduled Posts", callback_data="scheduled_posts"),
        InlineKeyboardButton("Edit Post", callback_data="edit_post"),
    )
    kb.row(
        InlineKeyboardButton("Channel Stats", callback_data="channel_stats"),
        InlineKeyboardButton("Settings", callback_data="settings"),
    )
    return kb


def settings_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
        InlineKeyboardButton("🗑 Delete Channel", callback_data="delete_channel"),
    )
    kb.row(InlineKeyboardButton("« Back", callback_data="back_home"))
    return kb


def channels_keyboard():
    kb = InlineKeyboardMarkup()
    channels = load_channels()
    row = []
    for ch in channels:
        row.append(
            InlineKeyboardButton(
                ch["title"], callback_data=f"select_channel:{ch['id']}"
            )
        )
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.row(InlineKeyboardButton("« Back", callback_data="back_home"))
    return kb


def delete_channels_keyboard():
    kb = InlineKeyboardMarkup()
    channels = load_channels()
    row = []
    for ch in channels:
        row.append(
            InlineKeyboardButton(
                ch["title"], callback_data=f"remove_channel:{ch['id']}"
            )
        )
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.row(InlineKeyboardButton("« Back", callback_data="settings"))
    return kb


def post_builder_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("Attach Media", callback_data="attach_media"))
    kb.row(InlineKeyboardButton("Add URL Buttons", callback_data="add_url_buttons"))
    kb.row(InlineKeyboardButton("Delete Message", callback_data="delete_last_msg"))
    kb.row(InlineKeyboardButton("↓ Show Actions", callback_data="show_actions"))
    kb.row(
        InlineKeyboardButton("Delete All", callback_data="delete_all"),
        InlineKeyboardButton("Preview", callback_data="preview_post"),
        InlineKeyboardButton("Send", callback_data="send_post"),
    )
    return kb
