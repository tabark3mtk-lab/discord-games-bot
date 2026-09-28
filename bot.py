import os
import random
import asyncio
import discord

from discord.ext import commands
from discord import app_commands


# =========================================================
# إعداد البوت
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN غير موجود. أضف توكن البوت كـ Secret باسم DISCORD_TOKEN."
    )

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# عند تشغيل البوت
# =========================================================

@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync()

        print(f"Logged in as {bot.user}")
        print(f"Synced {len(synced)} commands.")

    except Exception as e:

        print("Sync error:", e)


# =========================================================
# 🪙 العملة
# =========================================================

@bot.tree.command(
    name="عملة",
    description="يقلب العملة"
)
async def coin(interaction: discord.Interaction):

    result = random.choice([
        "وجه 🪙",
        "كتابة 🪙"
    ])

    await interaction.response.send_message(
        f"النتيجة: **{result}**"
    )


# =========================================================
# 🎲 النرد
# =========================================================

@bot.tree.command(
    name="نرد",
    description="يرمي نرد من 1 إلى 6"
)
async def dice(interaction: discord.Interaction):

    number = random.randint(1, 6)

    await interaction.response.send_message(
        f"🎲 النتيجة: **{number}**"
    )


# =========================================================
# ✊✋✌️ حجر ورقة مقص - جماعية
# =========================================================

RPS_EMOJIS = {
    "حجر": "✊",
    "ورقة": "✋",
    "مقص": "✌️"
}


def rps_beats(move):

    return {
        "حجر": "مقص",
        "ورقة": "حجر",
        "مقص": "ورقة"
    }[move]


class RPSGame:

    def __init__(self, owner):

        self.owner = owner

        self.players = []

        self.started = False

        self.finished = False

        self.choices = {}


