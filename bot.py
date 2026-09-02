import os
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIGURATION
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing!"
    )

if not ADMIN_ID_RAW:
    raise RuntimeError(
        "ADMIN_ID environment variable is missing!"
    )

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError(
        "ADMIN_ID must be a numeric Telegram User ID!"
    )


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# CONVERSATION STATES
# =========================================================

CHANNEL = 1
POST_TEXT = 2
BUTTON_MENU = 3
BUTTON_NAME = 4
BUTTON_URL = 5


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(update: Update) -> bool:

    if not update.effective_user:
        return False

    return update.effective_user.id == ADMIN_ID


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):
        await update.message.reply_text(
            "❌ Unauthorized."
        )
        return

    await update.message.reply_text(
        "🤖 Channel Poster Bot Ready!\n\n"
        "📢 /post - নতুন পোস্ট তৈরি করুন\n"
        "🆔 /myid - আপনার Telegram ID দেখুন\n"
        "❌ /cancel - বর্তমান কাজ বন্ধ করুন"
    )


# =========================================================
# /MYID
# =========================================================

async def myid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"🆔 Your Telegram User ID:\n\n"
        f"`{update.effective_user.id}`",
        parse_mode="Markdown",
    )


# =========================================================
# /POST START
# =========================================================

async def post_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(update):
        await update.message.reply_text(
            "❌ Unauthorized."
        )
        return ConversationHandler.END

    # আগের data পরিষ্কার
    context.user_data.clear()

    # Button list তৈরি
    context.user_data["buttons"] = []

    await update.message.reply_text(
        "📢 **Channel নির্বাচন করুন**\n\n"
        "Public channel হলে username দিন:\n"
        "`@mychannel`\n\n"
        "Private channel হলে ID দিন:\n"
        "`-1001234567890`\n\n"
        "➡️ এখন Channel username/ID পাঠান।",
        parse_mode="Markdown",
    )

    return CHANNEL


# =========================================================
# CHANNEL
# =========================================================

async def receive_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    channel = update.message.text.strip()

    if not channel:
        await update.message.reply_text(
            "❌ Channel username/ID সঠিকভাবে দিন।"
        )
        return CHANNEL

    context.user_data["channel"] = channel

    await update.message.reply_text(
        "✅ Channel saved:\n"
        f"{channel}\n\n"
        "📝 এখন আপনার সম্পূর্ণ পোস্টের লেখা পাঠান।"
    )

    return POST_TEXT


# =========================================================
# POST TEXT
# =========================================================

async def receive_post_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    if not text.strip():
        await update.message.reply_text(
            "❌ পোস্ট খালি হতে পারবে না। আবার পাঠান।"
        )
        return POST_TEXT

    context.user_data["post_text"] = text

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Inline Button যোগ করুন",
                callback_data="add_button",
            )
        ],
        [
            InlineKeyboardButton(
                "🚀 সরাসরি পোস্ট করুন",
                callback_data="publish",
            )
        ],
    ]

    await update.message.reply_text(
        "📝 Post text saved.\n\n"
        "এখন চাইলে Inline Button যোগ করতে পারেন।",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return BUTTON_MENU


# =========================================================
# BUTTON MENU
# =========================================================

async def button_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "Unauthorized",
            show_alert=True,
        )
        return ConversationHandler.END

    # Add button
    if query.data == "add_button":

        await query.edit_message_text(
            "🔘 **Button-এর নাম পাঠান।**\n\n"
            "Example:\n"
            "📚 Udvash\n\n"
            "অথবা:\n"
            "🎓 10 MS",
            parse_mode="Markdown",
        )

        return BUTTON_NAME

    # Publish
    if query.data == "publish":

        await query.edit_message_text(
            "⏳ পোস্ট করা হচ্ছে..."
        )

        return await publish_post(
            query,
            context,
        )

    return BUTTON_MENU


# =========================================================
# BUTTON NAME
# =========================================================

async def receive_button_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "❌ Button name খালি হতে পারবে না।"
        )
        return BUTTON_NAME

    context.user_data["current_button_name"] = name

    await update.message.reply_text(
        "🔗 এখন Button-এর URL পাঠান।\n\n"
        "Example:\n"
        "https://t.me/udvaash"
    )

    return BUTTON_URL


# =========================================================
# BUTTON URL
# =========================================================

