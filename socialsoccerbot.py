import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Enable logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize variables
yes_votes = []
no_votes = []
waitlist = []
attendance = {}
ban_list = {}
members = [(123, "John Doe"), (124, "Jane Doe"), (125, "Max Mustermann")]  # Dummy member list for demonstration

# Your user ID (provided by you)
bot_owner_id = 122542800

# Group rules
terms_and_conditions = (
    """1. No slide tackle.\n
    2. Respect the group rules.\n
    3. Be on time and respect other people's time by being punctual. We appreciate your help.\n
    4. Only two captains are allowed to discuss and give instructions in the game. No players are allowed to instruct other players on what they should do. These captains will be chosen at the beginning of each game and may carry a captain armband.\n
    5. Disrespecting group rules will result in a temporary or permanent ban from the group, which will be done via one of the admins.\n
    6. The group voting system is based on first-come, first-served. This means the first 20 people who confirm will be in the game, and no additional players will be allowed.\n
    7. If any of the 20 people change their vote from 'Yes' to 'No,' the first person on the waitlist will automatically replace them.\n
    8. The voting will stop 1 hour before the start of the game, and no one can change their vote.\n
    9. If someone votes 'Yes' and doesn't show up, admins will mark them as a no-show and will ban them on a temporary or permanent basis.\n\n
    1. تکل سر خوردن ممنوع است.\n
    2. به قوانین گروه احترام بگذارید.\n
    3. سر وقت حاضر شوید و به وقت دیگران احترام بگذارید. ما قدردان همکاری شما هستیم.\n
    4. فقط دو کاپیتان مجاز به بحث و دستور دادن در بازی هستند. هیچ بازیکنی مجاز نیست به دیگران بگوید چه کاری باید انجام دهند. این کاپیتان‌ها در ابتدای هر بازی انتخاب می‌شوند و ممکن است بازوبند کاپیتانی داشته باشند.\n
    5. بی‌احترامی به قوانین گروه منجر به ممنوعیت موقت یا دائمی از گروه خواهد شد که توسط یکی از ادمین‌ها انجام می‌شود.\n
    6. سیستم رأی‌گیری گروه بر اساس اولویت ورود است. این به این معناست که اولین ۲۰ نفری که تأیید کنند در بازی شرکت می‌کنند و بازیکن اضافی پذیرفته نمی‌شود.\n
    7. اگر هر یک از این ۲۰ نفر رأی خود را از 'بله' به 'خیر' تغییر دهند، اولین نفر در لیست انتظار به طور خودکار جایگزین خواهد شد.\n
    8. رأی‌گیری ۱ ساعت قبل از شروع بازی متوقف می‌شود و هیچ‌کس نمی‌تواند رأی خود را تغییر دهد.\n
    9. اگر کسی رأی 'بله' بدهد و در بازی حاضر نشود، ادمین‌ها او را به عنوان غایب علامت‌گذاری کرده و به صورت موقت یا دائمی او را ممنوع می‌کنند."""
)

# Function to check if the user is a group admin or the bot owner
async def is_group_admin_or_owner(update: Update) -> bool:
    user_id = update.effective_user.id
    chat = update.effective_chat

    # Check if the user is the bot owner
    if user_id == bot_owner_id:
        logger.info(f"User {user_id} is the bot owner.")
        return True

    # Check if the user is the chat owner or an admin
    try:
        member = await chat.get_member(user_id)
        if member.status in ['administrator', 'creator']:
            logger.info(f"User {user_id} is an admin or the creator.")
            return True
        else:
            logger.info(f"User {user_id} is neither admin nor creator.")
            return False
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

