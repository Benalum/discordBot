import discord
from discord.ext import commands
import re
import random
import smtplib
from email.mime.text import MIMEText
import asyncio
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Read email, password, bot token, and allowed domains from file
def read_config(file_path):
    config = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            config[key] = value
    return config

def read_domains(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file]

config = read_config('resources/discord.txt')
from_email = config['from_email']
from_password = config['from_password']
bot_token = config['bot_token']
smtp_server = config['smtp_server']
smtp_port = int(config['smtp_port'])
allowed_domains = read_domains('resources/domains.txt')

# Update the email pattern
def update_email_pattern():
    global email_pattern
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@(' + '|'.join([re.escape(domain) for domain in allowed_domains]) + r')$')
    print(f"[DEBUG] Updated email pattern: {email_pattern.pattern}")

update_email_pattern()
verification_codes = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await check_all_members()

async def check_all_members():
    print("[DEBUG] Starting check_all_members")
    for guild in bot.guilds:
        print(f"[DEBUG] Checking guild: {guild.name}")
        for member in guild.members:
            print(f"[DEBUG] Checking member: {member.name}")
            if len(member.roles) == 1:  # Only has the `@everyone` role
                print(f"[DEBUG] Member {member.name} has no roles, checking email")
                await check_email(member)
            else:
                print(f"[DEBUG] Member {member.name} has roles: {', '.join([role.name for role in member.roles if role.name != '@everyone'])}")

@bot.event
async def on_member_update(before, after):
    if len(after.roles) == 1:  # Only has the `@everyone` role
        await check_email(after)

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        await welcome_image(member, channel)

async def check_email(member):
    await member.send("Welcome! Please provide your UNM E-mail for student verification.")
    def check(m):
        return m.author == member and isinstance(m.channel, discord.DMChannel)
    try:
        msg = await bot.wait_for('message', check=check, timeout=300)  # 5-minute timeout
        user_email = msg.content
        if any(user_email.endswith(domain) for domain in allowed_domains):
            code = generate_verification_code()
            verification_codes[member.id] = code
            send_email(user_email, code)
            await member.send("A verification code has been sent to your email. Please enter the code here.")
            attempts = 0
            while attempts < 3:
                msg = await bot.wait_for('message', check=check, timeout=300)  # 5-minute timeout
                if msg.content == code:
                    await member.send("Email verified! You have been granted access to the server.")
                    
                    # Assigning the "General Member" role
                    role = discord.utils.get(member.guild.roles, name="General Member")
                    if role:
                        await member.add_roles(role)


                    # Send welcome message to the welcome channel
                    channel = discord.utils.get(member.guild.text_channels, name="welcome")
                    if channel:
                        await welcome_image(member, channel)
                    return
                else:
                    attempts += 1
                    if attempts < 3:
                        await member.send("Verification code incorrect. Please try again.")
                    else:
                        await member.send("Verification code incorrect. You have been removed.")
                        if len(member.roles) == 1:  # Check if user still only has `@everyone` role
                            await member.kick(reason="Email verification failed")
        else:
            await member.send("You do not meet the requirements and will be removed.")
            if len(member.roles) == 1:  # Check if user still only has `@everyone` role
                await member.kick(reason="Email verification failed")
    except asyncio.TimeoutError:
        await member.send("Verification timed out. You have been removed from the server.")
        if len(member.roles) == 1:  # Check if user still only has `@everyone` role
            await member.kick(reason="Email verification timeout")

def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_email(to_email, code):
    msg = MIMEText(f"Your verification code is: {code}")
    msg['Subject'] = 'Email Verification Code'
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())

def save_domains(file_path):
    with open(file_path, 'w') as file:
        for domain in allowed_domains:
            file.write(f"{domain}\n")

