import os
import threading
import asyncio
import discord
from discord.ext import commands
from flask import Flask

# --- RENDER УНТАХААС ХАМГААЛАХ ВЭБ СЕРВЕР ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_web).start()

# --- DISCORD BOT ТОХИРГОО ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

PANEL_CHANNEL_ID = 1566402878560665600  # Панель байрлах сувгийн ID
LOG_CHANNEL_ID = 1566358811223138375    # Лог сувгийн ID-гаа энд солино уу


# --- МЕССЕЖҮҮДИЙГ ХАДГАЛЖ ЛОГ РУУ ИЛГЭЭХ ФУНКЦ ---
async def close_and_log_ticket(channel, closed_by):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    
    messages = []
    async for msg in channel.history(limit=500, oldest_first=True):
        if not msg.author.bot:
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(f"[{timestamp}] {msg.author.name}: {msg.content}")
    
    log_text = "\n".join(messages) if messages else "Ямар нэгэн мессеж бичигдээгүй байна."
    
    if log_channel:
        embed = discord.Embed(
            title=f"📋 Билет Хаагдлаа: {channel.name}",
            description=f"**Хаасан хэрэглэгч:** {closed_by.mention}\n**Сувгийн нэр:** {channel.name}",
            color=discord.Color.blue()
        )
        
        if len(log_text) < 1900:
            embed.add_field(name="Мессежийн түүх:", value=f"```text\n{log_text}\n```", inline=False)
            await log_channel.send(embed=embed)
        else:
            with open("transcript.txt", "w", encoding="utf-8") as f:
                f.write(log_text)
            await log_channel.send(embed=embed, file=discord.File("transcript.txt"))
            os.remove("transcript.txt")

    await channel.send("🔒 Билет болон мессежийн түүхийг хадгаллаа. 5 секундын дараа суваг устгагдана...")
    await asyncio.sleep(5)
    await channel.delete()


# --- TICKET ХААХ ТОВЧ (VIEW) ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Түүхийг хадгалж байна...", ephemeral=True)
        await close_and_log_ticket(interaction.channel, interaction.user)


# --- ҮНДСЭН ПАНЕЛЬ СОНГОЛТ (VIEW) ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Сонголт хийх...",
        options=[
            discord.SelectOption(label="Support Ticket", description="Тусламж авах"),
            discord.SelectOption(label="Clan Join", description="Кландах орох"),
        ],
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Хугацаа хэтрэхээс сэргийлж хүлээгдэж буй төлөвт шилжүүлэх
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        user = interaction.user
        selected_value = select.values[0]
        
        channel_name = f"ticket-{selected_value.lower().replace(' ', '-')}-{user.name}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
        
        embed = discord.Embed(
            title=f"❖ Ticket: {selected_value}",
            description=f"Сайн байна уу {user.mention}? Та **{selected_value}** төрлөөр билет нээлээ. Энд асуудлаа дэлгэрэнгүй бичиж үлдээнэ үү.",
            color=discord.Color.red()
        )
        
        await ticket_channel.send(embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"Таны билет амжилттай нээгдлээ: {ticket_channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} амжилттай холбогдон ажиллаж байна!")


@bot.command()
@commands.has_permissions(administrator=True)
async def sendpanel(ctx):
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if channel:
        view = TicketView()
        embed = discord.Embed(
            title="ELITE Support Center",
            description="Доорх цэснээс сонголт хийж билет нээнэ үү.",
            color=discord.Color.gold(),
        )
        await channel.send(embed=embed, view=view)
        await ctx.send("Панель амжилттай байршлаа!", ephemeral=True)
    else:
        await ctx.send("Суваг олдсонгүй! ID-гаа шалгана уу.", ephemeral=True)


@bot.command()
async def close(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("Түүхийг хадгалж байна...")
        await close_and_log_ticket(ctx.channel, ctx.author)
    else:
        await ctx.send("Энэ командыг зөвхөн билетний суваг дотор ашиглах боломжтой!", ephemeral=True)


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)