from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def welcome_image(ctx, member: discord.Member):
    # Load profile picture
    avatar_url = member.avatar_url
    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content))

    # Create a new image
    base = Image.new('RGB', (500, 700), (255, 255, 255))
    draw = ImageDraw.Draw(base)
    
    # Add text
    font = ImageFont.truetype("arial.ttf", 40)
    welcome_text = f"Welcome {member.display_name}"
    bottom_text = "to Student Veterans of America - UNM"
    
    text_width, _ = draw.textsize(welcome_text, font=font)
    draw.text(((500 - text_width) / 2, 50), welcome_text, fill="black", font=font)
    
    text_width, _ = draw.textsize(bottom_text, font=font)
    draw.text(((500 - text_width) / 2, 600), bottom_text, fill="black", font=font)
    
    # Add profile picture in the center
    avatar = avatar.resize((300, 300))
    base.paste(avatar, (100, 150))
    
    # Save the image
    image_path = f"welcome_{member.id}.png"
    base.save(image_path)
    
    # Send the image in the welcome channel
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        await channel.send(file=discord.File(image_path))

# Run your bot with the token
bot.run('YOUR_BOT_TOKEN')
