# Discord Wordle Bot in Python

A production-ready Discord Wordle bot written in Python, featuring the same functionality as the Mojo version with simplified setup and deployment.

## Features

- **NYT-style Wordle gameplay** with official scoring rules
- **Multiple difficulty levels**: Easy (8 guesses), Medium (6 guesses), Hard (6 guesses with hard mode)
- **Persistent scoring system** with JSON storage
- **Interactive keyboard display** showing letter status
- **Leaderboard system** with top player rankings
- **Hard mode constraints** that enforce revealed letter usage
- **Visual PNG images** for guesses and game history with colored boxes and letters

## Project Structure

```
wordle-python/
├── bot.py              # Main Discord bot entry point
├── wordle_game.py      # Core Wordle game logic
├── storage.py          # JSON storage helpers
├── word_lists.py       # Word lists (solutions and allowed guesses)
├── image_generator.py  # PNG image generation for guesses
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── .env.example       # Environment variables template
├── data/              # Persistent data directory (auto-created)
│   ├── scores.json    # Player scores and statistics
│   └── games.json     # Active games data
└── wordle_images/      # Generated PNG images (auto-created)
```

## Prerequisites

1. **Python 3.8+**: Required for running the bot
2. **Discord Bot Token**: Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
3. **Enable Message Content Intent**: Required for the bot to read message content

## Installation

### Option 1: Virtual Environment (Recommended)

1. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Run the bot**:
   ```bash
   python bot.py
   ```

### Option 2: Global Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

3. **Run the bot**:
   ```bash
   python bot.py
   ```

## Discord Bot Setup

### Critical: Enable Message Content Intent

**Before running the bot, you MUST enable Message Content Intent in the Discord Developer Portal:**

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to the "Bot" section in the left sidebar
4. Scroll down to "Privileged Gateway Intents"
5. **Enable "Message Content Intent"**
6. Save changes

### Bot Setup Steps

1. Create a new application in the [Discord Developer Portal](https://discord.com/developers/applications)
2. Go to the "Bot" section and create a bot
3. Copy the bot token and add it to your `.env` file
4. Invite the bot to your server with these permissions:
   - Send Messages
   - Embed Links
   - Read Message History

## Commands

The bot uses plain-text commands (no prefix required):

### Starting Games
- `new wordle` - Start a medium difficulty game (6 guesses)
- `new wordle easy` - Start an easy game (8 guesses)
- `new wordle medium` - Start a medium game (6 guesses)
- `new wordle hard` - Start a hard game (6 guesses, hard mode)

### Game Management
- `wordle status` - View your current game status with guess history and keyboard
- **Make a guess**: Use `guess <word>` command (e.g., `guess apple` to guess the word "apple")
- **Example**: If you want to guess "hello", type: `guess hello`

### Points and Leaderboard
- `wordle points` - Check your total points
- `wordle top` - View the top 5 players in the server
- `wordle quit` - Quit your current active game

## Game Rules

### Wordle Gameplay
- Use `guess <word>` to make guesses (e.g., `guess hello`)
- **Green**: Correct letter in correct position
- **Yellow**: Correct letter in wrong position
- **Grey**: Letter not in the word
- Only valid English words from the allowed list are accepted
- **Visual feedback**: Each guess generates a PNG image with letters centered in colored boxes on a black background

### Difficulty Levels
- **Easy**: 8 guesses, base 5 points
- **Medium**: 6 guesses, base 10 points  
- **Hard**: 6 guesses with hard mode constraints, base 15 points

### Hard Mode Constraints
- Once a letter is revealed as green, it must stay in that position
- Letters revealed as yellow must appear somewhere in subsequent guesses
- Violating constraints rejects the guess without consuming a turn

### Points System
- **Base points**: Easy (5), Medium (10), Hard (15)
- **Bonus points**: `max_guesses - guesses_used`
- **Total**: Base + Bonus points
- Points are only awarded for wins

## Technical Details

### Python Implementation
- Uses `discord.py` library for Discord integration
- Pure Python classes and functions for game logic
- JSON persistence through Python `json` module
- Object-oriented design with proper separation of concerns
- **Visual PNG generation** using Pillow (PIL) library for professional-looking guess displays
- **Black background images** with letters centered in colored boxes
- **Command-based guessing**: `guess <word>` syntax for making guesses

### Data Storage
- **scores.json**: Player statistics per guild
- **games.json**: Active game states
- Automatic file creation and error handling
- In-memory caching with disk persistence

### Word Lists
- **SOLUTIONS**: 100+ valid 5-letter answer words
- **ALLOWED_GUESSES**: 1000+ valid guess words (includes all solutions)
- Proper duplicate handling and alphabetical sorting

## Error Handling

- Graceful handling of missing files and corrupted data
- Clear error messages for invalid guesses
- Bot restart resilience with game state preservation
- Network error recovery for Discord API

## Development

### Adding New Words
Edit `word_lists.py` and add words to the `solution_words` or `additional_guesses` arrays.

### Modifying Game Rules
Update constants and logic in `wordle_game.py`:
- `_get_max_guesses()` for guess limits
- `_get_base_points()` for point values
- `_calculate_guess_result()` for scoring algorithm

### Extending Features
- Add new commands in `bot.py` `_handle_message()`
- Create new storage methods in `storage.py`
- Add new game modes in `wordle_game.py`

## Deployment

### Running as a Service (Linux)

Create a systemd service file `/etc/systemd/system/wordle-bot.service`:

```ini
[Unit]
Description=Discord Wordle Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/wordle-python
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:
```bash
sudo systemctl enable wordle-bot
sudo systemctl start wordle-bot
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
```

Build and run:
```bash
docker build -t wordle-bot .
docker run -d --name wordle-bot -v $(pwd)/data:/app/data -v $(pwd)/.env:/app/.env wordle-bot
```

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check DISCORD_TOKEN in `.env`
   - Verify bot has Message Content intent enabled
   - Check bot is invited to the server with correct permissions

2. **"Word not in allowed list"**
   - The word is not in the allowed guesses list
   - Only valid 5-letter English words are accepted

3. **Game state lost after restart**
   - Games are automatically saved to `data/games.json`
   - Check file permissions and disk space

4. **Import errors**
   - Ensure all dependencies are installed
   - Check Python version compatibility
   - Verify file paths and module imports

5. **Permission errors**
   - Ensure the bot has write permissions to the data directory
   - Check file ownership and permissions

## License

This project is for educational and personal use. Wordle is a trademark of The New York Times Company.

## Contributing

Feel free to submit issues and pull requests for improvements and bug fixes.