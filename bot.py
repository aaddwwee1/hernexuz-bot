import discord
from discord.ext import commands
import json
import os

TOKEN = os.environ.get("TOKEN")

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"keys": {}, "users": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.success, emoji="🔑", custom_id="redeem_key")
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary, emoji="📋", custom_id="get_script")
    async def get_script(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        if not data["users"].get(user_id, {}).get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        await interaction.response.send_message(
            "📦 **Script ของคุณพร้อมแล้ว!**\n🔗 ลิงก์: `ใส่ลิงก์ script ของคุณตรงนี้`",
            ephemeral=True
        )

    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="get_role")
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        if not data["users"].get(user_id, {}).get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        BUYER_ROLE_ID = int(os.environ.get("BUYER_ROLE_ID", "0"))
        role = interaction.guild.get_role(BUYER_ROLE_ID)
        if not role:
            await interaction.response.send_message("❌ ไม่พบ Role กรุณาแจ้ง Admin", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("✅ คุณมี Role นี้อยู่แล้ว!", ephemeral=True)
            return
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"🎭 ได้รับ Role **{role.name}** แล้ว!", ephemeral=True)

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.danger, emoji="⚙️", custom_id="reset_hwid")
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        user_info = data["users"].get(user_id, {})
        if not user_info.get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        resets_left = user_info.get("hwid_resets", 0)
        if resets_left <= 0:
            await interaction.response.send_message("❌ HWID Reset หมดแล้ว! ติดต่อ Admin", ephemeral=True)
            return
        data["users"][user_id]["hwid"] = None
        data["users"][user_id]["hwid_resets"] = resets_left - 1
        save_data(data)
        await interaction.response.send_message(
            f"🔄 Reset HWID สำเร็จ! เหลืออีก **{resets_left - 1}** ครั้ง", ephemeral=True
        )

    @discord.ui.button(label="Get Stats", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="get_stats")
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        user_info = data["users"].get(user_id, {})
        if not user_info.get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 สถิติของคุณ", color=discord.Color.blurple())
        embed.add_field(name="🔑 Key", value=f"`{user_info.get('key_used','?')}`", inline=False)
        embed.add_field(name="🔄 HWID Resets เหลือ", value=str(user_info.get("hwid_resets", 0)), inline=True)
        embed.add_field(name="💻 HWID", value=f"`{user_info.get('hwid') or 'ยังไม่ได้ตั้ง'}`", inline=False)
        embed.set_footer(text=f"User: {interaction.user.name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RedeemModal(discord.ui.Modal, title="Redeem License Key"):
    key_input = discord.ui.TextInput(
        label="License Key", placeholder="HD-XXXX-XXXX-XXXX", required=True, max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        data = load_data()
        user_id = str(interaction.user.id)
        if key not in data["keys"]:
            await interaction.response.send_message("❌ Key ไม่ถูกต้อง!", ephemeral=True)
            return
        key_info = data["keys"][key]
        if key_info.get("used"):
            msg = "✅ คุณ Redeem ไปแล้ว!" if key_info.get("used_by") == user_id else "❌ Key ถูกใช้ไปแล้ว!"
            await interaction.response.send_message(msg, ephemeral=True)
            return
        data["keys"][key].update({"used": True, "used_by": user_id})
        data["users"][user_id] = {"redeemed": True, "key_used": key, "hwid": None, "hwid_resets": 3}
        save_data(data)
        await interaction.response.send_message(
            f"✅ Redeem สำเร็จ! ยินดีต้อนรับ **{interaction.user.name}**\nกด **Get Script** และ **Get Role** ได้เลย!",
            ephemeral=True
        )


@bot.command(name="panel")
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="Hermanos'Dev — Control Panel",
        description="This control panel is for the project: **Hermanos'Dev Paid Script**\nIf you're a buyer, click on the buttons below to redeem your key, get the script or get your role.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Sent by {ctx.author.name}")
    await ctx.send(embed=embed, view=ControlPanel())
    await ctx.message.delete()

@bot.command(name="addkey")
@commands.has_permissions(administrator=True)
async def addkey(ctx, key: str):
    data = load_data()
    if key in data["keys"]:
        await ctx.send(f"❌ Key `{key}` มีอยู่แล้ว!", delete_after=5); return
    data["keys"][key] = {"used": False, "used_by": None}
    save_data(data)
    await ctx.send(f"✅ เพิ่ม Key `{key}` สำเร็จ!", delete_after=5)
    await ctx.message.delete()

@bot.command(name="removekey")
@commands.has_permissions(administrator=True)
async def removekey(ctx, key: str):
    data = load_data()
    if key not in data["keys"]:
        await ctx.send(f"❌ ไม่พบ Key `{key}`", delete_after=5); return
    del data["keys"][key]
    save_data(data)
    await ctx.send(f"🗑️ ลบ Key `{key}` สำเร็จ!", delete_after=5)
    await ctx.message.delete()

@bot.command(name="resetuser")
@commands.has_permissions(administrator=True)
async def resetuser(ctx, member: discord.Member):
    data = load_data()
    user_id = str(member.id)
    if user_id not in data["users"]:
        await ctx.send(f"❌ ไม่พบข้อมูลของ {member.name}", delete_after=5); return
    data["users"][user_id].update({"hwid": None, "hwid_resets": 3})
    save_data(data)
    await ctx.send(f"✅ Reset HWID ของ {member.mention} สำเร็จ!", delete_after=5)
    await ctx.message.delete()


@bot.event
async def on_ready():
    print(f"✅ Bot online: {bot.user}")
    bot.add_view(ControlPanel())

bot.run(TOKEN)
