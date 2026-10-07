"""
Snake Game - Classic Arcade Clone
Python + Pygame

Features:
- 1 or 2 player mode
- Classic and Reverse game modes (controls flip every time food is eaten)
- Poison food (shrinks the snake and costs points)
- Difficulty selection and colour themes
- Sound effects (generated in code)
- Individual player scores
- Multiplayer snake collisions
- Bonus food
- High scores for single-player mode

Controls:
  1 player : WASD or Arrow keys
  2 players: Player 1 = WASD, Player 2 = Arrow keys
  P pause, ESC back to menu
"""

import json
import math
import os
import random
import sys
from array import array

import pygame

# ----------------------------- Settings ------------------------------------

CELL = 20
COLS, ROWS = 30, 22
HUD_HEIGHT = 40

WIDTH = COLS * CELL
HEIGHT = ROWS * CELL + HUD_HEIGHT

FOODS_PER_LEVEL = 4
BONUS_EVERY = 5
BONUS_DURATION_MS = 5000

MAX_FPS = 28

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

# Poison feature settings
POISON_EVERY = 3                # a poison item appears after every N normal foods
POISON_DURATION_MS = 8000       # poison disappears after this long
POISON_PENALTY = 2              # points lost when poison is eaten
POISON_SHRINK = 2               # tail segments lost when poison is eaten
MIN_SNAKE_LENGTH = 3            # poison that would shrink below this kills the snake
MAX_POISON_ON_SCREEN = 2
POISON_COLOUR = (170, 70, 220)  # purple

# ----------------------------- Difficulty -----------------------------------

DIFFICULTIES = {
    "Easy": {"base_fps": 6, "step": 1},
    "Medium": {"base_fps": 8, "step": 2},
    "Hard": {"base_fps": 11, "step": 2},
}
DIFFICULTY_NAMES = list(DIFFICULTIES.keys())

# ----------------------------- Game modes -----------------------------------

GAME_MODES = ["Classic", "Reverse"]

# ----------------------------- Colour themes --------------------------------

THEMES = {
    "Classic": {
        "bg": (15, 15, 20), "grid": (28, 28, 36), "hud": (25, 25, 35),
        "head": (90, 230, 120), "tail": (25, 110, 55),
        "food": (230, 60, 60), "bonus": (250, 200, 40),
        "text": (240, 240, 240), "accent": (250, 200, 40), "muted": (150, 150, 160),
    },
    "Neon": {
        "bg": (10, 5, 25), "grid": (25, 15, 50), "hud": (20, 10, 40),
        "head": (0, 255, 230), "tail": (120, 40, 200),
        "food": (255, 60, 180), "bonus": (255, 240, 60),
        "text": (235, 235, 255), "accent": (255, 60, 180), "muted": (140, 130, 190),
    },
    "Retro": {
        "bg": (8, 22, 8), "grid": (14, 36, 14), "hud": (10, 30, 10),
        "head": (150, 255, 120), "tail": (40, 120, 40),
        "food": (220, 255, 120), "bonus": (255, 255, 255),
        "text": (170, 255, 150), "accent": (220, 255, 120), "muted": (90, 160, 90),
    },
    "Sunset": {
        "bg": (30, 15, 30), "grid": (45, 25, 45), "hud": (40, 20, 40),
        "head": (255, 190, 90), "tail": (200, 60, 90),
        "food": (120, 230, 255), "bonus": (255, 255, 140),
        "text": (255, 235, 220), "accent": (255, 150, 80), "muted": (190, 140, 150),
    },
}
THEME_NAMES = list(THEMES.keys())

# ----------------------------- Directions -----------------------------------

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


# ----------------------------- Helpers --------------------------------------

