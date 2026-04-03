import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# ===================================
#   TOKEN และ GUILD ID จาก Environment
# ===================================
TOKEN          = os.environ.get("TOKEN")
BUYER_ROLE_ID  = int(os.environ.get("BUYER_ROLE_ID", "0"))

DATA_FILE = "data.json"

# ===================================
#   โหลด / บันทึกข้อมูล
# ===================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"keys": {}, "users": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ===================================
#   ตั้งค่า Bot
# ===================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # slash command tree

# ===================================
#   ปุ่ม Control Panel
# ===================================
class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.success, emoji="🔑", custom_id="btn_redeem")
    async def redeem_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary, emoji="📋", custom_id="btn_script")
    async def get_script(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        uid = str(interaction.user.id)
        if not data["users"].get(uid, {}).get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        await interaction.response.send_message(
            "📦 **Script ของคุณพร้อมแล้ว!**\n🔗 ลิงก์: `ใส่ลิงก์ script ของคุณตรงนี้`",
            ephemeral=True
        )

    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="btn_role")
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        uid = str(interaction.user.id)
        if not data["users"].get(uid, {}).get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        role = interaction.guild.get_role(BUYER_ROLE_ID)
        if not role:
            await interaction.response.send_message("❌ ไม่พบ Role กรุณาแจ้ง Admin", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("✅ คุณมี Role นี้อยู่แล้ว!", ephemeral=True)
            return
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"🎭 ได้รับ Role **{role.name}** แล้ว!", ephemeral=True)

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.danger, emoji="⚙️", custom_id="btn_hwid")
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        uid = str(interaction.user.id)
        info = data["users"].get(uid, {})
        if not info.get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        left = info.get("hwid_resets", 0)
        if left <= 0:
            await interaction.response.send_message("❌ HWID Reset หมดแล้ว! ติดต่อ Admin", ephemeral=True)
            return
        data["users"][uid]["hwid"] = None
        data["users"][uid]["hwid_resets"] = left - 1
        save_data(data)
        await interaction.response.send_message(
            f"🔄 Reset HWID สำเร็จ! เหลืออีก **{left - 1}** ครั้ง", ephemeral=True
        )

    @discord.ui.button(label="Get Stats", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="btn_stats")
    async def get_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        uid = str(interaction.user.id)
        info = data["users"].get(uid, {})
        if not info.get("redeemed"):
            await interaction.response.send_message("❌ คุณยังไม่ได้ Redeem Key!", ephemeral=True)
            return
        embed = discord.Embed(title="📊 สถิติของคุณ", color=discord.Color.blurple())
        embed.add_field(name="🔑 Key", value=f"`{info.get('key_used','?')}`", inline=False)
        embed.add_field(name="🔄 HWID Resets เหลือ", value=str(info.get("hwid_resets", 0)), inline=True)
        embed.add_field(name="💻 HWID", value=f"`{info.get('hwid') or 'ยังไม่ได้ตั้ง'}`", inline=False)
        embed.set_footer(text=f"User: {interaction.user.name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===================================
#   Modal กรอก Key
# ===================================
class RedeemModal(discord.ui.Modal, title="Redeem License Key"):
    key_input = discord.ui.TextInput(
        label="License Key",
        placeholder="HD-XXXX-XXXX-XXXX",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        data = load_data()
        uid = str(interaction.user.id)

        if key not in data["keys"]:
            await interaction.response.send_message("❌ Key ไม่ถูกต้อง!", ephemeral=True)
            return

        info = data["keys"][key]
        if info.get("used"):
            msg = "✅ คุณ Redeem ไปแล้ว!" if info.get("used_by") == uid else "❌ Key ถูกใช้ไปแล้ว!"
            await interaction.response.send_message(msg, ephemeral=True)
            return

        data["keys"][key].update({"used": True, "used_by": uid})
        data["users"][uid] = {
            "redeemed": True,
            "key_used": key,
            "hwid": None,
            "hwid_resets": 3
        }
        save_data(data)
        await interaction.response.send_message(
            f"✅ Redeem สำเร็จ! ยินดีต้อนรับ **{interaction.user.name}**\n"
            "กด **Get Script** และ **Get Role** ได้เลย!",
            ephemeral=True
        )


# ===================================
#   /panel — ส่ง Control Panel embed
# ===================================
@tree.command(name="panel", description="ส่ง Control Panel (Admin เท่านั้น)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Hermanos'Dev — Control Panel",
        description=(
            "This control panel is for the project: **Hermanos'Dev Paid Script**\n"
            "If you're a buyer, click on the buttons below to redeem your key, "
            "get the script or get your role."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Sent by {interaction.user.name}")
    await interaction.response.send_message(embed=embed, view=ControlPanel())


# ===================================
#   /addkey <key> — เพิ่ม Key
# ===================================
@tree.command(name="addkey", description="เพิ่ม License Key (Admin เท่านั้น)")
@app_commands.describe(key="Key ที่ต้องการเพิ่ม เช่น HD-1234-5678-ABCD")
@app_commands.checks.has_permissions(administrator=True)
async def slash_addkey(interaction: discord.Interaction, key: str):
    data = load_data()
    if key in data["keys"]:
        await interaction.response.send_message(f"❌ Key `{key}` มีอยู่แล้ว!", ephemeral=True)
        return
    data["keys"][key] = {"used": False, "used_by": None}
    save_data(data)
    await interaction.response.send_message(f"✅ เพิ่ม Key `{key}` สำเร็จ!", ephemeral=True)


# ===================================
#   /removekey <key> — ลบ Key
# ===================================
@tree.command(name="removekey", description="ลบ License Key (Admin เท่านั้น)")
@app_commands.describe(key="Key ที่ต้องการลบ")
@app_commands.checks.has_permissions(administrator=True)
async def slash_removekey(interaction: discord.Interaction, key: str):
    data = load_data()
    if key not in data["keys"]:
        await interaction.response.send_message(f"❌ ไม่พบ Key `{key}`", ephemeral=True)
        return
    del data["keys"][key]
    save_data(data)
    await interaction.response.send_message(f"🗑️ ลบ Key `{key}` สำเร็จ!", ephemeral=True)


# ===================================
#   /resetuser @user — Reset HWID ให้ user
# ===================================
@tree.command(name="resetuser", description="Reset HWID ให้ User (Admin เท่านั้น)")
@app_commands.describe(member="User ที่ต้องการ Reset HWID")
@app_commands.checks.has_permissions(administrator=True)
async def slash_resetuser(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    uid = str(member.id)
    if uid not in data["users"]:
        await interaction.response.send_message(f"❌ ไม่พบข้อมูลของ {member.name}", ephemeral=True)
        return
    data["users"][uid].update({"hwid": None, "hwid_resets": 3})
    save_data(data)
    await interaction.response.send_message(f"✅ Reset HWID ของ {member.mention} สำเร็จ!", ephemeral=True)


# ===================================
#   /listkeys — ดู Key ทั้งหมด
# ===================================
@tree.command(name="listkeys", description="ดู Key ทั้งหมดในระบบ (Admin เท่านั้น)")
@app_commands.checks.has_permissions(administrator=True)
async def slash_listkeys(interaction: discord.Interaction):
    data = load_data()
    keys = data.get("keys", {})
    if not keys:
        await interaction.response.send_message("📭 ยังไม่มี Key ในระบบ", ephemeral=True)
        return

    lines = []
    for k, v in keys.items():
        status = "✅ ใช้แล้ว" if v.get("used") else "🟢 ว่างอยู่"
        lines.append(f"`{k}` — {status}")

    embed = discord.Embed(
        title=f"🔑 Keys ทั้งหมด ({len(keys)} ชุด)",
        description="\n".join(lines),
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ===================================
#   /userinfo @user — ดูข้อมูล user
# ===================================
@tree.command(name="userinfo", description="ดูข้อมูล User ในระบบ (Admin เท่านั้น)")
@app_commands.describe(member="User ที่ต้องการดูข้อมูล")
@app_commands.checks.has_permissions(administrator=True)
async def slash_userinfo(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    uid = str(member.id)
    info = data["users"].get(uid)
    if not info:
        await interaction.response.send_message(f"❌ ไม่พบข้อมูลของ {member.mention}", ephemeral=True)
        return
    embed = discord.Embed(title=f"👤 ข้อมูลของ {member.name}", color=discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🔑 Key", value=f"`{info.get('key_used','?')}`", inline=False)
    embed.add_field(name="🔄 HWID Resets เหลือ", value=str(info.get("hwid_resets", 0)), inline=True)
    embed.add_field(name="💻 HWID", value=f"`{info.get('hwid') or 'ยังไม่ได้ตั้ง'}`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ===================================
#   Error handler — บอกถ้าไม่ใช่ Admin
# ===================================
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {error}", ephemeral=True)


# ===================================
#   เริ่ม Bot + Sync Slash Commands
# ===================================
@bot.event
async def on_ready():
    bot.add_view(ControlPanel())
    await tree.sync()  # sync slash commands กับ Discord
    print(f"✅ Bot online: {bot.user}")
    print(f"   Slash commands synced!")

bot.run(TOKEN)
