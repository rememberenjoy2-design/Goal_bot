import os
import logging
import feedparser  # Dynamic feed reader
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Retrieve configuration from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID") 

# Sky Sports Football RSS feed URL
FOOTBALL_FEED_URL = "https://www.skysports.com/rss/12040" 

async def is_user_subscribed(bot, user_id: int) -> bool:
    """Checks if a user is subscribed to the required channel."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
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
    
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        await send_sports_menu(update, context)
    else:
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
    await query.answer()
    
    user_id = query.from_user.id
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        await query.edit_message_text("🎉 Access Granted! Welcome to the premium sports club.")
        await send_sports_menu_from_callback(query, context)
    else:
        await query.answer("❌ You haven't joined the channel yet. Please join first!", show_alert=True)

async def send_sports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the main sports menu options."""
    keyboard = [
        [InlineKeyboardButton("🔥 Today's Football Trends", callback_data="get_trends")],
        [InlineKeyboardButton("🔄 Refresh News", callback_data="get_trends")]
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
        [InlineKeyboardButton("🔄 Refresh News", callback_data="get_trends")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "⚡ **Sports Hub Active** ⚡\nChoose an option below to get the latest update:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_trends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches real football headlines from the RSS feed and displays them."""
    query = update.callback_query
    await query.answer("Fetching latest transfer news & trends...")
    
    try:
        # Parse the Sky Sports RSS feed
        feed = feedparser.parse(FOOTBALL_FEED_URL)
        
        # Check if we got any entries back
        if not feed.entries:
            await query.edit_message_text("⚠️ No trending news found at the moment. Try again shortly!")
            return
            
        # Build our news response message (let's grab the top 5 articles)
        news_message = "🔥 **TRENDING FOOTBALL NEWS** 🔥\n\n"
        
        for index, entry in enumerate(feed.entries[:5], start=1):
            title = entry.title
            link = entry.link
            news_message += f"{index}. [{title}]({link})\n\n"
            
        # Add a call to action back to your channel!
        news_message += f"📢 *For live match discussions and more updates, head over to* {CHANNEL_ID}!"
        
        # Add a back button to go back to the menu
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text=news_message, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error fetching RSS feed: {e}")
        await query.edit_message_text("❌ Oops! Something went wrong while loading the news. Please try again later.")

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the user back to the main sports menu."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔥 Today's Football Trends", callback_data="get_trends")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚡ **Sports Hub Active** ⚡\nChoose an option below to get the latest update:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

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
    app.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))

    # Start Polling
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
