import os
import asyncio

import disnake
from disnake.ext import commands
from dotenv import dotenv_values

import shitty_chessgamelogic as chess

config = dotenv_values(".env")

token = config['token']

async def playOverwrite(self, lobby):

    await lobby.send("> Welcome to this new game of chess, you have **10** minutes to make **a** move or you lose.\nGLHF all !")
    hello = await lobby.send("Use this thread to navigate to previous moves")
    await hello.pin()

    thread = await lobby.create_thread(name = "You can click the moves to go see its board state.\n", message=hello)

    white = disnake.utils.get(lobby.guild.roles, name="chessbot team white")
    black = disnake.utils.get(lobby.guild.roles, name="chessbot team black")

    roles = [white, black]

    def createcheck(role):
        return lambda message: message.channel == lobby and role in message.author.roles

    dict = {1 : "**White**", -1 : "**Black**"}

    while True:

        if self.history:
            lastmove = ' *' + self.history[-1] + '*'

        else:
            lastmove = 'None'

        payload = disnake.Embed(title = dict[self.turn] + " to play.", description = "Last move:" + lastmove)
        payload.add_field(name = "Current boardstate:", value = str(self).replace('♟', '\\♟').replace('.', '   .   ') )

        # dict[self.turn] + " to play. Last move:" + lastmove + '\n\n\n' + str(self).replace('♟', '\\♟').replace('.', '   .   ')

        board_msg = await lobby.send(embed = payload)

        if self.history:
            lastmove = self.history[-1]
            button = disnake.ui.Button(label = lastmove, url = board_msg.jump_url)
            if self.turn == -1:
                view = disnake.ui.View(timeout = None)
                view.add_item(button)
                thread_msg = await thread.send(content = str(len(self.history)//2) + '. ', view = view )
            else:
                view.add_item(button)
                await thread_msg.edit(content = str(len(self.history)//2) + '. ', view = view )
        else:
            button = disnake.ui.Button(label = "Game Start", url = board_msg.jump_url)
            view = disnake.ui.View(timeout = None)
            view.add_item(button)
            thread_msg = await thread.send(content = str(len(self.history)//2) + '. ', view = view )

        self.checkgamestatus()

        if self.game_status != '':
            break

        while True:
            try:
                move = await bot.wait_for('message', timeout=600.0, check = createcheck(roles[(self.turn-1)//2]))
                print(move.content)

            except asyncio.TimeoutError:
                self.game_status = '> ' + dict[self.turn] + " `lost` on time."
            else:

                try:
                    if move.content == 'resign':
                        self.game_status = dict[self.turn] + ' resigns.'
                    else:
                        self.playturn(move.content)

                except chess.InvalidMove:
                    await lobby.send('Invalid Move (can be my fault)')
                except chess.AmbiguousMove:
                    await lobby.send('Ambiguous Move')
                except chess.ParseError:
                    await lobby.send('Failed to parse Move')
                else:
                    break


    await lobby.send('> **' + self.game_status + '**')

chess.Game.play = playOverwrite

bot = commands.Bot(
    command_prefix=commands.when_mentioned,
    # Insert IDs of your test guilds below, if
    # you want the context menus to instantly appear.
    # Without test_guilds specified, your commands will
    # register globally in ~1 hour.
)

@bot.event
async def on_ready():
    print("Bot is ready")

def create_overwrites(ctx, *objects):
    """This is just a helper function that creates the overwrites for the
    voice/text channels.
    A `disnake.PermissionOverwrite` allows you to determine the permissions
    of an object, whether it be a `disnake.Role` or a `disnake.Member`.
    In this case, the `view_channel` permission is being used to hide the channel
    from being viewed by whoever does not meet the criteria, thus creating a
    secret channel.
    """

    # a dict comprehension is being utilised here to set the same permission overwrites
    # for each `disnake.Role` or `disnake.Member`.
    overwrites = {obj: disnake.PermissionOverwrite(view_channel=True) for obj in objects}

    # prevents the default role (@everyone) from viewing the channel
    # if it isn't already allowed to view the channel.
    overwrites.setdefault(ctx.guild.default_role, disnake.PermissionOverwrite(view_channel=False))


    return overwrites

# Define a simple View that gives us a confirmation menu
class Confirm(disnake.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @disnake.ui.button(label="Confirm", style=disnake.ButtonStyle.red)
    async def confirm(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Deleting...", ephemeral=True)
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.grey)
    async def cancel(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_message("Aborted.", ephemeral=True)
        self.value = False
        self.stop()

async def ask(ctx: commands.Context):
    """Asks the user a question to confirm something."""
    # We create the view and assign it to a variable so we can wait for it later.
    view = Confirm()
    await ctx.send("Do you want to delete the chessbot channels and roles?", view=view)
    # Wait for the View to stop listening for input...
    await view.wait()

    return view.value

@bot.command(name = 'setupforthefirsttime')
async def setup(ctx: disnake.ApplicationCommandInteraction):
    if not disnake.utils.get(ctx.guild.channels, name='chessbot gameroom'):

        white = await ctx.guild.create_role(name="chessbot team white", colour = disnake.Colour.from_rgb(255,255,255), reason="chessbot setup")
        black = await ctx.guild.create_role(name="chessbot team black", colour = disnake.Colour.from_rgb(1,1,1), reason="chessbot setup")

        roles = [white, black]

        category = await ctx.guild.create_category_channel(name = "chessbot gameroom", reason="chessbot setup")
        lobby = await ctx.guild.create_text_channel(name = "chessbot lobby", category = category, reason="chessbot setup")

        for role in roles:
            overwrites = create_overwrites(ctx, role)
            await ctx.guild.create_text_channel(name = role.name, overwrites=overwrites, category = category, reason="chessbot setup")
            await ctx.guild.create_voice_channel(name = role.name, overwrites=overwrites, category = category, reason="chessbot setup")

@bot.command(name = 'cleanupforthelasttime')
async def cleanup(ctx: disnake.ApplicationCommandInteraction):
    if await ask(ctx):
        for channel in ctx.guild.channels:
            if channel.name in {"chessbot gameroom", "chessbot-team-white", "chessbot-team-black", "chessbot-lobby", "chessbot team black", "chessbot team white"}:
                await channel.delete(reason = "chessbot cleanup")

        for role in ctx.guild.roles:
            if role.name in {"chessbot team white", "chessbot team black"}:
                await role.delete(reason = "chessbot cleanup")


# Defines a custom Select containing colour options
# that the user can choose. The callback function
# of this class is called when the user changes their choice
class Dropdown(disnake.ui.Select):
    def __init__(self):

        # Set the options that will be presented inside the dropdown
        options = [
            disnake.SelectOption(
                label="White", description="I want to play with the White pieces", emoji="⬜"
            ),
            disnake.SelectOption(
                label="Black", description="I want to play with the Black pieces", emoji="⬛"
            )
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Click on me to choose a team",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: disnake.MessageInteraction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.

        white = disnake.utils.get(interaction.guild.roles, name="chessbot team white")
        black = disnake.utils.get(interaction.guild.roles, name="chessbot team black")

        await interaction.response.send_message(f"Protip: don't tell anyone but you can switch midmatch to spy on others (or just be a server admin)", ephemeral=True)
        if self.values[0] == "White":
            await interaction.user.add_roles(white)
            await interaction.user.remove_roles(black)

        elif self.values[0] == "Black":
            await interaction.user.add_roles(black)
            await interaction.user.remove_roles(white)



class DropdownView(disnake.ui.View):
    def __init__(self):
        super().__init__()

        # Adds the dropdown to our view object.
        self.add_item(Dropdown())



game_isrunnng = []
        
async def chooseside(ctx):
    """Sends a message with our dropdown containing colours"""
    url = disnake.utils.get(ctx.guild.channels, name='chessbot-lobby').jump_url
    # Create the view containing our dropdown
    view = DropdownView()

    button_goto = disnake.ui.Button(label="Go to channel", style=disnake.ButtonStyle.gray, url = url)
    view.add_item(button_goto)

    # Sending a message containing our view
    await ctx.send("", view=view)

@bot.slash_command()
async def playchess(ctx: disnake.ApplicationCommandInteraction):
    lobby = disnake.utils.get(ctx.guild.channels, name='chessbot-lobby')
    if lobby is None:
        await ctx.response.send_message("Whoops, seems like I was not setup properly...\nTry '@chessbot setmeupforthefirsttime' for the setup\nand '@chessbot cleanupforthelasttime' to delete everything", ephemeral=True)
        return
    
    if ctx.guild in game_isrunning:
        await ctx.response.send_message("A game is still in progress !", ephemeral=True)
        return

    game_isrunnng.append(ctx.guild)
    
    await chooseside(ctx)
    game = chess.Game()
    await game.play(lobby)
    
    game_isrunning.append(ctx.guild)
    
bot.run(token)
