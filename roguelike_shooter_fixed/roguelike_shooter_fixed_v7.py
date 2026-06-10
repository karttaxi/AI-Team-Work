# roguelike_shooter_fixed_v7.py
# Python pygame 기반 로그라이크 자동 슈팅 게임 수정판 v7
# 설치: pip install pygame-ce
# 실행: python roguelike_shooter_fixed_v7.py

import pygame
import random
import math
import sys
from copy import deepcopy

# -----------------------------
# 초기 설정
# -----------------------------
pygame.init()

WIDTH, HEIGHT = 960, 640
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Roguelike Auto Shooter")
clock = pygame.time.Clock()

# 색상
WHITE = (245, 245, 245)
BLACK = (18, 18, 22)
GRAY = (70, 70, 78)
DARK_GRAY = (38, 38, 45)
GREEN = (80, 220, 120)
RED = (240, 70, 70)
YELLOW = (255, 220, 80)
BLUE = (80, 160, 255)
PURPLE = (180, 80, 255)
CYAN = (80, 230, 255)
ORANGE = (255, 150, 70)
PINK = (255, 120, 180)

# -----------------------------
# 배경 캐싱
# 격자 배경은 매 프레임 새로 그리지 않고, 한 번 만든 Surface를 재사용한다.
# -----------------------------
def create_background_surface():
    bg = pygame.Surface((WIDTH, HEIGHT))
    bg.fill(BLACK)

    for x in range(0, WIDTH, 48):
        pygame.draw.line(bg, (28, 28, 34), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 48):
        pygame.draw.line(bg, (28, 28, 34), (0, y), (WIDTH, y))

    return bg


BG_SURFACE = create_background_surface()

# -----------------------------
# 한글 폰트 설정
# -----------------------------
def get_font(size):
    """한글 폰트를 최대한 안전하게 찾는다.

    pygame.font.SysFont()는 원하는 폰트를 못 찾아도 기본 폰트를 반환할 수 있어서
    match_font()로 실제 폰트 파일을 찾은 뒤 Font로 여는 방식을 사용한다.
    """
    candidates = ["malgungothic", "gulim", "arialunicode", "consolas"]

    for name in candidates:
        font_path = pygame.font.match_font(name)
        if font_path:
            try:
                return pygame.font.Font(font_path, size)
            except pygame.error:
                pass

    # 마지막 보험: 한글이 깨질 수 있지만 게임 자체는 실행되게 한다.
    return pygame.font.Font(None, size)


FONT = get_font(22)
SMALL_FONT = get_font(18)
BIG_FONT = get_font(46)
TITLE_FONT = get_font(58)

# -----------------------------
# 무기 데이터
# ranged 무기는 탄창/재장전이 있음
# melee 무기는 탄창 제한 없이 자동 근접 공격
# -----------------------------
WEAPON_DATA = {
    "gun": {
        "name": "권총",
        "kind": "ranged",
        "damage": 22,
        "cooldown": 330,
        "bullet_speed": 11,
        "bullet_radius": 5,
        "max_ammo": 12,
        "reload_time": 1100,
        "color": YELLOW,
        "pierce": 1,
        "desc": "안정적인 기본 원거리 무기"
    },
    "laser": {
        "name": "레이저",
        "kind": "ranged",
        "damage": 11,
        "cooldown": 95,
        "bullet_speed": 16,
        "bullet_radius": 4,
        "max_ammo": 45,
        "reload_time": 1800,
        "color": CYAN,
        "pierce": 1,
        "desc": "빠르게 연사하지만 한 발 피해는 낮음"
    },
    "shuriken": {
        "name": "수리검",
        "kind": "ranged",
        "damage": 16,
        "cooldown": 160,
        "bullet_speed": 9,
        "bullet_radius": 7,
        "max_ammo": 18,
        "reload_time": 1500,
        "color": PURPLE,
        "pierce": 2,
        "desc": "적을 2번 관통할 수 있음"
    },
    "rifle": {
        "name": "소총",
        "kind": "ranged",
        "damage": 18,
        "cooldown": 140,
        "bullet_speed": 13,
        "bullet_radius": 4,
        "max_ammo": 30,
        "reload_time": 1500,
        "color": ORANGE,
        "pierce": 1,
        "desc": "탄창이 넉넉한 연사 무기"
    },
    "shotgun": {
        "name": "샷건",
        "kind": "ranged",
        "damage": 13,
        "cooldown": 720,
        "bullet_speed": 10,
        "bullet_radius": 4,
        "max_ammo": 6,
        "reload_time": 950,
        "color": ORANGE,
        "pierce": 1,
        "pellet_count": 5,
        "spread": 34,
        "desc": "여러 발이 퍼지는 근거리 산탄 무기"
    },
    "sword": {
        "name": "칼",
        "kind": "melee",
        "damage": 24,
        "cooldown": 420,
        "range": 72,
        "color": WHITE,
        "desc": "가까운 적을 자동으로 베는 근접 무기"
    },
    "axe": {
        "name": "도끼",
        "kind": "melee",
        "damage": 42,
        "cooldown": 760,
        "range": 88,
        "color": ORANGE,
        "desc": "느리지만 강력한 광역 근접 무기"
    },
    "bat": {
        "name": "빠따",
        "kind": "melee",
        "damage": 18,
        "cooldown": 300,
        "range": 62,
        "color": GREEN,
        "desc": "빠르게 주변 적을 밀어내듯 공격"
    },
}

