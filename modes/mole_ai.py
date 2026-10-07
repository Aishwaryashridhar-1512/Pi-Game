import heapq

COLS = 30
ROWS = 22


def get_neighbors(position):
    x, y = position

    neighbors = [
        (x + 1, y),
        (x - 1, y),
        (x, y + 1),
        (x, y - 1),
    ]

    return [
        cell
        for cell in neighbors
        if 0 <= cell[0] < COLS
        and 0 <= cell[1] < ROWS
    ]


def heuristic(a, b):
    """Estimate distance between two grid cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(start, goal, blocked):
    """Find the shortest available path."""

    open_set = []
    heapq.heappush(open_set, (0, start))

    parent = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(parent, start, goal)

        for neighbor in get_neighbors(current):

            if neighbor in blocked:
                continue

            new_cost = g_score[current] + 1

            if (
                neighbor not in g_score
                or new_cost < g_score[neighbor]
            ):
                g_score[neighbor] = new_cost
                parent[neighbor] = current

                priority = (
                    new_cost
                    + heuristic(neighbor, goal)
                )

                heapq.heappush(
                    open_set,
                    (priority, neighbor)
                )

    return []


def reconstruct_path(parent, start, goal):
    path = []
    current = goal

    while current != start:
        path.append(current)
        current = parent[current]

    path.reverse()
    return path