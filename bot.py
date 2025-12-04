import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)


# ---------------- JSON FILE HANDLER ----------------

def load_channels():
    try:
        with open("channels.json", "r") as f:
            data = json.load(f)
            return data.get("channels", [])
    except:
        return []


def save_channels(channels):
    with open("channels.json", "w") as f:
        json.dump({"channels": channels}, f, indent=4)


# ---------------- KEYBOARDS ----------------

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
