import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

CHANNELS_FILE = "channels.json"

# ========= SIMPLE USER STATE (memory) =========
# user_states[chat_id] = {"mode": "add_channel" / "create_post", "channel_id": "..."}
user_states = {}


def set_state(chat_id: int, mode: str, channel_id: str | None = None):
    user_states[chat_id] = {"mode": mode, "channel_id": channel_id}


def get_state(chat_id: int):
    return user_states.get(chat_id)


def clear_state(chat_id: int):
    user_states.pop(chat_id, None)


# ========= CHANNELS JSON HELPERS =========

def load_channels():
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            channels = data.get("channels", [])
            # ensure correct format
            clean = []
            for ch in channels:
                if isinstance(ch, dict) and "id" in ch and "title" in ch:
                    clean.append(ch)
            return clean
    except FileNotFoundError:
        return []
    except Exception:
        return []


def save_channels(channels: list[dict]):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump({"channels": channels}, f, ensure_ascii=False, indent=2)


def add_channel_to_json(ch_id: int, title: str):
    ch_id_str = str(ch_id)
    channels = load_channels()
    for ch in channels:
        if ch["id"] == ch_id_str:
            return  # already there
    channels.append({"id": ch_id_str, "title": title})
    save_channels(channels)


# ========= KEYBOARDS =========

def add_channel_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("+ Add Channel", callback_data="add_channel"))
    return kb


def settings_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("+ Add Channel", callback_data="add_channel"))
    kb.add(InlineKeyboardButton("« Back", callback_data="back_home"))
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


def channels_keyboard():
    channels = load_channels()
    kb = InlineKeyboardMarkup()

    # 2 buttons per row, title text
    row: list[InlineKeyboardButton] = []
    for idx, ch in enumerate(channels, start=1):
        btn = InlineKeyboardButton(
            ch["title"],
            callback_data=f"select_channel:{ch['id']}",
        )
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.row(InlineKeyboardButton("« Back", callback_data="back_home"))
    return kb


# ========= /start =========

@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    channels = load_channels()

    if not channels:
        # No channels → force add first
        msg = bot.send_message(
            chat_id,
            "📌 <b>Please add a channel to continue.</b>",
            reply_markup=add_channel_keyboard(),
        )
        return

    first = message.from_user.first_name or "Friend"
    bot.send_message(
        chat_id,
        f"Hello <b>{first}</b>! 👋\n\n"
        "Here you can create rich posts, view stats and accomplish other tasks.\n\n"
        "Choose an option below:",
        reply_markup=main_menu_keyboard(),
    )


# ========= CALLBACKS =========

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    data = call.data

    bot.answer_callback_query(call.id)

    if data == "add_channel":
        # Purana message delete
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

        set_state(chat_id, "add_channel")

        bot.send_message(
            chat_id,
            "➡ Add this bot as <b>Admin (full rights)</b> in your channel.\n\n"
            "➡ Then <b>forward any one message</b> from that channel to me.",
        )
        return

    if data == "settings":
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        bot.send_message(
            chat_id,
            "⚙ <b>Settings</b>",
            reply_markup=settings_keyboard(),
        )
        return

    if data == "back_home":
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        # show main menu (channels must exist already)
        bot.send_message(
            chat_id,
            "🏠 Main menu:",
            reply_markup=main_menu_keyboard(),
        )
        clear_state(chat_id)
        return

    if data == "create_post":
        channels = load_channels()
        if not channels:
            bot.send_message(
                chat_id,
                "❌ No channel added yet.",
                reply_markup=add_channel_keyboard(),
            )
            return

        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

        bot.send_message(
            chat_id,
            "📌 <b>Select a channel to create a new post:</b>",
            reply_markup=channels_keyboard(),
        )
        return

    if data.startswith("select_channel:"):
        # user chose one channel
        channel_id = data.split(":", 1)[1]

        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

        set_state(chat_id, "create_post", channel_id=channel_id)

        bot.send_message(
            chat_id,
            "📝 <b>Send the post content now:</b>\n"
            "You can send text, photo, video, document, etc.",
        )
        return

    if data == "scheduled_posts":
        bot.send_message(chat_id, "⏰ Scheduled posts → coming soon!")
        return

    if data == "edit_post":
        bot.send_message(chat_id, "✏ Edit Post → coming soon!")
        return

    if data == "channel_stats":
        bot.send_message(chat_id, "📊 Channel stats → coming soon!")
        return


# ========= MESSAGE HANDLER =========

