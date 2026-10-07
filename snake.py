"""
Snake Game - Classic Arcade Clone (Python + Pygame)  --  Version 2 (upgraded interface)

New in this version:
  - Start menu (Play / Difficulty / Theme / Sound / Quit)
  - Three difficulty levels (Easy, Medium, Hard) with separate high scores
  - Four colour themes
  - Sound effects (generated in code, so no audio files are needed)
  - Better visuals: gradient body, eyes on the head, floating "+score" pop-ups

Controls:
  Menu    : UP/DOWN select, LEFT/RIGHT change a setting, ENTER choose, ESC quit
  In game : Arrow keys / WASD move, P pause, ESC back to menu
  Game over: R restart, M menu, Q quit

Run:
  pip install pygame
  python snake_v2.py
"""

import json
import math
import os
import random
import sys
from array import array

import pygame

# ----------------------------- Settings ------------------------------------
CELL = 20                      # size of one grid cell in pixels
COLS, ROWS = 30, 22            # grid size
HUD_HEIGHT = 40                # top bar for score text
WIDTH = COLS * CELL
HEIGHT = ROWS * CELL + HUD_HEIGHT

FOODS_PER_LEVEL = 4            # level up after this many foods
BONUS_EVERY = 5                # a bonus food appears after every N normal foods
BONUS_DURATION_MS = 5000       # bonus food lifetime
MAX_FPS = 28                   # speed cap for every difficulty
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

#Poison feature settings
POISON_EVERY = 3
POISON_DURATION_MS = 8000
POISON_PENALTY = 2
POISON_SHRINK = 2
MIN_SNAKE_LENGTH = 3
MAX_POISON_ON_SCREEN = 2
POISON_COLOUR = (170, 70, 220) #Purple
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")

# Difficulty: starting speed and how much speed rises per level
DIFFICULTIES = {
    "Easy":   {"base_fps": 6,  "step": 1},
    "Medium": {"base_fps": 8,  "step": 2},
    "Hard":   {"base_fps": 11, "step": 2},
}
DIFFICULTY_NAMES = list(DIFFICULTIES.keys())

# Colour themes
THEMES = {
    "Classic": {"bg": (15, 15, 20), "grid": (28, 28, 36), "hud": (25, 25, 35),
                "head": (90, 230, 120), "tail": (25, 110, 55), "food": (230, 60, 60),
                "bonus": (250, 200, 40), "text": (240, 240, 240), "accent": (250, 200, 40),
                "muted": (150, 150, 160)},
    "Neon":    {"bg": (10, 5, 25), "grid": (25, 15, 50), "hud": (20, 10, 40),
                "head": (0, 255, 230), "tail": (120, 40, 200), "food": (255, 60, 180),
                "bonus": (255, 240, 60), "text": (235, 235, 255), "accent": (255, 60, 180),
                "muted": (140, 130, 190)},
    "Retro":   {"bg": (8, 22, 8), "grid": (14, 36, 14), "hud": (10, 30, 10),
                "head": (150, 255, 120), "tail": (40, 120, 40), "food": (220, 255, 120),
                "bonus": (255, 255, 255), "text": (170, 255, 150), "accent": (220, 255, 120),
                "muted": (90, 160, 90)},
    "Sunset":  {"bg": (30, 15, 30), "grid": (45, 25, 45), "hud": (40, 20, 40),
                "head": (255, 190, 90), "tail": (200, 60, 90), "food": (120, 230, 255),
                "bonus": (255, 255, 140), "text": (255, 235, 220), "accent": (255, 150, 80),
                "muted": (190, 140, 150)},
}
THEME_NAMES = list(THEMES.keys())

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


