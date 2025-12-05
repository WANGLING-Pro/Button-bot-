import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

CHANNELS_FILE = "channels.json"


# ========= SIMPLE USER STATE =========
user_states = {}


def set_state(chat_id: int, mode: str, channel_id: str | None = None):
    user_states[chat_id] = {"mode": mode, "channel_id": channel_id}


def get_state(chat_id: int):
    return user_states.get(chat_id)


def clear_state(chat_id: int):
    user_states.pop(chat_id, None)


# ========= CHANNELS JSON =========

def load_channels():
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("channels", [])
    except:
        return []


def save_channels(channels: list[dict]):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump({"channels": channels}, f, indent=2, ensure_ascii=False)


def add_channel_to_json(ch_id: int, title: str):
    channels = load_channels()
    ch_id = str(ch_id)

    for c in channels:
        if c["id"] == ch_id:
            return

    channels.append({"id": ch_id, "title": title})
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
    kb = InlineKeyboardMarkup()
    channels = load_channels()

    row = []
    for c in channels:
        row.append(InlineKeyboardButton(c["title"], callback_data=f"select_channel:{c['id']}"))
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
        bot.send_message(
            chat_id,
            "📌 <b>Please add a channel to continue.</b>",
            reply_markup=add_channel_keyboard(),
        )
        return

    name = message.from_user.first_name or "Friend"
    bot.send_message(
        chat_id,
        f"Hello <b>{name}</b>! 👋\n\n"
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
        bot.delete_message(chat_id, msg_id)
        set_state(chat_id, "add_channel")
        bot.send_message(
            chat_id,
            "➡ Add the bot as <b>Admin (full rights)</b> in your channel.\n\n"
            "➡ Then forward <b>any one message</b> from that channel here."
        )
        return

    if data == "settings":
        bot.delete_message(chat_id, msg_id)
        bot.send_message(chat_id, "⚙ <b>Settings</b>", reply_markup=settings_keyboard())
        return

    if data == "back_home":
        bot.delete_message(chat_id, msg_id)
        clear_state(chat_id)
        bot.send_message(chat_id, "🏠 Main menu:", reply_markup=main_menu_keyboard())
        return

    if data == "create_post":
        channels = load_channels()
        if not channels:
            bot.send_message(chat_id, "❌ No channels yet!", reply_markup=add_channel_keyboard())
            return

        bot.delete_message(chat_id, msg_id)
        bot.send_message(
            chat_id,
            "📌 <b>Select a channel to create a new post:</b>",
            reply_markup=channels_keyboard(),
        )
        return

    if data.startswith("select_channel:"):
        channel_id = data.split(":", 1)[1]
        bot.delete_message(chat_id, msg_id)
        set_state(chat_id, "create_post", channel_id)
        bot.send_message(chat_id, "📝 <b>Send your post content now.</b>")
        return

    # Coming soon buttons
    if data in ["scheduled_posts", "edit_post", "channel_stats"]:
        bot.send_message(chat_id, "⏳ Coming soon!")
        return


# ========= MESSAGE HANDLER =========

@bot.message_handler(content_types=[
    "text", "photo", "video", "document", "animation",
    "audio", "voice", "video_note", "sticker"
])
def handle_messages(message):
    chat_id = message.chat.id
    state = get_state(chat_id)

    # Add Channel
    if state and state["mode"] == "add_channel":
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            ch = message.forward_from_chat
            add_channel_to_json(ch.id, ch.title or str(ch.id))

            clear_state(chat_id)
            bot.send_message(
                chat_id,
                f"✅ Channel <b>{ch.title or ch.id}</b> added!",
                reply_markup=main_menu_keyboard(),
            )
        else:
            bot.send_message(chat_id, "❌ Please forward a valid channel message.")
        return

    # Create Post
    if state and state["mode"] == "create_post":
        ch_id = state["channel_id"]
        try:
            if message.content_type == "text":
                bot.send_message(ch_id, message.text, parse_mode="HTML")

            elif message.content_type == "photo":
                bot.send_photo(ch_id, message.photo[-1].file_id, caption=message.caption)

            elif message.content_type == "video":
                bot.send_video(ch_id, message.video.file_id, caption=message.caption)

            elif message.content_type == "document":
                bot.send_document(ch_id, message.document.file_id, caption=message.caption)

            elif message.content_type == "animation":
                bot.send_animation(ch_id, message.animation.file_id, caption=message.caption)

            elif message.content_type == "audio":
                bot.send_audio(ch_id, message.audio.file_id, caption=message.caption)

            elif message.content_type == "voice":
                bot.send_voice(ch_id, message.voice.file_id)

            elif message.content_type == "video_note":
                bot.send_video_note(ch_id, message.video_note.file_id)

            elif message.content_type == "sticker":
                bot.send_sticker(ch_id, message.sticker.file_id)

            bot.send_message(chat_id, "✅ Post sent successfully!")

        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Failed:\n<code>{e}</code>")

        clear_state(chat_id)
        return


# ========= DUMMY WEB SERVER (RENDER FIX) =========

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot running!")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}")
    httpd.serve_forever()


threading.Thread(target=run_server).start()


# ========= START BOT =========

print("Bot started with polling...")
bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
