import pygame


# Normal keyboard controls
NORMAL_CONTROLS = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),

    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),

    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),

    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}


def reverse_direction(key, reversed_mode):
    """
    Convert a keyboard key into a snake direction.

    If reversed_mode is False:
        Controls work normally.

    If reversed_mode is True:
        Controls are reversed.

    Returns:
        A direction tuple such as (0, -1),
        or None if the key is not a movement key.
    """

    if key not in NORMAL_CONTROLS:
        return None

    direction = NORMAL_CONTROLS[key]

    if reversed_mode:
        direction = (-direction[0], -direction[1])

    return direction