# -----------------------------
# 업그레이드 후보
# -----------------------------
UPGRADE_POOL = [
    {"id": "weapon_laser", "title": "레이저 획득/강화", "desc": "자동 레이저 무기 추가 또는 강화"},
    {"id": "weapon_shuriken", "title": "수리검 획득/강화", "desc": "관통 수리검 무기 추가 또는 강화"},
    {"id": "weapon_rifle", "title": "소총 획득/강화", "desc": "빠른 연사의 원거리 무기 추가 또는 강화"},
    {"id": "weapon_shotgun", "title": "샷건 획득/강화", "desc": "여러 탄환이 퍼지는 산탄 무기 추가 또는 강화"},
    {"id": "weapon_sword", "title": "칼 획득/강화", "desc": "재장전 없는 근접 무기 추가 또는 강화"},
    {"id": "weapon_axe", "title": "도끼 획득/강화", "desc": "넓고 강한 근접 공격 추가 또는 강화"},
    {"id": "weapon_bat", "title": "빠따 획득/강화", "desc": "짧은 쿨타임의 근접 무기 추가 또는 강화"},
    {"id": "damage_all", "title": "무기 숙련", "desc": "모든 무기 공격력 증가"},
    {"id": "cooldown_all", "title": "전투 감각", "desc": "모든 무기 공격 속도 증가"},
    {"id": "ammo_all", "title": "확장 탄창", "desc": "원거리 무기 최대 탄약 증가"},
    {"id": "reload_all", "title": "빠른 장전", "desc": "원거리 무기 재장전 시간 감소"},
    {"id": "projectile_speed", "title": "고속 탄환", "desc": "원거리 탄환 속도 증가"},
    {"id": "max_hp", "title": "체력 단련", "desc": "최대 체력 증가 및 일부 회복"},
    {"id": "move_speed", "title": "가벼운 발걸음", "desc": "이동 속도 증가"},
    {"id": "magnet", "title": "자석 부적", "desc": "경험치 구슬 흡수 범위 증가"},
    {"id": "freeze_skill", "title": "냉기 장치", "desc": "주기적으로 적을 잠깐 느리게 만듦"},
    {"id": "lifesteal", "title": "흡혈 부적", "desc": "적 처치 시 체력을 조금 회복"},
    {"id": "shield", "title": "자동 방어막", "desc": "일정 주기마다 피해 1회를 무효화"},
    {"id": "heal", "title": "응급 치료", "desc": "즉시 체력 회복"},
]

# -----------------------------
# 유틸 함수
# -----------------------------
def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def draw_text(surface, text, font, color, x, y, center=False):
    image = font.render(text, True, color)
    rect = image.get_rect()

    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    surface.blit(image, rect)
    return rect


def get_nearest_enemy(x, y, enemies):
    if not enemies:
        return None
    return min(enemies, key=lambda e: distance(x, y, e.x, e.y))


# -----------------------------
# 클래스 정의
# -----------------------------
class Weapon:
    def __init__(self, weapon_id):
        data = deepcopy(WEAPON_DATA[weapon_id])
        self.id = weapon_id
        self.name = data["name"]
        self.kind = data["kind"]
        self.level = 1
        self.max_level = 6
        self.damage = data["damage"]
        self.cooldown = data["cooldown"]
        self.color = data["color"]
        self.last_used = 0

        if self.kind == "ranged":
            self.bullet_speed = data["bullet_speed"]
            self.bullet_radius = data["bullet_radius"]
            self.max_ammo = data["max_ammo"]
            self.ammo = self.max_ammo
            self.reload_time = data["reload_time"]
            self.reload_end_time = 0
            self.pierce = data["pierce"]
            self.pellet_count = data.get("pellet_count", 1)
            self.spread = data.get("spread", 0)
        else:
            self.range = data["range"]

    def upgrade(self):
        if self.level >= self.max_level:
            return False

        self.level += 1
        self.damage = int(self.damage * 1.18) + 2
        self.cooldown = max(60, int(self.cooldown * 0.92))

        if self.kind == "ranged":
            self.max_ammo += 3
            self.ammo = self.max_ammo
            self.reload_time = max(450, int(self.reload_time * 0.92))
            if self.level % 3 == 0:
                self.pierce += 1
            if self.id == "shotgun":
                if self.level in [3, 5]:
                    self.pellet_count += 1
                self.spread = max(24, int(self.spread * 0.95))
        else:
            self.range += 5

        return True

    def ready_to_fire(self, now):
        return now - self.last_used >= self.cooldown

    def is_reloading(self, now):
        return self.kind == "ranged" and self.reload_end_time > now

    def start_reload(self, now):
        if self.kind == "ranged" and self.reload_end_time <= now:
            self.reload_end_time = now + self.reload_time

    def finish_reload_if_needed(self, now):
        if self.kind == "ranged" and self.reload_end_time > 0 and now >= self.reload_end_time:
            self.ammo = self.max_ammo
            self.reload_end_time = 0


