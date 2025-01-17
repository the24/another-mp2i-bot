from __future__ import annotations

import datetime as dt
import json
import os
import random
from typing import TYPE_CHECKING, cast

import discord
import pytz
from discord import Member, TextChannel, ui
from discord.app_commands import command, guild_only
from discord.ext import tasks
from discord.ext.commands import Cog  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import Self

from utils import get_first_and_last_names
from utils.constants import GUILD_ID

if TYPE_CHECKING:
    from discord import Interaction, Message

    from bot import MP2IBot


class Fun(Cog):
    def __init__(self, bot: MP2IBot) -> None:
        self.bot = bot

        # reactions that can be randomly added under these users messages.
        self.users_reactions = {
            726867561924263946: ["🕳️"],
            1015216092920168478: ["🏳‍🌈"],
            433713351592247299: ["🩴"],
            199545535017779200: ["🪜"],
            823477539167141930: ["🥇"],
            533272313588613132: ["🥕"],
            777852203414454273: ["🐀"],
        }

        raw_birthdates: dict[str, str]
        if os.path.exists("./data/birthdates.json"):
            with open("./data/birthdates.json", "r") as f:
                raw_birthdates = json.load(f)
        else:
            raw_birthdates = {}

        self.birthdates: dict[int, dt.datetime] = {  # maps from user_ids to datetime
            bot.names_to_ids[get_first_and_last_names(name)]: dt.datetime.strptime(date, r"%d-%m-%Y")
            for name, date in raw_birthdates.items()
        }

    async def cog_load(self) -> None:
        self.general_channel = cast(TextChannel, await self.bot.fetch_channel(1015172827650998352))
        self.birthday.start()

    async def cog_unload(self) -> None:
        self.birthday.stop()

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID:  # only works into the MP2I guild.
            return

        # the bot is assumed admin on MP2I guild. We will not check permissions.

        if self.is_birthday(message.author.id):  # add 🎉 reaction if birthday
            await message.add_reaction("🎉")

        if "cqfd" in message.content.lower():  # add reaction if "cqfd" in message
            await message.add_reaction("<:prof:1015373456159805440>")

        # add reactions "OUI" on provocation
        if "tu veux te battre" in message.content.lower() or "vous voulez vous battre" in message.content.lower():
            await message.add_reaction("⭕")
            await message.add_reaction("🇺")
            await message.add_reaction("🇮")

        # add special reactions for specific users
        reactions = self.users_reactions.get(message.author.id)
        if reactions:
            # users are able to have multiple reactions assigned, so we select one ! (Not atm)
            reaction = random.choice(reactions)  # nosec

            # only add reactions with a chance of 1/25
            if random.randint(0, 25) == 0:  # nosec
                await message.add_reaction(reaction)

    def is_birthday(self, user_id: int) -> bool:
        """Tell if a user has birthday or not.

        Args:
            user_id (int): the user to check

        Returns:
            bool: also return False if the birthdate is unknown.
        """
        birthdate = self.birthdates.get(user_id)
        if not birthdate:  # if we don't have any informations about the user birthday, return False.
            return False
        now = dt.datetime.now()
        return birthdate.day == now.day and birthdate.month == now.month

    @command()
    @guild_only()
    async def ratio(self, inter: Interaction, user: Member) -> None:
        if not isinstance(inter.channel, discord.abc.Messageable):
            return

        message: Message | None = await discord.utils.find(
            lambda m: m.author.id == user.id, inter.channel.history(limit=100)
        )

        await inter.response.send_message(
            "Le ratio est à utiliser avec modération. (Je te le présenterais à l'occasion).", ephemeral=True
        )
        if message:
            response = await message.reply("RATIO!")
            await response.add_reaction("💟")

    @tasks.loop(time=dt.time(hour=7, tzinfo=pytz.timezone("Europe/Paris")))
    async def birthday(self) -> None:
        """At 7am, check if it's someone's birthday and send a message if it is."""
        now = dt.datetime.now()
        for user_id, birthday in self.birthdates.items():  # iter over {user_id: birthdate}
            if birthday.month == now.month and birthday.day == now.day:
                # All ids from birthdates needs to be in ids_to_names. Bugs will happen otherwise.
                name = self.bot.ids_to_names[user_id]
                await self.general_channel.send(
                    f"Eh ! {name.first} {name.last[0]}. a anniversaire ! Souhaitez-le lui !",
                    view=TellHappyBirthday(user_id),  # add a button to spam (lovely) the user with mentions.
                )


class TellHappyBirthday(ui.View):
    """A view with a single button to tell a user happy birthday (with mention <3).


    Args:
        user_id (int): the user who had birthday !
    """

    def __init__(self, user_id: int) -> None:

        self.user_id = user_id
        super().__init__(timeout=None)

    @ui.button(label="Happy Birthday !", emoji="🎉")
    async def tell_happy_birthday(self, inter: Interaction, button: ui.Button[Self]) -> None:
        await inter.response.send_message(
            f"{inter.user.display_name} souhaite un joyeux anniversaire à <@{self.user_id}> !"
        )


async def setup(bot: MP2IBot) -> None:
    await bot.add_cog(Fun(bot))
