import math
import os
import random
import sys

import pygame

pygame.init()

# 1. Окно
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Смайлик на pygame")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 44)

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "images")
SCALE = 0.75  # картинки в файлах 160x160, уменьшаем до 120x120


def load(name, factor=SCALE):
    """Картинка с прозрачным фоном (convert_alpha), плавно изменённая по размеру."""
    img = pygame.image.load(os.path.join(IMG, name)).convert_alpha()
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (int(w * factor), int(h * factor)))


# 2. Картинки Kenney (PNG без фона).
# Персонаж собирается из частей: тело + лицо + две руки + тень.
COLORS = ["blue", "green", "pink", "purple", "red", "yellow"]
SHAPES = ["circle", "rhombus", "square", "squircle"]
FACES = "abcdefghijkl"


def hand_name(color, kind):
    # у жёлтого цвета файл называется иначе: hand_yellow_open.png
    if color == "yellow":
        return f"hand_yellow_{kind}.png"
    return f"{color}_hand_{kind}.png"


bodies = {(c, s): load(f"{c}_body_{s}.png") for c in COLORS for s in SHAPES}
hands_open = {c: load(hand_name(c, "open")) for c in COLORS}
hands_closed = {c: load(hand_name(c, "closed")) for c in COLORS}
faces = [load(f"face_{f}.png") for f in FACES]
shadow = load("shadow.png")

# Снаряд - маленький круглый шарик цвета персонажа
BALL = 30
BALL_R = BALL // 2
balls = {c: pygame.transform.smoothscale(bodies[(c, "circle")], (BALL, BALL)) for c in COLORS}


# 3. Случайные объекты: маленькие смайлики-мишени, которые двигаются хаотично
ENEMY = 64
ENEMY_R = ENEMY // 2