class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.radius = 18
        self.speed = 4.8
        self.hp = 120
        self.max_hp = 120
        self.level = 1
        self.exp = 0
        self.exp_needed = 100
        self.magnet_range = 85
        self.last_hit = 0
        self.hit_delay = 650
        self.weapons = [Weapon("gun")]
        self.freeze_skill = False
        self.freeze_skill_last = 0
        self.freeze_skill_delay = 9000

        # 추가 패시브 능력
        self.lifesteal_level = 0
        self.shield_level = 0
        self.shield_ready = False
        self.shield_last_charge = 0
        self.shield_cooldown = 10000
        self.shield_flash_until = 0

        # 아이템 효과 시간
        self.magnet_boost_until = 0
        self.freeze_until = 0
        self.freeze_flash_until = 0

    def move(self, keys):
        dx = 0
        dy = 0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1

        length = math.hypot(dx, dy)
        if length > 0:
            dx /= length
            dy /= length

        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

    def update_passives(self):
        now = pygame.time.get_ticks()

        # 방어막은 업그레이드가 있을 때만 일정 시간마다 충전된다.
        if self.shield_level > 0 and not self.shield_ready:
            if now - self.shield_last_charge >= self.shield_cooldown:
                self.shield_ready = True

    def take_damage(self, damage):
        now = pygame.time.get_ticks()

        if now - self.last_hit >= self.hit_delay:
            if self.shield_level > 0 and self.shield_ready:
                self.shield_ready = False
                self.shield_last_charge = now
                self.shield_flash_until = now + 360
                self.last_hit = now
                return "blocked"

            self.hp = max(0, self.hp - damage)
            self.last_hit = now
            return "hit"

        return None

    def heal_by_lifesteal(self, enemy_type):
        if self.lifesteal_level <= 0:
            return 0

        amount = 2 + self.lifesteal_level
        if enemy_type == "elite":
            amount += 4 + self.lifesteal_level
        if enemy_type == "boss":
            amount += 8 + self.lifesteal_level * 2

        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def gain_exp(self, amount):
        self.exp += amount
        leveled = False

        while self.exp >= self.exp_needed:
            self.exp -= self.exp_needed
            self.level += 1
            self.exp_needed = int(self.exp_needed * 1.35 + 25)
            leveled = True

        return leveled

    def add_or_upgrade_weapon(self, weapon_id):
        for weapon in self.weapons:
            if weapon.id == weapon_id:
                upgraded = weapon.upgrade()
                if upgraded:
                    return f"{weapon.name} 강화"
                return f"{weapon.name} 최대 레벨"

        self.weapons.append(Weapon(weapon_id))
        return f"{WEAPON_DATA[weapon_id]['name']} 획득"

    def apply_upgrade(self, upgrade_id):
        if upgrade_id == "weapon_laser":
            return self.add_or_upgrade_weapon("laser")
        if upgrade_id == "weapon_shuriken":
            return self.add_or_upgrade_weapon("shuriken")
        if upgrade_id == "weapon_rifle":
            return self.add_or_upgrade_weapon("rifle")
        if upgrade_id == "weapon_shotgun":
            return self.add_or_upgrade_weapon("shotgun")
        if upgrade_id == "weapon_sword":
            return self.add_or_upgrade_weapon("sword")
        if upgrade_id == "weapon_axe":
            return self.add_or_upgrade_weapon("axe")
        if upgrade_id == "weapon_bat":
            return self.add_or_upgrade_weapon("bat")

        if upgrade_id == "damage_all":
            for weapon in self.weapons:
                weapon.damage += 5
            return "모든 무기 공격력 증가"

        if upgrade_id == "cooldown_all":
            for weapon in self.weapons:
                weapon.cooldown = max(50, int(weapon.cooldown * 0.88))
            return "모든 무기 공격 속도 증가"

        if upgrade_id == "ammo_all":
            for weapon in self.weapons:
                if weapon.kind == "ranged":
                    weapon.max_ammo += 6
                    weapon.ammo = weapon.max_ammo
            return "원거리 무기 탄창 증가"

        if upgrade_id == "reload_all":
            for weapon in self.weapons:
                if weapon.kind == "ranged":
                    weapon.reload_time = max(350, int(weapon.reload_time * 0.75))
            return "재장전 속도 증가"

        if upgrade_id == "projectile_speed":
            for weapon in self.weapons:
                if weapon.kind == "ranged":
                    weapon.bullet_speed += 2
            return "탄환 속도 증가"

        if upgrade_id == "max_hp":
            self.max_hp += 25
            self.hp = min(self.max_hp, self.hp + 35)
            return "최대 체력 증가"

        if upgrade_id == "move_speed":
            self.speed += 0.45
            return "이동 속도 증가"

        if upgrade_id == "magnet":
            self.magnet_range += 45
            return "자석 범위 증가"

        if upgrade_id == "freeze_skill":
            self.freeze_skill = True
            self.freeze_skill_delay = max(4500, self.freeze_skill_delay - 1200)
            return "냉기 장치 강화"

        if upgrade_id == "lifesteal":
            self.lifesteal_level += 1
            return "흡혈 부적 강화"

        if upgrade_id == "shield":
            self.shield_level += 1
            self.shield_cooldown = max(5200, self.shield_cooldown - 1400)
            self.shield_ready = True
            return "자동 방어막 강화"

        if upgrade_id == "heal":
            self.hp = min(self.max_hp, self.hp + 60)
            return "체력 회복"

        return "업그레이드 적용"

    def draw(self, surface):
        pygame.draw.circle(surface, BLUE, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)

        # 방어막이 준비되어 있으면 파란 테두리로 표시한다.
        now = pygame.time.get_ticks()
        if self.shield_ready:
            pygame.draw.circle(surface, CYAN, (int(self.x), int(self.y)), self.radius + 8, 3)
        elif now < self.shield_flash_until:
            pygame.draw.circle(surface, CYAN, (int(self.x), int(self.y)), self.radius + 12, 4)

        # 피격 직후 짧게 테두리 표시
        if now - self.last_hit < 160:
            pygame.draw.circle(surface, RED, (int(self.x), int(self.y)), self.radius + 5, 2)


class Bullet:
    def __init__(self, x, y, vx, vy, damage, radius, color, pierce, weapon_name):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.radius = radius
        self.color = color
        self.pierce = pierce
        self.weapon_name = weapon_name
        self.hit_enemies = set()

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def offscreen(self):
        return self.x < -40 or self.x > WIDTH + 40 or self.y < -40 or self.y > HEIGHT + 40

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        if self.weapon_name == "수리검":
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 1)


