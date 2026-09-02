from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = "YOUR_BOT_TOKEN"

# শুধু তোমার Telegram User ID এখানে বসাও
# /myid command দিয়ে ID বের করতে পারবে
ADMIN_ID = 123456789

# Conversation states
CHANNEL, POST, BUTTONS, BUTTON_NAME, BUTTON_URL = range(5)


# ==================================================
# /start
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return

    await update.message.reply_text(
        "🤖 Bot Ready!\n\n"
        "/post - নতুন পোস্ট তৈরি করুন\n"
        "/myid - আপনার Telegram ID দেখুন\n"
        "/cancel - বর্তমান কাজ বন্ধ করুন"
    )


# ==================================================
# /myid
# ==================================================

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"🆔 Your Telegram ID:\n\n{update.effective_user.id}"
    )


# ==================================================
# /post
# ==================================================

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return ConversationHandler.END

    context.user_data["buttons"] = []

    await update.message.reply_text(
        "📢 কোন Channel-এ পোস্ট করবেন?\n\n"
        "Channel username দিন। Example:\n"
        "@mychannel\n\n"
        "অথবা channel ID:\n"
        "-1001234567890"
    )

    return CHANNEL


# ==================================================
# CHANNEL
# ==================================================

async def get_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    channel = update.message.text.strip()

    context.user_data["channel"] = channel

    await update.message.reply_text(
        "📝 এখন পোস্টের সম্পূর্ণ লেখা পাঠান:"
    )

    return POST


# ==================================================
# POST TEXT
# ==================================================

async def get_post(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["post_text"] = update.message.text

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Button যোগ করব",
                callback_data="add_button"
            )
        ],
        [
            InlineKeyboardButton(
                "🚀 Button ছাড়াই পোস্ট",
                callback_data="finish_post"
            )
        ]
    ]

    await update.message.reply_text(
        "🔘 পোস্টে Inline Button দিতে চান?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return BUTTONS


# ==================================================
# BUTTON DECISION
# ==================================================

async def button_decision(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return ConversationHandler.END

    if query.data == "add_button":

        await query.edit_message_text(
            "🔘 Button-এর নাম দিন:\n\n"
            "Example:\n"
            "📚 Course"
        )

        return BUTTON_NAME

    if query.data == "finish_post":

        await query.edit_message_text(
            "⏳ পোস্ট করা হচ্ছে..."
        )

        return await send_post(query, context)


# ==================================================
# BUTTON NAME
# ==================================================

async def get_button_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["button_name"] = update.message.text.strip()

    await update.message.reply_text(
        "🔗 এখন Button-এর URL দিন:\n\n"
        "Example:\n"
        "https://t.me/example"
    )

    return BUTTON_URL


# ==================================================
# BUTTON URL
# ==================================================

async def get_button_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    url = update.message.text.strip()

    if not (
        url.startswith("https://")
        or url.startswith("http://")
        or url.startswith("tg://")
    ):
        await update.message.reply_text(
            "❌ Valid URL দিন।\n\n"
            "Example:\n"
            "https://t.me/example"
        )
        return BUTTON_URL

    button_name = context.user_data["button_name"]

    context.user_data["buttons"].append(
        {
            "name": button_name,
            "url": url
        }
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ আরেকটি Button",
                callback_data="add_button"
            )
        ],
        [
            InlineKeyboardButton(
                "🚀 পোস্ট করুন",
                callback_data="finish_post"
            )
        ]
    ]

    await update.message.reply_text(
        f"✅ Button added:\n\n"
        f"{button_name}\n"
        f"{url}\n\n"
        f"আরেকটি button যোগ করবেন?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return BUTTONS


# ==================================================
# SEND POST
# ==================================================

async def send_post(query, context):

    channel = context.user_data["channel"]
    post_text = context.user_data["post_text"]
    buttons = context.user_data.get("buttons", [])

    # Inline keyboard তৈরি
    keyboard = []

    for button in buttons:

        keyboard.append(
            [
                InlineKeyboardButton(
                    button["name"],
                    url=button["url"]
                )
            ]
        )

    reply_markup = None

    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)

    try:

        await context.bot.send_message(
            chat_id=channel,
            text=post_text,
            reply_markup=reply_markup
        )

        await query.edit_message_text(
            f"✅ পোস্ট সফলভাবে পাঠানো হয়েছে!\n\n"
            f"📢 Channel: {channel}\n"
            f"🔘 Buttons: {len(buttons)}"
        )

    except Exception as e:

        await query.edit_message_text(
            "❌ পোস্ট করা যায়নি!\n\n"
            f"Error:\n{e}\n\n"
            "চেক করুন:\n"
            "• Bot-কে Channel Admin করা হয়েছে কিনা\n"
            "• Post Messages permission আছে কিনা\n"
            "• Channel username সঠিক কিনা"
        )

    context.user_data.clear()

    return ConversationHandler.END


# ==================================================
# CANCEL
# ==================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Post creation cancelled."
    )

    return ConversationHandler.END


# ==================================================
# MAIN
# ==================================================

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    conversation = ConversationHandler(

        entry_points=[
            CommandHandler("post", post_start)
        ],

        states={

            CHANNEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_channel
                )
            ],

            POST: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_post
                )
            ],

            BUTTONS: [],

            BUTTON_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_button_name
                )
            ],

            BUTTON_URL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_button_url
                )
            ],
        },

        fallbacks=[
            CommandHandler("cancel", cancel)
        ],

    )

    # Callback handler আলাদাভাবে ConversationHandler-এর ভিতরে
    from telegram.ext import CallbackQueryHandler

    conversation.states[BUTTONS] = [
        CallbackQueryHandler(
            button_decision,
            pattern="^(add_button|finish_post)$"
        )
    ]

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(conversation)

    print("================================")
    print("Telegram Channel Poster Started")
    print("================================")

    app.run_polling()


if __name__ == "__main__":
    main()
