import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
CHANNELS_FILE = "channels.json"

# user_states[chat_id] = {
#   "mode": "add_channel" / "collect_post",
#   "channel_id": "...",
#   "panel_id": int,
#   "buffer": [message_id, ...]
# }
user_states = {}


# ========= STATE HELPERS =========
def set_state(chat_id, mode, channel_id=None, panel_id=None, buffer=None):
    if buffer is None:
        buffer = []
    user_states[chat_id] = {
        "mode": mode,
        "channel_id": channel_id,
        "panel_id": panel_id,
        "buffer": buffer,
    }


def get_state(chat_id):
    return user_states.get(chat_id)


def clear_state(chat_id):
    user_states.pop(chat_id, None)


# ========= CHANNEL JSON HELPERS =========
def load_channels():
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            channels = data.get("channels", [])
            clean = []
            for ch in channels:
                if isinstance(ch, dict) and "id" in ch and "title" in ch:
                    clean.append(ch)
            return clean
    except Exception:
        return []


def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump({"channels": channels}, f, indent=2, ensure_ascii=False)


def add_channel(ch_id, title):
    ch_id = str(ch_id)
    channels = load_channels()
    for ch in channels:
        if ch["id"] == ch_id:
            return
    channels.append({"id": ch_id, "title": title})
    save_channels(channels)


def remove_channel(ch_id):
    ch_id = str(ch_id)
    channels = load_channels()
    new_list = [ch for ch in channels if ch["id"] != ch_id]
    save_channels(new_list)


def get_channel(ch_id):
    ch_id = str(ch_id)
    for ch in load_channels():
        if ch["id"] == ch_id:
            return ch
    return None


# ========= KEYBOARDS =========
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


# ========= /start =========
@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    channels = load_channels()

    if not channels:
        text = (
            "📌 <b>Please add a channel to continue.</b>\n\n"
            "Click the button below to add your first channel."
        )
        kb = add_channel_keyboard()
    else:
        first = message.from_user.first_name or "User"
        text = (
            f"Hello <b>{first}</b>! 👋\n\n"
            "Here you can create rich posts, view stats and manage channels.\n\n"
            "<b>Choose an option below:</b>"
        )
        kb = main_menu_keyboard()

    sent = bot.send_message(chat_id, text, reply_markup=kb)
    clear_state(chat_id)
    # we don't strictly need panel_id here, callbacks ke time mil jayega


