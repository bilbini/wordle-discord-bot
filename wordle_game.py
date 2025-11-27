# wordle_game.py

import random
import time
from word_lists import word_lists

class GuessResult:
    def __init__(self):
        self.statuses = []
        self.is_correct = False
        self.is_finished = False
        self.error = ""

class GameState:
    def __init__(self, answer, difficulty, max_guesses, channel_id):
        self.answer = answer
        self.difficulty = difficulty
        self.max_guesses = max_guesses
        self.guesses = []
        self.guess_results = []
        self.channel_id = channel_id
        self.created_at = time.time()
        self.is_hard_mode = difficulty == "hard"
        self.green_constraints = {}  # position -> required letter
        self.yellow_constraints = {}  # letter -> forbidden positions

    def apply_guess(self, guess):
        """Apply a guess to the game state"""
        result = GuessResult()
        
        # Validate guess length
        if len(guess) != 5:
            result.error = "Guess must be exactly 5 letters"
            return result
        
        # Validate guess is alphabetic
        if not guess.isalpha():
            result.error = "Guess must contain only letters"
            return result
        
        # Convert to lowercase
        guess_lower = guess.lower()
        
        # Check for repeated guess
        if guess_lower in self.guesses:
            result.error = "That word has already been guessed."
            return result
        
        # Validate guess is in allowed word list
        if not word_lists.is_valid_guess(guess_lower):
            result.error = "Not a valid word!"
            return result
        
        # Check hard mode constraints
        if self.is_hard_mode:
            hard_mode_check = self._check_hard_mode_constraints(guess_lower)
            if hard_mode_check != "":
                result.error = hard_mode_check
                return result
        
        # Process the guess
        self.guesses.append(guess_lower)
        
        # Calculate guess result
        statuses = self._calculate_guess_result(guess_lower)
        result.statuses = statuses
        result.is_correct = guess_lower == self.answer
        
        # Update constraints for hard mode
        if self.is_hard_mode:
            self._update_hard_mode_constraints(guess_lower, statuses)
        
        # Check if game is finished
        guesses_used = len(self.guesses)
        if result.is_correct or (self.max_guesses > 0 and guesses_used >= self.max_guesses):
            result.is_finished = True
        
        self.guess_results.append(result)
        return result

    def _check_hard_mode_constraints(self, guess):
        """Check if guess violates hard mode constraints"""
        # Check green constraints
        for i in range(5):
            if i in self.green_constraints:
                required_letter = self.green_constraints[i]
                if guess[i] != required_letter:
                    return f"Hard mode: position {i+1} must be '{required_letter.upper()}'"
        
        # Check yellow constraints - require the letter to be present somewhere
        for letter, forbidden_positions in self.yellow_constraints.items():
            if letter not in guess:
                return f"Hard mode: must use '{letter.upper()}' from previous guesses"
        
        return ""

    def _update_hard_mode_constraints(self, guess, statuses):
        """Update hard mode constraints based on the guess result"""
        for i in range(5):
            status = statuses[i]
            letter = guess[i]
            
            if status == "green":
                self.green_constraints[i] = letter
            elif status == "yellow":
                if letter not in self.yellow_constraints:
                    self.yellow_constraints[letter] = []
                if i not in self.yellow_constraints[letter]:
                    self.yellow_constraints[letter].append(i)

    def _calculate_guess_result(self, guess):
        """Calculate the Wordle result for a guess using official rules"""
        statuses = ["grey"] * 5
        
        # First pass: mark greens and track remaining letter counts
        remaining_counts = {}
        for i in range(5):
            answer_letter = self.answer[i]
            if answer_letter not in remaining_counts:
                remaining_counts[answer_letter] = 0
            remaining_counts[answer_letter] += 1
        
        # Mark greens and update remaining counts
        for i in range(5):
            if guess[i] == self.answer[i]:
                statuses[i] = "green"
                remaining_counts[guess[i]] -= 1
        
        # Second pass: mark yellows
        for i in range(5):
            if statuses[i] != "green":
                letter = guess[i]
                if letter in remaining_counts and remaining_counts[letter] > 0:
                    statuses[i] = "yellow"
                    remaining_counts[letter] -= 1
        
        return statuses

    def get_keyboard_state(self):
        """Get the current keyboard state based on all guesses"""
        keyboard_state = {}
        
        # Initialize all letters as "unguessed"
        letters = "qwertyuiopasdfghjklzxcvbnm"
        for letter in letters:
            keyboard_state[letter] = "unguessed"
        
        # Update based on all guess results
        for i, guess_result in enumerate(self.guess_results):
            guess = self.guesses[i]
            for j in range(5):
                letter = guess[j]
                status = guess_result.statuses[j]
                
                # Only upgrade status (grey -> yellow -> green)
                current_status = keyboard_state[letter]
                if current_status == "unguessed" or (
                    current_status == "grey" and status in ["yellow", "green"]
                ) or (
                    current_status == "yellow" and status == "green"
                ):
                    keyboard_state[letter] = status
        
        return keyboard_state

    def get_guess_count(self):
        """Get number of guesses made"""
        return len(self.guesses)

    def is_game_over(self):
        """Check if game is over"""
        if len(self.guesses) == 0:
            return False
        
        last_result = self.guess_results[-1]
        return last_result.is_finished

    def to_dict(self):
        """Convert game state to dict for storage"""
        game_dict = {
            "answer": self.answer,
            "difficulty": self.difficulty,
            "maxGuesses": self.max_guesses,
            "guesses": self.guesses.copy(),
            "channel_id": self.channel_id,
            "created_at": self.created_at,
            "is_hard_mode": self.is_hard_mode,
            "green_constraints": self.green_constraints.copy(),
            "yellow_constraints": {k: v.copy() for k, v in self.yellow_constraints.items()}
        }
        
        # Convert guess results
        guess_results_list = []
        for result in self.guess_results:
            result_dict = {
                "statuses": result.statuses.copy(),
                "is_correct": result.is_correct,
                "is_finished": result.is_finished,
                "error": result.error
            }
            guess_results_list.append(result_dict)
        
        game_dict["guess_results"] = guess_results_list
        return game_dict

    @classmethod
    def from_dict(cls, game_dict):
        """Create GameState from dict"""
        game_state = cls(
            game_dict["answer"],
            game_dict["difficulty"],
            game_dict["maxGuesses"],
            game_dict["channel_id"]
        )
        game_state.created_at = game_dict["created_at"]
        game_state.is_hard_mode = game_dict["is_hard_mode"]
        game_state.guesses = game_dict["guesses"].copy()
        
        # Restore guess results
        for result_dict in game_dict["guess_results"]:
            result = GuessResult()
            result.statuses = result_dict["statuses"].copy()
            result.is_correct = result_dict["is_correct"]
            result.is_finished = result_dict["is_finished"]
            result.error = result_dict["error"]
            game_state.guess_results.append(result)
        
        # Restore constraints
        raw_green = game_dict.get("green_constraints", {})
        # Convert JSON string keys ("0", "1", ...) back to ints
        game_state.green_constraints = {int(k): v for k, v in raw_green.items()}

        raw_yellow = game_dict.get("yellow_constraints", {})
        game_state.yellow_constraints = {k: v.copy() for k, v in raw_yellow.items()}

        
        return game_state

