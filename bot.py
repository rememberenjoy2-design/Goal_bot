import os
import logging
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID") 
FOOTBALL_FEED_URL = "https://www.skysports.com/rss/12040" 

async def is_user_subscribed(bot, user_id: int) -> bool:
    """Checks if a user is subscribed to the required channel."""
    logger.info(f"Checking subscription for user {user_id} in channel {CHANNEL_ID}...")
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        logger.info(f"Subscription status for {user_id}: {member.status}")
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except TelegramError as e:
        logger.error(f"Failed to check subscription: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when the user runs /start."""
    user = update.effective_user
    logger.info(f"RECEIVED /start command from user: {user.first_name} (ID: {user.id})")
    
    user_id = user.id
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        logger.info(f"User {user_id} is subscribed! Showing sports menu.")
        await send_sports_menu(update, context)
    else:
        logger.info(f"User {user_id} is NOT subscribed. Showing lock screen.")
        clean_channel_link = CHANNEL_ID.replace("@", "")
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel Here", url=f"https://t.me/{clean_channel_link}")],
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
    logger.info(f"User {user_id} clicked 'I Have Joined' button.")
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        await query.edit_message_text("🎉 Access Granted! Welcome to the premium sports club.")
        await send_sports_menu_from_callback(query, context)
    else:
        await query.answer("❌ You haven't joined the channel yet. Please join first!", show_alert=True)

async def send_sports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🔥 Today's Football Trends", callback_data="get_trends")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚡ **Sports Hub Active** ⚡\nChoose an option below to get the latest update:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_sports_menu_from_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🔥 Today's Football Trends", callback_data="get_trends")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "⚡ **Sports Hub Active** ⚡\nChoose an option below to get the latest update:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def fetch_and_send_news(update_or_query, context: ContextTypes.DEFAULT_TYPE, is_callback=True) -> None:
    try:
        logger.info("Fetching RSS feed headlines...")
        feed = feedparser.parse(FOOTBALL_FEED_URL)
        if not feed.entries:
            text = "⚠️ No trending news found at the moment. Try again shortly!"
            if is_callback:
                await update_or_query.edit_message_text(text)
            else:
                await update_or_query.reply_text(text)
            return
            
        news_message = "🔥 **TRENDING FOOTBALL NEWS** 🔥\n\n"
        for index, entry in enumerate(feed.entries[:5], start=1):
            title = entry.title
            link = entry.link
            news_message += f"{index}. [{title}]({link})\n\n"
            
        news_message += f"📢 *For live match discussions and more updates, head over to* {CHANNEL_ID}!"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_callback:
            await update_or_query.edit_message_text(text=news_message, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await update_or_query.reply_text(text=news_message, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)
            
    except Exception as e:
        logger.error(f"Error fetching RSS feed: {e}")
        err_msg = "❌ Oops! Something went wrong while loading the news."
        if is_callback:
            await update_or_query.edit_message_text(err_msg)
        else:
            await update_or_query.reply_text(err_msg)

async def handle_trends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Fetching latest transfer news & trends...")
    await fetch_and_send_news(query, context, is_callback=True)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text.lower()
    user_id = update.effective_user.id
    logger.info(f"Received text message: '{user_text}' from user {user_id}")
    
    subscribed = await is_user_subscribed(context.bot, user_id)
    if not subscribed:
        await start(update, context)
        return

    if "trend" in user_text or "news" in user_text:
        await fetch_and_send_news(update.message, context, is_callback=False)
    else:
        await update.message.reply_text(
            "⚽ I only speak football! Type **'news'** or click `/start` to access the main menu.",
            parse_mode="Markdown"
        )

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    if not TOKEN or not CHANNEL_ID:
        logger.error("Missing environment variables!")
        return

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(CallbackQueryHandler(handle_trends_callback, pattern="^get_trends$"))
    app.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    
    # Plain text listener
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
