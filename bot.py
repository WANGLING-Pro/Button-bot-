import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram bot token env variable se lo
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable set nahi hai!")

bot = telebot.TeleBot(BOT_TOKEN)


def main_menu_keyboard() -> InlineKeyboardMarkup:
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


@bot.message_handler(commands=["start"])
def handle_start(message):
    first_name = message.from_user.first_name or "friend"

    text = (
        f"Hello {first_name}! 👋\n\n"
        "Here you can create rich posts, view stats and accomplish other tasks.\n\n"
        "Choose an option below:"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    if data == "create_post":
        bot.send_message(chat_id, "📝 Create Post → coming soon!")

    elif data == "scheduled_posts":
        bot.send_message(chat_id, "⏰ Scheduled posts → coming soon!")

    elif data == "edit_post":
        bot.send_message(chat_id, "✏ Edit Post → coming soon!")

    elif data == "channel_stats":
        bot.send_message(chat_id, "📊 Stats → coming soon!")

    elif data == "settings":
        bot.send_message(chat_id, "⚙ Settings → coming soon!")

    else:
        bot.send_message(chat_id, "❓ Unknown action.")


if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
