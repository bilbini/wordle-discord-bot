# bot.py

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from wordle_game import WordleGame, GameState
from storage import storage
from image_generator import image_generator

# Load environment variables
load_dotenv()

class DiscordWordleBot:
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        # Create bot instance with slash commands
        self.bot = commands.Bot(command_prefix="", intents=intents)
        self.token = os.getenv("DISCORD_TOKEN")
        self.letter_emojis = {}  # name -> discord.Emoji
        
        # Register event handlers and slash commands
        self._register_handlers()
        self._register_slash_commands()

    def _register_handlers(self):
        """Register Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            print(f"Logged in as {self.bot.user}")
            
            # Sync slash commands to all guilds
            try:
                synced = await self.bot.tree.sync()
                print(f"Synced {len(synced)} slash commands globally")
                
                # Also sync to each guild for faster availability
                for guild in self.bot.guilds:
                    await self.bot.tree.sync(guild=guild)
                    print(f"Synced commands to guild: {guild.name}")
                    
            except Exception as e:
                print(f"Failed to sync commands: {e}")
            
            print("Slash commands are ready!")
            self._build_letter_emoji_cache()
        
        @self.bot.event
        async def on_guild_join(guild):
            """Sync commands when bot joins a new guild"""
            try:
                await self.bot.tree.sync(guild=guild)
                print(f"Synced commands to new guild: {guild.name}")
            except Exception as e:
                print(f"Failed to sync commands to new guild {guild.name}: {e}")
        
        @self.bot.event
        async def on_message(message):
            await self._handle_message(message)

    def _register_slash_commands(self):
        """Register slash commands"""
        
        @self.bot.tree.command(name="wordle", description="Wordle game commands")
        async def wordle(interaction: discord.Interaction):
            """Main wordle command group - just show help"""
            await interaction.response.send_message(
                "Use `/wordle-new` to start a game, `/wordle-guess` to guess, or `/wordle-help` for all commands.",
                ephemeral=True
            )
        
        @self.bot.tree.command(name="wordle-new", description="Start a new Wordle game")
        @discord.app_commands.choices(difficulty=[
            discord.app_commands.Choice(name="Easy (8 guesses)", value="easy"),
            discord.app_commands.Choice(name="Medium (6 guesses)", value="medium"),
            discord.app_commands.Choice(name="Hard (6 guesses + hard mode)", value="hard")
        ])
        async def wordle_new(interaction: discord.Interaction, difficulty: discord.app_commands.Choice[str] = None):
            """Start a new Wordle game with optional difficulty"""
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            channel = interaction.channel
            
            # Use medium as default if no difficulty provided
            difficulty_value = difficulty.value if difficulty else "medium"
            
            await self._handle_new_wordle_command(f"new wordle {difficulty_value}", guild_id, user_id, channel, interaction)
        
        @self.bot.tree.command(name="wordle-guess", description="Make a Wordle guess")
        async def wordle_guess(interaction: discord.Interaction, word: str):
            """Make a guess in the current Wordle game"""
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            channel = interaction.channel
            
            # Validate word length
            if len(word) != 5 or not word.isalpha():
                await interaction.response.send_message("Guess must be exactly 5 letters and contain only letters.", ephemeral=True)
                return
            
            await self._handle_guess(word.lower(), guild_id, user_id, channel, interaction)
        
        @self.bot.tree.command(name="wordle-status", description="Show current Wordle game status")
        async def wordle_status(interaction: discord.Interaction):
            """Show the current Wordle game status"""
            guild_id = str(interaction.guild.id)
            channel = interaction.channel
            await self._handle_status_command(guild_id, channel, interaction)
        
        @self.bot.tree.command(name="wordle-points", description="Show your Wordle points")
        async def wordle_points(interaction: discord.Interaction):
            """Show your Wordle points"""
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            channel = interaction.channel
            await self._handle_points_command(guild_id, user_id, channel, interaction)
        
        @self.bot.tree.command(name="wordle-top", description="Show top Wordle players in this server")
        async def wordle_top(interaction: discord.Interaction):
            """Show top Wordle players"""
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            channel = interaction.channel
            await self._handle_top_command(guild_id, user_id, channel, interaction)
        
        @self.bot.tree.command(name="wordle-quit", description="Quit the current Wordle game")
        async def wordle_quit(interaction: discord.Interaction):
            """Quit the current Wordle game"""
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            channel = interaction.channel
            await self._handle_quit_command(guild_id, user_id, channel, interaction)
        
        @self.bot.tree.command(name="wordle-help", description="Show Wordle help and commands")
        async def wordle_help(interaction: discord.Interaction):
            """Show Wordle help"""
            channel = interaction.channel
            await self._handle_help_command(channel, interaction)

    async def _handle_message(self, message):
        """Handle incoming messages"""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        content = message.content.strip().lower()
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        channel = message.channel
        
        # Handle commands
        if content in ["new wordle", "new wordle easy", "new wordle medium", "new wordle hard"]:
            await self._handle_new_wordle_command(content, guild_id, user_id, channel, message)
        elif content == "wordle status":
            await self._handle_status_command(guild_id, channel)
        elif content == "wordle points":
            await self._handle_points_command(guild_id, user_id, channel)
        elif content == "wordle top":
            await self._handle_top_command(guild_id, user_id, channel, message)
        elif content == "wordle quit":
            await self._handle_quit_command(guild_id, user_id, channel)
        elif content == "wordle help":
            await self._handle_help_command(channel)
        else:
            # Check if this is a guess command
            if content.startswith("guess ") and len(content.split()) == 2:
                guess_word = content.split()[1].lower()
                if len(guess_word) == 5 and guess_word.isalpha():
                    await self._handle_guess(guess_word, guild_id, user_id, channel)
        
        # Process other commands
        await self.bot.process_commands(message)

    async def _handle_new_wordle_command(self, content, guild_id, user_id, channel, message_or_interaction):
        """Handle new wordle command"""
        # Parse difficulty
        difficulty = "medium"
        if content == "new wordle easy":
            difficulty = "easy"
        elif content == "new wordle medium":
            difficulty = "medium"
        elif content == "new wordle hard":
            difficulty = "hard"
        
        # Check if channel already has an active game
        existing_game = storage.get_channel_game(guild_id, channel.id)
        if existing_game is not None:
            # Channel has an active game, inform user
            await self._send_response(channel, "There is already an ongoing game. Type `guess {your guess}` to join the round.", message_or_interaction)
            return
        
        # Create new game
        game_state = WordleGame.start_new_game(difficulty, str(channel.id))
        
        # Save game to storage (per channel)
        storage.save_channel_game(guild_id, channel.id, game_state.to_dict())
        
        # Send game start message
        max_guesses = WordleGame._get_max_guesses(difficulty)
        difficulty_display = difficulty.upper()
        
        # Format start message based on difficulty
        if difficulty == "hard":
            start_message = "A new wordle game has started. Type `guess {your guess}` to start playing! Since you're playing hard mode, you can only guess the word in 6 tries, and any revealed hints must be used in subsequent guesses!"
        else:
            start_message = "A new wordle game has started. Type `guess {your guess}` to start playing!"
        
        await self._send_response(channel, start_message, message_or_interaction)

    def _render_guess_history_block(self, game_state):
        """
        Build the "Previously guessed words" block as numbered lines,
        using the custom letter emojis for each guess.
        """
        lines = []

        for index, result in enumerate(game_state.guess_results):
            guess = game_state.guesses[index]
            # statuses list: ["green", "grey", "yellow", ...]
            emoji_row = self._render_emoji_row(guess, result.statuses)
            # Example line: "1. <:a_g:...><:u_j:...><:d_y:...>..."
            lines.append(f"{index + 1}. {emoji_row}")

        if not lines:
            return "No guesses yet!"

        return "\n".join(lines)

    def _render_keyboard_block(self, game_state):
        """
        Build a QWERTY keyboard view using the custom letter emojis.
        Each key is colored according to the letter's best-known status:
        green / yellow / grey / unguessed.
        """
        keyboard_state = game_state.get_keyboard_state()

        # QWERTY rows
        rows = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
        ]

        status_suffix = {
            "green": "g",
            "yellow": "y",
            "grey": "j",
            "unguessed": "j",  # show unguessed as grey-style key
        }

        rendered_rows = []

        for row_index, row in enumerate(rows):
            pieces = []

            for letter in row:
                status = keyboard_state.get(letter, "unguessed")
                suffix = status_suffix.get(status, "j")
                key = f"{letter}_{suffix}"  # e.g. "q_g", "w_y", "e_j"

                emoji = self.letter_emojis.get(key)
                if emoji is not None:
                    pieces.append(str(emoji))
                else:
                    # Fallback to plain letter if custom emoji is missing
                    pieces.append(letter.upper())

            line = "".join(pieces)

            # Add small indentation to mimic a physical keyboard shape
            if row_index == 1:
                line = " " + line
            elif row_index == 2:
                line = "  " + line

            rendered_rows.append(line)

        return "\n".join(rendered_rows)

    async def _handle_status_command(self, guild_id, channel, message_or_interaction=None):
        """Handle wordle status command"""
        game_data = storage.get_channel_game(guild_id, channel.id)
        if game_data is None:
            text = "This channel has no active Wordle game. Start one with `/wordle-new` or `new wordle`."
            if hasattr(message_or_interaction, "response") and hasattr(message_or_interaction.response, "send_message"):
                await message_or_interaction.response.send_message(text)
            else:
                await channel.send(text)
            return

        game_state = GameState.from_dict(game_data)

        # Build the "Previously guessed words" description using emoji rows
        if game_state.guesses:
            lines = []
            for idx, guess_result in enumerate(game_state.guess_results):
                guess_word = game_state.guesses[idx]
                emoji_row = self._render_emoji_row(guess_word, guess_result.statuses)
                lines.append(f"{idx + 1}. {emoji_row}")
            description = "\n".join(lines)
        else:
            description = "No guesses yet!"

        # Build keyboard image based on current keyboard state
        keyboard_state = game_state.get_keyboard_state()

        image_path = None
        try:
            image_path = image_generator.generate_keyboard_image(keyboard_state)
            with open(image_path, "rb") as f:
                file = discord.File(f, filename="wordle_keyboard.png")

            embed = discord.Embed(
                title="Previously guessed words",
                description=description,
                color=discord.Color.green(),
            )
            embed.set_image(url="attachment://wordle_keyboard.png")
            embed.set_footer(
                text="Wafflers Remastered (powered by Mafia Remastered) © 2025 – Version: 2.3.0"
            )

            if hasattr(message_or_interaction, "response") and hasattr(message_or_interaction.response, "send_message"):
                await message_or_interaction.response.send_message(embed=embed, file=file)
            else:
                await channel.send(embed=embed, file=file)

        except Exception as e:
            # Fallback to a simple text-based embed if image generation fails
            print(f"Status keyboard image generation failed: {e}")

            keyboard_display = WordleGame.format_keyboard_display(game_state.get_keyboard_state())
            fallback_embed = discord.Embed(
                title="Wordle Status",
                color=discord.Color.blue(),
                description=description,
            )
            fallback_embed.add_field(
                name="Keyboard",
                value=keyboard_display,
                inline=False,
            )

            if hasattr(message_or_interaction, "response") and hasattr(message_or_interaction.response, "send_message"):
                await message_or_interaction.response.send_message(embed=fallback_embed)
            else:
                await channel.send(embed=fallback_embed)

        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Failed to delete status image file {image_path}: {e}")

    async def _handle_points_command(self, guild_id, user_id, channel, message_or_interaction=None):
        """Handle wordle points command"""
        score_data = storage.get_user_score(guild_id, user_id)
        points = score_data["points"]
        await self._send_response(channel, f"You have {points} points!", message_or_interaction)

    async def _handle_top_command(self, guild_id, user_id, channel, message_or_interaction):
        """Handle wordle top command"""
        top_players = storage.get_top_players(guild_id, 5)
        
        if len(top_players) == 0:
            await self._send_response(channel, "No one has any Wordle points yet. Solve a puzzle to get on the board!", message_or_interaction)
            return
        
        # Get guild name
        guild = None
        if hasattr(message_or_interaction, 'guild'):
            guild = message_or_interaction.guild
        else:
            guild = channel.guild
        
        # Create embed
        embed = discord.Embed(
            title=f"Top Wordle Players in {guild.name}",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉", "🌟", "⭐"]
        description = ""
        
        for i, player in enumerate(top_players):
            user_id_str = player["user_id"]
            points = player["points"]
            medal = medals[i]
            
            # Get user mention
            user = guild.get_member(int(user_id_str))
            user_mention = user.mention if user else f"<@{user_id_str}>"
            
            description += f"{medal} {user_mention} – {points} points\n"
        
        embed.description = description
        await self._send_response(channel, embed=embed, message_or_interaction=message_or_interaction)

    async def _handle_quit_command(self, guild_id, user_id, channel, message_or_interaction=None):
        """Handle wordle quit command"""
        game_data = storage.get_channel_game(guild_id, channel.id)
        if game_data is None:
            await self._send_response(channel, "This channel doesn't have an active Wordle game to quit.", message_or_interaction)
            return
        
        # Check if the game is in hard mode
        if game_data.get("difficulty") == "hard":
            await self._send_response(channel, "You cannot quit a Hard mode Wordle game.", message_or_interaction)
            return
        
        # Delete the game
        storage.delete_channel_game(guild_id, channel.id)
        await self._send_response(channel, "The Wordle game has been quit. Start a new one with `/wordle-new` or `new wordle` when you're ready!", message_or_interaction)

    async def _handle_help_command(self, channel, message_or_interaction=None):
        """Handle wordle help command"""
        embed = discord.Embed(
            title="Wordle Bot Commands",
            color=discord.Color.blue(),
            description="Here are all the commands you can use to play Wordle:"
        )

        # Text Commands
        text_commands = """
