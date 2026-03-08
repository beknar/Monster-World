import pygame


def check_rect_collision(rect1: pygame.Rect, rect2: pygame.Rect) -> bool:
    """Check if two rectangles overlap."""
    return rect1.colliderect(rect2)


def check_group_collision(entity_rect: pygame.Rect, rects: list) -> list:
    """Check entity_rect against a list of pygame.Rects. Returns list of colliding rects."""
    return [r for r in rects if entity_rect.colliderect(r)]


def resolve_movement(old_rect: pygame.Rect, new_rect: pygame.Rect,
                     obstacles: list) -> pygame.Rect:
    """Try to move from old_rect to new_rect. If new_rect collides with any obstacle,
    try moving only on X axis, then only on Y axis, to allow sliding along walls.
    obstacles: list of pygame.Rects.
    Returns the final valid position as a new Rect."""

    # Try full movement first
    if not any(new_rect.colliderect(o) for o in obstacles):
        return new_rect

    # Try X only
    x_rect = pygame.Rect(new_rect.x, old_rect.y, new_rect.width, new_rect.height)
    if not any(x_rect.colliderect(o) for o in obstacles):
        # X works, now try Y from x_rect
        xy_rect = pygame.Rect(x_rect.x, new_rect.y, new_rect.width, new_rect.height)
        if not any(xy_rect.colliderect(o) for o in obstacles):
            return xy_rect
        return x_rect

    # Try Y only
    y_rect = pygame.Rect(old_rect.x, new_rect.y, new_rect.width, new_rect.height)
    if not any(y_rect.colliderect(o) for o in obstacles):
        return y_rect

    # Can't move at all
    return old_rect


def check_entity_collision(entity_rect: pygame.Rect, entities: list,
                           exclude=None) -> list:
    """Check entity_rect against a list of entity objects that have a .collision_rect attribute.
    Returns list of colliding entities. Optionally exclude one entity (e.g., self)."""
    result = []
    for e in entities:
        if e is exclude:
            continue
        other_rect = getattr(e, 'collision_rect', getattr(e, 'rect', None))
        if other_rect and entity_rect.colliderect(other_rect):
            result.append(e)
    return result


def get_obstacle_rects_near(obstacles: list, center: pygame.Rect, margin: int = 200) -> list:
    """Filter obstacles to only those near the center rect for performance.
    obstacles: list of pygame.Rects or objects with .rect attribute."""
    expanded = center.inflate(margin * 2, margin * 2)
    result = []
    for o in obstacles:
        r = o if isinstance(o, pygame.Rect) else getattr(o, 'rect', None)
        if r and expanded.colliderect(r):
            result.append(r)
    return result
