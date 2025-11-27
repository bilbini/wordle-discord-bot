# bot.py

import os
import asyncio
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
        
        # Create bot instance
        self.bot = commands.Bot(command_prefix="", intents=intents)
        self.token = os.getenv("DISCORD_TOKEN")
        self.letter_emojis = {}  # name -> discord.Emoji
        
        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            print(f"Logged in as {self.bot.user}")
            self._build_letter_emoji_cache()
            print("Bot is ready!")
            # Start periodic image cleanup (every 10 minutes)
            asyncio.create_task(image_generator.start_periodic_cleanup())
        
        @self.bot.event
        async def on_message(message):
            await self._handle_message(message)


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
        if content in ["new wordle", "new wordle normal", "new wordle hard"]:
            await self._handle_new_wordle_command(content, guild_id, user_id, channel, message)
        elif content.startswith("wordle points"):
            # Check if there's a user mention
            if message.mentions:
                target_user_id = str(message.mentions[0].id)
                await self._handle_points_command(guild_id, target_user_id, channel, message)
            else:
                await self._handle_points_command(guild_id, user_id, channel, message)
        elif content.startswith("wordle stats"):
            # Check if there's a user mention
            if message.mentions:
                target_user_id = str(message.mentions[0].id)
                await self._handle_statistics_command(guild_id, target_user_id, channel, message)
            else:
                await self._handle_statistics_command(guild_id, user_id, channel, message)
        elif content == "wordle status":
            await self._handle_status_command(guild_id, channel)
        elif content == "wordle top":
            await self._handle_top_command(guild_id, user_id, channel, message)
        elif content == "wordle global":
            await self._handle_global_command(guild_id, user_id, channel, message)
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
        
        # Don't process commands again to avoid duplicate responses
        # await self.bot.process_commands(message)  # Removed to prevent duplicate messages

    async def _handle_new_wordle_command(self, content, guild_id, user_id, channel, message_or_interaction):
        """Handle new wordle command"""
        # Parse difficulty
        difficulty = "normal"
        if content == "new wordle normal":
            difficulty = "normal"
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
            start_message = "A new wordle game has started. Type `guess {your guess}` to start playing! Normal mode: unlimited guesses, but you lose 2 points for each guess beyond the first (minimum 0 points)."
        
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
                text="Wordle Corner (powered by abuhaidar) © 2025 – Version: 1.0.0"
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
                color=discord.Color.green(),
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
                asyncio.create_task(self._delete_image_after_delay(image_path, 600))  # 600 seconds = 10 minutes

    async def _handle_points_command(self, guild_id, user_id, channel, message_or_interaction=None):
        """Handle wordle points command"""
        score_data = storage.get_user_score(guild_id, user_id)
        points = score_data.get("points", 0)
        
        # Check if we're showing someone else's points (via mention)
        if hasattr(message_or_interaction, 'mentions') and message_or_interaction.mentions:
            target_user = message_or_interaction.mentions[0]
            response = f"{target_user.display_name} has {points} points!"
        else:
            response = f"You have {points} points!"
            
        await self._send_response(channel, response, message_or_interaction)

    async def _handle_statistics_command(self, guild_id, user_id, channel, message_or_interaction=None):
        """Handle wordle statistics command"""
        score_data = storage.get_user_score(guild_id, user_id)

        points = score_data.get("points", 0)
        total_correct_guesses = score_data.get("gamesWon", 0)  # games won = correct words
        total_guesses = score_data.get("totalGuesses", 0)
        first_attempt_guesses = score_data.get("firstAttemptGuesses", 0)

        if total_correct_guesses > 0:
            avg_guesses = total_guesses / total_correct_guesses
        else:
            avg_guesses = 0.0

        # Figure out display name
        display_name = "Unknown"
        user = None
        if hasattr(message_or_interaction, "author"):
            user = message_or_interaction.author
        elif hasattr(message_or_interaction, "user"):
            user = message_or_interaction.user

        if user is not None:
            display_name = user.display_name or user.name

        embed = discord.Embed(
            title=f"Wordle Statistics for {display_name}",
            color=discord.Color.green(),
        )

        embed.description = (
            f"• Points: {points}\n"
            f"• Total Guesses: {total_guesses}\n"
            f"• Total Correct Guesses: {total_correct_guesses}\n"
            f"• Average Guesses per Correct Word: {avg_guesses:.2f}\n"
            f"• First Attempt Guesses: {first_attempt_guesses}"
        )

        embed.set_footer(
            text="Wordle Corner (Powered by abuhaidar) © 2025 - Version: 1.0.0"
        )

        await self._send_response(
            channel,
            embed=embed,
            message_or_interaction=message_or_interaction,
        )

    async def _handle_top_command(self, guild_id, user_id, channel, message_or_interaction):
        """Handle wordle top command (server members with global scores)"""
        # Get all global players
        all_global_players = storage.get_global_top_players(limit=None)
        
        # Get guild object
        guild = None
        if hasattr(message_or_interaction, 'guild'):
            guild = message_or_interaction.guild
        else:
            guild = channel.guild
        
        # Filter to only include members who are in this server
        server_members_with_scores = []
        for player in all_global_players:
            user_id_str = player["user_id"]
            # Check if this user is a member of the current server
            user = guild.get_member(int(user_id_str))
            if user:  # User is in this server
                server_members_with_scores.append(player)
        
        # Take top 5 server members by global score
        top_players = server_members_with_scores[:5]
        
        if len(top_players) == 0:
            await self._send_response(channel, "No one in this server has any Wordle points yet. Solve a puzzle to get on the board!", message_or_interaction)
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"🏆 Top Wordle Players in {guild.name}",
            color=discord.Color.green()
        )
        
        medals = ["🥇", "🥈", "🥉", "🌟", "⭐"]
        description = ""
        
        for i, player in enumerate(top_players):
            user_id_str = player["user_id"]
            points = player["points"]
            medal = medals[i]
            
            # Get user mention (we know they're in the server from our filter)
            user = guild.get_member(int(user_id_str))
            user_mention = user.mention if user else f"<@{user_id_str}>"
            
            description += f"{medal} {user_mention} – **{points:,}** points\n"
            
            # Add extra spacing between entries (like <br>)
            if i < len(top_players) - 1:
                description += "\n"
        
        embed.description = description
        embed.set_footer(text="Showing global scores of server members")
        await self._send_response(channel, embed=embed, message_or_interaction=message_or_interaction)

    async def _handle_global_command(self, guild_id, user_id, channel, message_or_interaction):
        """Handle wordle global command (global leaderboard)"""
        top_players = storage.get_global_top_players(10)
        
        if len(top_players) == 0:
            await self._send_response(channel, "No one has any Wordle points yet globally. Solve a puzzle to get on the board!", message_or_interaction)
            return
        
        # Create embed
        embed = discord.Embed(
            title="🌍 Global Top Wordle Players",
            color=discord.Color.green()
        )
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        description = ""
        
        for i, player in enumerate(top_players):
            user_id_str = player["user_id"]
            points = player["points"]
            medal = medals[i]
            
            # Get user mention - try to find user in current guild first
            guild = None
            if hasattr(message_or_interaction, 'guild'):
                guild = message_or_interaction.guild
            else:
                guild = channel.guild
            
            user = guild.get_member(int(user_id_str))
            user_mention = user.mention if user else f"<@{user_id_str}>"
            
            description += f"{medal} {user_mention} – **{points:,}** points\n"
            
            # Add extra spacing between entries (like <br>)
            if i < len(top_players) - 1:
                description += "\n"
        
        embed.description = description
        embed.set_footer(text="Global leaderboard across all servers")
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
            color=discord.Color.green(),
            description="Here are all the commands you can use to play Wordle:"
        )

        # Commands
        commands = """
`new wordle` - Start a new Wordle game (normal difficulty)
`new wordle normal` - Start with unlimited guesses, -2 points per guess after first
`new wordle hard` - Start with 6 guesses + hard mode rules
`guess <word>` - Make a guess (5-letter word)
`wordle status` - Show current game status
`wordle points` - Show your points
`wordle statistics` - Show your detailed statistics
`wordle top` - Show top players in this server
`wordle global` - Show global top 10 players
`wordle quit` - Quit the current game
`wordle help` - Show this help message
"""
        embed.add_field(name="Commands", value=commands, inline=False)

        # Game Rules
        game_rules = """
- One active game per server
- Everyone can guess
- 5-letter words only
- Official NYT Wordle word list
- Points awarded for wins with bonus for fewer guesses
"""
        embed.add_field(name="Game Rules", value=game_rules, inline=False)

        embed.set_footer(text="Wordle Corner (powered by abuhaidar) © 2025 – Version: 1.0.0")

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
            # Clean up the image file after 10 minutes
            if image_path and os.path.exists(image_path):
                asyncio.create_task(self._delete_image_after_delay(image_path, 600))  # 600 seconds = 10 minutes

        # If the game is finished (loss or max guesses), show final history
        if result.is_finished:
            await self._handle_game_completion(game_state, guild_id, user_id, channel, result.is_correct)

    async def _delete_image_after_delay(self, image_path, delay_seconds):
        """Delete image file after specified delay"""
        await asyncio.sleep(delay_seconds)
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"Deleted image file after delay: {image_path}")
        except Exception as e:
            print(f"Failed to delete image file {image_path}: {e}")

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
            new_points = current_score.get("points", 0) + points_earned
            new_games_won = current_score.get("gamesWon", 0) + 1
            new_games_played = current_score.get("gamesPlayed", 0) + 1

            new_total_guesses = current_score.get("totalGuesses", 0) + guesses_used
            new_first_attempt_guesses = current_score.get("firstAttemptGuesses", 0)
            if guesses_used == 1:
                new_first_attempt_guesses += 1

            new_score_data = {
                "points": new_points,
                "gamesWon": new_games_won,
                "gamesPlayed": new_games_played,
                "totalGuesses": new_total_guesses,
                "firstAttemptGuesses": new_first_attempt_guesses,
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
                    asyncio.create_task(self._delete_image_after_delay(image_path, 600))  # 600 seconds = 10 minutes

        else:
            # Loss: update only gamesPlayed
            current_score = storage.get_user_score(guild_id, user_id)
            new_games_played = current_score.get("gamesPlayed", 0) + 1

            new_score_data = {
                "points": current_score.get("points", 0),
                "gamesWon": current_score.get("gamesWon", 0),
                "gamesPlayed": new_games_played,
                "totalGuesses": current_score.get("totalGuesses", 0),
                "firstAttemptGuesses": current_score.get("firstAttemptGuesses", 0),
            }
            storage.update_user_score(guild_id, user_id, new_score_data)

            # Custom handling for hard mode losses (no image)
            if game_state.difficulty == "hard":
                loss_message = f"RIP - Since this was hard mode, you only get 6 tries to guess the word! The correct word was: **{answer.upper()}**"
                dict_url = f"https://www.merriam-webster.com/dictionary/{answer}"

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Dictionary",
                        style=discord.ButtonStyle.link,
                        url=dict_url,
                    )
                )

                # Send text message with button only (no image)
                await channel.send(loss_message, view=view)
            else:
                # Normal mode losses still use image
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
                        asyncio.create_task(self._delete_image_after_delay(image_path, 600))  # 600 seconds = 10 minutes

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