def make_enemy_sprite():
    """Случайное маленькое тело + лицо, собранные в одну картинку."""
    body = pygame.transform.smoothscale(
        bodies[(random.choice(COLORS), random.choice(SHAPES))], (ENEMY, ENEMY)
    )
    face = random.choice(faces)
    face = pygame.transform.smoothscale(face, (face.get_width() // 2, face.get_height() // 2))
    sprite = pygame.Surface((ENEMY, ENEMY), pygame.SRCALPHA)
    sprite.blit(body, (0, 0))
    sprite.blit(face, face.get_rect(center=(ENEMY // 2, ENEMY // 2 + 3)))
    return sprite


def new_direction(enemy):
    angle = random.uniform(0, 2 * math.pi)
    sp = random.uniform(1.5, 3.5)
    enemy["vx"] = math.cos(angle) * sp
    enemy["vy"] = math.sin(angle) * sp
    enemy["timer"] = random.randint(40, 120)  # через сколько кадров снова сменить курс


def spawn_enemy(avoid=None):
    while True:
        ex = random.randint(ENEMY_R, WIDTH - ENEMY_R)
        ey = random.randint(ENEMY_R, HEIGHT - ENEMY_R)
        # не появляемся прямо на игроке
        if avoid is None or math.hypot(ex - avoid[0], ey - avoid[1]) > 200:
            break
    enemy = {
        "x": ex, "y": ey, "vx": 0, "vy": 0, "timer": 0,
        "base": make_enemy_sprite(),
        "rot": random.uniform(0, 360),
        "spin": random.choice([-1, 1]) * random.uniform(1, 4),  # вращение
    }
    new_direction(enemy)
    return enemy


# 4. Состояние игры
x, y = WIDTH / 2, HEIGHT / 2
speed = 5
color_i, shape_i, face_i = 0, 0, 0
look = 0.0            # куда смотрит лицо: -1 влево ... +1 вправо
shoot_dir = 1         # куда стрелять: 1 вправо, -1 влево
t = 0.0
score = 0
shoot_cooldown = 0
bullets = []
enemies = [spawn_enemy((x, y)) for _ in range(6)]

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_c:       # C - цвет
                color_i = (color_i + 1) % len(COLORS)
            if event.key == pygame.K_z:       # Z - форма тела
                shape_i = (shape_i + 1) % len(SHAPES)
            if event.key == pygame.K_f:       # F - лицо
                face_i = (face_i + 1) % len(faces)

    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])

    moving = bool(dx or dy)
    if moving:
        length = math.hypot(dx, dy)
        x += dx / length * speed
        y += dy / length * speed
        t += 0.3
        if dx:
            shoot_dir = 1 if dx > 0 else -1
    else:
        t += 0.08
    look += (dx - look) * 0.2  # плавный поворот лица

    color, shape = COLORS[color_i], SHAPES[shape_i]
    body = bodies[(color, shape)]
    face = faces[face_i]
    hand = hands_closed[color] if moving else hands_open[color]
    hand_l = pygame.transform.flip(hand, True, False)  # левая рука - зеркало правой

    # анимация: подпрыгивание и качание рук
    bob = abs(math.sin(t)) * (-10 if moving else -3)
    sway = math.sin(t) * (10 if moving else 3)

    bw, bh = body.get_size()
    cx, cy = int(x), int(y + bob)

    # --- ОГРАНИЧЕНИЕ ПО РАМКЕ ЭКРАНА ---
    # персонаж вместе с руками не выходит за окно
    margin_x = bw // 2 + hand.get_width() + 6
    cx = max(margin_x, min(WIDTH - margin_x, cx))
    cy = max(bh // 2, min(HEIGHT - bh // 2 - 10, cy))
    x = cx
    y = cy - bob

    # --- СТРЕЛЬБА ПО ПРОБЕЛУ ---
    if shoot_cooldown > 0:
        shoot_cooldown -= 1
    if keys[pygame.K_SPACE] and shoot_cooldown == 0:
        start_x = cx + shoot_dir * (bw // 2 + hand.get_width())
        bullets.append({"x": start_x, "y": cy + 8, "vx": 12 * shoot_dir, "color": color})
        shoot_cooldown = 15  # не чаще 4 выстрелов в секунду

    for b in bullets:
        b["x"] += b["vx"]
    bullets = [b for b in bullets if -40 < b["x"] < WIDTH + 40]

    # --- ХАОТИЧНОЕ ДВИЖЕНИЕ МИШЕНЕЙ ---
    for e in enemies:
        e["timer"] -= 1
        if e["timer"] <= 0:
            new_direction(e)           # время от времени резко меняем курс
        e["vy"] += random.uniform(-0.3, 0.3)       # и постоянно чуть "виляем"
        e["vy"] = max(-3.5, min(3.5, e["vy"]))
        e["x"] += e["vx"]
        e["y"] += e["vy"]
        e["rot"] += e["spin"]
        # отскок от краёв окна
        if e["x"] < ENEMY_R:
            e["x"] = ENEMY_R
            e["vx"] = abs(e["vx"])
        if e["x"] > WIDTH - ENEMY_R:
            e["x"] = WIDTH - ENEMY_R
            e["vx"] = -abs(e["vx"])
        if e["y"] < ENEMY_R:
            e["y"] = ENEMY_R
            e["vy"] = abs(e["vy"])
        if e["y"] > HEIGHT - ENEMY_R:
            e["y"] = HEIGHT - ENEMY_R
            e["vy"] = -abs(e["vy"])

    # --- ПОПАДАНИЯ ---
    alive_bullets = []
    for b in bullets:
        hit = False
        for k, e in enumerate(enemies):
            if math.hypot(b["x"] - e["x"], b["y"] - e["y"]) < ENEMY_R + BALL_R:
                score += 1
                enemies[k] = spawn_enemy((x, y))  # подбитый смайлик появляется заново
                hit = True
                break
        if not hit:
            alive_bullets.append(b)
    bullets = alive_bullets

    # --- РИСУЕМ ---
    screen.fill((228, 233, 240))

    for e in enemies:
        spr = pygame.transform.rotate(e["base"], e["rot"])
        screen.blit(spr, spr.get_rect(center=(e["x"], e["y"])))
    for b in bullets:
        ball = balls[b["color"]]
        screen.blit(ball, ball.get_rect(center=(b["x"], b["y"])))

    # тень остаётся на земле, пока персонаж подпрыгивает
    ground_y = int(y) + bh // 2 - 4
    screen.blit(shadow, shadow.get_rect(center=(cx, ground_y)))
    screen.blit(body, body.get_rect(center=(cx, cy)))
    face_pos = (cx + look * 6, cy + 3)
    screen.blit(face, face.get_rect(center=face_pos))
    # руки по бокам тела, качаются в противоположные стороны
    hy = cy + 8
    screen.blit(hand, hand.get_rect(midright=(cx - bw // 2 + 4, hy + sway)).move(-4, 0))
    screen.blit(hand_l, hand_l.get_rect(midleft=(cx + bw // 2 - 4, hy - sway)).move(4, 0))

    hint = font.render(
        "Стрелки/WASD - идти, Пробел - стрелять, C - цвет, Z - форма, F - лицо, Esc - выход",
        True, (60, 70, 90),
    )
    screen.blit(hint, (10, 10))
    score_text = big_font.render(f"Счёт: {score}", True, (60, 70, 90))
    screen.blit(score_text, (WIDTH - score_text.get_width() - 15, 40))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
