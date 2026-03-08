"""Lightweight A* pathfinding for Monster World monsters."""
import heapq
from collections import deque
from typing import List, Tuple, Optional


def build_walkable_grid(obstacles: list, grid_cols: int, grid_rows: int,
                        tile_size: int) -> List[List[bool]]:
    """Build a 2D boolean grid: True = walkable, False = blocked by an obstacle.

    Args:
        obstacles:  List of pygame.Rect obstacle collision rects (world pixels).
        grid_cols:  Number of tile columns in the stage.
        grid_rows:  Number of tile rows in the stage.
        tile_size:  Pixel size of each tile.

    Returns:
        grid[row][col] — True if the tile is passable.
    """
    grid = [[True] * grid_cols for _ in range(grid_rows)]

    for obs in obstacles:
        tx_min = max(0, obs.left // tile_size)
        ty_min = max(0, obs.top // tile_size)
        tx_max = min(grid_cols - 1, (obs.right - 1) // tile_size)
        ty_max = min(grid_rows - 1, (obs.bottom - 1) // tile_size)
        for ty in range(ty_min, ty_max + 1):
            for tx in range(tx_min, tx_max + 1):
                grid[ty][tx] = False

    return grid


def astar(grid: List[List[bool]],
          start: Tuple[int, int],
          goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """A* pathfinding on a 2-D boolean tile grid (4-directional movement).

    Args:
        grid:   grid[row][col], True = walkable.
        start:  (col, row) of the starting tile.
        goal:   (col, row) of the destination tile.

    Returns:
        List of (col, row) tiles from start to goal inclusive, or None if
        no path exists.
    """
    if not grid:
        return None

    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    # Clamp coordinates to grid bounds
    sx = max(0, min(cols - 1, start[0]))
    sy = max(0, min(rows - 1, start[1]))
    gx = max(0, min(cols - 1, goal[0]))
    gy = max(0, min(rows - 1, goal[1]))

    # Snap blocked start/goal to nearest walkable tile
    if not grid[sy][sx]:
        sx, sy = _nearest_walkable(grid, sx, sy, cols, rows)
    if not grid[gy][gx]:
        gx, gy = _nearest_walkable(grid, gx, gy, cols, rows)

    if (sx, sy) == (gx, gy):
        return [(sx, sy)]

    def h(x: int, y: int) -> int:
        return abs(x - gx) + abs(y - gy)

    # Priority queue entries: (f, g, col, row)
    open_heap: list = []
    heapq.heappush(open_heap, (h(sx, sy), 0, sx, sy))
    came_from: dict = {}
    g_score: dict = {(sx, sy): 0}

    _dirs = ((0, -1), (0, 1), (-1, 0), (1, 0))

    while open_heap:
        _, g, cx, cy = heapq.heappop(open_heap)

        if (cx, cy) == (gx, gy):
            # Reconstruct path
            path: List[Tuple[int, int]] = []
            pos = (cx, cy)
            while pos in came_from:
                path.append(pos)
                pos = came_from[pos]
            path.append((sx, sy))
            path.reverse()
            return path

        if g > g_score.get((cx, cy), float('inf')):
            continue  # Stale heap entry

        for dx, dy in _dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx]:
                ng = g + 1
                if ng < g_score.get((nx, ny), float('inf')):
                    g_score[(nx, ny)] = ng
                    came_from[(nx, ny)] = (cx, cy)
                    heapq.heappush(open_heap, (ng + h(nx, ny), ng, nx, ny))

    return None  # No path found


def _nearest_walkable(grid: List[List[bool]], x: int, y: int,
                      cols: int, rows: int) -> Tuple[int, int]:
    """BFS outward from (x, y) to find the nearest walkable tile."""
    visited = {(x, y)}
    q = deque([(x, y)])
    while q:
        cx, cy = q.popleft()
        if grid[cy][cx]:
            return cx, cy
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append((nx, ny))
    return x, y  # fallback — return original if nothing found
