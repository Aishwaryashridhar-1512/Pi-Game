import random
import pygame

from mole_ai import find_path


CELL = 20
COLS = 30
ROWS = 22
HUD_HEIGHT = 40

WIDTH = COLS * CELL
HEIGHT = ROWS * CELL + HUD_HEIGHT


UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


class MoleSnake:

    def __init__(self):

        start_x = COLS // 2
        start_y = ROWS // 2

        self.body = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y),
        ]

        self.direction = RIGHT
        self.next_direction = RIGHT
        self.grow_pending = 0
        self.score = 0

    @property
    def head(self):
        return self.body[0]

    def set_direction(self, new_direction):

        opposite = (
            -self.direction[0],
            -self.direction[1]
        )

        if new_direction != opposite:
            self.next_direction = new_direction

    def move(self):
        self.direction = self.next_direction
        x, y = self.head
        dx, dy = self.direction
        new_head = (
            x + dx,
            y + dy
            )
        self.body.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
    def grow(self):
        self.grow_pending += 1
        self.score += 10

    def hit_wall(self):

        x, y = self.head

        return (
            x < 0
            or x >= COLS
            or y < 0
            or y >= ROWS
        )

    def hit_self(self):

        return self.head in self.body[1:]

    def draw(self, surface):

        for i, (x, y) in enumerate(self.body):

            rect = pygame.Rect(
                x * CELL,
                y * CELL + HUD_HEIGHT,
                CELL,
                CELL
            )

            if i == 0:
                color = (90, 230, 120)
            else:
                color = (40, 150, 70)

            pygame.draw.rect(
                surface,
                color,
                rect.inflate(-2, -2),
                border_radius=5
            )

class Food:

    def __init__(self, blocked):
        self.pos = None
        self.spawn(blocked)

    def spawn(self, blocked):

        free_cells = [
            (x, y)
            for x in range(COLS)
            for y in range(ROWS)
            if (x, y) not in blocked
        ]

        if free_cells:
            self.pos = random.choice(free_cells)

    def eaten(self, snake):
        return self.pos == snake.head

    def draw(self, surface):

        x, y = self.pos

        cx = x * CELL + CELL // 2
        cy = y * CELL + HUD_HEIGHT + CELL // 2

        pygame.draw.circle(
            surface,
            (220, 70, 70),
            (cx, cy),
            7
        )

class Mole:

    def __init__(self, snake_body):

        self.pos = self.random_position(snake_body)

        self.path = []

        self.move_counter = 0

        # Smaller number = faster mole
        self.move_delay = 3

        # Mole starts underground
        self.active = False

        self.spawn_time = pygame.time.get_ticks()

        self.emerge_delay = 3000

    def random_position(self, snake_body):

        blocked = set(snake_body)

        free_cells = [
            (x, y)
            for x in range(COLS)
            for y in range(ROWS)
            if (x, y) not in blocked
        ]

        return random.choice(free_cells)

    def update(self, snake_body):

        # Still underground
        if not self.active:

            elapsed = (
                pygame.time.get_ticks()
                - self.spawn_time
            )

            if elapsed >= self.emerge_delay:
                self.active = True
            else:
                return

        self.move_counter += 1

        if self.move_counter < self.move_delay:
            return

        self.move_counter = 0

        self.find_path(snake_body)

        if self.path:
            self.pos = self.path[0]

    def find_path(self, snake_body):

        start = self.pos
        goal = snake_body[0]

        # Don't let the mole travel through the snake's body
        blocked = set(snake_body[1:])

        self.path = find_path(
            start,
            goal,
            blocked
        )

    def caught_snake(self, snake):

        return self.pos == snake.head

    def draw(self, surface):

        if not self.active:
            self.draw_hole(surface)
            return

        x, y = self.pos

        cx = (
            x * CELL
            + CELL // 2
        )

        cy = (
            y * CELL
            + HUD_HEIGHT
            + CELL // 2
        )

        # Body
        pygame.draw.circle(
            surface,
            (110, 70, 45),
            (cx, cy + 3),
            8
        )

        # Head
        pygame.draw.circle(
            surface,
            (160, 100, 60),
            (cx, cy - 3),
            7
        )

        # Eyes
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (cx - 3, cy - 5),
            2
        )

        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (cx + 3, cy - 5),
            2
        )

        # Pupils
        pygame.draw.circle(
            surface,
            (30, 15, 10),
            (cx, cy),
            2
        )

    def draw_hole(self, surface):

        x, y = self.pos

        rect = pygame.Rect(
            x * CELL + 3,
            y * CELL + HUD_HEIGHT + 5,
            CELL - 6,
            CELL - 10
        )

        pygame.draw.ellipse(
            surface,
            (45, 30, 20),
            rect
        )