# Function to start the bot and send the welcome message with admin buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_group_admin_or_owner(update):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    logger.info("Start command received")
    welcome_message = (
        "Welcome to our Saturday Social Soccer program! Please respect the group rules and others "
        "as we aim to have a friendly but competitive game. Please confirm you have read and agree to the following rules:"
    )
    welcome_message += terms_and_conditions

    # Add terms confirmation button
    keyboard = [[InlineKeyboardButton("I Agree", callback_data="agree_terms")]]
    
    # Admin buttons (visible to group admins, owners, and the bot owner)
    keyboard.append([InlineKeyboardButton("🔨 Admin Actions", callback_data="admin_actions")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Function to handle the agreement to terms
async def agree_terms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    # Send the attendance confirmation buttons
    keyboard = [
        [InlineKeyboardButton("👍 Yes, I'll be there", callback_data="confirm_attendance")],
        [InlineKeyboardButton("🚫 No, I can't make it", callback_data="cancel_attendance")],
        [InlineKeyboardButton("🔄 Change Vote", callback_data="change_vote")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Thank you for agreeing to the terms. Please confirm or change your attendance:",
        reply_markup=reply_markup
    )

# Function to handle attendance confirmation and changes
async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    user_name = user.first_name  # Using first name for simplicity

    # Remove user from any list if they are already there
    if (user_id, user_name) in yes_votes:
        yes_votes.remove((user_id, user_name))
    if (user_id, user_name) in no_votes:
        no_votes.remove((user_id, user_name))
    if (user_id, user_name) in waitlist:
        waitlist.remove((user_id, user_name))

    # Handle vote based on button clicked
    if query.data == "confirm_attendance":
        if len(yes_votes) < 20:
            yes_votes.append((user_id, user_name))
            attendance[user_id] = "confirmed"
        else:
            waitlist.append((user_id, user_name))
            attendance[user_id] = "waitlist"
    elif query.data == "cancel_attendance":
        no_votes.append((user_id, user_name))
        attendance[user_id] = "canceled"
    elif query.data == "change_vote":
        # Allow the user to change their vote
        keyboard = [
            [InlineKeyboardButton("👍 Yes, I'll be there", callback_data="confirm_attendance")],
            [InlineKeyboardButton("🚫 No, I can't make it", callback_data="cancel_attendance")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_actions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="You can change your vote below:",
            reply_markup=reply_markup
        )
        return

    # Move the first person from the waitlist to the main list if needed
    if len(yes_votes) < 20 and waitlist:
        next_user_id, next_user_name = waitlist.pop(0)
        yes_votes.append((next_user_id, next_user_name))
        attendance[next_user_id] = "confirmed"
        await context.bot.send_message(chat_id=next_user_id, text="A spot opened up for you. You're now confirmed!")

    # Prepare the message to display current attendance status
    confirmed_list = "\n".join([f"{uid} - {name}" for uid, name in yes_votes])
    waitlist_list = "\n".join([f"{uid} - {name}" for uid, name in waitlist])
    no_list = "\n".join([f"{uid} - {name}" for uid, name in no_votes])

    # Create the updated text
    new_text = (
        f"**Total Confirmed ({len(yes_votes)}):**\n{confirmed_list}\n\n"
        f"**Total Waitlist ({len(waitlist)}):**\n{waitlist_list}\n\n"
        f"**Total No ({len(no_votes)}):**\n{no_list}"
    )

    # Check if the new text is different before attempting to edit
    if query.message.text != new_text:
        # Show the updated lists with an option to change the vote
        keyboard = [
            [InlineKeyboardButton("🔄 Change Vote", callback_data="change_vote")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_actions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=new_text,
            reply_markup=reply_markup
        )

# Admin actions menu
async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Log for debugging
    logger.info(f"Admin actions button clicked by user {query.from_user.id}")

    # Admin actions available
    keyboard = [
        [InlineKeyboardButton("➕ Create Event", callback_data="create_event")],
        [InlineKeyboardButton("🔨 Ban a Member", callback_data="ban_member")],
        [InlineKeyboardButton("🚫 Unban a Member", callback_data="unban_member")],
        [InlineKeyboardButton("📋 Generate Report", callback_data="generate_report")],
        [InlineKeyboardButton("🚫 Mark No-Show", callback_data="mark_no_show")],
        [InlineKeyboardButton("❌ Close Voting", callback_data="close_voting")],
        [InlineKeyboardButton("❌ Exit Admin Actions", callback_data="exit_admin_actions")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Select an admin action:", reply_markup=reply_markup)

# Function to handle event creation
async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("Please type the event details you'd like to create.")
    context.user_data['creating_event'] = True

# Function to handle the event message
async def handle_event_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('creating_event'):
        logger.info(f"Event message received: {update.message.text}")
        context.user_data['event_content'] = update.message.text
        context.user_data['creating_event'] = False
        
        keyboard = [
            [InlineKeyboardButton("Edit Event", callback_data="edit_event")],
            [InlineKeyboardButton("Approve Event", callback_data="approve_event")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text("Here's the event you've prepared:")
        await update.message.reply_text(context.user_data['event_content'], reply_markup=reply_markup)
    else:
        logger.info("Event creation was not started, ignoring message")

# Function to edit the event message
async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("Please send the updated event details.")
    context.user_data['creating_event'] = True

# Function to approve the event and ask for T&Cs agreement
async def approve_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    event_content = context.user_data.get('event_content')
    if event_content:
        logger.info("Event approved. Asking members to agree to T&Cs.")
        keyboard = [[InlineKeyboardButton("I Agree", callback_data="agree_terms")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text("Please agree to the terms and conditions to participate:")
        await query.message.reply_text(f"Terms & Conditions: \n{terms_and_conditions}", reply_markup=reply_markup)
    else:
        logger.info("No event content found to approve")
        await query.edit_message_text("No event content found. Please create an event first.")

# Function to close voting manually
async def close_voting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Prevent further changes to the voting
    for user_id in yes_votes:
        await context.bot.send_message(chat_id=user_id, text="Voting has been closed by an admin. Thank you for participating!")
    
    await query.edit_message_text("Voting has been closed.")

# Function to notify participants of last-minute changes
async def notify_last_minute_changes(context: ContextTypes.DEFAULT_TYPE) -> None:
    event_content = context.user_data.get('event_content')
    for user_id, status in attendance.items():
        if status == "confirmed":
            await context.bot.send_message(chat_id=user_id, text=f"Attention: The event details have been updated. Here are the latest details:\n{event_content}")

# Function to list members to ban
async def list_members_to_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # Generate buttons for each member
    buttons = [
        [InlineKeyboardButton(f"{name}", callback_data=f"select_ban_{user_id}")]
        for user_id, name in members
    ]

    # Pagination for large member lists
    if len(buttons) > 10:
        buttons = buttons[:10]  # Show only the first 10 for now
        buttons.append([InlineKeyboardButton("Next", callback_data="next_page_ban_1")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_actions")])  # Add Back button

    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Select a member to ban:", reply_markup=reply_markup)

# Function to handle member selection for banning
async def select_member_to_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = int(query.data.split("_")[2])
    user_name = next(name for uid, name in members if uid == user_id)

    # Ask for ban duration
    buttons = [
        [InlineKeyboardButton("1 Week", callback_data=f"confirm_ban_{user_id}_7")],
        [InlineKeyboardButton("2 Weeks", callback_data=f"confirm_ban_{user_id}_14")],
        [InlineKeyboardButton("1 Month", callback_data=f"confirm_ban_{user_id}_30")],
        [InlineKeyboardButton("📅 Custom Date", callback_data=f"custom_ban_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="list_members_to_ban")]  # Back to list members to ban
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(f"Choose ban duration for {user_name}:", reply_markup=reply_markup)

# Function to confirm the ban with a specified duration
async def confirm_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id, days = map(int, query.data.split("_")[2:4])
    user_name = next(name for uid, name in members if uid == user_id)
    ban_until = datetime.now() + timedelta(days=days)
    ban_list[user_id] = (user_name, ban_until)

    # Return to admin actions after banning
    await query.edit_message_text(f"User {user_name} has been banned until {ban_until.strftime('%Y-%m-%d')}.")
    await admin_actions(update, context)

# Function to list members for unbanning
async def list_members_to_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # Generate buttons for each banned member
    buttons = [
        [InlineKeyboardButton(f"{name} (Banned until {ban_until.strftime('%Y-%m-%d')})", callback_data=f"select_unban_{user_id}")]
        for user_id, (name, ban_until) in ban_list.items()
    ]

    # Handle empty ban list
    if not buttons:
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_actions")])
        await query.edit_message_text("No banned members to unban.", reply_markup=InlineKeyboardMarkup(buttons))
        return

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_actions")])  # Add Back button

    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Select a member to unban:", reply_markup=reply_markup)

# Function to handle member selection for unbanning
async def select_member_to_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = int(query.data.split("_")[2])
    user_name, ban_until = ban_list[user_id]

    # Ask for confirmation
    buttons = [
        [InlineKeyboardButton("Confirm Unban", callback_data=f"confirm_unban_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="list_members_to_unban")]  # Back to list members to unban
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(f"Are you sure you want to unban {user_name}?", reply_markup=reply_markup)

# Function to confirm the unban
async def confirm_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = int(query.data.split("_")[2])
    user_name, _ = ban_list.pop(user_id, (None, None))

    # Return to admin actions after unbanning
    await query.edit_message_text(f"User {user_name} has been unbanned.")
    await admin_actions(update, context)

# Function to list confirmed members for marking as no-shows
async def list_members_for_no_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # Generate buttons for each confirmed member
    buttons = [
        [InlineKeyboardButton(f"{name}", callback_data=f"select_no_show_{user_id}")]
        for user_id, name in yes_votes
    ]

    # Handle empty list
    if not buttons:
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_actions")])
        await query.edit_message_text("No confirmed members to mark as no-show.", reply_markup=InlineKeyboardMarkup(buttons))
        return

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_actions")])  # Add Back button

    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Select a member to mark as no-show:", reply_markup=reply_markup)

# Function to handle selection for marking as no-show
async def select_member_as_no_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = int(query.data.split("_")[2])
    user_name = next(name for uid, name in yes_votes if uid == user_id)

    # Ask for confirmation
    buttons = [
        [InlineKeyboardButton("Confirm No-Show", callback_data=f"confirm_no_show_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="list_members_for_no_show")]  # Back to list members for no-show
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(f"Are you sure you want to mark {user_name} as a no-show?", reply_markup=reply_markup)

# Function to confirm the no-show and ban the member
async def confirm_no_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = int(query.data.split("_")[2])
    user_name = next(name for uid, name in yes_votes if uid == user_id)

    # Mark as no-show and ban
    ban_list[user_id] = (user_name, datetime.now() + timedelta(weeks=1))
    yes_votes.remove((user_id, user_name))  # Remove from the confirmed list

    # Move the first person from the waitlist to the main list if needed
    if len(yes_votes) < 20 and waitlist:
        next_user_id, next_user_name = waitlist.pop(0)
        yes_votes.append((next_user_id, next_user_name))
        attendance[next_user_id] = "confirmed"
        await context.bot.send_message(chat_id=next_user_id, text="A spot opened up for you due to a no-show. You're now confirmed!")

    await query.edit_message_text(f"User {user_name} has been marked as a no-show and banned for 1 week.")
    await admin_actions(update, context)

# Function to handle pagination for large member lists
async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    page = int(query.data.split("_")[-1])

    start = page * 10
    end = start + 10

    # Generate buttons for the current page
    buttons = [
        [InlineKeyboardButton(f"{name}", callback_data=f"select_ban_{user_id}")]
        for user_id, name in members[start:end]
    ]

    # Add Previous and Next buttons for pagination
    if page > 0:
        buttons.insert(0, [InlineKeyboardButton("Previous", callback_data=f"next_page_ban_{page - 1}")])
    if end < len(members):
        buttons.append([InlineKeyboardButton("Next", callback_data=f"next_page_ban_{page + 1}")])

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_actions")])  # Add Back button

    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Select a member to ban:", reply_markup=reply_markup)

# Function to exit admin actions
async def exit_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.edit_message_text("Admin actions exited.")

# Function to generate participation report
async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    confirmed_list = "\n".join([f"{uid} - {name}" for uid, name in yes_votes]) if yes_votes else "No confirmed participants."
    waitlist_list = "\n".join([f"{uid} - {name}" for uid, name in waitlist]) if waitlist else "No waitlisted participants."
    no_show_list = "\n".join([f"{uid} - {name}" for uid, name in ban_list if ban_list[uid][1] > datetime.now()]) if ban_list else "No no-shows recorded."

    report = (
        f"**Participation Report**\n\n"
        f"**Confirmed ({len(yes_votes)}):**\n{confirmed_list}\n\n"
        f"**Waitlist ({len(waitlist)}):**\n{waitlist_list}\n\n"
        f"**No-Shows:**\n{no_show_list}\n"
    )

    await update.callback_query.edit_message_text(report)

def main():
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("7440125060:AAGajH921h9t9T70i75PmDz57h6UMMac6JU").build()

    # Register the command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(create_event, pattern="create_event"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_message))
    application.add_handler(CallbackQueryHandler(edit_event, pattern="edit_event"))
    application.add_handler(CallbackQueryHandler(approve_event, pattern="approve_event"))
    application.add_handler(CallbackQueryHandler(agree_terms, pattern="agree_terms"))
    application.add_handler(CallbackQueryHandler(handle_attendance, pattern="confirm_attendance|cancel_attendance|change_vote"))
    application.add_handler(CallbackQueryHandler(admin_actions, pattern="admin_actions"))
    application.add_handler(CallbackQueryHandler(close_voting, pattern="close_voting"))
    application.add_handler(CallbackQueryHandler(list_members_to_ban, pattern="ban_member"))
    application.add_handler(CallbackQueryHandler(select_member_to_ban, pattern="select_ban_"))
    application.add_handler(CallbackQueryHandler(confirm_ban, pattern="confirm_ban_"))
    application.add_handler(CallbackQueryHandler(list_members_to_unban, pattern="unban_member"))
    application.add_handler(CallbackQueryHandler(select_member_to_unban, pattern="select_unban_"))
    application.add_handler(CallbackQueryHandler(confirm_unban, pattern="confirm_unban"))
    application.add_handler(CallbackQueryHandler(list_members_for_no_show, pattern="mark_no_show"))
    application.add_handler(CallbackQueryHandler(select_member_as_no_show, pattern="select_no_show_"))
    application.add_handler(CallbackQueryHandler(confirm_no_show, pattern="confirm_no_show"))
    application.add_handler(CallbackQueryHandler(handle_pagination, pattern="next_page_ban_"))
    application.add_handler(CallbackQueryHandler(exit_admin_actions, pattern="exit_admin_actions"))
    application.add_handler(CallbackQueryHandler(generate_report, pattern="generate_report"))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
