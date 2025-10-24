import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime
import pytz

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Your bot token
TOKEN = ''

# Global dictionary to store timers
timers = {}

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the slash commands with Discord
    print(f'Bot is online as {bot.user}')

@bot.tree.command(name="croles")
async def create_role(interaction: discord.Interaction, role_name: str):
    """Creates a new role by entered the name."""
    guild = interaction.guild

    permissions = discord.Permissions(send_messages=True, read_messages=True)

    try:
        role = await guild.create_role(name=role_name, permissions=permissions)
        await interaction.response.send_message(f'Role "{role_name}" has been created with write message and view channel permissions.', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"I do not have permissions to create roles.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred while creating the role: {str(e)}", ephemeral=True)

@bot.tree.command(name="addroles")
async def add_role(interaction: discord.Interaction, role: discord.Role, users: str):
    """Add few members to a role (use, and space)."""
    user_mentions = [user.strip() for user in users.split(",") if user.strip()]
    guild = interaction.guild

    if not user_mentions:
        await interaction.response.send_message("Please specify at least one user.", ephemeral=True)
        return

    success_count = 0
    error_count = 0
    error_users = []

    # Check bot's highest role and required permissions
    bot_member = guild.get_member(bot.user.id)
    bot_highest_role = bot_member.top_role

    if bot_highest_role <= role:
        await interaction.response.send_message(f"The bot's highest role ({bot_highest_role}) is not high enough to manage the role ({role}).", ephemeral=True)
        return

    if not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message("The bot does not have the 'Manage Roles' permission.", ephemeral=True)
        return

    for mention in user_mentions:
        # Extract user ID from mention
        user_id = int(mention.strip('<@!>'))
        user = guild.get_member(user_id)
        if user:
            try:
                await user.add_roles(role)
                success_count += 1
            except discord.Forbidden:
                error_count += 1
                error_users.append(f"{mention} (Forbidden)")
            except discord.HTTPException as e:
                error_count += 1
                error_users.append(f"{mention} (HTTPException: {str(e)})")
        else:
            error_count += 1
            error_users.append(f"{mention} (User not found)")

    if success_count > 0:
        await interaction.response.send_message(f'Role "{role.name}" has been added to {success_count} user(s).', ephemeral=True)
    if error_count > 0:
        await interaction.response.send_message(f"Failed to add role to {error_count} user(s): {', '.join(error_users)}. Ensure all usernames are correct and the bot has appropriate permissions.", ephemeral=True)

@bot.tree.command(name="stime")
async def set_time(interaction: discord.Interaction, name: str, date_time: str, role1: discord.Role, role2: discord.Role, message: str = "START!"):
    """Write a set time message and might ping u on that time"""
    try:
        target_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M')
        target_time = target_time.replace(tzinfo=pytz.UTC)
        
        now = datetime.now(pytz.UTC)
        time_diff = (target_time - now).total_seconds()
        
        if time_diff <= 0:
            await interaction.response.send_message("The specified time is in the past. Please provide a future time in UTC.", ephemeral=True)
            return

        if interaction.user.id in timers and name in timers[interaction.user.id]:
            timers[interaction.user.id][name].cancel()

        await interaction.response.send_message(f'Timer "{name}" set for {target_time.strftime("%Y-%m-%d %H:%M UTC")}. {role1.mention} and {role2.mention}, please be on time.')

        if interaction.user.id not in timers:
            timers[interaction.user.id] = {}
        timer_task = asyncio.create_task(schedule_message(interaction, name, time_diff, role1, role2, message))
        timers[interaction.user.id][name] = timer_task

    except ValueError:
        await interaction.response.send_message("Invalid date/time format. Please use 'YYYY-MM-DD HH:MM' in 24-hour format (UTC).", ephemeral=True)

async def schedule_message(interaction, name, time_diff, role1, role2, message):
    await asyncio.sleep(time_diff)

    if interaction.user.id in timers and name in timers[interaction.user.id]:
        await interaction.followup.send(f'{role1.mention} {role2.mention} {message}')
        del timers[interaction.user.id][name]

        if not timers[interaction.user.id]:
            del timers[interaction.user.id]

@bot.tree.command(name="fnmessage")
async def form_nego_message(interaction: discord.Interaction, name: str, time1: str, time2: str, channel: discord.TextChannel):
    """Write a nego message and send it to different channel"""
    message = f"This is {name} tournament. Please nego your match before {time1} until {time2}. Ping staff or admin to set your time."

    try:
        await channel.send(message)
        await interaction.response.send_message(f'Message sent to {channel.mention}.', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"Cannot send message to {channel.mention}. Permissions issue.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred while sending the message to {channel.mention}: {str(e)}", ephemeral=True)

