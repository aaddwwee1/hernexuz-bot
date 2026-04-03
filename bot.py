import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from flask import Flask
from threading import Thread

# ===================================
#   ระบบ Keep Alive (Flask)
# ===================================
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    # Render จะใช้ Port จาก Environment หรือ 8080 เป็นค่าเริ่มต้น
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

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
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ===================================
#   ตั้งค่า Bot
# ===================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

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
        role = interaction.guild.get_role(1481631709693743104)
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
#   Slash Commands (Admin)
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

@tree.command(name="addkey", description="เพิ่ม License Key (Admin เท่านั้น)")
@app_commands.describe(key="Key ที่ต้องการเพิ่ม")
@app_commands.checks.has_permissions(administrator=True)
async def slash_addkey(interaction: discord.Interaction, key: str):
    data = load_data()
    if key in data["keys"]:
        await interaction.response.send_message(f"❌ Key `{key}` มีอยู่แล้ว!", ephemeral=True)
        return
    data["keys"][key] = {"used": False, "used_by": None}
    save_data(data)
    await interaction.response.send_message(f"✅ เพิ่ม Key `{key}` สำเร็จ!", ephemeral=True)

# ... (คำสั่งอื่นๆ เหมือนเดิมของคุณ) ...

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {error}", ephemeral=True)

# ===================================
#   เริ่ม Bot + Keep Alive
# ===================================
@bot.event
async def on_ready():
    bot.add_view(ControlPanel())
    await tree.sync()
    print(f"✅ Bot online: {bot.user}")
    print(f"📡 Web Server started!")

if __name__ == "__main__":
    if TOKEN:
        keep_alive()  # <--- เรียกใช้งานตรงนี้
        bot.run(TOKEN)
    else:
        print("❌ ERROR: TOKEN not found in Environment Variables")
