import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from storage import load_channels, add_channel, remove_channel, get_channel
from keyboards import (
    add_channel_keyboard,
    main_menu_keyboard,
    settings_keyboard,
    channels_keyboard,
    delete_channels_keyboard,
    post_builder_keyboard,
)
from states import (
    MODE_ADD_CHANNEL,
    MODE_COLLECT_POST,
    MODE_ADD_URL_BUTTON,
    set_state,
    get_state,
    clear_state,
)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


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
    # panel_id = sent.message_id if ever needed


# ========= CALLBACKS =========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    data = call.data

    bot.answer_callback_query(call.id)

    state = get_state(chat_id)

    # ----- Add Channel start -----
    if data == "add_channel":
        bot.edit_message_text(
            "➡ Add this bot as <b>Admin (full rights)</b> in your channel.\n\n"
            "➡ Then forward <b>any one message</b> from that channel here.",
            chat_id,
            msg_id,
        )
        set_state(chat_id, MODE_ADD_CHANNEL, panel_id=msg_id)
        return

    # ----- Settings -----
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
                "❌ No channels to delete.\n\nUse <b>Add Channel</b> first.",
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
                "✅ Channel removed.\n\nNo channels left, please add a new channel.",
                chat_id,
                msg_id,
                reply_markup=add_channel_keyboard(),
            )
        else:
            title = ch["title"] if ch else ch_id
            bot.edit_message_text(
                f"✅ Channel <b>{title}</b> removed.\n\nMore options:",
                chat_id,
                msg_id,
                reply_markup=settings_keyboard(),
            )
        clear_state(chat_id)
        return

    # ----- Back to home -----
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

    # ----- Create Post flow -----
    if data == "create_post":
        channels = load_channels()
        if not channels:
            bot.edit_message_text(
                "❌ No channels yet.\n\nPlease add a channel first.",
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

        set_state(
            chat_id,
            MODE_COLLECT_POST,
            channel_id=channel_id,
            panel_id=msg_id,
            buffer=[],
            buttons=[],
        )
        return

    # ===== POST BUILDER BUTTONS =====
    state = get_state(chat_id)

    if data == "attach_media":
        bot.answer_callback_query(
            call.id, "Just send media/messages below. They will be added.", show_alert=False
        )
        return

    if data == "add_url_buttons":
        if not state or state["mode"] != MODE_COLLECT_POST:
            bot.answer_callback_query(call.id, "No active post.", show_alert=True)
            return
        bot.answer_callback_query(
            call.id,
            "Send button in this format:\n\nButton text | https://example.com",
            show_alert=True,
        )
        set_state(
            chat_id,
            MODE_ADD_URL_BUTTON,
            channel_id=state["channel_id"],
            panel_id=state["panel_id"],
            buffer=state["buffer"],
            buttons=state["buttons"],
        )
        return

    if data == "delete_last_msg":
        if not state or state["mode"] not in [MODE_COLLECT_POST, MODE_ADD_URL_BUTTON]:
            return
        if not state["buffer"]:
            bot.answer_callback_query(call.id, "No messages to delete.", show_alert=False)
            return
        last_id = state["buffer"].pop()
        try:
            bot.delete_message(chat_id, last_id)
        except Exception:
            pass
        bot.answer_callback_query(call.id, "Last message removed.", show_alert=False)
        return

    if data == "delete_all":
        if not state or state["mode"] not in [MODE_COLLECT_POST, MODE_ADD_URL_BUTTON]:
            return
        for mid in state["buffer"]:
            try:
                bot.delete_message(chat_id, mid)
            except Exception:
                pass
        state["buffer"].clear()
        bot.answer_callback_query(call.id, "All messages cleared.", show_alert=False)
        return

    if data == "preview_post":
        if not state or state["mode"] not in [MODE_COLLECT_POST, MODE_ADD_URL_BUTTON]:
            bot.answer_callback_query(call.id, "Nothing to preview.", show_alert=True)
            return
        count = len(state["buffer"])
        btn_count = len(state["buttons"])
        bot.answer_callback_query(
            call.id,
            f"Preview:\nMessages: {count}\nButtons: {btn_count}",
            show_alert=True,
        )
        return

    if data == "send_post":
        if not state or state["mode"] not in [MODE_COLLECT_POST, MODE_ADD_URL_BUTTON]:
            bot.answer_callback_query(call.id, "No post to send.", show_alert=True)
            return

        channel_id = state["channel_id"]
        buffer = state["buffer"]
        buttons = state["buttons"]

        if not buffer and not buttons:
            bot.answer_callback_query(call.id, "Post is empty.", show_alert=True)
            return

        # 1) copy messages to channel
        for mid in buffer:
            try:
                bot.copy_message(channel_id, chat_id, mid)
            except Exception as e:
                print("Copy error:", e)

        # 2) if URL buttons hain → ek extra message with inline keyboard
        if buttons:
            kb = InlineKeyboardMarkup()
            for b in buttons:
                kb.add(InlineKeyboardButton(b["text"], url=b["url"]))
            bot.send_message(channel_id, "🔗 Buttons:", reply_markup=kb)

        bot.edit_message_text(
            "✅ Post sent successfully!\n\nBack to main menu:",
            chat_id,
            state["panel_id"],
            reply_markup=main_menu_keyboard(),
        )
        clear_state(chat_id)
        return

    if data == "show_actions":
        bot.answer_callback_query(
            call.id,
            "Use Delete All / Preview / Send below.",
            show_alert=False,
        )
        return

    # place-holders
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

    # ---- Add Channel ----
    if state and state["mode"] == MODE_ADD_CHANNEL:
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            ch = message.forward_from_chat
            add_channel(ch.id, ch.title or str(ch.id))

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

    # ---- URL Button input ----
    if state and state["mode"] == MODE_ADD_URL_BUTTON:
        text = message.text or ""
        if "|" not in text:
            bot.send_message(
                chat_id,
                "❌ Wrong format.\nUse: <code>Button text | https://example.com</code>",
            )
            return
        label, url = [x.strip() for x in text.split("|", 1)]
        if not label or not url:
            bot.send_message(chat_id, "❌ Text or URL missing.")
            return

        state["buttons"].append({"text": label, "url": url})
        # back to collect mode
        set_state(
            chat_id,
            MODE_COLLECT_POST,
            channel_id=state["channel_id"],
            panel_id=state["panel_id"],
            buffer=state["buffer"],
            buttons=state["buttons"],
        )
        bot.send_message(
            chat_id,
            f"✅ Button added: <b>{label}</b>\nNow continue sending post content.",
        )
        return

    # ---- Collect post messages ----
    if state and state["mode"] == MODE_COLLECT_POST:
        state["buffer"].append(message.message_id)
        bot.send_message(
            chat_id,
            f"✅ Saved ({len(state['buffer'])}) message(s) for this post.\n"
            "Tap <b>Send</b> when you are ready.",
        )
        return

    # else: ignore / help
    # bot.send_message(chat_id, "Use /start to open menu.")
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


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print("Bot started with polling...")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