def lerp_colour(c1, c2, t):
    """Blend two RGB colours; t=0 gives c1, t=1 gives c2."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def load_high_scores():
    """Read per-difficulty high scores from disk."""
    scores = {name: 0 for name in DIFFICULTY_NAMES}
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        for name in DIFFICULTY_NAMES:
            scores[name] = int(data.get(name, 0))
    except (OSError, ValueError, TypeError):
        pass
    return scores


def save_high_scores(scores):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(scores, f)
    except OSError:
        pass


def make_tone(freq_start, freq_end, ms, volume=0.35):
    """Build a short beep (optionally sliding in pitch) as a pygame Sound."""
    sample_rate = 22050
    n = int(sample_rate * ms / 1000)
    buf = array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase += 2 * math.pi * freq / sample_rate
        envelope = 1.0 - t
        buf.append(int(32767 * volume * envelope * math.sin(phase)))
    return pygame.mixer.Sound(buffer=buf.tobytes())


# ----------------------------- Game objects ---------------------------------

class Snake:
    """The snake: a list of grid cells, head first."""

    def __init__(self, start_pos, direction=RIGHT):
        self.player_id = None
        self.color = None            # None = use the theme colours

        start_x, start_y = start_pos
        dx, dy = direction
        self.body = [
            (start_x, start_y),
            (start_x - dx, start_y - dy),
            (start_x - 2 * dx, start_y - 2 * dy),
        ]
        self.direction = direction
        self.next_direction = direction
        self.grow_pending = 0

    @property
    def head(self):
        return self.body[0]

    def set_direction(self, new_dir):
        """Never allow a 180-degree reverse."""
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.next_direction = new_dir

    def move(self):
        """Advance one cell."""
        self.direction = self.next_direction
        new_head = (self.head[0] + self.direction[0], self.head[1] + self.direction[1])
        self.body.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def grow(self, amount=1):
        self.grow_pending += amount

    def hit_wall(self):
        x, y = self.head
        return x < 0 or x >= COLS or y < 0 or y >= ROWS

    def hit_self(self):
        return self.head in self.body[1:]

    def draw(self, surface, theme):
        total = len(self.body)
        for i, (x, y) in enumerate(self.body):
            rect = pygame.Rect(x * CELL, y * CELL + HUD_HEIGHT, CELL, CELL)
            t = i / max(total - 1, 1)
            if self.color is not None:
                darker = tuple(max(0, c - 70) for c in self.color)
                colour = lerp_colour(self.color, darker, t)
            else:
                colour = lerp_colour(theme["head"], theme["tail"], t)
            pygame.draw.rect(surface, colour, rect.inflate(-2, -2), border_radius=6)
        self._draw_eyes(surface)

    def _draw_eyes(self, surface):
        hx, hy = self.head
        cx = hx * CELL + CELL // 2
        cy = hy * CELL + HUD_HEIGHT + CELL // 2
        dx, dy = self.direction
        px, py = -dy, dx
        for side in (1, -1):
            ex = cx + dx * 4 + px * 4 * side
            ey = cy + dy * 4 + py * 4 * side
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), 3)
            pygame.draw.circle(surface, (0, 0, 0), (ex + dx, ey + dy), 1)


class Food:
    """A food item placed on a random free cell.

    snakes: list of Snake objects whose bodies are blocked.
    avoid:  extra cells to keep clear (other food, poison).
    """

    def __init__(self, snakes, bonus=False, avoid=()):
        self.bonus = bonus
        self.points = 5 if bonus else 1
        self.spawn_time = pygame.time.get_ticks()
        self.pos = self._random_free_cell(snakes, avoid)

    @staticmethod
    def _random_free_cell(snakes, avoid):
        blocked = set(avoid)
        for snake in snakes:
            blocked.update(snake.body)
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in blocked]
        return random.choice(free)

    def expired(self):
        return self.bonus and pygame.time.get_ticks() - self.spawn_time > BONUS_DURATION_MS

    def draw(self, surface, theme):
        x, y = self.pos
        rect = pygame.Rect(x * CELL, y * CELL + HUD_HEIGHT, CELL, CELL)
        colour = theme["bonus"] if self.bonus else theme["food"]
        if self.bonus:
            pulse = int(2 * math.sin(pygame.time.get_ticks() / 120))
            pygame.draw.ellipse(surface, colour, rect.inflate(-2 + pulse, -2 + pulse))
        else:
            pygame.draw.ellipse(surface, colour, rect.inflate(-4, -4))


class PoisonFood:
    """Poison item: purple, flickers before it vanishes.
    Eating it shrinks the snake and costs points."""

    def __init__(self, snakes, avoid):
        self.spawn_time = pygame.time.get_ticks()
        blocked = set(avoid)
        for snake in snakes:
            blocked.update(snake.body)
        heads = [snake.head for snake in snakes]
        # Keep poison a few cells away from every head so players can react
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in blocked
                and all(abs(x - hx) + abs(y - hy) > 3 for hx, hy in heads)]
        self.pos = random.choice(free)

    def expired(self):
        return pygame.time.get_ticks() - self.spawn_time > POISON_DURATION_MS

    def draw(self, surface):
        age = pygame.time.get_ticks() - self.spawn_time
        # Flicker during the last 2 seconds as a warning that it will vanish
        if age > POISON_DURATION_MS - 2000 and (age // 150) % 2 == 0:
            return
        x, y = self.pos
        rect = pygame.Rect(x * CELL, y * CELL + HUD_HEIGHT, CELL, CELL)
        pygame.draw.ellipse(surface, POISON_COLOUR, rect.inflate(-4, -4))
        cx, cy = rect.center
        pygame.draw.line(surface, (255, 255, 255), (cx - 3, cy - 3), (cx + 3, cy + 3), 2)
        pygame.draw.line(surface, (255, 255, 255), (cx - 3, cy + 3), (cx + 3, cy - 3), 2)


class Popup:
    """Floating score text that rises and fades."""

    DURATION_MS = 800

    def __init__(self, text, x, y, colour):
        self.text, self.x, self.y, self.colour = text, x, y, colour
        self.start = pygame.time.get_ticks()

    def alive(self):
        return pygame.time.get_ticks() - self.start < self.DURATION_MS

    def draw(self, surface, font):
        t = (pygame.time.get_ticks() - self.start) / self.DURATION_MS
        img = font.render(self.text, True, self.colour)
        img.set_alpha(int(255 * (1 - t)))
        surface.blit(img, (self.x - img.get_width() // 2, self.y - int(30 * t)))


# ----------------------------- Main game class ------------------------------

class Game:
    MENU_ITEMS = ["Play", "Players", "Mode", "Difficulty", "Theme", "Sound", "Quit"]

    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("Snake")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("consolas", 22)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 52, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 80, bold=True)

        self.sounds = self._load_sounds()

        # Settings chosen from the menu
        self.difficulty_index = 1
        self.mode_index = 0
        self.player_count = 1
        self.theme_index = 0
        self.sound_on = True

        self.high_scores = load_high_scores()
        self.state = "menu"           # "menu", "playing", "gameover"
        self.menu_index = 0
        self.reset()

    # ------------------------- Settings -------------------------

    @property
    def difficulty(self):
        return DIFFICULTY_NAMES[self.difficulty_index]

    @property
    def game_mode(self):
        return GAME_MODES[self.mode_index]

    @property
    def theme(self):
        return THEMES[THEME_NAMES[self.theme_index]]

    @property
    def high_score(self):
        return self.high_scores[self.difficulty]

    # ------------------------- Sound ----------------------------

    def _load_sounds(self):
        try:
            return {
                "move": make_tone(500, 500, 40, 0.2),
                "select": make_tone(700, 900, 90),
                "eat": make_tone(600, 1000, 110),
                "bonus": make_tone(800, 1600, 260),
                "gameover": make_tone(400, 90, 600, 0.45),
                "poison": make_tone(350, 110, 320, 0.4),
            }
        except pygame.error:
            return {}

    def play(self, name):
        if self.sound_on and name in self.sounds:
            self.sounds[name].play()

    # ------------------------- Game setup -----------------------

    def reset(self):
        """Start (or restart) a fresh game with the current settings."""
        start_positions = [(5, 5), (COLS - 6, 5)]
        directions = [RIGHT, LEFT]
        player_colors = [(50, 220, 120), (80, 160, 255)]   # P1 green, P2 blue

        self.scores = [0] * self.player_count
        self.winner = None
        self.snakes = []

        for i in range(self.player_count):
            snake = Snake(start_positions[i], directions[i])
            snake.player_id = i
            snake.color = player_colors[i] if self.player_count == 2 else None
            self.snakes.append(snake)

        self.poison_foods = []
        self.bonus_food = None
        self.food = None
        self.food = Food(self.snakes, avoid=self.extra_cells())

        self.flash_until = 0          # time until which the poison flash is shown
        self.popups = []
        self.foods_eaten = 0
        self.level = 1
        self.paused = False
        self.new_best = False
        self.reverse_controls = False

    def start_game(self):
        self.reset()
        self.state = "playing"

    def extra_cells(self):
        """Cells taken by food, bonus food and poison (used to avoid overlaps)."""
        cells = [p.pos for p in self.poison_foods]
        if self.food is not None:
            cells.append(self.food.pos)
        if self.bonus_food is not None:
            cells.append(self.bonus_food.pos)
        return cells

    # ------------------------- Difficulty -----------------------

    @property
    def fps(self):
        cfg = DIFFICULTIES[self.difficulty]
        return min(cfg["base_fps"] + (self.level - 1) * cfg["step"], MAX_FPS)

    # ------------------------- Events ---------------------------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type != pygame.KEYDOWN:
                continue
            if self.state == "menu":
                self.handle_menu_key(event.key)
            elif self.state == "playing":
                self.handle_play_key(event.key)
            else:
                self.handle_gameover_key(event.key)

    # ------------------------- Menu -----------------------------

    def handle_menu_key(self, key):
        if key == pygame.K_ESCAPE:
            self.quit()
        elif key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.MENU_ITEMS)
            self.play("move")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.MENU_ITEMS)
            self.play("move")
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.change_setting(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.change_setting(1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            item = self.MENU_ITEMS[self.menu_index]
            if item == "Play":
                self.play("select")
                self.start_game()
            elif item == "Quit":
                self.quit()
            else:
                self.change_setting(1)

    def change_setting(self, step):
        """Change the highlighted menu setting."""
        item = self.MENU_ITEMS[self.menu_index]
        if item == "Players":
            self.player_count = 1 + ((self.player_count - 1 + step) % 2)   # toggle 1 <-> 2
        elif item == "Mode":
            self.mode_index = (self.mode_index + step) % len(GAME_MODES)
        elif item == "Difficulty":
            self.difficulty_index = (self.difficulty_index + step) % len(DIFFICULTY_NAMES)
        elif item == "Theme":
            self.theme_index = (self.theme_index + step) % len(THEME_NAMES)
        elif item == "Sound":
            self.sound_on = not self.sound_on
        else:
            return
        self.play("select")

    # ------------------------- Player controls ------------------

    def player_controls(self):
        """Key maps per player. A single player may use WASD or the arrow keys."""
        wasd = {pygame.K_w: UP, pygame.K_s: DOWN, pygame.K_a: LEFT, pygame.K_d: RIGHT}
        arrows = {pygame.K_UP: UP, pygame.K_DOWN: DOWN,
                  pygame.K_LEFT: LEFT, pygame.K_RIGHT: RIGHT}
        if self.player_count == 1:
            return [{**wasd, **arrows}]
        return [wasd, arrows]

    def handle_play_key(self, key):
        if key == pygame.K_ESCAPE:
            self.state = "menu"
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif not self.paused:
            controls = self.player_controls()
            # Look up the snake by player_id so controls stay correct after a player dies
            for snake in self.snakes:
                keymap = controls[snake.player_id]
                if key in keymap:
                    direction = keymap[key]
                    if self.reverse_controls:           # Reverse mode: flip the input
                        direction = (-direction[0], -direction[1])
                    snake.set_direction(direction)
                    break

    def handle_gameover_key(self, key):
        if key == pygame.K_r:
            self.start_game()
        elif key in (pygame.K_m, pygame.K_ESCAPE):
            self.state = "menu"
        elif key == pygame.K_q:
            self.quit()

    # ------------------------- Game logic -----------------------

    def update(self):
        if self.state != "playing" or self.paused:
            return

        for snake in self.snakes:
            snake.move()

        dead_players = set()

        # Wall and self collisions
        for i, snake in enumerate(self.snakes):
            if snake.hit_wall() or snake.hit_self():
                dead_players.add(i)

        # Snake vs other snake
        for i, snake in enumerate(self.snakes):
            if i in dead_players:
                continue
            for j, other in enumerate(self.snakes):
                if i != j and snake.head in other.body:
                    dead_players.add(i)
                    break

        # Head-to-head collisions
        head_positions = {}
        for i, snake in enumerate(self.snakes):
            head_positions.setdefault(snake.head, []).append(i)
        for players in head_positions.values():
            if len(players) > 1:
                dead_players.update(players)

        # Remove dead snakes
        self.snakes = [s for i, s in enumerate(self.snakes) if i not in dead_players]

        if self.check_round_over():
            return

        # Normal food
        for snake in self.snakes:
            if snake.head == self.food.pos:
                self.eat(self.food, snake)

                if self.game_mode == "Reverse":
                    self.reverse_controls = not self.reverse_controls

                self.foods_eaten += 1
                self.level = 1 + self.foods_eaten // FOODS_PER_LEVEL
                self.food = Food(self.snakes, avoid=self.extra_cells())

                if self.foods_eaten % BONUS_EVERY == 0 and self.bonus_food is None:
                    self.bonus_food = Food(self.snakes, bonus=True, avoid=self.extra_cells())

                if (self.foods_eaten % POISON_EVERY == 0
                        and len(self.poison_foods) < MAX_POISON_ON_SCREEN):
                    self.poison_foods.append(PoisonFood(self.snakes, self.extra_cells()))
                break

        # Bonus food
        if self.bonus_food:
            for snake in self.snakes:
                if snake.head == self.bonus_food.pos:
                    self.eat(self.bonus_food, snake)
                    self.bonus_food = None
                    break

        # Poison
        for snake in list(self.snakes):
            for poison in list(self.poison_foods):
                if snake.head == poison.pos:
                    self.poison_foods.remove(poison)
                    self.eat_poison(poison, snake)
                    if self.state == "gameover":
                        return

        # Timeouts
        if self.bonus_food and self.bonus_food.expired():
            self.bonus_food = None
        self.poison_foods = [p for p in self.poison_foods if not p.expired()]

        self.popups = [p for p in self.popups if p.alive()]

    def check_round_over(self):
        """End the game if everyone died or only one of two players is left."""
        if not self.snakes:
            self.winner = None
            self.end_game()
            return True
        if self.player_count == 2 and len(self.snakes) == 1:
            self.winner = self.snakes[0].player_id
            self.end_game()
            return True
        return False

    # ------------------------- Eating ---------------------------

    def eat(self, food, snake):
        self.scores[snake.player_id] += food.points
        snake.grow(1)

        x, y = food.pos
        px = x * CELL + CELL // 2
        py = y * CELL + HUD_HEIGHT

        if food.bonus:
            colour = self.theme["bonus"]
        elif snake.color is not None:
            colour = snake.color
        else:
            colour = self.theme["text"]

        self.popups.append(Popup(f"+{food.points}", px, py, colour))
        self.play("bonus" if food.bonus else "eat")

    def eat_poison(self, poison, snake):
        """Penalty: lose points and tail segments. Too short -> that snake dies."""
        x, y = poison.pos
        self.popups.append(Popup(f"-{POISON_PENALTY}", x * CELL + CELL // 2,
                                 y * CELL + HUD_HEIGHT, POISON_COLOUR))
        self.play("poison")
        self.flash_until = pygame.time.get_ticks() + 250

        if len(snake.body) - POISON_SHRINK < MIN_SNAKE_LENGTH:
            self.snakes.remove(snake)        # too short to survive
            self.check_round_over()
            return

        pid = snake.player_id
        self.scores[pid] = max(0, self.scores[pid] - POISON_PENALTY)
        for _ in range(POISON_SHRINK):
            snake.body.pop()
        snake.grow_pending = 0

    # ------------------------- End game -------------------------

    def end_game(self):
        self.state = "gameover"
        self.play("gameover")

        # High score is saved for 1-player mode only
        if self.player_count == 1 and self.scores[0] > self.high_scores[self.difficulty]:
            self.high_scores[self.difficulty] = self.scores[0]
            self.new_best = True
            save_high_scores(self.high_scores)

    # ------------------------- Drawing helpers ------------------

    def draw_text(self, text, font, colour, center=None, topleft=None, topright=None):
        surf = font.render(text, True, colour)
        rect = surf.get_rect()
        if center:
            rect.center = center
        if topleft:
            rect.topleft = topleft
        if topright:
            rect.topright = topright
        self.screen.blit(surf, rect)

    def draw_overlay(self, title, lines):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        t = self.theme
        self.draw_text(title, self.big_font, t["text"], center=(WIDTH // 2, HEIGHT // 2 - 60))
        for i, line in enumerate(lines):
            self.draw_text(line, self.font, t["muted"], center=(WIDTH // 2, HEIGHT // 2 + i * 32))

    # ------------------------- Draw game ------------------------

    def draw_game(self):
        t = self.theme
        self.screen.fill(t["bg"])

        for x in range(0, WIDTH, CELL):
            pygame.draw.line(self.screen, t["grid"], (x, HUD_HEIGHT), (x, HEIGHT))
        for y in range(HUD_HEIGHT, HEIGHT, CELL):
            pygame.draw.line(self.screen, t["grid"], (0, y), (WIDTH, y))

        self.food.draw(self.screen, t)
        if self.bonus_food:
            self.bonus_food.draw(self.screen, t)
        for poison in self.poison_foods:
            poison.draw(self.screen)
        for snake in self.snakes:
            snake.draw(self.screen, t)
        for p in self.popups:
            p.draw(self.screen, self.small_font)

        # Brief purple flash when poison is eaten
        if pygame.time.get_ticks() < self.flash_until:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*POISON_COLOUR, 70))
            self.screen.blit(flash, (0, 0))

        # Reverse-mode indicator
        if self.reverse_controls:
            self.draw_text("CONTROLS REVERSED", self.small_font, t["accent"],
                           center=(WIDTH // 2, HUD_HEIGHT + 14))

        # HUD
        pygame.draw.rect(self.screen, t["hud"], (0, 0, WIDTH, HUD_HEIGHT))
        score_text = "  ".join(f"P{i + 1}: {self.scores[i]}" for i in range(self.player_count))
        self.draw_text(score_text, self.font, t["text"], topleft=(10, 8))
        self.draw_text(f"{self.difficulty} - Lvl {self.level}", self.font, t["accent"],
                       center=(WIDTH // 2, HUD_HEIGHT // 2))
        if self.player_count == 1:
            self.draw_text(f"Best: {self.high_score}", self.font, t["muted"],
                           topright=(WIDTH - 10, 8))

        if self.paused:
            self.draw_overlay("PAUSED", ["Press P to resume"])

        if self.state == "gameover":
            lines = ["Final Scores:", score_text]
            if self.player_count == 2:
                lines.insert(0, f"PLAYER {self.winner + 1} WINS!" if self.winner is not None
                             else "DRAW!")
            if self.new_best:
                lines.append("NEW HIGH SCORE!")
            lines.append("R restart  |  M menu  |  Q quit")
            self.draw_overlay("GAME OVER", lines)

    # ------------------------- Draw menu ------------------------

    def draw_menu(self):
        t = self.theme
        self.screen.fill(t["bg"])

        # Animated decorative snake
        ticks = pygame.time.get_ticks()
        for i in range(18):
            x = WIDTH // 2 - 180 + i * 20
            y = 175 + int(8 * math.sin(ticks / 250 + i * 0.5))
            pygame.draw.circle(self.screen, lerp_colour(t["head"], t["tail"], i / 17), (x, y), 8)

        self.draw_text("SNAKE", self.title_font, t["head"], center=(WIDTH // 2, 100))

        values = {
            "Players": f"< {self.player_count} >",
            "Mode": f"< {self.game_mode} >",
            "Difficulty": f"< {self.difficulty} >",
            "Theme": f"< {THEME_NAMES[self.theme_index]} >",
            "Sound": f"< {'On' if self.sound_on else 'Off'} >",
        }

        for i, item in enumerate(self.MENU_ITEMS):
            selected = i == self.menu_index
            colour = t["accent"] if selected else t["text"]
            label = f"> {item}" if selected else item
            y = 215 + i * 32
            self.draw_text(label, self.font, colour, topleft=(WIDTH // 2 - 130, y))
            if item in values:
                self.draw_text(values[item], self.font, colour, topright=(WIDTH // 2 + 150, y))

        if self.player_count == 1:
            self.draw_text(f"High score ({self.difficulty}): {self.high_score}",
                           self.small_font, t["muted"], center=(WIDTH // 2, HEIGHT - 50))
        else:
            self.draw_text("P1: WASD    P2: Arrow keys",
                           self.small_font, t["muted"], center=(WIDTH // 2, HEIGHT - 50))
        self.draw_text("UP/DOWN select   LEFT/RIGHT change   ENTER confirm",
                       self.small_font, t["muted"], center=(WIDTH // 2, HEIGHT - 26))

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    # ------------------------- Main loop ------------------------

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(30 if self.state == "menu" else self.fps)

    @staticmethod
    def quit():
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()