class MoleGame:

    def __init__(self):

        pygame.init()

        pygame.display.set_caption(
            "Snake - Hunter Prey"
        )

        self.screen = pygame.display.set_mode(
            (WIDTH, HEIGHT)
        )

        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont(
            "consolas",
            20
        )

        self.big_font = pygame.font.SysFont(
            "consolas",
            50,
            bold=True
        )

        self.snake = MoleSnake()

        self.mole = Mole(
            self.snake.body
        )
        self.food = Food(
             self.snake.body
        )
        self.score = 0

        self.running = True
        self.game_over = False
        self.death_reason = ""
        self.paused = False

    def handle_events(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                self.running = False
                return

            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_ESCAPE:

                self.running = False
                return

            if self.game_over:

                if event.key == pygame.K_r:
                    self.__init__()

                elif event.key == pygame.K_m:
                    self.running = False

                continue

            if event.key == pygame.K_p:

                self.paused = not self.paused
                continue

            # Snake movement
            if event.key in (
                pygame.K_UP,
                pygame.K_w
            ):
                self.snake.set_direction(UP)

            elif event.key in (
                pygame.K_DOWN,
                pygame.K_s
            ):
                self.snake.set_direction(DOWN)

            elif event.key in (
                pygame.K_LEFT,
                pygame.K_a
            ):
                self.snake.set_direction(LEFT)

            elif event.key in (
                pygame.K_RIGHT,
                pygame.K_d
            ):
                self.snake.set_direction(RIGHT)

    def update(self):
        if self.game_over:
            return
        if self.paused:
            return
        self.snake.move()
        # Wall/self collision
        if (
            self.snake.hit_wall()
            or self.snake.hit_self()
            ):
            self.game_over = True
            self.death_reason = "WALL"
            return

    # Eat food
        if self.food.eaten(self.snake):

            self.snake.grow()
 
            self.food.spawn(
                set(self.snake.body) | {self.mole.pos}
                )

    # Mole hunting
        self.mole.update(
            self.snake.body
            )

    # Mole catches snake
        if self.mole.active:
            if self.mole.caught_snake(
                self.snake
                ):
                self.game_over = True
                self.death_reason = "MOLE"

    def draw_text(
        self,
        text,
        font,
        position
    ):

        image = font.render(
            text,
            True,
            (240, 240, 240)
        )

        rect = image.get_rect(
            center=position
        )

        self.screen.blit(
            image,
            rect
        )

    def draw(self):

        self.screen.fill(
            (15, 15, 20)
        )

        # Grid
        for x in range(
            0,
            WIDTH,
            CELL
        ):

            pygame.draw.line(
                self.screen,
                (28, 28, 36),
                (x, HUD_HEIGHT),
                (x, HEIGHT)
            )

        for y in range(
            HUD_HEIGHT,
            HEIGHT,
            CELL
        ):

            pygame.draw.line(
                self.screen,
                (28, 28, 36),
                (0, y),
                (WIDTH, y)
            )
        self.food.draw(
            self.screen
        )

        self.mole.draw(
            self.screen
        )

        self.snake.draw(
            self.screen
        )

        # HUD
        pygame.draw.rect(
            self.screen,
            (25, 25, 35),
            (0, 0, WIDTH, HUD_HEIGHT)
        )

        self.draw_text(
            f"MOLE HUNT   SCORE: {self.snake.score}",
            self.font,
            (WIDTH // 2, HUD_HEIGHT // 2)
        )

        if not self.mole.active:

            self.draw_text(
                "Something is digging...",
                self.font,
                (
                    WIDTH // 2,
                    HEIGHT // 2
                )
            )

        if self.paused:

            self.draw_overlay(
                "PAUSED",
                "Press P to resume"
            )

        if self.game_over:
            if self.death_reason == "MOLE":
                title = "CAUGHT!"
            else:
                title = "GAME OVER"
            self.draw_overlay(
                title,
                "R = restart   M = menu   ESC = exit"
            )

        pygame.display.flip()

    def draw_overlay(
        self,
        title,
        message
    ):

        overlay = pygame.Surface(
            (WIDTH, HEIGHT),
            pygame.SRCALPHA
        )

        overlay.fill(
            (0, 0, 0, 180)
        )

        self.screen.blit(
            overlay,
            (0, 0)
        )

        self.draw_text(
            title,
            self.big_font,
            (
                WIDTH // 2,
                HEIGHT // 2 - 40
            )
        )

        self.draw_text(
            message,
            self.font,
            (
                WIDTH // 2,
                HEIGHT // 2 + 30
            )
        )

    def run(self):

        while self.running:

            self.handle_events()

            self.update()

            self.draw()

            self.clock.tick(10)

        pygame.quit()


if __name__ == "__main__":
    MoleGame().run()