@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "video",
        "document",
        "animation",
        "audio",
        "voice",
        "video_note",
        "sticker",
    ]
)
def handle_messages(message):
    chat_id = message.chat.id
    state = get_state(chat_id)

    # 1) User is adding channel via forward
    if state and state["mode"] == "add_channel":
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            ch = message.forward_from_chat
            add_channel_to_json(ch.id, ch.title or str(ch.id))

            clear_state(chat_id)

            bot.send_message(
                chat_id,
                f"✅ Channel <b>{ch.title or ch.id}</b> added successfully!",
                reply_markup=main_menu_keyboard(),
            )
            return
        else:
            bot.send_message(
                chat_id,
                "❌ Please forward a <b>message from a channel</b> only.",
            )
            return

    # 2) User is sending content for Create Post
    if state and state["mode"] == "create_post":
        channel_id = state["channel_id"]
        sent = False

        try:
            if message.content_type == "text":
                bot.send_message(channel_id, message.text)
                sent = True

            elif message.content_type == "photo":
                file_id = message.photo[-1].file_id
                bot.send_photo(
                    channel_id,
                    file_id,
                    caption=message.caption,
                )
                sent = True

            elif message.content_type == "video":
                bot.send_video(
                    channel_id,
                    message.video.file_id,
                    caption=message.caption,
                )
                sent = True

            elif message.content_type == "document":
                bot.send_document(
                    channel_id,
                    message.document.file_id,
                    caption=message.caption,
                )
                sent = True

            elif message.content_type == "animation":
                bot.send_animation(
                    channel_id,
                    message.animation.file_id,
                    caption=message.caption,
                )
                sent = True

            elif message.content_type == "audio":
                bot.send_audio(
                    channel_id,
                    message.audio.file_id,
                    caption=message.caption,
                )
                sent = True

            elif message.content_type == "voice":
                bot.send_voice(
                    channel_id,
                    message.voice.file_id,
                )
                sent = True

            elif message.content_type == "video_note":
                bot.send_video_note(
                    channel_id,
                    message.video_note.file_id,
                )
                sent = True

            elif message.content_type == "sticker":
                bot.send_sticker(
                    channel_id,
                    message.sticker.file_id,
                )
                sent = True

        except Exception as e:
            bot.send_message(
                chat_id,
                f"⚠️ Failed to send message to channel.\n<code>{e}</code>",
            )

        if sent:
            bot.send_message(chat_id, "✅ Post sent successfully!")
        else:
            bot.send_message(
                chat_id,
                "❌ This message type is not supported yet.",
            )

        clear_state(chat_id)
        return

    # 3) Normal messages (no active state)
    # yaha tum kuch default behavior rakh sakte ho, abhi ignore kar dete hain
    # bot.send_message(chat_id, "Use /start to use the menu.")
    return


# ========= RUN =========

if __name__ == "__main__":
    print("Bot started with polling...")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)    kb.add(InlineKeyboardButton("« Back", callback_data="back_home"))
    return kb


def main_menu_keyboard():
    kb = InlineKeyboardMarkup()

    kb.row(InlineKeyboardButton("Create Post", callback_data="create_post"))

    kb.row(
        InlineKeyboardButton("Scheduled Posts", callback_data="scheduled_posts"),
        InlineKeyboardButton("Edit Post", callback_data="edit_post")
    )

    kb.row(
        InlineKeyboardButton("Channel Stats", callback_data="channel_stats"),
        InlineKeyboardButton("Settings", callback_data="settings")
    )
    return kb


# ---------------- START COMMAND ----------------

@bot.message_handler(commands=["start"])
def start(message):
    channels = load_channels()

    if len(channels) == 0:
        bot.send_message(
            message.chat.id,
            "📌 *Please add a channel to continue.*",
            parse_mode="Markdown",
            reply_markup=add_channel_keyboard()
        )
        return

    # If channel exists → show Main Menu
    first = message.from_user.first_name or "Friend"
    bot.send_message(
        message.chat.id,
        f"Hello {first}! 👋\n\nHere you can create rich posts, view stats and accomplish other tasks.\n\nChoose an option below:",
        reply_markup=main_menu_keyboard()
    )


# ---------------- CALLBACK HANDLERS ----------------

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = call.data
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if data == "add_channel":
        bot.send_message(
            chat_id,
            "➡ Add this bot as *Admin (full rights)* in your channel.\n\n"
            "➡ Then *forward* any one message from that channel to me.",
            parse_mode="Markdown"
        )
        bot.set_state(chat_id, "waiting_for_channel")
        return

    if data == "settings":
        bot.send_message(chat_id, "⚙ *Settings*", parse_mode="Markdown", reply_markup=settings_keyboard())
        return

    if data == "back_home":
        start(call.message)
        return

    if data == "create_post":
        channels = load_channels()
        if len(channels) == 0:
            bot.send_message(chat_id, "❌ No channel added yet!", reply_markup=add_channel_keyboard())
            return

        kb = InlineKeyboardMarkup()
        for ch in channels:
            kb.add(InlineKeyboardButton(ch, callback_data=f"select_channel_{ch}"))

        kb.add(InlineKeyboardButton("« Back", callback_data="back_home"))
        bot.send_message(chat_id, "📌 Select a channel to post:", reply_markup=kb)
        return

    if data.startswith("select_channel_"):
        channel_id = data.replace("select_channel_", "")
        bot.set_state(chat_id, "waiting_for_post", channel_id)
        bot.send_message(chat_id, "📝 Send the post content now:")
        return

    if data == "scheduled_posts":
        bot.send_message(chat_id, "⏳ Scheduled posts → coming soon!")
        return

    if data == "edit_post":
        bot.send_message(chat_id, "✏ Edit Post → coming soon!")
        return

    if data == "channel_stats":
        bot.send_message(chat_id, "📊 Channel stats → coming soon!")
        return


# ---------------- MESSAGE HANDLER ----------------

@bot.message_handler(func=lambda m: True)
def forward_handler(message):
    state = bot.get_state(message.chat.id)

    # User is adding a channel
    if state == "waiting_for_channel":
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            ch_id = message.forward_from_chat.id
            channels = load_channels()

            if str(ch_id) not in channels:
                channels.append(str(ch_id))
                save_channels(channels)

            bot.send_message(
                message.chat.id,
                f"✅ Channel *{ch_id}* added successfully!",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            bot.delete_state(message.chat.id)
            return

        bot.send_message(message.chat.id, "❌ Please forward a *channel message* only!", parse_mode="Markdown")
        return

    # User is sending post content
    if isinstance(state, dict) and state.get("state") == "waiting_for_post":
        channel = state["data"]
        bot.send_message(channel, message.text)
        bot.send_message(message.chat.id, "✅ Post sent successfully!")
        bot.delete_state(message.chat.id)
        return


# ---------------- RUN BOT ----------------

bot.infinity_polling(skip_pending=True)