class RPSLobbyView(discord.ui.View):

    def __init__(self, game):

        super().__init__(timeout=600)

        self.game = game

    def player_list(self):

        if not self.game.players:
            return "ماكو لاعبين حالياً."

        return "\n".join(
            f"• {player.mention}"
            for player in self.game.players
        )

    @discord.ui.button(
        label="ادخل اللعبة",
        emoji="➕",
        style=discord.ButtonStyle.success
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.game.started:

            await interaction.response.send_message(
                "اللعبة بدأت بالفعل.",
                ephemeral=True
            )

            return

        if interaction.user.id in [
            player.id
            for player in self.game.players
        ]:

            await interaction.response.send_message(
                "أنت داخل اللعبة أصلاً.",
                ephemeral=True
            )

            return

        self.game.players.append(
            interaction.user
        )

        await interaction.response.edit_message(

            content=(
                "✊✋✌️ **حجر ورقة مقص**\n\n"
                f"**اللاعبون ({len(self.game.players)}):**\n"
                f"{self.player_list()}\n\n"
                "➕ ادخل اللعبة\n"
                "🚪 اخرج من اللعبة\n"
                "▶️ ابدأ اللعبة"
            ),

            view=self
        )

    @discord.ui.button(
        label="اخرج من اللعبة",
        emoji="🚪",
        style=discord.ButtonStyle.danger
    )
    async def leave(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.game.started:

            await interaction.response.send_message(
                "اللعبة بدأت، ما تقدر تطلع الآن.",
                ephemeral=True
            )

            return

        before = len(self.game.players)

        self.game.players = [
            player
            for player in self.game.players
            if player.id != interaction.user.id
        ]

        if len(self.game.players) == before:

            await interaction.response.send_message(
                "أنت مو داخل اللعبة.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(

            content=(
                "✊✋✌️ **حجر ورقة مقص**\n\n"
                f"**اللاعبون ({len(self.game.players)}):**\n"
                f"{self.player_list()}\n\n"
                "➕ ادخل اللعبة\n"
                "🚪 اخرج من اللعبة\n"
                "▶️ ابدأ اللعبة"
            ),

            view=self
        )

    @discord.ui.button(
        label="ابدأ اللعبة",
        emoji="▶️",
        style=discord.ButtonStyle.primary
    )
    async def start(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.game.owner.id:

            await interaction.response.send_message(
                "فقط صاحب اللعبة يقدر يبدأ.",
                ephemeral=True
            )

            return

        if len(self.game.players) < 2:

            await interaction.response.send_message(
                "لازم لاعبين اثنين على الأقل.",
                ephemeral=True
            )

            return

        self.game.started = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(

            content=(
                "✊✋✌️ **حجر ورقة مقص**\n\n"
                f"عدد اللاعبين: **{len(self.game.players)}**\n\n"
                "🎮 بدأت الجولة!"
            ),

            view=self
        )

        await run_rps_game(
            interaction,
            self.game
        )

        self.stop()


class RPSChoiceView(discord.ui.View):

    def __init__(self, game):

        super().__init__(timeout=35)

        self.game = game

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        if interaction.user.id not in [
            player.id
            for player in self.game.players
        ]:

            await interaction.response.send_message(
                "أنت مو لاعب بهذه الجولة.",
                ephemeral=True
            )

            return False

        if interaction.user.id in self.game.choices:

            await interaction.response.send_message(
                "أنت اخترت بالفعل.",
                ephemeral=True
            )

            return False

        return True

    async def choose(
        self,
        interaction,
        choice
    ):

        self.game.choices[
            interaction.user.id
        ] = choice

        await interaction.response.send_message(
            f"تم تسجيل اختيارك: {RPS_EMOJIS[choice]}",
            ephemeral=True
        )

        if len(self.game.choices) >= len(
            self.game.players
        ):

            self.stop()

    @discord.ui.button(
        label="حجر",
        emoji="✊",
        style=discord.ButtonStyle.primary
    )
    async def rock(self, interaction, button):

        await self.choose(
            interaction,
            "حجر"
        )

    @discord.ui.button(
        label="ورقة",
        emoji="✋",
        style=discord.ButtonStyle.success
    )
    async def paper(self, interaction, button):

        await self.choose(
            interaction,
            "ورقة"
        )

    @discord.ui.button(
        label="مقص",
        emoji="✌️",
        style=discord.ButtonStyle.danger
    )
    async def scissors(self, interaction, button):

        await self.choose(
            interaction,
            "مقص"
        )


async def run_rps_game(
    interaction,
    game
):

    players = game.players[:]

    round_number = 1

    while len(players) > 1:

        game.players = players

        game.choices = {}

        choice_view = RPSChoiceView(
            game
        )

        await interaction.followup.send(

            "✊✋✌️ **الجولة "
            f"{round_number}**\n\n"
            "كل لاعب يختار حجر أو ورقة أو مقص.\n"
            "عندك **35 ثانية**.",

            view=choice_view
        )

        await choice_view.wait()

        # اللاعبون الذين لم يختاروا
        chosen_ids = set(
            game.choices.keys()
        )

        players = [
            player
            for player in players
            if player.id in chosen_ids
        ]

        if len(players) <= 1:
            break

        moves = set(
            game.choices.values()
        )

        # نفس الحركة عند الجميع = إعادة الجولة
        if len(moves) == 1:

            await interaction.followup.send(
                "🤝 الكل اختار نفس الحركة، نعيد الجولة."
            )

            round_number += 1

            continue

        # إذا ظهرت الحركات الثلاث كلها
        if len(moves) == 3:

            result_text = "\n".join(

                f"• {player.mention}: "
                f"{RPS_EMOJIS[game.choices[player.id]]}"

                for player in players
            )

            await interaction.followup.send(

                f"🔄 **الجولة {round_number}**\n\n"
                f"{result_text}\n\n"
                "الثلاث حركات موجودة، لذلك ماكو فائز بالجولة.\n"
                "ننتقل للجولة التالية."
            )

            round_number += 1

            continue

        # حركتان فقط
        move_a, move_b = list(moves)

        winning_move = (
            move_a
            if rps_beats(move_a) == move_b
            else move_b
        )

        winners = [
            player
            for player in players
            if game.choices[player.id] == winning_move
        ]

        eliminated = [
            player
            for player in players
            if player not in winners
        ]

        result_text = "\n".join(

            f"• {player.mention}: "
            f"{RPS_EMOJIS[game.choices[player.id]]}"

            for player in players
        )

        eliminated_text = ", ".join(
            player.mention
            for player in eliminated
        )

        await interaction.followup.send(

            f"✊✋✌️ **الجولة {round_number}**\n\n"
            f"{result_text}\n\n"
            f"🏆 الفائزون بالجولة: "
            f"{', '.join(p.mention for p in winners)}\n"
            f"❌ خرج: {eliminated_text}"
        )

        players = winners

        round_number += 1

    if players:

        game.finished = True

        await interaction.followup.send(

            "🏆🏆 **انتهت اللعبة!**\n\n"
            f"الفائز: **{players[0].mention}**"
        )

    else:

        await interaction.followup.send(
            "انتهت اللعبة بدون فائز."
        )


@bot.tree.command(
    name="حجر_ورقة_مقص",
    description="لعبة حجر ورقة مقص بين اللاعبين"
)
async def rps(
    interaction: discord.Interaction
):

    game = RPSGame(
        interaction.user
    )

    game.players.append(
        interaction.user
    )

    view = RPSLobbyView(
        game
    )

    await interaction.response.send_message(

        "✊✋✌️ **حجر ورقة مقص**\n\n"
        "اللاعبين يدخلون ويطلعون من الأزرار.\n\n"
        "➕ ادخل اللعبة\n"
        "🚪 اخرج من اللعبة\n"
        "▶️ ابدأ اللعبة",

        view=view
    )


# =========================================================
# 🎯 روليت ترفيهية
# =========================================================

class RouletteView(discord.ui.View):

    def __init__(self, owner):

        super().__init__(timeout=600)

        self.owner = owner

        self.players = []

    def list_players(self):

        if not self.players:
            return "ماكو لاعبين."

        return "\n".join(
            f"• {player.mention}"
            for player in self.players
        )

    @discord.ui.button(
        label="ادخل",
        emoji="➕",
        style=discord.ButtonStyle.success
    )
    async def join(self, interaction, button):

        if interaction.user.id not in [
            p.id for p in self.players
        ]:

            self.players.append(
                interaction.user
            )

        await interaction.response.edit_message(

            content=(
                "🎯 **الروليت الترفيهية**\n\n"
                f"{self.list_players()}\n\n"
                "اضغط اختيار لما تجهزون."
            ),

            view=self
        )

    @discord.ui.button(
        label="اخرج",
        emoji="🚪",
        style=discord.ButtonStyle.danger
    )
    async def leave(self, interaction, button):

        self.players = [
            p for p in self.players
            if p.id != interaction.user.id
        ]

        await interaction.response.edit_message(

            content=(
                "🎯 **الروليت الترفيهية**\n\n"
                f"{self.list_players()}"
            ),

            view=self
        )

    @discord.ui.button(
        label="اختيار عشوائي",
        emoji="🎯",
        style=discord.ButtonStyle.primary
    )
    async def choose(self, interaction, button):

        if interaction.user.id != self.owner.id:

            await interaction.response.send_message(
                "صاحب اللعبة فقط.",
                ephemeral=True
            )

            return

        if len(self.players) < 2:

            await interaction.response.send_message(
                "لازم لاعبين اثنين على الأقل.",
                ephemeral=True
            )

            return

        winner = random.choice(
            self.players
        )

        await interaction.response.edit_message(

            content=(
                "🎯 **النتيجة العشوائية**\n\n"
                f"تم اختيار: **{winner.mention}**"
            ),

            view=None
        )

        self.stop()


@bot.tree.command(
    name="روليت",
    description="اختيار لاعب عشوائي للترفيه"
)
async def roulette(interaction):

    await interaction.response.send_message(

        "🎯 **الروليت الترفيهية**\n\n"
        "أدخلوا اللاعبين من الأزرار.",

        view=RouletteView(
            interaction.user
        )
    )


# =========================================================
# 💣 Mines
# =========================================================

class MinesGame:

    def __init__(self, player):

        self.player = player

        self.mines = set(
            random.sample(
                range(25),
                5
            )
        )

        self.safe = set()

        self.points = 0

        self.finished = False


class MinesView(discord.ui.View):

    def __init__(self, game):

        super().__init__(
            timeout=300
        )

        self.game = game

        for i in range(25):

            button = discord.ui.Button(

                label="⬜",

                style=discord.ButtonStyle.secondary,

                row=i // 5,

                custom_id=f"mine_{i}"

            )

            button.callback = (
                self.make_callback(i)
            )

            self.add_item(button)

        stop_button = discord.ui.Button(

            label="توقف",

            emoji="🏁",

            style=discord.ButtonStyle.success,

            row=4,

            custom_id="mine_stop"

        )

        stop_button.callback = (
            self.stop_game
        )

        self.add_item(
            stop_button
        )

    async def check_player(
        self,
        interaction
    ):

        if interaction.user.id != self.game.player.id:

            await interaction.response.send_message(
                "هذه اللعبة مو إلك.",
                ephemeral=True
            )

            return False

        if self.game.finished:

            await interaction.response.send_message(
                "اللعبة انتهت.",
                ephemeral=True
            )

            return False

        return True

    def make_callback(self, index):

        async def callback(interaction):

            if not await self.check_player(
                interaction
            ):
                return

            if (
                index in self.game.safe
                or
                index in self.game.mines
            ):

                await interaction.response.send_message(
                    "هذا المربع انفتح.",
                    ephemeral=True
                )

                return

            self.game.safe.add(
                index
            )

            self.game.points += 1

            button = next(

                b for b in self.children

                if getattr(
                    b,
                    "custom_id",
                    ""
                ) == f"mine_{index}"

            )

            button.label = "💎"

            button.style = (
                discord.ButtonStyle.success
            )

            button.disabled = True

            # كل المربعات الآمنة
            if len(self.game.safe) >= 20:

                self.game.finished = True

                for child in self.children:
                    child.disabled = True

                await interaction.response.edit_message(

                    content=(
                        "🏆 **فزت!**\n\n"
                        "فتحت كل المربعات الآمنة.\n"
                        f"النقاط: **{self.game.points}**"
                    ),

                    view=self
                )

                self.stop()

                return

            await interaction.response.edit_message(

                content=(
                    "💣 **Mines**\n\n"
                    f"النقاط: **{self.game.points}**\n\n"
                    "افتح مربع أو اضغط توقف."
                ),

                view=self
            )

        return callback

    async def stop_game(
        self,
        interaction
    ):

        if not await self.check_player(
            interaction
        ):
            return

        self.game.finished = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(

            content=(
                "🏁 **توقفت اللعبة**\n\n"
                f"النقاط: **{self.game.points}**"
            ),

            view=self
        )

        self.stop()


@bot.tree.command(
    name="ماينز",
    description="لعبة ألغام ترفيهية"
)
async def mines(
    interaction: discord.Interaction
):

    game = MinesGame(
        interaction.user
    )

    await interaction.response.send_message(

        "💣 **Mines**\n\n"
        "25 مربع.\n"
        "5 منها ألغام.\n"
        "اجمع نقاط من المربعات الآمنة.",

        view=MinesView(game)
    )


# =========================================================
# 🔴🟡 توصيل 4
# =========================================================

class ConnectFourGame:

    def __init__(self, first):

        self.players = [
            first
        ]

        self.board = [

            ["⚪"] * 7

            for _ in range(6)

        ]

        self.turn = 0

        self.finished = False

    def render(self):

        board = "\n".join(

            " ".join(row)

            for row in self.board

        )

        players = (
            f"🔴 {self.players[0].mention}"
        )

        if len(self.players) == 2:

            players += (
                f"\n🟡 {self.players[1].mention}"
            )

            turn = (
                self.players[
                    self.turn
                ].mention
            )

        else:

            turn = (
                "بانتظار اللاعب الثاني..."
            )

        return (

            "🔴🟡 **توصيل 4**\n\n"

            f"{players}\n\n"

            f"{board}\n\n"

            "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣\n\n"

            f"الدور: {turn}"

        )

    def drop(
        self,
        column,
        symbol
    ):

        for row in range(
            5,
            -1,
            -1
        ):

            if self.board[row][column] == "⚪":

                self.board[row][column] = symbol

                return row

        return None

    def count(
        self,
        row,
        column,
        dr,
        dc,
        symbol
    ):

        total = 0

        row += dr
        column += dc

        while (

            0 <= row < 6

            and

            0 <= column < 7

            and

            self.board[row][column] == symbol

        ):

            total += 1

            row += dr
            column += dc

        return total

    def is_winner(
        self,
        row,
        column,
        symbol
    ):

        directions = [

            (0, 1),
            (1, 0),
            (1, 1),
            (1, -1)

        ]

        for dr, dc in directions:

            total = (

                1

                + self.count(
                    row,
                    column,
                    dr,
                    dc,
                    symbol
                )

                + self.count(
                    row,
                    column,
                    -dr,
                    -dc,
                    symbol
                )

            )

            if total >= 4:

                return True

        return False

    def is_draw(self):

        return all(
            self.board[0][c] != "⚪"
            for c in range(7)
        )


class ConnectFourView(discord.ui.View):

    def __init__(self, game):

        super().__init__(
            timeout=900
        )

        self.game = game

        for column in range(7):

            button = discord.ui.Button(

                label=str(column + 1),

                style=discord.ButtonStyle.primary,

                row=0,

                custom_id=f"connect_{column}"

            )

            button.callback = (
                self.make_callback(column)
            )

            self.add_item(
                button
            )

        join = discord.ui.Button(

            label="ادخل اللعبة",

            emoji="➕",

            style=discord.ButtonStyle.success,

            row=1

        )

        join.callback = (
            self.join_game
        )

        self.add_item(
            join
        )

        self.join_button = join

        leave = discord.ui.Button(

            label="اخرج من اللعبة",

            emoji="🚪",

            style=discord.ButtonStyle.danger,

            row=1

        )

        leave.callback = (
            self.leave_game
        )

        self.add_item(
            leave
        )

        self.leave_button = leave

    async def join_game(
        self,
        interaction
    ):

        if len(self.game.players) >= 2:

            await interaction.response.send_message(
                "اللعبة مكتملة.",
                ephemeral=True
            )

            return

        if interaction.user.id == self.game.players[0].id:

            await interaction.response.send_message(
                "أنت اللاعب الأول.",
                ephemeral=True
            )

            return

        self.game.players.append(
            interaction.user
        )

        self.join_button.disabled = True
        self.leave_button.disabled = True

        await interaction.response.edit_message(

            content=self.game.render(),

            view=self
        )

    async def leave_game(
        self,
        interaction
    ):

        if interaction.user.id == self.game.players[0].id:

            await interaction.response.send_message(
                "صاحب الجولة ما يقدر يطلع منها.",
                ephemeral=True
            )

            return

        self.game.players = [

            p for p in self.game.players

            if p.id != interaction.user.id

        ]

        await interaction.response.edit_message(

            content=self.game.render(),

            view=self
        )

    def make_callback(
        self,
        column
    ):

        async def callback(interaction):

            if self.game.finished:

                await interaction.response.send_message(
                    "اللعبة انتهت.",
                    ephemeral=True
                )

                return

            if len(self.game.players) < 2:

                await interaction.response.send_message(
                    "انتظر اللاعب الثاني.",
                    ephemeral=True
                )

                return

            current = (
                self.game.players[
                    self.game.turn
                ]
            )

            if interaction.user.id != current.id:

                await interaction.response.send_message(
                    "مو دورك.",
                    ephemeral=True
                )

                return

            symbol = (
                "🔴"
                if self.game.turn == 0
                else "🟡"
            )

            row = self.game.drop(
                column,
                symbol
            )

            if row is None:

                await interaction.response.send_message(
                    "هذا العمود ممتلئ.",
                    ephemeral=True
                )

                return

            if self.game.is_winner(
                row,
                column,
                symbol
            ):

                self.game.finished = True

                for child in self.children:
                    child.disabled = True

                await interaction.response.edit_message(

                    content=(
                        self.game.render()
                        +
                        f"\n\n🏆 الفائز: **{current.mention}**"
                    ),

                    view=self
                )

                self.stop()

                return

            if self.game.is_draw():

                self.game.finished = True

                for child in self.children:
                    child.disabled = True

                await interaction.response.edit_message(

                    content=(
                        self.game.render()
                        +
                        "\n\n🤝 **تعادل!**"
                    ),

                    view=self
                )

                self.stop()

                return

            self.game.turn = (
                1 - self.game.turn
            )

            await interaction.response.edit_message(

                content=self.game.render(),

                view=self
            )

        return callback


@bot.tree.command(
    name="توصيل",
    description="لعبة توصيل 4 - لوحة 6x7"
)
async def connect_four(
    interaction: discord.Interaction
):

    game = ConnectFourGame(
        interaction.user
    )

    await interaction.response.send_message(

        game.render(),

        view=ConnectFourView(game)
    )


# =========================================================
# 🪑 الكراسي الموسيقية
# =========================================================

class ChairsGame:

    def __init__(self, owner):

        self.owner = owner

        self.players = []

        self.started = False


class ChairsView(discord.ui.View):

    def __init__(self, game):

        super().__init__(
            timeout=600
        )

        self.game = game

    def player_text(self):

        if not self.game.players:

            return "ماكو لاعبين."

        return "\n".join(

            f"• {p.mention}"

            for p in self.game.players

        )

    @discord.ui.button(
        label="ادخل اللعبة",
        emoji="➕",
        style=discord.ButtonStyle.success
    )
    async def join(
        self,
        interaction,
        button
    ):

        if self.game.started:

            await interaction.response.send_message(
                "اللعبة بدأت.",
                ephemeral=True
            )

            return

        if interaction.user.id not in [
            p.id for p in self.game.players
        ]:

            self.game.players.append(
                interaction.user
            )

        await interaction.response.edit_message(

            content=(
                "🪑 **الكراسي الموسيقية**\n\n"
                f"{self.player_text()}\n\n"
                "اضغط ابدأ لما تجهزون."
            ),

            view=self
        )

    @discord.ui.button(
        label="اخرج من اللعبة",
        emoji="🚪",
        style=discord.ButtonStyle.danger
    )
    async def leave(
        self,
        interaction,
        button
    ):

        if self.game.started:
            return

        self.game.players = [

            p for p in self.game.players

            if p.id != interaction.user.id

        ]

        await interaction.response.edit_message(

            content=(
                "🪑 **الكراسي الموسيقية**\n\n"
                f"{self.player_text()}"
            ),

            view=self
        )

    @discord.ui.button(
        label="ابدأ",
        emoji="▶️",
        style=discord.ButtonStyle.primary
    )
    async def start(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.game.owner.id:

            await interaction.response.send_message(
                "صاحب اللعبة فقط.",
                ephemeral=True
            )

            return

        if len(self.game.players) < 2:

            await interaction.response.send_message(
                "لازم لاعبين اثنين على الأقل.",
                ephemeral=True
            )

            return

        self.game.started = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(

            content=(
                "🪑 **بدأت الكراسي الموسيقية!**\n\n"
                "🎵 الموسيقى بدأت..."
            ),

            view=self
        )

        alive = self.game.players[:]

        while len(alive) > 1:

            await asyncio.sleep(3)

            eliminated = random.choice(
                alive
            )

            alive.remove(
                eliminated
            )

            await interaction.edit_original_response(

                content=(
                    "🪑 **الكراسي الموسيقية**\n\n"
                    f"❌ خرج: {eliminated.mention}\n\n"
                    "👥 الباقون:\n"
                    +
                    "\n".join(
                        p.mention
                        for p in alive
                    )
                ),

                view=None
            )

            await asyncio.sleep(2)

        await interaction.edit_original_response(

            content=(
                "🏆 **الفائز بالكراسي الموسيقية:**\n\n"
                f"{alive[0].mention}"
            ),

            view=None
        )

        self.stop()


@bot.tree.command(
    name="كراسي",
    description="لعبة الكراسي الموسيقية"
)
async def chairs(
    interaction: discord.Interaction
):

    game = ChairsGame(
        interaction.user
    )

    await interaction.response.send_message(

        "🪑 **الكراسي الموسيقية**\n\n"
        "ادخلوا اللعبة من الزر.",

        view=ChairsView(game)
    )


# =========================================================
# 🎭 مافيا
# =========================================================

MAFIA_GAMES = {}


class MafiaGame:

    def __init__(
        self,
        owner,
        channel
    ):

        self.owner = owner

        self.channel = channel

        self.players = []

        self.roles = {}

        self.alive = set()

        self.started = False

        self.phase = "lobby"

        self.votes = {}

        self.kill_target = None

        self.save_target = None

    def create_roles(self):

        count = len(
            self.players
        )

        mafia_count = max(
            1,
            count // 4
        )

        roles = (
            ["Mafia"] * mafia_count
        )

        if count >= 5:
            roles.append("Doctor")

        if count >= 6:
            roles.append("Detective")

        while len(roles) < count:

            roles.append(
                "Citizen"
            )

        random.shuffle(
            roles
        )

        return roles

    def winner(self):

        mafia = sum(

            1

            for player_id in self.alive

            if self.roles.get(
                player_id
            ) == "Mafia"

        )

        citizens = (
            len(self.alive)
            - mafia
        )

        if mafia == 0:

            return (
                "🎉 **المدينة فازت!**\n"
                "تم القضاء على كل المافيا."
            )

        if mafia >= citizens:

            return (
                "🔴 **المافيا فازت!**"
            )

        return None


class MafiaLobbyView(discord.ui.View):

    def __init__(self, game):

        super().__init__(
            timeout=900
        )

        self.game = game

    def players_text(self):

        if not self.game.players:
            return "ماكو لاعبين."

        return "\n".join(

            f"• {p.mention}"

            for p in self.game.players

        )

    @discord.ui.button(
        label="ادخل اللعبة",
        emoji="➕",
        style=discord.ButtonStyle.success
    )
    async def join(
        self,
        interaction,
        button
    ):

        if self.game.started:

            await interaction.response.send_message(
                "اللعبة بدأت.",
                ephemeral=True
            )

            return

        if interaction.user.id not in [

            p.id
            for p in self.game.players

        ]:

            self.game.players.append(
                interaction.user
            )

        await interaction.response.edit_message(

            content=(
                "🎭 **مافيا**\n\n"
                f"عدد اللاعبين: **{len(self.game.players)}**\n\n"
                f"{self.players_text()}\n\n"
                "الحد الأدنى 6 لاعبين."
            ),

            view=self
        )

    @discord.ui.button(
        label="اخرج من اللعبة",
        emoji="🚪",
        style=discord.ButtonStyle.danger
    )
    async def leave(
        self,
        interaction,
        button
    ):

        if self.game.started:
            return

        self.game.players = [

            p

            for p in self.game.players

            if p.id != interaction.user.id

        ]

        await interaction.response.edit_message(

            content=(
                "🎭 **مافيا**\n\n"
                f"عدد اللاعبين: **{len(self.game.players)}**\n\n"
                f"{self.players_text()}"
            ),

            view=self
        )

    @discord.ui.button(
        label="ابدأ",
        emoji="▶️",
        style=discord.ButtonStyle.primary
    )
    async def start(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.game.owner.id:

            await interaction.response.send_message(
                "صاحب اللعبة فقط.",
                ephemeral=True
            )

            return

        if len(self.game.players) < 6:

            await interaction.response.send_message(
                "المافيا تحتاج 6 لاعبين على الأقل.",
                ephemeral=True
            )

            return

        self.game.started = True

        for child in self.children:
            child.disabled = True

        roles = self.game.create_roles()

        self.game.roles = {

            player.id: roles[i]

            for i, player
            in enumerate(
                self.game.players
            )

        }

        self.game.alive = set(

            player.id

            for player
            in self.game.players

        )

        # إرسال الدور بالخاص
        for player in self.game.players:

            role = self.game.roles[
                player.id
            ]

            try:

                await player.send(

                    "🎭 **دورك في المافيا**\n\n"
                    f"دورك: **{role}**\n\n"
                    "لا تخبر اللاعبين بدورك."
                )

            except discord.Forbidden:
                pass

        await interaction.response.edit_message(

            content=(
                "🎭 **بدأت لعبة المافيا!**\n\n"
                "تم إرسال الأدوار بالخاص.\n"
                "🌙 سيبدأ الليل الآن."
            ),

            view=self
        )

        self.stop()

        await run_mafia(
            self.game
        )


async def run_mafia(game):

    channel = game.channel

    while game.started:

        # =================================================
        # الليل
        # =================================================

        game.phase = "night"

        game.kill_target = None
        game.save_target = None

        await channel.send(

            "🌙 **بدأ الليل**\n\n"
            "المافيا والطبيب والمحقق يستخدمون أوامرهم الخاصة.\n"
            "مدة الليل: **30 ثانية**."
        )

        await asyncio.sleep(30)

        # قتل المافيا
        target = game.kill_target

        # حماية الطبيب
        saved = game.save_target

        if (
            target
            and target in game.alive
            and target != saved
        ):

            game.alive.remove(
                target
            )

            await channel.send(
                f"☀️ في الصباح، تم العثور على لاعب خارج اللعبة: <@{target}>"
            )

        else:

            await channel.send(
                "☀️ انتهى الليل ولم يخرج أحد."
            )

        winner = game.winner()

        if winner:

            await channel.send(
                winner
            )

            game.started = False

            break

        # =================================================
        # النهار
        # =================================================

        game.phase = "day"

        game.votes = {}

        alive_mentions = ", ".join(

            f"<@{player_id}>"

            for player_id in game.alive

        )

        await channel.send(

            "☀️ **بدأ النهار**\n\n"
            f"الأحياء:\n{alive_mentions}\n\n"
            "ناقشوا واستخدموا:\n"
            "`/مافيا_تصويت`"
            " للتصويت على لاعب.\n\n"
            "مدة التصويت: **30 ثانية**."
        )

        await asyncio.sleep(30)

        if game.votes:

            counts = {}

            for target in game.votes.values():

                if target in game.alive:

                    counts[target] = (
                        counts.get(
                            target,
                            0
                        ) + 1
                    )

            if counts:

                highest = max(
                    counts.values()
                )

                top = [

                    player_id

                    for player_id, votes
                    in counts.items()

                    if votes == highest

                ]

                if len(top) == 1:

                    eliminated = top[0]

                    game.alive.remove(
                        eliminated
                    )

                    await channel.send(

                        "⚖️ **نتيجة التصويت**\n\n"
                        f"تم إخراج <@{eliminated}>."
                    )

                else:

                    await channel.send(
                        "⚖️ صار تعادل، ما خرج أحد."
                    )

        else:

            await channel.send(
                "⚖️ ماكو أصوات، ما خرج أحد."
            )

        winner = game.winner()

        if winner:

            await channel.send(
                winner
            )

            game.started = False

            break


@bot.tree.command(
    name="مافيا",
    description="إنشاء لعبة مافيا"
)
async def mafia(
    interaction: discord.Interaction
):

    if interaction.guild_id in MAFIA_GAMES:

        old_game = MAFIA_GAMES[
            interaction.guild_id
        ]

        if old_game.started:

            await interaction.response.send_message(
                "هناك لعبة مافيا شغالة بالفعل.",
                ephemeral=True
            )

            return

    game = MafiaGame(

        interaction.user,

        interaction.channel

    )

    game.players.append(
        interaction.user
    )

    MAFIA_GAMES[
        interaction.guild_id
    ] = game

    await interaction.response.send_message(

        "🎭 **لعبة المافيا**\n\n"
        "اضغط **ادخل اللعبة** حتى تدخل.\n"
        "اضغط **اخرج من اللعبة** حتى تطلع.\n"
        "تحتاج اللعبة 6 لاعبين على الأقل.",

        view=MafiaLobbyView(
            game
        )
    )


# =========================================================
# مافيا - قتل
# =========================================================

@bot.tree.command(
    name="مافيا_قتل",
    description="المافيا تختار لاعباً"
)
@app_commands.describe(
    target="اللاعب الذي تريد استهدافه"
)
async def mafia_kill(
    interaction,
    target: discord.Member
):

    game = MAFIA_GAMES.get(
        interaction.guild_id
    )

    if not game:

        await interaction.response.send_message(
            "ماكو لعبة مافيا.",
            ephemeral=True
        )

        return

    if game.phase != "night":

        await interaction.response.send_message(
            "هذا الأمر متاح أثناء الليل فقط.",
            ephemeral=True
        )

        return

    if interaction.user.id not in game.alive:

        await interaction.response.send_message(
            "أنت خارج اللعبة.",
            ephemeral=True
        )

        return

    if game.roles.get(
        interaction.user.id
    ) != "Mafia":

        await interaction.response.send_message(
            "هذا الأمر للمافيا فقط.",
            ephemeral=True
        )

        return

    if target.id not in game.alive:

        await interaction.response.send_message(
            "اللاعب غير موجود في اللعبة.",
            ephemeral=True
        )

        return

    if game.roles.get(
        target.id
    ) == "Mafia":

        await interaction.response.send_message(
            "ما تقدر تستهدف لاعب من المافيا.",
            ephemeral=True
        )

        return

    game.kill_target = target.id

    await interaction.response.send_message(
        f"🔴 تم تسجيل الهدف: {target.mention}",
        ephemeral=True
    )


# =========================================================
# مافيا - الطبيب
# =========================================================

@bot.tree.command(
    name="مافيا_حماية",
    description="الطبيب يحمي لاعباً"
)
@app_commands.describe(
    target="اللاعب الذي تريد حمايته"
)
async def mafia_save(
    interaction,
    target: discord.Member
):

    game = MAFIA_GAMES.get(
        interaction.guild_id
    )

    if not game:

        await interaction.response.send_message(
            "ماكو لعبة مافيا.",
            ephemeral=True
        )

        return

    if game.phase != "night":

        await interaction.response.send_message(
            "هذا الأمر متاح بالليل فقط.",
            ephemeral=True
        )

        return

    if game.roles.get(
        interaction.user.id
    ) != "Doctor":

        await interaction.response.send_message(
            "هذا الأمر للطبيب فقط.",
            ephemeral=True
        )

        return

    if target.id not in game.alive:

        await interaction.response.send_message(
            "اللاعب غير موجود.",
            ephemeral=True
        )

        return

    game.save_target = target.id

    await interaction.response.send_message(
        f"💚 تمت حماية {target.mention}",
        ephemeral=True
    )


# =========================================================
# مافيا - المحقق
# =========================================================

@bot.tree.command(
    name="مافيا_تحقيق",
    description="المحقق يفحص لاعباً"
)
@app_commands.describe(
    target="اللاعب الذي تريد التحقيق معه"
)
async def mafia_check(
    interaction,
    target: discord.Member
):

    game = MAFIA_GAMES.get(
        interaction.guild_id
    )

    if not game:

        await interaction.response.send_message(
            "ماكو لعبة مافيا.",
            ephemeral=True
        )

        return

    if game.phase != "night":

        await interaction.response.send_message(
            "هذا الأمر متاح بالليل فقط.",
            ephemeral=True
        )

        return

    if game.roles.get(
        interaction.user.id
    ) != "Detective":

        await interaction.response.send_message(
            "هذا الأمر للمحقق فقط.",
            ephemeral=True
        )

        return

    if target.id not in game.alive:

        await interaction.response.send_message(
            "اللاعب غير موجود.",
            ephemeral=True
        )

        return

    role = game.roles.get(
        target.id
    )

    await interaction.response.send_message(

        f"🔎 نتيجة التحقيق:\n"
        f"**{target.display_name}** دوره **{role}**",

        ephemeral=True
    )


# =========================================================
# مافيا - التصويت
# =========================================================

@bot.tree.command(
    name="مافيا_تصويت",
    description="تصويت النهار"
)
@app_commands.describe(
    target="اللاعب الذي تصوت عليه"
)
async def mafia_vote(
    interaction,
    target: discord.Member
):

    game = MAFIA_GAMES.get(
        interaction.guild_id
    )

    if not game:

        await interaction.response.send_message(
            "ماكو لعبة مافيا.",
            ephemeral=True
        )

        return

    if game.phase != "day":

        await interaction.response.send_message(
            "التصويت متاح بالنهار فقط.",
            ephemeral=True
        )

        return

    if interaction.user.id not in game.alive:

        await interaction.response.send_message(
            "أنت خارج اللعبة.",
            ephemeral=True
        )

        return

    if target.id not in game.alive:

        await interaction.response.send_message(
            "هذا اللاعب مو داخل اللعبة.",
            ephemeral=True
        )

        return

    game.votes[
        interaction.user.id
    ] = target.id

    await interaction.response.send_message(
        f"⚖️ تم تسجيل تصويتك ضد {target.mention}.",
        ephemeral=True
    )


# =========================================================
# تشغيل البوت
# =========================================================

bot.run(TOKEN)