`new wordle` - Start a new Wordle game (medium difficulty)
`new wordle easy` - Start with 8 guesses
`new wordle medium` - Start with 6 guesses
`new wordle hard` - Start with 6 guesses + hard mode rules
`guess <word>` - Make a guess (5-letter word)
`wordle status` - Show current game status
`wordle points` - Show your points
`wordle top` - Show top players in this server
`wordle quit` - Quit the current game
`wordle help` - Show this help message
"""
        embed.add_field(name="Text Commands", value=text_commands, inline=False)

        # Slash Commands
        slash_commands = """
`/wordle-new` - Start a new Wordle game with difficulty selection
`/wordle-guess <word>` - Make a guess (5-letter word)
`/wordle-status` - Show current game status
`/wordle-points` - Show your points
`/wordle-top` - Show top players in this server
`/wordle-quit` - Quit the current game
`/wordle-help` - Show this help message
"""
        embed.add_field(name="Slash Commands", value=slash_commands, inline=False)

        # Game Rules
        game_rules = """
- One active game per server
- Everyone can guess
- 5-letter words only
- Official NYT Wordle word list
- Points awarded for wins with bonus for fewer guesses
"""
        embed.add_field(name="Game Rules", value=game_rules, inline=False)

        embed.set_footer(text="Wafflers Remastered (powered by Mafia Remastered) © 2025 – Version: 2.3.0")

        await self._send_response(channel, embed=embed, message_or_interaction=message_or_interaction)

    async def _send_response(self, channel, content=None, message_or_interaction=None, embed=None, file=None):
        """Helper method to send responses for both regular messages and slash commands"""
        if hasattr(message_or_interaction, 'response') and hasattr(message_or_interaction.response, 'send_message'):
            # This is a slash command interaction
            if file:
                await message_or_interaction.response.send_message(file=file)
            elif embed:
                await message_or_interaction.response.send_message(embed=embed)
            else:
                await message_or_interaction.response.send_message(content)
        else:
            # This is a regular message
            if file:
                await channel.send(file=file)
            elif embed:
                await channel.send(embed=embed)
            else:
                await channel.send(content)

    async def _handle_guess(self, guess, guild_id, user_id, channel):
        """Handle a word guess"""
        game_data = storage.get_channel_game(guild_id, channel.id)
        if game_data is None:
            return  # Ignore guesses if no active game in channel

        game_state = GameState.from_dict(game_data)

        # Apply the guess
        result = game_state.apply_guess(guess)

        if result.error != "":
            # Map error messages to the specific formats requested
            if "already guessed" in result.error:
                await channel.send("That word has already been guessed.")
            elif "not a valid word" in result.error:
                await channel.send("Not a valid word!")
            else:
                await channel.send(result.error)
            return

        # Update storage with new game state
        storage.save_channel_game(guild_id, channel.id, game_state.to_dict())

        # If the game is finished AND this guess is correct, we skip the per-guess
        # image and directly show the final history image via _handle_game_completion.
        if result.is_finished and result.is_correct:
            await self._handle_game_completion(game_state, guild_id, user_id, channel, True)
            return

        # For all other cases, show the single-row guess image
        image_path = None
        try:
            image_path = image_generator.generate_guess_image(guess, result.statuses)
            with open(image_path, "rb") as f:
                picture = discord.File(f, filename=f"wordle_guess_{guess}.png")
            await channel.send(file=picture)
        except Exception as e:
            # Fallback to text if image generation fails
            print(f"Image generation failed: {e}")
            guess_display = WordleGame.format_guess_display(guess, result.statuses)
            await channel.send(guess_display)
        finally:
            # Clean up the image file after sending
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Failed to delete image file {image_path}: {e}")

        # If the game is finished (loss or max guesses), show final history
        if result.is_finished:
            await self._handle_game_completion(game_state, guild_id, user_id, channel, result.is_correct)

    def _build_letter_emoji_cache(self):
        """
        Load all custom letter emojis from the two guilds:

        - 1443491143450103818  (grey + x_y, y_y, z_y)
        - 1443246134469333074  (rest of green/yellow letters)
        Emoji names follow the pattern 'a_g', 'b_y', 'c_j', etc.
        """
        target_guild_ids = {1443491143450103818, 1443246134469333074}
        self.letter_emojis = {}

        for guild in self.bot.guilds:
            if guild.id not in target_guild_ids:
                continue

            for emoji in guild.emojis:
                # cache by name, e.g. "a_g"
                self.letter_emojis[emoji.name] = emoji

        print(f"Cached {len(self.letter_emojis)} Wordle letter emojis")

    def _render_emoji_row(self, word, statuses):
        """
        Render a word as a row of custom letter emojis based on statuses.
        statuses is a list like ["green", "yellow", "grey", ...].
        """
        word = word.lower()
        if statuses is None or len(statuses) != len(word):
            statuses = ["green"] * len(word)

        status_suffix = {
            "green": "g",
            "yellow": "y",
            "grey": "j",
        }

        pieces = []
        for ch, status in zip(word, statuses):
            suffix = status_suffix.get(status, "j")
            key = f"{ch}_{suffix}"  # e.g. "a_g"
            emoji = self.letter_emojis.get(key)

            if emoji is not None:
                pieces.append(str(emoji))  # "<:a_g:1234567890>"
            else:
                # Fallback: plain letter if emoji is missing
                pieces.append(ch.upper())

        return "".join(pieces)

    async def _handle_game_completion(self, game_state, guild_id, user_id, channel, is_win):
        """Handle game completion (win or loss)"""
        guesses_used = len(game_state.guesses)
        answer = game_state.answer.lower()

        if is_win:
            # Calculate points
            points_earned = WordleGame.calculate_points(game_state.difficulty, guesses_used)

            # Update user score
            current_score = storage.get_user_score(guild_id, user_id)
            new_points = current_score["points"] + points_earned
            new_games_won = current_score["gamesWon"] + 1
            new_games_played = current_score["gamesPlayed"] + 1

            new_score_data = {
                "points": new_points,
                "gamesWon": new_games_won,
                "gamesPlayed": new_games_played,
            }
            storage.update_user_score(guild_id, user_id, new_score_data)

            # Build the win text
            if game_state.difficulty == "hard":
                win_message = (
                    f"Correct! You guessed it in {guesses_used} tries. "
                    f"Since it was hard mode, you gained {points_earned} points!"
                )
            else:
                win_message = (
                    f"Correct! You guessed it in {guesses_used} tries. "
                    f"You gained {points_earned} points!"
                )

            image_path = None
            try:
                # Generate single word image (the final guess)
                last_guess = game_state.guesses[-1]
                last_statuses = game_state.guess_results[-1].statuses
                image_path = image_generator.generate_guess_image(last_guess, last_statuses)
                with open(image_path, "rb") as f:
                    picture = discord.File(f, filename="wordle_final.png")

                dict_url = f"https://www.merriam-webster.com/dictionary/{answer}"

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Dictionary",
                        style=discord.ButtonStyle.link,
                        url=dict_url,
                    )
                )

                # Send text message with photo and button (no embed)
                await channel.send(win_message, file=picture, view=view)

            except Exception as e:
                # Fallback: text-only message
                print(f"Final guess image generation failed: {e}")
                dict_url = f"https://www.merriam-webster.com/dictionary/{answer}"
                win_message += f"\n\nDictionary: {dict_url}"
                await channel.send(win_message)
            finally:
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Failed to delete image file {image_path}: {e}")

        else:
            # Loss: update only gamesPlayed
            current_score = storage.get_user_score(guild_id, user_id)
            new_games_played = current_score["gamesPlayed"] + 1

            new_score_data = {
                "points": current_score["points"],
                "gamesWon": current_score["gamesWon"],
                "gamesPlayed": new_games_played,
            }
            storage.update_user_score(guild_id, user_id, new_score_data)

            image_path = None
            try:
                # Generate single word image showing the answer as all green
                statuses = ["green"] * len(answer)
                image_path = image_generator.generate_guess_image(answer, statuses)
                with open(image_path, "rb") as f:
                    picture = discord.File(f, filename="wordle_final.png")

                loss_message = f"😞 Game over! The word was **{answer.upper()}**."
                dict_url = f"https://www.merriam-webster.com/dictionary/{answer}"

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Dictionary",
                        style=discord.ButtonStyle.link,
                        url=dict_url,
                    )
                )

                # Send text message with photo and button (no embed)
                await channel.send(loss_message, file=picture, view=view)

            except Exception as e:
                print(f"Final guess image generation failed (loss): {e}")
                dict_url = f"https://www.merriam-webster.com/dictionary/{answer}"
                loss_message = f"😞 Game over! The word was **{answer.upper()}**."
                loss_message += f"\n\nDictionary: {dict_url}"
                await channel.send(loss_message)
            finally:
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Failed to delete image file {image_path}: {e}")

        # Remove the completed game from storage
        storage.delete_channel_game(guild_id, channel.id)

    def run(self):
        """Run the bot"""
        if not self.token:
            print("Error: DISCORD_TOKEN environment variable not set")
            return
        
        try:
            self.bot.run(self.token)
        except Exception as e:
            print(f"Error running bot: {e}")

# Main entry point
if __name__ == "__main__":
    bot = DiscordWordleBot()
    bot.run()