class Enemy:
    next_id = 1

    def __init__(self, wave, forced_type=None):
        self.id = Enemy.next_id
        Enemy.next_id += 1

        enemy_type = forced_type or random.choices(
            ["normal", "runner", "brute", "tank"],
            weights=[45, 25, 20, 10],
            k=1
        )[0]

        self.enemy_type = enemy_type
        self.spawn_at_edge()

        scale = 1 + wave * 0.12

        if enemy_type == "runner":
            self.name = "날쌘 적"
            self.radius = 12
            self.max_hp = int((22 + wave * 5) * scale)
            self.speed = 2.45 + wave * 0.06
            self.damage = 7 + wave // 4
            self.color = YELLOW
            self.exp_amount = 18 + wave * 2
        elif enemy_type == "brute":
            self.name = "강한 적"
            self.radius = 24
            self.max_hp = int((70 + wave * 12) * scale)
            self.speed = 1.15 + wave * 0.035
            self.damage = 18 + wave // 3
            self.color = RED
            self.exp_amount = 40 + wave * 4
        elif enemy_type == "tank":
            self.name = "샌드백"
            self.radius = 28
            self.max_hp = int((130 + wave * 18) * scale)
            self.speed = 0.75 + wave * 0.02
            self.damage = 10 + wave // 4
            self.color = GREEN
            self.exp_amount = 55 + wave * 5
        elif enemy_type == "elite":
            self.name = "엘리트"
            self.radius = 34
            self.max_hp = int(260 + wave * 55)
            self.speed = 1.35 + wave * 0.035
            self.damage = 18 + wave // 3
            self.color = PINK
            self.exp_amount = 95 + wave * 10
        elif enemy_type == "boss":
            self.name = "보스"
            self.radius = 46
            self.max_hp = int(550 + wave * 150)
            self.speed = 0.95 + wave * 0.015
            self.damage = 25 + wave // 2
            self.color = PURPLE
            self.exp_amount = 180 + wave * 20
        else:
            self.name = "일반 적"
            self.radius = 18
            self.max_hp = int((45 + wave * 8) * scale)
            self.speed = 1.55 + wave * 0.04
            self.damage = 10 + wave // 4
            self.color = RED
            self.exp_amount = 28 + wave * 3

        self.hp = self.max_hp
        self.last_hit = 0

        # 엘리트 전용 돌진 패턴
        # 일반 이동과 구분되는 짧은 고속 돌진을 주기적으로 사용한다.
        self.next_dash_at = pygame.time.get_ticks() + random.randint(1200, 2600)
        self.dash_until = 0
        self.dash_duration = 360
        self.dash_interval = 2600
        self.is_dashing = False

    def spawn_at_edge(self):
        side = random.randint(0, 3)
        margin = 50

        if side == 0:
            self.x = -margin
            self.y = random.randint(0, HEIGHT)
        elif side == 1:
            self.x = WIDTH + margin
            self.y = random.randint(0, HEIGHT)
        elif side == 2:
            self.x = random.randint(0, WIDTH)
            self.y = -margin
        else:
            self.x = random.randint(0, WIDTH)
            self.y = HEIGHT + margin

    def update(self, player, frozen=False):
        now = pygame.time.get_ticks()
        speed = self.speed * (0.18 if frozen else 1.0)

        # 엘리트는 일정 주기마다 짧게 돌진한다.
        # frozen 상태에서는 돌진 타이머만 밀어두고, 실제 돌진은 하지 않는다.
        self.is_dashing = False
        if self.enemy_type == "elite":
            if frozen:
                self.next_dash_at = max(self.next_dash_at, now + 350)
                self.dash_until = 0
            else:
                if now >= self.next_dash_at:
                    self.dash_until = now + self.dash_duration
                    self.next_dash_at = now + self.dash_interval

                if now < self.dash_until:
                    self.is_dashing = True
                    speed *= 3.15

        angle = math.atan2(player.y - self.y, player.x - self.x)
        self.x += math.cos(angle) * speed
        self.y += math.sin(angle) * speed

    def take_damage(self, damage):
        self.hp -= damage
        self.last_hit = pygame.time.get_ticks()

    def draw(self, surface):
        now = pygame.time.get_ticks()
        hit = now - self.last_hit < 85

        # 일반 적은 피격 시 몸 전체가 흰색으로 깜빡이고,
        # 보스는 BOSS 글자가 묻히지 않도록 몸 색은 유지한 채 테두리만 강조한다.
        if self.enemy_type == "boss":
            color = self.color
        else:
            color = WHITE if hit else self.color

        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)

        if hit and self.enemy_type == "boss":
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius + 5, 4)

        if self.enemy_type == "runner":
            pygame.draw.circle(surface, BLACK, (int(self.x), int(self.y)), max(3, self.radius // 3))
        elif self.enemy_type == "tank":
            pygame.draw.rect(surface, BLACK, (int(self.x - 8), int(self.y - 8), 16, 16))
        elif self.enemy_type == "elite":
            # 평소에는 흰 테두리, 돌진 중에는 주황색 테두리로 위험 신호를 준다.
            ring_color = ORANGE if self.is_dashing else WHITE
            pygame.draw.circle(surface, ring_color, (int(self.x), int(self.y)), self.radius + 4, 3)
            if self.is_dashing:
                pygame.draw.circle(surface, ORANGE, (int(self.x), int(self.y)), self.radius + 9, 2)
            draw_text(surface, "ELITE", SMALL_FONT, WHITE, int(self.x - 28), int(self.y - 8))
        elif self.enemy_type == "boss":
            draw_text(surface, "BOSS", SMALL_FONT, WHITE, int(self.x - 24), int(self.y - 8))

        # 체력바
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bar_w = max(42, self.radius * 2)
        bar_h = 6
        bx = int(self.x - bar_w / 2)
        by = int(self.y - self.radius - 14)
        pygame.draw.rect(surface, GRAY, (bx, by, bar_w, bar_h))
        pygame.draw.rect(surface, GREEN, (bx, by, int(bar_w * ratio), bar_h))


class ExpOrb:
    def __init__(self, x, y, amount):
        self.x = x
        self.y = y
        self.amount = amount
        self.radius = 7
        self.created_at = pygame.time.get_ticks()
        self.lifetime = 18000  # 18초 뒤 자동 소멸

    def expired(self):
        return pygame.time.get_ticks() - self.created_at >= self.lifetime

    def update(self, player):
        now = pygame.time.get_ticks()
        attract_range = player.magnet_range

        if now < player.magnet_boost_until:
            attract_range = 2000

        d = distance(self.x, self.y, player.x, player.y)
        if d < attract_range and d > 0:
            speed = 4.5 + (attract_range - min(d, attract_range)) / 80
            self.x += (player.x - self.x) / d * speed
            self.y += (player.y - self.y) / d * speed

    def draw(self, surface):
        # 사라지기 직전에는 살짝 작아져서 수명이 끝나감을 보여준다.
        remain_ratio = 1 - clamp((pygame.time.get_ticks() - self.created_at) / self.lifetime, 0, 1)
        radius = max(3, int(self.radius * (0.55 + 0.45 * remain_ratio)))

        pygame.draw.circle(surface, GREEN, (int(self.x), int(self.y)), radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), radius, 1)


class ItemDrop:
    def __init__(self, x, y, item_type):
        self.x = x
        self.y = y
        self.type = item_type
        self.radius = 11

    def apply(self, player):
        now = pygame.time.get_ticks()

        if self.type == "heal":
            player.hp = min(player.max_hp, player.hp + 35)
            return "체력 회복"
        if self.type == "magnet":
            player.magnet_boost_until = now + 4500
            return "자석 발동"
        if self.type == "freeze":
            player.freeze_until = now + 3200
            player.freeze_flash_until = now + 260
            return "적 일시정지"
        if self.type == "max_hp":
            player.max_hp += 10
            player.hp = min(player.max_hp, player.hp + 20)
            return "최대 체력 증가"

        return "아이템 획득"

    def draw(self, surface):
        if self.type == "heal":
            color = RED
            label = "+"
        elif self.type == "magnet":
            color = CYAN
            label = "M"
        elif self.type == "freeze":
            color = BLUE
            label = "F"
        else:
            color = YELLOW
            label = "H"

        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.radius)
        draw_text(surface, label, SMALL_FONT, WHITE, int(self.x - 5), int(self.y - 10))


