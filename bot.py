import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

# Enable logging so we can debug errors on Railway
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Retrieve configuration from environment variables (Railway Secrets)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # e.g. "@your_channel" or "-100xxxxxxxxx"

async def is_user_subscribed(bot, user_id: int) -> bool:
    """Checks if a user is subscribed to the required channel."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        # Allowed states: member, administrator, or creator (owner)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except TelegramError as e:
        logger.error(f"Error checking subscription: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when the user runs /start."""
    user = update.effective_user
    user_id = user.id
    
    # Check if they are subscribed
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        # If subscribed, show the welcome screen and sports options
        await send_sports_menu(update, context)
    else:
        # If NOT subscribed, show the lock screen with a join button
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel Here", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
            [InlineKeyboardButton("✅ I Have Joined!", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚽ Welcome {user.first_name}!\n\n"
            "To unlock the latest football trends, live updates, and match summaries, "
            "please join our official sports channel first!",
            reply_markup=reply_markup
        )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when user clicks 'I Have Joined!' button."""
    query = update.callback_query
    await query.answer() # Acknowledge the click immediately
    
    user_id = query.from_user.id
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        await query.edit_message_text("🎉 Access Granted! Welcome to the premium sports club.")
        # Proceed to show them the sports content
        await send_sports_menu_from_callback(query, context)
    else:
        # Alert them they still need to join
        await query.answer("❌ You haven't joined the channel yet. Please join first!", show_alert=True)

async def send_sports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the main sports menu options."""
    keyboard = [
        [InlineKeyboardButton("🔥 Today's Football Trends", callback_data="get_trends")],
        [InlineKeyboardButton("🏆 League Standings", callback_data="get_standings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚡ **Sports Hub Active** ⚡\nChoose an option below to get the latest update:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_sports_menu_from_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Helper to show the sports menu when transitioning from a button click."""
    keyboard = [
        [InlineKeyboardButton("🔥 Today's Football Trends", callback_data="get_trends")],
        [InlineKeyboardButton("🏆 League Standings", callback_data="get_standings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "⚡ **Sports Hub Active** ⚡\nChoose an option below to get the latest update:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_trends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder trend news response."""
    query = update.callback_query
    await query.answer()
    
    # We will expand this to fetch real sports news later!
    trending_news = (
        "📊 **Trending Sports News today:**\n\n"
        "• Rumors are heating up around summer transfers!\n"
        "• Preparation matches kick off this evening.\n"
        "• Click below to discuss in the main channel!"
    )
    await query.edit_message_text(text=trending_news, parse_mode="Markdown")

def main():
    """Start the bot."""
    if not TOKEN or not CHANNEL_ID:
        logger.error("Missing environment variables!")
        return

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    
    # Button Callbacks
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(CallbackQueryHandler(handle_trends_callback, pattern="^get_trends$"))

    # Start Polling
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