@bot.tree.command(name="cchannel")
async def create_channel(interaction: discord.Interaction, channel_name: str, channel_type: str):
    """Create text or voice channel"""
    guild = interaction.guild

    # Determine the channel type
    if channel_type.lower() == "text":
        channel_type = discord.ChannelType.text
    elif channel_type.lower() == "voice":
        channel_type = discord.ChannelType.voice
    else:
        await interaction.response.send_message("Invalid channel type. Please specify 'text' or 'voice'.", ephemeral=True)
        return

    try:
        # Create the channel
        channel = await guild.create_text_channel(channel_name) if channel_type == discord.ChannelType.text else await guild.create_voice_channel(channel_name)
        await interaction.response.send_message(f'{channel_type.name.capitalize()} channel "{channel_name}" has been created.', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permissions to create channels.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred while creating the channel: {str(e)}", ephemeral=True)

@bot.tree.command(name="ccategory")
async def create_category(interaction: discord.Interaction, category_name: str):
    """Creates a new category in the server."""
    guild = interaction.guild

    try:
        # Create the category
        category = await guild.create_category(category_name)
        await interaction.response.send_message(f'Category "{category_name}" has been created.', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permissions to create categories.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred while creating the category: {str(e)}", ephemeral=True)

@bot.tree.command(name="cspecialchannel")
async def create_channel_in_category(interaction: discord.Interaction, channel_name: str, channel_type: str, category_name: str):
    """Create a text or voice channel in a specified category."""
    guild = interaction.guild

    # Determine the channel type
    if channel_type.lower() == "text":
        channel_type = discord.ChannelType.text
    elif channel_type.lower() == "voice":
        channel_type = discord.ChannelType.voice
    else:
        await interaction.response.send_message("Invalid channel type. Please specify 'text' or 'voice'.", ephemeral=True)
        return

    # Find the category
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        await interaction.response.send_message(f'Category "{category_name}" not found.', ephemeral=True)
        return

    try:
        # Create the channel in the specified category
        channel = await guild.create_text_channel(channel_name, category=category) if channel_type == discord.ChannelType.text else await guild.create_voice_channel(channel_name, category=category)
        await interaction.response.send_message(f'{channel_type.name.capitalize()} channel "{channel_name}" has been created in the category "{category_name}".', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permissions to create channels.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred while creating the channel: {str(e)}", ephemeral=True)

@bot.tree.command(name="addutc")
async def add_users_to_channel(interaction: discord.Interaction, users: str, channel: discord.abc.GuildChannel):
    """Add multiple users to a specific text or voice channel."""
    user_mentions = [user.strip() for user in users.split(",") if user.strip()]
    if not user_mentions:
        await interaction.response.send_message("Please specify at least one user.", ephemeral=True)
        return

    success_count = 0
    error_count = 0
    error_users = []

    for mention in user_mentions:
        # Extract user ID from mention
        user_id = int(mention.strip('<@!>'))
        user = interaction.guild.get_member(user_id)
        if user:
            try:
                # Define the permissions you want to grant to the user
                overwrite = discord.PermissionOverwrite()
                overwrite.view_channel = True  # Allows the user to view the channel
                overwrite.send_messages = True if isinstance(channel, discord.TextChannel) else None  # Allows sending messages if it's a text channel
                overwrite.connect = True if isinstance(channel, discord.VoiceChannel) else None  # Allows connecting if it's a voice channel

                # Set the permissions for the user in the channel
                await channel.set_permissions(user, overwrite=overwrite)
                success_count += 1
            except discord.Forbidden:
                error_count += 1
                error_users.append(f"{mention} (Forbidden)")
            except discord.HTTPException as e:
                error_count += 1
                error_users.append(f"{mention} (HTTPException: {str(e)})")
        else:
            error_count += 1
            error_users.append(f"{mention} (User not found)")

    if success_count > 0:
        await interaction.response.send_message(f'{success_count} user(s) have been added to the channel "{channel.name}".', ephemeral=True)
    if error_count > 0:
        await interaction.response.send_message(f"Failed to add {error_count} user(s) to the channel: {', '.join(error_users)}. Ensure all usernames are correct and the bot has appropriate permissions.", ephemeral=True)

# Run the bot
bot.run(TOKEN)