class SlashEffect:
    def __init__(self, x, y, radius, color):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.life = 12

    def update(self):
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        width = max(1, self.life // 3)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius, width)


class FloatingText:
    def __init__(self, text, x, y, color=WHITE):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.life = 60

    def update(self):
        self.y -= 0.5
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            draw_text(surface, self.text, SMALL_FONT, self.color, int(self.x), int(self.y))


# -----------------------------
# 게임 로직 함수
# -----------------------------
def auto_attack(player, enemies, bullets, effects):
    now = pygame.time.get_ticks()

    # 냉기 장치 패시브: 일정 주기마다 적 둔화/정지 효과
    if player.freeze_skill and now - player.freeze_skill_last >= player.freeze_skill_delay:
        player.freeze_until = now + 1300
        player.freeze_flash_until = now + 260
        player.freeze_skill_last = now

    for weapon in player.weapons:
        weapon.finish_reload_if_needed(now)

        if not weapon.ready_to_fire(now):
            continue

        if weapon.kind == "ranged":
            if weapon.ammo <= 0:
                weapon.start_reload(now)
                continue

            target = get_nearest_enemy(player.x, player.y, enemies)
            if target is None:
                continue

            angle = math.atan2(target.y - player.y, target.x - player.x)
            pellet_count = getattr(weapon, "pellet_count", 1)
            spread_degrees = getattr(weapon, "spread", 0)

            if pellet_count <= 1:
                shot_angles = [angle]
            else:
                spread_radians = math.radians(spread_degrees)
                start_angle = angle - spread_radians / 2
                step = spread_radians / (pellet_count - 1)
                shot_angles = [start_angle + step * i for i in range(pellet_count)]

            for shot_angle in shot_angles:
                vx = math.cos(shot_angle) * weapon.bullet_speed
                vy = math.sin(shot_angle) * weapon.bullet_speed

                bullets.append(
                    Bullet(
                        player.x,
                        player.y,
                        vx,
                        vy,
                        weapon.damage,
                        weapon.bullet_radius,
                        weapon.color,
                        weapon.pierce,
                        weapon.name,
                    )
                )

            weapon.ammo -= 1
            weapon.last_used = now

            if weapon.ammo <= 0:
                weapon.start_reload(now)

        else:
            # 근접 무기는 주변 범위 안의 모든 적을 자동 공격
            attacked = False
            for enemy in enemies:
                if distance(player.x, player.y, enemy.x, enemy.y) <= weapon.range + enemy.radius:
                    enemy.take_damage(weapon.damage)
                    attacked = True

            if attacked:
                effects.append(SlashEffect(player.x, player.y, weapon.range, weapon.color))
                weapon.last_used = now


def handle_bullet_collisions(bullets, enemies, floating_texts):
    for bullet in bullets[:]:
        bullet.update()

        if bullet.offscreen():
            if bullet in bullets:
                bullets.remove(bullet)
            continue

        for enemy in enemies[:]:
            if enemy.id in bullet.hit_enemies:
                continue

            if distance(bullet.x, bullet.y, enemy.x, enemy.y) < bullet.radius + enemy.radius:
                enemy.take_damage(bullet.damage)
                bullet.hit_enemies.add(enemy.id)
                bullet.pierce -= 1
                floating_texts.append(
                    FloatingText(f"-{bullet.damage}", enemy.x, enemy.y - enemy.radius - 8, YELLOW)
                )

                # 관통 수가 남아 있으면 같은 프레임에서도 다음 적을 계속 검사한다.
                if bullet.pierce <= 0:
                    if bullet in bullets:
                        bullets.remove(bullet)
                    break


def remove_dead_enemies(enemies, orbs, items, floating_texts, wave, player):
    kills = 0
    survivors = []

    for enemy in enemies:
        if enemy.hp <= 0:
            orbs.append(ExpOrb(enemy.x, enemy.y, enemy.exp_amount))
            floating_texts.append(FloatingText(f"+{enemy.exp_amount} EXP", enemy.x, enemy.y - 20, GREEN))

            healed = player.heal_by_lifesteal(enemy.enemy_type)
            if healed > 0:
                floating_texts.append(FloatingText(f"+{healed} HP", player.x + 16, player.y - 28, GREEN))

            # 아이템 드롭
            drop_chance = 0.12
            if enemy.enemy_type == "elite":
                drop_chance = 0.45
            if enemy.enemy_type == "boss":
                drop_chance = 1.0

            if random.random() < drop_chance:
                item_type = random.choices(
                    ["heal", "magnet", "freeze", "max_hp"],
                    weights=[40, 25, 25, 10],
                    k=1
                )[0]
                items.append(ItemDrop(enemy.x, enemy.y, item_type))

            kills += 1
        else:
            survivors.append(enemy)

    enemies[:] = survivors
    return kills


def spawn_enemy_if_needed(enemies, wave, spawn_timer, boss_spawned_waves, elite_spawned_waves, dt):
    spawn_timer += dt
    interval = max(260, 1150 - wave * 45)

    # 5웨이브마다 보스 1회 소환
    if wave % 5 == 0 and wave not in boss_spawned_waves:
        enemies.append(Enemy(wave, forced_type="boss"))
        boss_spawned_waves.add(wave)
        return spawn_timer

    # 3웨이브마다 엘리트 적 1회 소환
    # 보스 웨이브에서는 보스가 우선이라 엘리트는 건너뛴다.
    if wave >= 3 and wave % 3 == 0 and wave % 5 != 0 and wave not in elite_spawned_waves:
        enemies.append(Enemy(wave, forced_type="elite"))
        elite_spawned_waves.add(wave)
        return spawn_timer

    # 적이 너무 많아지는 것 방지
    max_enemies = min(80, 18 + wave * 3)
    if len(enemies) >= max_enemies:
        return spawn_timer

    if spawn_timer >= interval:
        spawn_timer = 0
        enemies.append(Enemy(wave))

        # 후반부에는 가끔 2마리씩 등장
        if wave >= 4 and random.random() < 0.25:
            enemies.append(Enemy(wave))

    return spawn_timer


# -----------------------------
# UI 화면
# -----------------------------
def draw_background(surface):
    surface.blit(BG_SURFACE, (0, 0))


def draw_freeze_flash(surface, player):
    now = pygame.time.get_ticks()
    if now >= player.freeze_flash_until:
        return

    remain = clamp((player.freeze_flash_until - now) / 260, 0, 1)
    flash = pygame.Surface((WIDTH, HEIGHT))
    flash.set_alpha(int(58 * remain))
    flash.fill(BLUE)
    surface.blit(flash, (0, 0))


def draw_ui(surface, player, wave, kills, next_wave_kills):
    # HP
    pygame.draw.rect(surface, GRAY, (20, 20, 230, 24))
    hp_ratio = clamp(player.hp / player.max_hp, 0, 1)
    pygame.draw.rect(surface, GREEN, (20, 20, int(230 * hp_ratio), 24))
    draw_text(surface, f"체력 {player.hp}/{player.max_hp}", SMALL_FONT, WHITE, 26, 21)

    # EXP
    pygame.draw.rect(surface, GRAY, (20, 54, 230, 16))
    exp_ratio = clamp(player.exp / player.exp_needed, 0, 1)
    pygame.draw.rect(surface, PURPLE, (20, 54, int(230 * exp_ratio), 16))

    draw_text(surface, f"레벨 {player.level}", FONT, WHITE, 20, 78)
    draw_text(surface, f"웨이브 {wave}", FONT, WHITE, 20, 106)
    draw_text(surface, f"처치 {kills}/{next_wave_kills}", FONT, WHITE, 20, 134)

    # 상태 효과
    now = pygame.time.get_ticks()
    status_y = 166
    if now < player.magnet_boost_until:
        draw_text(surface, "자석 발동 중", SMALL_FONT, CYAN, 20, status_y)
        status_y += 22
    if now < player.freeze_until:
        draw_text(surface, "적 일시정지 중", SMALL_FONT, BLUE, 20, status_y)
        status_y += 22
    if player.shield_level > 0:
        shield_text = "방어막 준비" if player.shield_ready else "방어막 충전 중"
        draw_text(surface, shield_text, SMALL_FONT, CYAN, 20, status_y)
        status_y += 22
    if player.lifesteal_level > 0:
        draw_text(surface, f"흡혈 Lv.{player.lifesteal_level}", SMALL_FONT, GREEN, 20, status_y)
        status_y += 22

    # 무기 상태
    panel_x = WIDTH - 300
    panel_y = 18
    pygame.draw.rect(surface, (25, 25, 32), (panel_x - 10, panel_y - 8, 288, 205), border_radius=8)
    pygame.draw.rect(surface, GRAY, (panel_x - 10, panel_y - 8, 288, 205), 2, border_radius=8)
    draw_text(surface, "무기 상태", FONT, WHITE, panel_x, panel_y)

    y = panel_y + 32
    for weapon in player.weapons[:7]:
        if weapon.kind == "ranged":
            if weapon.reload_end_time > now:
                remain = max(0, (weapon.reload_end_time - now) / 1000)
                text = f"{weapon.name} Lv.{weapon.level} 재장전 {remain:.1f}s"
                color = YELLOW
            else:
                text = f"{weapon.name} Lv.{weapon.level} 탄약 {weapon.ammo}/{weapon.max_ammo}"
                color = WHITE
        else:
            text = f"{weapon.name} Lv.{weapon.level} 근접 무제한"
            color = WHITE

        draw_text(surface, text, SMALL_FONT, color, panel_x, y)
        y += 23

    if len(player.weapons) > 7:
        draw_text(surface, f"외 {len(player.weapons) - 7}개 무기 보유", SMALL_FONT, YELLOW, panel_x, y)

    # 조작 안내
    draw_text(surface, "이동: WASD/방향키 | 자동공격 | P: 일시정지 | ESC: 종료", SMALL_FONT, WHITE, 20, HEIGHT - 30)


def draw_boss_hp_bar(surface, enemies):
    bosses = [enemy for enemy in enemies if enemy.enemy_type == "boss" and enemy.hp > 0]
    if not bosses:
        return False

    boss = bosses[0]
    bar_w = 430
    bar_h = 20
    x = WIDTH // 2 - bar_w // 2
    y = 14
    ratio = clamp(boss.hp / boss.max_hp, 0, 1)

    pygame.draw.rect(surface, DARK_GRAY, (x - 8, y - 8, bar_w + 16, bar_h + 34), border_radius=8)
    pygame.draw.rect(surface, GRAY, (x, y, bar_w, bar_h), border_radius=4)
    pygame.draw.rect(surface, PURPLE, (x, y, int(bar_w * ratio), bar_h), border_radius=4)
    pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), 2, border_radius=4)

    draw_text(surface, f"보스 체력 {boss.hp}/{boss.max_hp}", SMALL_FONT, WHITE, WIDTH // 2, y + 31, center=True)
    return True


def is_upgrade_available(player, upgrade):
    upgrade_id = upgrade["id"]

    if upgrade_id.startswith("weapon_"):
        weapon_id = upgrade_id.replace("weapon_", "")
        for weapon in player.weapons:
            if weapon.id == weapon_id:
                return weapon.level < weapon.max_level
        # 아직 보유하지 않은 무기는 새로 획득할 수 있어야 한다.
        return True

    # 너무 많이 찍어서 밸런스가 무너지는 업그레이드는 적당히 제한한다.
    if upgrade_id == "move_speed" and player.speed >= 8.5:
        return False
    if upgrade_id == "magnet" and player.magnet_range >= 360:
        return False
    if upgrade_id == "freeze_skill" and player.freeze_skill_delay <= 4500:
        return False
    if upgrade_id == "lifesteal" and player.lifesteal_level >= 5:
        return False
    if upgrade_id == "shield" and player.shield_level >= 4:
        return False

    return True


def level_up_screen(surface, player):
    # 이미 최대치에 도달한 선택지는 제외한다.
    available = [upgrade for upgrade in UPGRADE_POOL if is_upgrade_available(player, upgrade)]

    # 선택지가 3개보다 적을 때도 막힌 업그레이드를 되살리지 않는다.
    # 보통 heal은 항상 가능하므로 최소 1개는 남지만, 안전 장치로 heal을 보장한다.
    if not available:
        available = [{"id": "heal", "title": "응급 치료", "desc": "즉시 체력 회복"}]

    choice_count = min(3, len(available))
    choices = random.sample(available, choice_count)
    buttons = []

    while True:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))

        draw_text(surface, "레벨 업!", TITLE_FONT, WHITE, WIDTH // 2, 95, center=True)
        draw_text(surface, "하나를 선택하세요", FONT, YELLOW, WIDTH // 2, 150, center=True)

        buttons.clear()
        for i, choice in enumerate(choices):
            rect = pygame.Rect(220, 220 + i * 105, 520, 76)
            buttons.append((rect, choice))

            pygame.draw.rect(surface, DARK_GRAY, rect, border_radius=10)
            pygame.draw.rect(surface, WHITE, rect, 3, border_radius=10)
            draw_text(surface, choice["title"], FONT, WHITE, rect.x + 24, rect.y + 12)
            draw_text(surface, choice["desc"], SMALL_FONT, YELLOW, rect.x + 24, rect.y + 44)

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                # 키보드 1, 2, 3으로도 선택 가능
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    index = event.key - pygame.K_1
                    if 0 <= index < len(choices):
                        result = player.apply_upgrade(choices[index]["id"])
                        return result

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                for rect, choice in buttons:
                    if rect.collidepoint(mx, my):
                        result = player.apply_upgrade(choice["id"])
                        return result


def draw_start_screen(surface):
    draw_background(surface)
    draw_text(surface, "로그라이크 자동 슈팅", TITLE_FONT, WHITE, WIDTH // 2, 170, center=True)
    draw_text(surface, "적을 피하면서 자동 공격으로 살아남는 게임", FONT, YELLOW, WIDTH // 2, 240, center=True)
    draw_text(surface, "Enter: 시작", FONT, WHITE, WIDTH // 2, 325, center=True)
    draw_text(surface, "이동: WASD/방향키 | 공격: 자동 | P: 일시정지 | 레벨업: 선택지 클릭", SMALL_FONT, WHITE, WIDTH // 2, 375, center=True)
    draw_text(surface, "원거리 무기는 탄약과 재장전이 있고, 근접 무기는 제한 없이 공격합니다.", SMALL_FONT, CYAN, WIDTH // 2, 405, center=True)
    draw_text(surface, "3웨이브마다 엘리트, 5웨이브마다 보스가 등장합니다.", SMALL_FONT, PINK, WIDTH // 2, 435, center=True)
    draw_text(surface, "레벨업으로 샷건, 흡혈, 방어막 같은 능력을 얻을 수 있습니다.", SMALL_FONT, GREEN, WIDTH // 2, 465, center=True)
    pygame.display.flip()


def draw_game_over(surface, player, wave, kills):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    draw_text(surface, "게임 오버", TITLE_FONT, RED, WIDTH // 2, HEIGHT // 2 - 155, center=True)
    draw_text(surface, f"최종 레벨: {player.level}", FONT, WHITE, WIDTH // 2, HEIGHT // 2 - 85, center=True)
    draw_text(surface, f"도달 웨이브: {wave}", FONT, WHITE, WIDTH // 2, HEIGHT // 2 - 50, center=True)
    draw_text(surface, f"총 처치 수: {kills}", FONT, WHITE, WIDTH // 2, HEIGHT // 2 - 15, center=True)

    weapon_summary = ", ".join([f"{weapon.name} Lv.{weapon.level}" for weapon in player.weapons])
    if len(weapon_summary) > 62:
        weapon_summary = weapon_summary[:59] + "..."

    draw_text(surface, "보유 무기", FONT, YELLOW, WIDTH // 2, HEIGHT // 2 + 35, center=True)
    draw_text(surface, weapon_summary, SMALL_FONT, WHITE, WIDTH // 2, HEIGHT // 2 + 67, center=True)
    draw_text(surface, "R: 다시 시작 | ESC: 종료", FONT, YELLOW, WIDTH // 2, HEIGHT // 2 + 128, center=True)


def draw_pause_screen(surface):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(190)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

    draw_text(surface, "일시정지", TITLE_FONT, WHITE, WIDTH // 2, HEIGHT // 2 - 55, center=True)
    draw_text(surface, "P: 계속하기 | ESC: 종료", FONT, YELLOW, WIDTH // 2, HEIGHT // 2 + 15, center=True)


# -----------------------------
# 게임 초기화
# -----------------------------
def reset_game():
    # 새 게임을 시작할 때 적 ID도 초기화한다.
    # 여러 판을 이어서 플레이해도 총알의 hit_enemies 기록과 ID가 불필요하게 커지지 않는다.
    Enemy.next_id = 1

    player = Player()
    enemies = []
    bullets = []
    orbs = []
    items = []
    effects = []
    floating_texts = []

    wave = 1
    kills = 0
    next_wave_kills = 14
    spawn_timer = 0
    boss_spawned_waves = set()
    elite_spawned_waves = set()
    message = "권총으로 시작합니다"
    message_until = pygame.time.get_ticks() + 2400

    return {
        "player": player,
        "enemies": enemies,
        "bullets": bullets,
        "orbs": orbs,
        "items": items,
        "effects": effects,
        "floating_texts": floating_texts,
        "wave": wave,
        "kills": kills,
        "next_wave_kills": next_wave_kills,
        "spawn_timer": spawn_timer,
        "boss_spawned_waves": boss_spawned_waves,
        "elite_spawned_waves": elite_spawned_waves,
        "message": message,
        "message_until": message_until,
        "state": "start",
    }


# -----------------------------
# 메인 루프
# -----------------------------
def main():
    game = reset_game()
    running = True

    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()

        player = game["player"]
        enemies = game["enemies"]
        bullets = game["bullets"]
        orbs = game["orbs"]
        items = game["items"]
        effects = game["effects"]
        floating_texts = game["floating_texts"]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if game["state"] == "start" and event.key == pygame.K_RETURN:
                    game["state"] = "playing"

                if event.key == pygame.K_p:
                    if game["state"] == "playing":
                        game["state"] = "paused"
                    elif game["state"] == "paused":
                        game["state"] = "playing"

                if game["state"] == "gameover" and event.key == pygame.K_r:
                    game = reset_game()
                    game["state"] = "playing"

        if game["state"] == "start":
            draw_start_screen(screen)
            continue

        if game["state"] == "playing":
            keys = pygame.key.get_pressed()
            player.move(keys)
            player.update_passives()

            # 적 생성
            game["spawn_timer"] = spawn_enemy_if_needed(
                enemies,
                game["wave"],
                game["spawn_timer"],
                game["boss_spawned_waves"],
                game["elite_spawned_waves"],
                dt
            )

            # 자동 공격
            auto_attack(player, enemies, bullets, effects)

            # 총알 충돌
            handle_bullet_collisions(bullets, enemies, floating_texts)

            # 적 이동 및 플레이어 충돌
            frozen = now < player.freeze_until
            for enemy in enemies:
                enemy.update(player, frozen=frozen)
                if distance(player.x, player.y, enemy.x, enemy.y) < player.radius + enemy.radius:
                    damage_result = player.take_damage(enemy.damage)
                    if damage_result == "blocked":
                        floating_texts.append(FloatingText("방어막!", player.x + 18, player.y - 42, CYAN))

            # 사망 적 제거 및 보상 생성
            new_kills = remove_dead_enemies(enemies, orbs, items, floating_texts, game["wave"], player)
            if new_kills > 0:
                game["kills"] += new_kills

            # 웨이브 증가: 처치 수 기준
            if game["kills"] >= game["next_wave_kills"]:
                game["wave"] += 1
                game["next_wave_kills"] += 14 + game["wave"] * 4
                if game["wave"] % 5 == 0:
                    game["message"] = f"웨이브 {game['wave']} 시작! 보스가 등장합니다."
                elif game["wave"] % 3 == 0:
                    game["message"] = f"웨이브 {game['wave']} 시작! 엘리트 적이 등장합니다."
                else:
                    game["message"] = f"웨이브 {game['wave']} 시작! 적이 더 강해집니다."
                game["message_until"] = now + 2300

            # 경험치 구슬 이동 및 획득
            for orb in orbs[:]:
                orb.update(player)

                if orb.expired():
                    if orb in orbs:
                        orbs.remove(orb)
                    continue

                if distance(player.x, player.y, orb.x, orb.y) < player.radius + orb.radius:
                    leveled = player.gain_exp(orb.amount)
                    if orb in orbs:
                        orbs.remove(orb)

                    if leveled:
                        result = level_up_screen(screen, player)
                        game["message"] = result
                        game["message_until"] = pygame.time.get_ticks() + 2400

            # 아이템 획득
            for item in items[:]:
                if distance(player.x, player.y, item.x, item.y) < player.radius + item.radius:
                    result = item.apply(player)
                    game["message"] = result
                    game["message_until"] = now + 2000
                    if item in items:
                        items.remove(item)

            # 이펙트 업데이트
            for effect in effects[:]:
                effect.update()
                if effect.life <= 0:
                    effects.remove(effect)

            # 떠오르는 텍스트 업데이트
            for text in floating_texts[:]:
                text.update()
                if text.life <= 0:
                    floating_texts.remove(text)

            # 게임 오버
            if player.hp <= 0:
                game["state"] = "gameover"

        # -----------------------------
        # 그리기
        # -----------------------------
        draw_background(screen)

        # 자석 범위 표시
        if game["state"] == "playing":
            pygame.draw.circle(screen, (35, 55, 65), (int(player.x), int(player.y)), int(player.magnet_range), 1)

        for orb in orbs:
            orb.draw(screen)

        for item in items:
            item.draw(screen)

        for bullet in bullets:
            bullet.draw(screen)

        for enemy in enemies:
            enemy.draw(screen)

        for effect in effects:
            effect.draw(screen)

        player.draw(screen)

        for text in floating_texts:
            text.draw(screen)

        draw_freeze_flash(screen, player)

        draw_ui(screen, player, game["wave"], game["kills"], game["next_wave_kills"])
        boss_bar_visible = draw_boss_hp_bar(screen, enemies)

        if now < game["message_until"]:
            message_y = 62 if boss_bar_visible else 22
            draw_text(screen, game["message"], FONT, YELLOW, WIDTH // 2, message_y, center=True)

        if game["state"] == "paused":
            draw_pause_screen(screen)

        if game["state"] == "gameover":
            draw_game_over(screen, player, game["wave"], game["kills"])

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
