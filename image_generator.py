# image_generator.py

import os
import random
import time
from PIL import Image, ImageDraw, ImageFont


class WordleImageGenerator:
    def __init__(self):
        # Colors taken from your reference images
        self.colors = {
            "green": (11, 102, 35),      # correct
            "yellow": (221, 159, 33),    # present
            "grey": (43, 43, 45),        # absent

            "bg": (18, 18, 19),          # background
            "letter": (215, 218, 220),   # letter color
            "white": (255, 255, 255),    # icons
        }

        # Layout copied from reference:
        #   - image size: 990 x 210
        #   - 5 tiles, each 180x180
        #   - 15px margin all around and 15px gap between tiles
        self.tile_size = 180
        self.gap = 15
        self.margin = 15

        self.images_dir = "wordle_images"
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Font cache to avoid reloading fonts repeatedly
        self._font_cache = {}

    # ------------------------------------------------------------------ helpers

    def _get_font(self, size: int, bold: bool = False):
        """Load a real TTF font; fall back with a visible warning."""
        # Create a cache key based on size and bold
        cache_key = f"{size}_{bold}"
        
        # Return cached font if available
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(base_dir, "fonts")

        font_file = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        font_path = os.path.join(font_dir, font_file)

        try:
            print("Loading font:", font_path, "size:", size)
            font = ImageFont.truetype(font_path, size)
            # Cache the font for future use
            self._font_cache[cache_key] = font
            return font
        except Exception as e:
            print("Falling back to default font:", e)
            font = ImageFont.load_default()
            # Cache the default font too
            self._font_cache[cache_key] = font
            return font


    def _normalize_status(self, status: str) -> str:
        """Map various status labels to green/yellow/grey."""
        s = (status or "").lower()
        if s in ("green", "yellow", "grey"):
            return s

        mapping = {
            "correct": "green",
            "present": "yellow",
            "found": "yellow",
            "absent": "grey",
            "miss": "grey",
            "wrong": "grey",
        }
        return mapping.get(s, "grey")

    def _draw_status_icon(self, draw: ImageDraw.ImageDraw, status: str, x0: int, y0: int):
        """
        Draws the small icon in the top-right corner of a tile:

        - green  -> check mark ✓
        - yellow -> hollow circle ○
        - grey   -> X
        """
        ts = self.tile_size

        icon_size = int(ts * 0.10)       # ≈ 24px for 180px tile
        pad_top = int(ts * 0.02)         # ≈ 5px from top
        pad_right = int(ts * 0.02)       # ≈ 3–4px from right

        x1 = x0 + ts - pad_right - icon_size
        y1 = y0 + pad_top
        x2 = x1 + icon_size
        y2 = y1 + icon_size

        line_w = max(2, icon_size // 6)
        white = self.colors["white"]

        status = self._normalize_status(status)

        if status == "green":
            # Check mark
            p1 = (x1 + icon_size * 0.10, y1 + icon_size * 0.55)
            p2 = (x1 + icon_size * 0.40, y1 + icon_size * 0.85)
            p3 = (x1 + icon_size * 0.90, y1 + icon_size * 0.15)
            draw.line([p1, p2, p3], fill=white, width=line_w)

        elif status == "yellow":
            # Hollow circle
            draw.ellipse([x1, y1, x2, y2], outline=white, width=line_w)

        else:
            # X
            draw.line([x1, y1, x2, y2], fill=white, width=line_w)
            draw.line([x1, y2, x2, y1], fill=white, width=line_w)

    def _draw_row(self, draw, word: str, statuses, row_index: int):
        """
        Draw a row of 5 tiles (same look as your reference) starting at row_index.
        """
        if len(word) != 5 or len(statuses) != 5:
            raise ValueError("Word and statuses must be exactly 5 elements")

        y0 = self.margin + row_index * (self.tile_size + self.gap)
        font = self._get_font(int(self.tile_size * 0.7), bold=True)

        for i, ch in enumerate(word):
            x0 = self.margin + i * (self.tile_size + self.gap)

            status = self._normalize_status(statuses[i])
            tile_color = self.colors[status]

            # Tile
            draw.rectangle(
                [x0, y0, x0 + self.tile_size, y0 + self.tile_size],
                fill=tile_color,
            )

            # --- Letter (perfectly centered) ---
            letter = ch.upper()
            cx = x0 + self.tile_size // 2
            cy = y0 + self.tile_size // 2

            try:
                # Pillow >= 8: anchor="mm" -> center of text at (cx, cy)
                draw.text(
                    (cx, cy),
                    letter,
                    font=font,
                    fill=self.colors["letter"],
                    anchor="mm",
                )
            except TypeError:
                # Fallback for older Pillow: manual centering
                bbox = draw.textbbox((0, 0), letter, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = x0 + (self.tile_size - tw) // 2
                ty = y0 + (self.tile_size - th) // 2
                draw.text((tx, ty), letter, font=font, fill=self.colors["letter"])
            # -----------------------------------

            # Status icon
            self._draw_status_icon(draw, status, x0, y0)

    def _generate_multi_row_image(self, game_state, filename: str | None, prefix: str):
        """
        Shared implementation for game history / status images:
        just stacks the exact same row aesthetic vertically.
        """
        if not game_state.guesses:
            raise ValueError("No guesses in game state")

        rows = len(game_state.guesses)

        width = 2 * self.margin + 5 * self.tile_size + 4 * self.gap
        height = 2 * self.margin + rows * self.tile_size + (rows - 1) * self.gap

        image = Image.new("RGB", (width, height), self.colors["bg"])
        draw = ImageDraw.Draw(image)

        for row_index in range(rows):
            word = game_state.guesses[row_index]
            guess_result = game_state.guess_results[row_index]
            statuses = guess_result.statuses
            self._draw_row(draw, word, statuses, row_index)

        if not filename:
            filename = f"{prefix}_{random.randint(1000, 9999)}.png"

        filepath = os.path.join(self.images_dir, filename)
        image.save(filepath, "PNG")
        return filepath

    # ------------------------------------------------------------------ public API

    def generate_guess_image(self, word, statuses, filename=None):
        """
        Single-row image that matches your TAINT / PANIC examples.
        Size: 990 x 210, 5 tiles with ✓ / ○ / ✕ icons.
        """
        if len(word) != 5 or len(statuses) != 5:
            raise ValueError("Word and statuses must be exactly 5 elements")

        width = 2 * self.margin + 5 * self.tile_size + 4 * self.gap
        height = 2 * self.margin + self.tile_size

        image = Image.new("RGB", (width, height), self.colors["bg"])
        draw = ImageDraw.Draw(image)

        # Draw row 0
        self._draw_row(draw, word, statuses, row_index=0)

        if not filename:
            filename = f"wordle_guess_{word}_{random.randint(1000, 9999)}.png"

        filepath = os.path.join(self.images_dir, filename)
        image.save(filepath, "PNG")
        return filepath

    def generate_game_history_image(self, game_state, filename=None):
        """
        Multi-row history: each row uses the exact same aesthetic
        as generate_guess_image, stacked vertically.
        """
        return self._generate_multi_row_image(
            game_state, filename, prefix="wordle_history"
        )

    def generate_status_image(self, game_state, filename=None):
        """
        Multi-row status image (current progress), visually identical
        to the history image but with a different default filename prefix.
        """
        return self._generate_multi_row_image(
            game_state, filename, prefix="wordle_status"
        )

    def generate_keyboard_image(self, keyboard_state, filename=None):
        """
        Generate a QWERTY keyboard image for the current game.

        - Non-used letters: white keys
        - Letters seen as grey/yellow: grey keys (no yellow color)
        - Letters seen as green: green keys
        """
        # QWERTY layout
        rows = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
        ]

        # Key geometry (smaller than main tiles)
        key_width = 60
        key_height = 80
        gap = 8
        margin_x = 20
        margin_y = 20

        max_row_len = max(len(r) for r in rows)
        width = margin_x * 2 + max_row_len * key_width + (max_row_len - 1) * gap
        height = margin_y * 2 + len(rows) * key_height + (len(rows) - 1) * gap

        image = Image.new("RGB", (width, height), self.colors["bg"])
        draw = ImageDraw.Draw(image)
        font = self._get_font(int(key_height * 0.5), bold=True)

        for row_index, row in enumerate(rows):
            y0 = margin_y + row_index * (key_height + gap)

            row_width = len(row) * key_width + (len(row) - 1) * gap
            x_start = (width - row_width) // 2

            for col_index, ch in enumerate(row):
                x0 = x_start + col_index * (key_width + gap)

                status = keyboard_state.get(ch, "unguessed")
                status = (status or "").lower()

                if status == "green":
                    fill = self.colors["green"]
                    text_color = self.colors["white"]  # White text on green
                elif status in ("grey", "yellow"):
                    # We only want grey here, no yellow color on the keyboard
                    fill = self.colors["grey"]
                    text_color = self.colors["white"]  # White text on grey
                else:
                    # Non-used letters -> white background
                    fill = self.colors["white"]
                    text_color = self.colors["bg"]  # Black text on white

                # Draw key rectangle
                draw.rounded_rectangle(
                    [x0, y0, x0 + key_width, y0 + key_height],
                    radius=10,
                    fill=fill,
                )

                # Draw letter centered on the key
                letter = ch.upper()
                cx = x0 + key_width // 2
                cy = y0 + key_height // 2

                try:
                    draw.text(
                        (cx, cy),
                        letter,
                        font=font,
                        fill=text_color,
                        anchor="mm",
                    )
                except TypeError:
                    # Fallback centering for older Pillow
                    bbox = draw.textbbox((0, 0), letter, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    tx = x0 + (key_width - tw) // 2
                    ty = y0 + (key_height - th) // 2
                    draw.text((tx, ty), letter, font=font, fill=text_color)

        if not filename:
            filename = f"wordle_keyboard_{random.randint(1000, 9999)}.png"

        filepath = os.path.join(self.images_dir, filename)
        image.save(filepath, "PNG")
        return filepath

    def cleanup_old_images(self, max_age_hours=24):
        """Clean up old image files to prevent disk space issues."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        for filename in os.listdir(self.images_dir):
            if filename.endswith(".png"):
                filepath = os.path.join(self.images_dir, filename)
                try:
                    file_age = current_time - os.path.getmtime(filepath)
                except OSError:
                    continue

                if file_age > max_age_seconds:
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass


# Global instance
image_generator = WordleImageGenerator()