# ----------------------------- Helpers -------------------------------------
def lerp_colour(c1, c2, t):
    """Blend two RGB colours; t=0 gives c1, t=1 gives c2."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def load_high_scores():
    """Read per-difficulty high scores from disk (default 0)."""
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
        pass  # not critical if saving fails


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
        envelope = 1.0 - t                       # fade out to avoid clicks
        buf.append(int(32767 * volume * envelope * math.sin(phase)))
    return pygame.mixer.Sound(buffer=buf.tobytes())


# ----------------------------- Game objects --------------------------------
class Snake:
    """The snake: a list of grid cells, head first."""

    def __init__(self):
        start_x, start_y = COLS // 2, ROWS // 2
        self.body = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.grow_pending = 0

    @property
    def head(self):
        return self.body[0]

    def set_direction(self, new_dir):
        """Change direction, but never allow a 180-degree reverse."""
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.next_direction = new_dir

    def move(self):
        """Advance one cell in the current direction."""
        self.direction = self.next_direction
        new_head = (self.head[0] + self.direction[0], self.head[1] + self.direction[1])
        self.body.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1          # keep tail -> snake grows
        else:
            self.body.pop()                 # remove tail -> same length

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
            colour = lerp_colour(theme["head"], theme["tail"], i / max(total - 1, 1))
            pygame.draw.rect(surface, colour, rect.inflate(-2, -2), border_radius=6)
        self._draw_eyes(surface)

    def _draw_eyes(self, surface):
        """Draw two eyes on the head, looking in the direction of travel."""
        hx, hy = self.head
        cx = hx * CELL + CELL // 2
        cy = hy * CELL + HUD_HEIGHT + CELL // 2
        dx, dy = self.direction
        px, py = -dy, dx                         # perpendicular direction
        for side in (1, -1):
            ex = cx + dx * 4 + px * 4 * side
            ey = cy + dy * 4 + py * 4 * side
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), 3)
            pygame.draw.circle(surface, (0, 0, 0), (ex + dx, ey + dy), 1)


class Food:
    """A food item placed on a random free cell."""

    def __init__(self, snake_body, bonus=False, other=None):
        self.bonus = bonus
        self.points = 5 if bonus else 1
        self.spawn_time = pygame.time.get_ticks()
        self.pos = self._random_free_cell(snake_body, other)

    @staticmethod
    def _random_free_cell(snake_body, other):
        blocked = set(snake_body)
        if other is not None:
            blocked.add(other.pos)
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in blocked]
        return random.choice(free)

    def expired(self):
        return self.bonus and pygame.time.get_ticks() - self.spawn_time > BONUS_DURATION_MS

    def draw(self, surface, theme):
        x, y = self.pos
        rect = pygame.Rect(x * CELL, y * CELL + HUD_HEIGHT, CELL, CELL)
        colour = theme["bonus"] if self.bonus else theme["food"]
        if self.bonus:
            # Pulsing size so the player notices the bonus food
            pulse = int(2 * math.sin(pygame.time.get_ticks() / 120))
            pygame.draw.ellipse(surface, colour, rect.inflate(-2 + pulse, -2 + pulse))
        else:
            pygame.draw.ellipse(surface, colour, rect.inflate(-4, -4))

class PoisonFood:
    """Poison item: purple, flickers, disappears after a few seconds.
    Eating it shrinks the snake and costs points."""
 
    def __init__(self, snake_body, avoid_positions):
        self.spawn_time = pygame.time.get_ticks()
        blocked = set(snake_body) | set(avoid_positions)
        # Also keep poison away from the cells right in front of the head,
        # so the player gets a fair chance to react.
        hx, hy = snake_body[0]
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in blocked and abs(x - hx) + abs(y - hy) > 3]
        self.pos = random.choice(free)
 
    def expired(self):
        return pygame.time.get_ticks() - self.spawn_time > POISON_DURATION_MS
 
    def draw(self, surface):
        age = pygame.time.get_ticks() - self.spawn_time
        # Flicker faster in the last 2 seconds as a warning that it will vanish
        if age > POISON_DURATION_MS - 2000 and (age // 150) % 2 == 0:
            return
        x, y = self.pos
        rect = pygame.Rect(x * CELL, y * CELL + HUD_HEIGHT, CELL, CELL)
        pygame.draw.ellipse(surface, POISON_COLOUR, rect.inflate(-4, -4))
        # A small "X" in the middle so it is easy to tell apart from normal food
        c = rect.center
        pygame.draw.line(surface, (255, 255, 255), (c[0] - 3, c[1] - 3), (c[0] + 3, c[1] + 3), 2)
        pygame.draw.line(surface, (255, 255, 255), (c[0] - 3, c[1] + 3), (c[0] + 3, c[1] - 3), 2)

class Popup:
    """A floating '+points' text that rises and fades out."""

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


# ----------------------------- Main game class -----------------------------
class Game:
    MENU_ITEMS = ["Play", "Difficulty", "Theme", "Sound", "Quit"]

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
        self.theme_index = 0
        self.sound_on = True

        self.high_scores = load_high_scores()
        self.state = "menu"           # "menu", "playing", "gameover"
        self.menu_index = 0
        self.reset()

    # ---- settings shortcuts ----
    @property
    def difficulty(self):
        return DIFFICULTY_NAMES[self.difficulty_index]

    @property
    def theme(self):
        return THEMES[THEME_NAMES[self.theme_index]]

    @property
    def high_score(self):
        return self.high_scores[self.difficulty]

    # ---- sound ----
    def _load_sounds(self):
        """Create all sound effects in code. Returns {} if audio is unavailable."""
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

    # ---- game setup ----
    def reset(self):
        """Start (or restart) a fresh game with the current settings."""
        self.snake = Snake()
        self.poison_foods = []
        self.flash_until = 0 
        self.food = Food(self.snake.body)
        self.bonus_food = None
        self.popups = []
        self.score = 0
        self.foods_eaten = 0
        self.level = 1
        self.paused = False
        self.new_best = False

    def start_game(self):
        self.reset()
        self.state = "playing"

    # ---- difficulty ----
    @property
    def fps(self):
        """Speed grows with level; how fast depends on the chosen difficulty."""
        cfg = DIFFICULTIES[self.difficulty]
        return min(cfg["base_fps"] + (self.level - 1) * cfg["step"], MAX_FPS)

    # ---- input ----
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
        """Change the highlighted menu setting (difficulty, theme or sound)."""
        item = self.MENU_ITEMS[self.menu_index]
        if item == "Difficulty":
            self.difficulty_index = (self.difficulty_index + step) % len(DIFFICULTY_NAMES)
        elif item == "Theme":
            self.theme_index = (self.theme_index + step) % len(THEME_NAMES)
        elif item == "Sound":
            self.sound_on = not self.sound_on
        else:
            return
        self.play("select")

    def handle_play_key(self, key):
        key_map = {
            pygame.K_UP: UP, pygame.K_w: UP,
            pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
            pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
            pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
        }
        if key == pygame.K_ESCAPE:
            self.state = "menu"
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key in key_map and not self.paused:
            self.snake.set_direction(key_map[key])

    def handle_gameover_key(self, key):
        if key == pygame.K_r:
            self.start_game()
        elif key in (pygame.K_m, pygame.K_ESCAPE):
            self.state = "menu"
        elif key == pygame.K_q:
            self.quit()

    # ---- game logic ----
    def update(self):
        if self.state != "playing" or self.paused:
            return

        self.snake.move()

        # Collisions
        if self.snake.hit_wall() or self.snake.hit_self():
            self.end_game()
            return

        # Eating normal food
        if self.snake.head == self.food.pos:
            self.eat(self.food)
            self.foods_eaten += 1
            self.level = 1 + self.foods_eaten // FOODS_PER_LEVEL
            self.food = self.spawn_food(other=self.bonus_food)
            if self.foods_eaten % BONUS_EVERY == 0 and self.bonus_food is None:
                self.bonus_food = self.spawn_food(bonus=True, other=self.food)
            if (self.foods_eaten % POISON_EVERY == 0
                    and len(self.poison_foods) < MAX_POISON_ON_SCREEN):
                self.spawn_poison()

        # Eating bonus food
        if self.bonus_food and self.snake.head == self.bonus_food.pos:
            self.eat(self.bonus_food)
            self.bonus_food = None

        #Eating poison
        for poison in list(self.poison_foods):
            if self.snake.head == poison.pos:
                self.poison_foods.remove(poison)
                self.eat_poison(poison)
                if self.state == "gameover":
                    return

        # Bonus food and poison timeouts
        if self.bonus_food and self.bonus_food.expired():
            self.bonus_food = None
        self.poison_foods = [p for p in self.poison_foods if not p.expired()]

        self.popups = [p for p in self.popups if p.alive()]

    #Poison Feature
    def poison_positions(self):
        return [p.pos for p in self.poison_foods]
 
    def spawn_food(self, bonus=False, other=None):
        """Create food that never lands on a poison item."""
        food = Food(self.snake.body, bonus=bonus, other=other)
        for _ in range(50):
            if food.pos not in self.poison_positions():
                break
            food = Food(self.snake.body, bonus=bonus, other=other)
        return food
 
    def spawn_poison(self):
        """Create a poison item away from the snake, food and other poison."""
        avoid = self.poison_positions() + [self.food.pos]
        if self.bonus_food:
            avoid.append(self.bonus_food.pos)
        self.poison_foods.append(PoisonFood(self.snake.body, avoid))
 
    def eat_poison(self, poison):
        """Penalty: lose points and tail segments. Too short -> game over."""
        x, y = poison.pos
        self.popups.append(Popup(f"-{POISON_PENALTY}", x * CELL + CELL // 2,
                                 y * CELL + HUD_HEIGHT, POISON_COLOUR))
        self.play("poison")
        self.flash_until = pygame.time.get_ticks() + 250
 
        if len(self.snake.body) - POISON_SHRINK < MIN_SNAKE_LENGTH:
            self.end_game()                  # the snake is too short to survive
            return
        self.score = max(0, self.score - POISON_PENALTY)
        for _ in range(POISON_SHRINK):
            self.snake.body.pop()            # remove tail segments
        self.snake.grow_pending = 0

    def eat(self, food):
        self.score += food.points
        self.snake.grow(1)
        x, y = food.pos
        px, py = x * CELL + CELL // 2, y * CELL + HUD_HEIGHT
        colour = self.theme["bonus"] if food.bonus else self.theme["text"]
        self.popups.append(Popup(f"+{food.points}", px, py, colour))
        self.play("bonus" if food.bonus else "eat")

    def end_game(self):
        self.state = "gameover"
        self.play("gameover")
        if self.score > self.high_scores[self.difficulty]:
            self.high_scores[self.difficulty] = self.score
            self.new_best = True
            save_high_scores(self.high_scores)

    # ---- drawing helpers ----
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

    # ---- drawing: game ----
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
        self.snake.draw(self.screen, t)
        for p in self.popups:
            p.draw(self.screen, self.small_font)
 
        # Brief purple flash when poison is eaten
        if pygame.time.get_ticks() < self.flash_until:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*POISON_COLOUR, 70))
            self.screen.blit(flash, (0, 0))


        # HUD
        pygame.draw.rect(self.screen, t["hud"], (0, 0, WIDTH, HUD_HEIGHT))
        self.draw_text(f"Score: {self.score}", self.font, t["text"], topleft=(10, 8))
        self.draw_text(f"{self.difficulty} - Lvl {self.level}", self.font, t["accent"],
                       center=(WIDTH // 2, HUD_HEIGHT // 2))
        self.draw_text(f"Best: {self.high_score}", self.font, t["muted"], topright=(WIDTH - 10, 8))

        if self.paused:
            self.draw_overlay("PAUSED", ["Press P to resume"])
        if self.state == "gameover":
            lines = [f"Score: {self.score}"]
            if self.new_best:
                lines.append("NEW HIGH SCORE!")
            lines.append("R restart  |  M menu  |  Q quit")
            self.draw_overlay("GAME OVER", lines)

    # ---- drawing: menu ----
    def draw_menu(self):
        t = self.theme
        self.screen.fill(t["bg"])

        # Animated decorative snake wiggling under the title
        ticks = pygame.time.get_ticks()
        for i in range(18):
            x = WIDTH // 2 - 180 + i * 20
            y = 175 + int(8 * math.sin(ticks / 250 + i * 0.5))
            colour = lerp_colour(t["head"], t["tail"], i / 17)
            pygame.draw.circle(self.screen, colour, (x, y), 8)

        self.draw_text("SNAKE", self.title_font, t["head"], center=(WIDTH // 2, 100))

        values = {
            "Difficulty": f"< {self.difficulty} >",
            "Theme": f"< {THEME_NAMES[self.theme_index]} >",
            "Sound": f"< {'On' if self.sound_on else 'Off'} >",
        }
        for i, item in enumerate(self.MENU_ITEMS):
            selected = i == self.menu_index
            colour = t["accent"] if selected else t["text"]
            label = f"> {item}" if selected else item
            y = 235 + i * 36
            self.draw_text(label, self.font, colour, topleft=(WIDTH // 2 - 130, y))
            if item in values:
                self.draw_text(values[item], self.font, colour, topright=(WIDTH // 2 + 150, y))

        self.draw_text(f"High score ({self.difficulty}): {self.high_score}",
                       self.small_font, t["muted"], center=(WIDTH // 2, HEIGHT - 50))
        self.draw_text("UP/DOWN select   LEFT/RIGHT change   ENTER confirm",
                       self.small_font, t["muted"], center=(WIDTH // 2, HEIGHT - 26))

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    # ---- main loop ----
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            # Menu runs at a steady 30 FPS; game speed depends on level
            self.clock.tick(30 if self.state == "menu" else self.fps)

    @staticmethod
    def quit():
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()