# ========= CALLBACKS =========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    data = call.data

    bot.answer_callback_query(call.id)

    # ---- Add Channel ----
    if data == "add_channel":
        bot.edit_message_text(
            "➡ Add this bot as <b>Admin (full rights)</b> in your channel.\n\n"
            "➡ Then forward <b>any one message</b> from that channel here.",
            chat_id,
            msg_id,
        )
        set_state(chat_id, "add_channel", panel_id=msg_id)
        return

    # ---- Settings ----
    if data == "settings":
        bot.edit_message_text(
            "⚙ <b>Settings</b>\nManage your connected channels:",
            chat_id,
            msg_id,
            reply_markup=settings_keyboard(),
        )
        clear_state(chat_id)
        return

    if data == "delete_channel":
        channels = load_channels()
        if not channels:
            bot.edit_message_text(
                "❌ No channels to delete.\n\n"
                "Use <b>Add Channel</b> to connect one.",
                chat_id,
                msg_id,
                reply_markup=settings_keyboard(),
            )
            return

        bot.edit_message_text(
            "🗑 <b>Select a channel to remove:</b>",
            chat_id,
            msg_id,
            reply_markup=delete_channels_keyboard(),
        )
        return

    if data.startswith("remove_channel:"):
        ch_id = data.split(":", 1)[1]
        ch = get_channel(ch_id)
        remove_channel(ch_id)

        channels = load_channels()
        if not channels:
            bot.edit_message_text(
                f"✅ Channel removed.\n\n"
                "No channels left. Please add a new channel to continue.",
                chat_id,
                msg_id,
                reply_markup=add_channel_keyboard(),
            )
        else:
            bot.edit_message_text(
                f"✅ Channel <b>{ch['title'] if ch else ch_id}</b> removed.\n\n"
                "You can manage more channels below:",
                chat_id,
                msg_id,
                reply_markup=settings_keyboard(),
            )
        clear_state(chat_id)
        return

    # ---- Back to Home ----
    if data == "back_home":
        channels = load_channels()
        if not channels:
            bot.edit_message_text(
                "📌 <b>Please add a channel to continue.</b>",
                chat_id,
                msg_id,
                reply_markup=add_channel_keyboard(),
            )
        else:
            bot.edit_message_text(
                "🏠 <b>Main Menu</b>\nChoose an option:",
                chat_id,
                msg_id,
                reply_markup=main_menu_keyboard(),
            )
        clear_state(chat_id)
        return

    # ---- Create Post ----
    if data == "create_post":
        channels = load_channels()
        if not channels:
            bot.edit_message_text(
                "❌ No channels added yet.\n\n"
                "Please add a channel first.",
                chat_id,
                msg_id,
                reply_markup=add_channel_keyboard(),
            )
            return

        bot.edit_message_text(
            "📌 <b>Choose a channel to create a new post.</b>",
            chat_id,
            msg_id,
            reply_markup=channels_keyboard(),
        )
        clear_state(chat_id)
        return

    if data.startswith("select_channel:"):
        channel_id = data.split(":", 1)[1]
        ch = get_channel(channel_id)
        title = ch["title"] if ch else channel_id

        text = (
            f'Here it is: <b>"{title}"</b>.\n\n'
            "Send me one or multiple messages you want to include in the post.\n"
            "It can be anything — a text, photo, video, even a sticker."
        )
        bot.edit_message_text(
            text,
            chat_id,
            msg_id,
            reply_markup=post_builder_keyboard(),
        )

        set_state(chat_id, "collect_post", channel_id=channel_id, panel_id=msg_id, buffer=[])
        return

    # ---- Post Builder Buttons ----
    state = get_state(chat_id)

    if data in ["attach_media", "add_url_buttons", "delete_last_msg", "show_actions"]:
        # Abhi ke liye sirf help text
        bot.answer_callback_query(
            call.id,
            "Just send messages below. They will be part of the post.",
            show_alert=False,
        )
        return

    if data == "delete_all":
        if state and state["mode"] == "collect_post":
            state["buffer"] = []
            bot.answer_callback_query(call.id, "Cleared all collected messages.")
        return

    if data == "preview_post":
        if not state or state["mode"] != "collect_post":
            bot.answer_callback_query(call.id, "Nothing to preview.", show_alert=False)
            return

        count = len(state["buffer"])
        bot.answer_callback_query(
            call.id,
            f"You have {count} message(s) in this post.",
            show_alert=True,
        )
        return

    if data == "send_post":
        if not state or state["mode"] != "collect_post":
            bot.answer_callback_query(call.id, "No post to send.", show_alert=True)
            return

        channel_id = state["channel_id"]
        buffer = state["buffer"]

        if not buffer:
            bot.answer_callback_query(call.id, "You haven't sent any message.", show_alert=True)
            return

        # Copy all collected messages to the channel
        for mid in buffer:
            try:
                bot.copy_message(channel_id, chat_id, mid)
            except Exception as e:
                print("Copy error:", e)

        bot.edit_message_text(
            "✅ Post sent successfully!\n\nBack to main menu:",
            chat_id,
            state["panel_id"],
            reply_markup=main_menu_keyboard(),
        )
        clear_state(chat_id)
        return

    # ---- Other menu buttons (placeholders) ----
    if data in ["scheduled_posts", "edit_post", "channel_stats"]:
        bot.answer_callback_query(call.id, "Coming soon…", show_alert=False)
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

    # ---- Add Channel flow ----
    if state and state["mode"] == "add_channel":
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            ch = message.forward_from_chat
            add_channel(ch.id, ch.title or str(ch.id))

            # Panel ko main menu me change karo
            try:
                bot.edit_message_text(
                    f"✅ Channel <b>{ch.title or ch.id}</b> added successfully!\n\n"
                    "Now you can create posts or manage channels.",
                    chat_id,
                    state["panel_id"],
                    reply_markup=main_menu_keyboard(),
                )
            except Exception:
                bot.send_message(
                    chat_id,
                    f"✅ Channel <b>{ch.title or ch.id}</b> added successfully!",
                    reply_markup=main_menu_keyboard(),
                )

            clear_state(chat_id)
        else:
            bot.send_message(
                chat_id,
                "❌ Please forward a <b>message from a channel</b> only.",
            )
        return

    # ---- Collect post content ----
    if state and state["mode"] == "collect_post":
        # Sirf collect, kuch send nahi karte abhi
        state["buffer"].append(message.message_id)
        # thoda feedback de sakte ho:
        bot.send_message(
            chat_id,
            f"✅ Saved ({len(state['buffer'])}) message(s) for this post.\n"
            "Tap <b>Send</b> when you are ready.",
        )
        return

    # No active state → ignore / or help
    # bot.send_message(chat_id, "Use /start to open the menu.")
    return


# ========= DUMMY WEB SERVER FOR RENDER =========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot running")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}")
    server.serve_forever()


# ========= START =========
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print("Bot started with polling...")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