async def receive_button_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    url = update.message.text.strip()

    # URL validation
    if not (
        url.startswith("https://")
        or url.startswith("http://")
        or url.startswith("tg://")
    ):

        await update.message.reply_text(
            "❌ Invalid URL!\n\n"
            "URL অবশ্যই এমন হতে হবে:\n"
            "https://example.com\n\n"
            "আবার URL পাঠান।"
        )

        return BUTTON_URL

    name = context.user_data.get(
        "current_button_name"
    )

    if not name:

        await update.message.reply_text(
            "❌ Button name পাওয়া যায়নি। আবার /post দিন।"
        )

        return ConversationHandler.END

    # Button save
    context.user_data["buttons"].append(
        {
            "name": name,
            "url": url,
        }
    )

    # Temporary data remove
    context.user_data.pop(
        "current_button_name",
        None,
    )

    total_buttons = len(
        context.user_data["buttons"]
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ আরেকটি Button",
                callback_data="add_button",
            )
        ],
        [
            InlineKeyboardButton(
                f"🚀 পোস্ট করুন ({total_buttons} Button)",
                callback_data="publish",
            )
        ],
    ]

    await update.message.reply_text(
        f"✅ Button added!\n\n"
        f"🔘 {name}\n"
        f"🔗 {url}\n\n"
        f"এখন আরেকটি button যোগ করতে পারেন "
        f"অথবা পোস্ট করতে পারেন।",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )

    return BUTTON_MENU


# =========================================================
# PUBLISH POST
# =========================================================

async def publish_post(
    query,
    context: ContextTypes.DEFAULT_TYPE,
):

    channel = context.user_data.get(
        "channel"
    )

    post_text = context.user_data.get(
        "post_text"
    )

    buttons = context.user_data.get(
        "buttons",
        []
    )

    if not channel or not post_text:

        await query.edit_message_text(
            "❌ Post data missing!\n\n"
            "আবার /post দিয়ে চেষ্টা করুন।"
        )

        context.user_data.clear()

        return ConversationHandler.END

    # =====================================================
    # CREATE INLINE KEYBOARD
    # =====================================================

    keyboard = []

    for button in buttons:

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=button["name"],
                    url=button["url"],
                )
            ]
        )

    reply_markup = None

    if keyboard:

        reply_markup = InlineKeyboardMarkup(
            keyboard
        )

    # =====================================================
    # SEND MESSAGE
    # =====================================================

    try:

        sent_message = await context.bot.send_message(
            chat_id=channel,
            text=post_text,
            reply_markup=reply_markup,
        )

        message_id = sent_message.message_id

        await query.edit_message_text(
            "✅ **POST SUCCESSFUL!**\n\n"
            f"📢 Channel: `{channel}`\n"
            f"🔘 Buttons: `{len(buttons)}`\n"
            f"🆔 Message ID: `{message_id}`",
            parse_mode="Markdown",
        )

        logger.info(
            "Post sent successfully to %s",
            channel,
        )

    except Exception as error:

        logger.exception(
            "Failed to send post"
        )

        await query.edit_message_text(
            "❌ **POST FAILED!**\n\n"
            f"📢 Channel:\n{channel}\n\n"
            f"⚠️ Error:\n`{error}`\n\n"
            "চেক করুন:\n"
            "1️⃣ Bot Channel-এর Admin কিনা\n"
            "2️⃣ Bot-এর Post Messages permission আছে কিনা\n"
            "3️⃣ Channel username/ID সঠিক কিনা",
            parse_mode="Markdown",
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================================================
# /CANCEL
# =========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Post creation cancelled.\n\n"
        "নতুন পোস্ট করতে /post দিন।"
    )

    return ConversationHandler.END


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("======================================")
    print(" Telegram Channel Poster Bot")
    print(" Starting...")
    print("======================================")

    # Create application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # CONVERSATION HANDLER
    # =====================================================

    conversation = ConversationHandler(

        entry_points=[
            CommandHandler(
                "post",
                post_start,
            )
        ],

        states={

            # ---------------------------------------------
            # CHANNEL
            # ---------------------------------------------

            CHANNEL: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_channel,
                )
            ],

            # ---------------------------------------------
            # POST TEXT
            # ---------------------------------------------

            POST_TEXT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_post_text,
                )
            ],

            # ---------------------------------------------
            # BUTTON MENU
            # ---------------------------------------------

            BUTTON_MENU: [
                CallbackQueryHandler(
                    button_menu,
                    pattern="^(add_button|publish)$",
                )
            ],

            # ---------------------------------------------
            # BUTTON NAME
            # ---------------------------------------------

            BUTTON_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_button_name,
                )
            ],

            # ---------------------------------------------
            # BUTTON URL
            # ---------------------------------------------

            BUTTON_URL: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_button_url,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            )
        ],

        allow_reentry=True,
    )

    # =====================================================
    # HANDLERS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "myid",
            myid,
        )
    )

    application.add_handler(
        conversation
    )

    application.add_error_handler(
        error_handler
    )

    # =====================================================
    # START BOT
    # =====================================================

    print("Bot is running...")
    print("======================================")

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
