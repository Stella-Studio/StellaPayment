import discord
from typing import List
from discord.ui import Button, View

class PaginatedView(View):
    def __init__(self, data: List[str], per_page, title):
        super().__init__(timeout=120)
        self.data = data
        self.page = 1
        self.title = title
        self.per_page = per_page
        self.max_page = max(1, (len(data) + per_page - 1) // per_page)
        self.message = None

    def update_buttons(self):
        self.clear_items()
        if self.page > 1: self.add_item(self.prev_page)
        if self.page < self.max_page: self.add_item(self.next_page)

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.blurple)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        self.page = max(1, self.page - 1)
        await self.update_view(interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.page = min(self.max_page, self.page + 1)
        await self.update_view(interaction)

    async def update_view(self, interaction: discord.Interaction):
        self.update_buttons()
        start_idx = (self.page - 1) * self.per_page
        embed = discord.Embed(title=self.title, description="\n".join(self.data[start_idx:start_idx + self.per_page]), color=discord.Color.blue())
        embed.set_footer(text=f"Trang {self.page}/{self.max_page}")
        await interaction.response.edit_message(embed=embed, view=self)

    async def send_message(self, interaction: discord.Interaction):
        self.update_buttons()
        start_idx = (self.page - 1) * self.per_page
        embed = discord.Embed(title=self.title, description="\n".join(self.data[start_idx:start_idx + self.per_page]), color=discord.Color.blue())
        embed.set_footer(text=f"Trang {self.page}/{self.max_page}")
        if not interaction.response.is_done(): await interaction.response.defer()
        self.message = await interaction.followup.send(embed=embed, view=self)