async def welcome_image(member, channel):
    # Load profile picture
    avatar_url = str(member.avatar.url)
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content))
    
    # Create a colorful background image with increased width and height
    base = Image.new('RGB', (1000, 875), (173, 216, 230))  # Light blue background
    draw = ImageDraw.Draw(base)
    
    # Add text with 3D effect
    font = ImageFont.truetype("arial.ttf", 60)
    welcome_text = f"Welcome {member.display_name}"
    top_text = "to the"
    middle_text = "Student Veterans of America"
    bottom_text = "UNM Discord!"
    
    # Add shadow for 3D effect
    shadow_color = (128, 128, 128)  # Gray shadow
    text_bbox = draw.textbbox((0, 0), welcome_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    draw.text(((1000 - text_width) / 2 + 2, 52), welcome_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2 + 4, 54), welcome_text, fill=shadow_color, font=font)
    
    # Add main text
    draw.text(((1000 - text_width) / 2, 50), welcome_text, fill="black", font=font)
    
    # Add more text for 'to' and 'Student Veterans of America'
    text_bbox = draw.textbbox((0, 0), top_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    draw.text(((1000 - text_width) / 2 + 2, 612), top_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2 + 4, 614), top_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2, 610), top_text, fill="black", font=font)
    
    text_bbox = draw.textbbox((0, 0), middle_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    draw.text(((1000 - text_width) / 2 + 2, 662), middle_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2 + 4, 664), middle_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2, 660), middle_text, fill="black", font=font)
    
    text_bbox = draw.textbbox((0, 0), bottom_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    draw.text(((1000 - text_width) / 2 + 2, 712), bottom_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2 + 4, 714), bottom_text, fill=shadow_color, font=font)
    draw.text(((1000 - text_width) / 2, 710), bottom_text, fill="black", font=font)
    
    # Add profile picture with pop-out effect
    avatar = avatar.resize((400, 400))
    avatar_border = Image.new('RGB', (420, 420), (0, 0, 0))  # Black border for pop-out effect
    avatar_border.paste(avatar, (10, 10))
    base.paste(avatar_border, (300, 150))
    
    # Save the image
    image_path = f"welcome_{member.id}.png"
    base.save(image_path)
    
    # Send the image in the welcome channel
    await channel.send(file=discord.File(image_path))


@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        await welcome_image(member, channel)


########################## The Following are Commands for the Bot ##########################

@bot.command()
async def testWelcomeImage(ctx):
    """Command to test the welcome image generation."""
    member = ctx.author
    channel = ctx.channel
    await welcome_image(member, channel)

@bot.command()
@commands.has_permissions(administrator=True)
async def addDomain(ctx, domain):
    """Command to add a new domain to the allowed list."""
    allowed_domains.append(domain)
    update_email_pattern()
    save_domains('domains.txt')
    await ctx.send(f"Domain {domain} added to the allowed list.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeDomain(ctx, domain):
    """Command to remove a domain from the allowed list."""
    if domain in allowed_domains:
        allowed_domains.remove(domain)
        update_email_pattern()
        save_domains('domains.txt')
        await ctx.send(f"Domain {domain} removed from the allowed list.")
    else:
        await ctx.send(f"Domain {domain} not found in the allowed list.")

@bot.command()
async def listDomains(ctx):
    """Command to show all allowed email domains."""
    await ctx.send(f"Allowed domains: {', '.join(allowed_domains)}")

@bot.command()
async def role(ctx):
    """Command to tell the user their role in the Discord channel."""
    roles = [role.name for role in ctx.author.roles if role.name != "@everyone"]
    if roles:
        await ctx.send(f"Your roles: {', '.join(roles)}")
    else:
        await ctx.send("You don't have any roles.")

@bot.command()
async def listCategoriesWithChannels(ctx):
    """Command to list all categories and their channels."""
    categories = []
    for category in ctx.guild.categories:
        channels = ', '.join([channel.name for channel in category.channels])
        categories.append(f"**{category.name}**: {channels}")
    if categories:
        await ctx.send("\n".join(categories))
    else:
        await ctx.send("No categories found.")

@bot.command()
async def welcomeMe(ctx):
    """Command to welcome the user in the server-setup channel within the SERVER category."""
    category = discord.utils.get(ctx.guild.categories, name="Server")
    if category:
        channel = discord.utils.get(category.channels, name="server-setup")
        if channel:
            await channel.send(f"Welcome {ctx.author.mention} to SVA-UNM!")

@bot.command()
async def commands(ctx):
    """Command to provide information on available commands."""
    help_text = """
    **Available Commands:**
 - `!role`: Show your roles in the Discord channel.
 - `!addDomain [domain]`: Add a new domain to the allowed list (admin required).
 - `!removeDomain [domain]`: Remove a domain from the allowed list (admin required).
 - `!listDomains`: Show all allowed email domains.
 - `!listCategoriesWithChannels`: List all categories and their channels.
 - `!commands`: Provide information on available commands.
    """
    await ctx.send(help_text)


# bot's token
bot.run(bot_token)