class WordleGame:
    @staticmethod
    def start_new_game(difficulty, channel_id):
        """Start a new Wordle game"""
        answer = word_lists.get_random_solution()
        
        # Determine max guesses based on difficulty
        max_guesses = WordleGame._get_max_guesses(difficulty)
        
        return GameState(answer, difficulty, max_guesses, channel_id)

    @staticmethod
    def _get_max_guesses(difficulty):
        """Get max guesses for a difficulty level"""
        if difficulty == "normal":
            return 0  # 0 means unlimited guesses
        elif difficulty == "hard":
            return 6
        else:  # default to normal
            return 0

    @staticmethod
    def calculate_points(difficulty, guesses_used):
        """Calculate points for a completed game"""
        # Special scoring for hard mode
        if difficulty == "hard":
            hard_mode_points = {
                1: 20,
                2: 18,
                3: 16,
                4: 14,
                5: 12,
                6: 10
            }
            return hard_mode_points.get(guesses_used, 0)
        
        # Normal mode: 10 - (guesses_used - 1), minimum 0
        if difficulty == "normal":
            points = 10 - (guesses_used - 1)
            return max(0, points)
        
        # Default to normal mode scoring
        points = 10 - (guesses_used - 1)
        return max(0, points)

    @staticmethod
    def _get_base_points(difficulty):
        """Get base points for a difficulty level"""
        if difficulty == "normal":
            return 10
        elif difficulty == "hard":
            return 15
        else:  # default to normal
            return 10

    @staticmethod
    def status_to_emoji(status):
        """Convert status to emoji"""
        if status == "green":
            return "🟩"
        elif status == "yellow":
            return "🟨"
        else:  # grey or unguessed
            return "⬛"

    @staticmethod
    def format_guess_display(guess, statuses):
        """Format a guess with emojis for display"""
        emojis = "".join(WordleGame.status_to_emoji(status) for status in statuses)
        return f"`{guess.upper()}`\n{emojis}"

    @staticmethod
    def format_keyboard_display(keyboard_state):
        """Format keyboard display with colored letters"""
        keyboard_layout = [
            "q w e r t y u i o p",
            " a s d f g h j k l ",
            "  z x c v b n m   "
        ]
        
        display_lines = []
        
        for line in keyboard_layout:
            display_line = ""
            for char in line:
                if char == " ":
                    display_line += " "
                else:
                    status = keyboard_state[char]
                    emoji = WordleGame.status_to_emoji(status)
                    display_line += emoji
            display_lines.append(display_line)
        
        return "\n".join(display_lines)

    @staticmethod
    def format_game_history(game_state):
        """Format the complete game history for display"""
        history_lines = []
        
        for i in range(len(game_state.guesses)):
            guess = game_state.guesses[i]
            result = game_state.guess_results[i]
            guess_number = i + 1
            emojis = "".join(WordleGame.status_to_emoji(status) for status in result.statuses)
            
            history_lines.append(f"{guess_number}. {guess.upper()}  {emojis}")
        
        return "\n".join(history_lines)