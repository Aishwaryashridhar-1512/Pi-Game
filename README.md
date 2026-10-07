# Pi-Game
# Snake Game

A classic Snake game built with Python and Pygame, extended with multiplayer support, multiple game modes, special food, difficulty levels, themes, sound effects, and high-score tracking.

## Project Overview

This project is a feature-rich implementation of the classic Snake game developed using Python and Pygame. The game supports both single-player and two-player gameplay, with multiple modes that introduce different challenges and mechanics.

Players can choose different difficulty levels, collect normal, bonus, and poison food, compete for high scores, and customize the gameplay through different themes and sound effects. The multiplayer mode allows two players to play on the same keyboard while managing their own snakes and scores.

The project is organized into separate folders for game modes and sounds, with high scores stored using JSON. This structure keeps the game components organized and makes it easier to extend the project with new features and modes.

## Features

- Single-player and two-player modes
- Classic and Reverse game modes
- Reverse controls that change after eating food
- Poison food that shrinks the snake and reduces the score
- Bonus food for extra points
- Multiple difficulty levels
- Multiple colour themes
- Sound effects
- Individual player scores
- Multiplayer snake collision detection
- High-score tracking
- Game-over and restart functionality

## Game Modes

### Classic Mode

The traditional Snake experience where the snake grows by eating food and the difficulty increases as the game progresses.

### Reverse Mode

The controls change direction after food is eaten, making the game more challenging and requiring players to adapt quickly.

### Multiplayer Mode

Two players can play on the same keyboard, with each player controlling their own snake and score.

## Food Types

- **Normal Food** – Increases the snake's length and score.
- **Bonus Food** – Gives additional points.
- **Poison Food** – Shrinks the snake and decreases the score.

## Controls

### Player 1

| Action | Key |
|---|---|
| Move Up | W |
| Move Down | S |
| Move Left | A |
| Move Right | D |

### Player 2

| Action | Key |
|---|---|
| Move Up | Arrow Up |
| Move Down | Arrow Down |
| Move Left | Arrow Left |
| Move Right | Arrow Right |

## Difficulty

Different difficulty levels change the speed of the game and increase the challenge.

## Technologies Used

- Python
- Pygame

## How to Run

Install Pygame:

```bash
pip install pygame
```

Run the game:

```bash
python snake.py
```

## Project Structure

```text
Snake-Game/
├── modes/
├── sounds/
├── .gitignore
├── README.md
├── highscores.json
├── snake.py
└── snake_backup.py
```

### File and Folder Description

- `snake.py` – Main game file containing the Snake game logic.
- `snake_backup.py` – Backup copy of the game code.
- `modes/` – Contains files related to the different game modes.
- `sounds/` – Contains sound files used in the game.
- `highscores.json` – Stores high scores.
- `.gitignore` – Specifies files that should not be tracked by Git.
- `README.md` – Project documentation.

## Gameplay

Control the snake, collect food, increase your score, and survive as long as possible.

Avoid hitting the walls and your own snake. In multiplayer mode, players must also avoid colliding with each other.

Special food items add additional challenges and scoring opportunities.

## Future Improvements

- Online multiplayer
- More game modes
- Additional power-ups
- Leaderboard system
- More maps and obstacles
- Improved animations

## License

This project was created for educational purposes.
