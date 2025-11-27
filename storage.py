# storage.py

import json
import os

class Storage:
    def __init__(self):
        self.scores_file = "data/scores.json"
        self.games_file = "data/games.json"
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def load_scores(self):
        """Load scores from JSON file"""
        try:
            if os.path.exists(self.scores_file):
                with open(self.scores_file, "r") as file:
                    return json.load(file)
            else:
                return {}
        except Exception as e:
            print(f"Error loading scores: {e}")
            return {}

    def save_scores(self, scores):
        """Save scores to JSON file"""
        try:
            with open(self.scores_file, "w") as file:
                json.dump(scores, file, indent=2)
        except Exception as e:
            print(f"Error saving scores: {e}")

    def load_games(self):
        """Load games from JSON file"""
        try:
            if os.path.exists(self.games_file):
                with open(self.games_file, "r") as file:
                    return json.load(file)
            else:
                return {}
        except Exception as e:
            print(f"Error loading games: {e}")
            return {}

    def save_games(self, games):
        """Save games to JSON file"""
        try:
            with open(self.games_file, "w") as file:
                json.dump(games, file, indent=2)
        except Exception as e:
            print(f"Error saving games: {e}")

    def get_user_score(self, guild_id, user_id):
        """Get user score data, return default if not exists"""
        scores = self.load_scores()
        
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str not in scores:
            return {
                "points": 0,
                "gamesWon": 0,
                "gamesPlayed": 0
            }
        
        guild_scores = scores[guild_id_str]
        if user_id_str not in guild_scores:
            return {
                "points": 0,
                "gamesWon": 0,
                "gamesPlayed": 0
            }
        
        return guild_scores[user_id_str]

    def update_user_score(self, guild_id, user_id, score_data):
        """Update user score data"""
        scores = self.load_scores()
        
        guild_id_str = str(guild_id)
        user_id_str = str(user_id)
        
        if guild_id_str not in scores:
            scores[guild_id_str] = {}
        
        scores[guild_id_str][user_id_str] = score_data
        self.save_scores(scores)

    def get_channel_game(self, guild_id, channel_id):
        """Get channel's active game (one game per channel)"""
        games = self.load_games()
        guild_id_str = str(guild_id)
        channel_id_str = str(channel_id)
        
        if guild_id_str not in games:
            return None
        guild_games = games[guild_id_str]
        return guild_games.get(channel_id_str)

    def save_channel_game(self, guild_id, channel_id, game_data):
        """Save channel's active game"""
        games = self.load_games()
        guild_id_str = str(guild_id)
        channel_id_str = str(channel_id)
        
        if guild_id_str not in games:
            games[guild_id_str] = {}
        
        games[guild_id_str][channel_id_str] = game_data
        self.save_games(games)

    def delete_channel_game(self, guild_id, channel_id):
        """Delete channel's active game"""
        games = self.load_games()
        guild_id_str = str(guild_id)
        channel_id_str = str(channel_id)
        
        if guild_id_str in games and channel_id_str in games[guild_id_str]:
            del games[guild_id_str][channel_id_str]
            # Remove guild entry if no channels have games
            if not games[guild_id_str]:
                del games[guild_id_str]
            self.save_games(games)

    # Keep old methods for backward compatibility during transition
    def get_guild_game(self, guild_id):
        """Get guild's active game (deprecated - use get_channel_game instead)"""
        # This will return None since we're moving to per-channel games
        return None

    def save_guild_game(self, guild_id, game_data):
        """Save guild's active game (deprecated - use save_channel_game instead)"""
        # Extract channel_id from game_data and use new method
        channel_id = game_data.get("channel_id")
        if channel_id:
            self.save_channel_game(guild_id, channel_id, game_data)

    def delete_guild_game(self, guild_id):
        """Delete guild's active game (deprecated - use delete_channel_game instead)"""
        # This will do nothing since we're moving to per-channel games
        # We can't delete all channel games without knowing which ones
        pass

    def get_top_players(self, guild_id, limit=5):
        """Get top players for a guild"""
        scores = self.load_scores()
        guild_id_str = str(guild_id)
        
        if guild_id_str not in scores:
            return []
        
        guild_scores = scores[guild_id_str]
        players = []
        
        for user_id, score_data in guild_scores.items():
            player_data = {
                "user_id": user_id,
                "points": score_data["points"],
                "gamesWon": score_data["gamesWon"],
                "gamesPlayed": score_data["gamesPlayed"]
            }
            players.append(player_data)
        
        # Sort by points descending
        sorted_players = sorted(players, key=lambda x: x["points"], reverse=True)
        
        # Return top N players
        return sorted_players[:limit]

# Global instance
storage = Storage()