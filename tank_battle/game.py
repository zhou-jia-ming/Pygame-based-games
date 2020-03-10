#!/usr/bin/env python
# coding:utf-8
# Created at: 2020-02
# Created by: Jiaming

import sys

from enum import IntEnum, unique
from typing import Tuple, Optional, List, Any
from random import randint
import shelve
import webbrowser
import os

from pygame.locals import *
from pygame.sprite import Sprite, Group, groupcollide, collide_mask, \
    collide_rect
from pygame.surface import Surface
from pygame.sysfont import SysFont
from pygame import Rect, init as game_init, display, image, mixer, \
    mixer_music, time as game_time, key, event, quit as game_quit, mouse

SCALE = 10
debug = False


def pos2index(pos):
    return int(pos / (Tank.tank_size / 2))


@unique
class Direction(IntEnum):
    right = 0
    down = 1
    left = 2
    up = 3


class Disjoint(object):
    def __init__(self, length):
        self.array = [-1] * length

    def find(self, i):
        while self.array[i] != -1:
            i = self.array[i]
        return i

    def union(self, i, j):
        x = self.find(i)
        y = self.find(j)
        if (x != y) or (x == -1 and y == -1):
            self.array[x] = y
        return self.find(i), self.find(j)

    def roots(self):
        root_set = set()
        for i in range(len(self.array)):
            new_root = self.find(i)
            if new_root not in root_set:
                root_set.add(new_root)
        return root_set


@unique
class MapItem(IntEnum):
    hard_wall = 0
    soft_wall = 1
    empty = 2
    green_land = 3
    tank = 4
    dummy = 5


def map_connect(m: List[List[MapItem]]):
    h = len(m)
    w = len(m[0])
    # 使用并查集算法 将不是硬墙的部分连接起来。根据root里empty的
    disj = Disjoint(w * h)
    for i in range(h * w):
        x, y = i // w, i % w
        item = m[x][y]
        if item != MapItem.hard_wall:
            down_pos = x, y + 1
            right_pos = x + 1, y
            left_pos = x - 1, y
            up_pos = x, y - 1
            for x_pos, y_pos in [down_pos, right_pos, left_pos, up_pos]:
                if 0 <= x_pos < w and 0 <= y_pos < h and \
                        m[x_pos][y_pos] != MapItem.hard_wall:
                    disj.union(i, x_pos * w + y_pos)

    count = 0
    for root in disj.roots():
        i, j = root // w, root % w
        if m[i][j] != MapItem.hard_wall:
            count += 1
    if count == 1:
        return True
    else:
        return False


noway = (MapItem.hard_wall, MapItem.soft_wall)


class DataMap(object):
    def __init__(self, x, y):
        self._map = list()
        self._width = x
        self._height = y
        for i in range(y):
            line = list()
            for j in range(x):
                line.append(MapItem.empty)
            self._map.append(line)

    def set(self, x, y, val):
        assert isinstance(val, MapItem)
        # check if tank near position x,y
        if MapItem.tank not in self.get_left_up_set(x, y):
            self._map[x][y] = val

    def get(self, x, y):
        if 0 <= x <= self.width - 1 and 0 <= y <= self.height - 1:
            return self._map[x][y]
        else:
            return None

    def get_left_up_set(self, x, y):
        left_up_set = set()
        if x - 1 >= 0:
            left_up_set.add(self.get(x - 1, y))
        if y - 1 >= 0:
            left_up_set.add(self.get(x, y - 1))
        if x - 1 >= 0 and y - 1 >= 0:
            left_up_set.add(self.get(x - 1, y - 1))
        return left_up_set

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def is_empty(self):
        for line in self._map:
            for item in line:
                if item != MapItem.empty:
                    return False
        return True

    def is_connected(self):
        if map_connect(m=self._map):
            return True
        else:
            return False


class Button(object):
    def __init__(self, screen: Surface, **kwargs):
        self._text = kwargs.get('text', '')
        self._inactive_color = kwargs.get('inactive_color', None)
        self._active_color = kwargs.get('active_color', None)
        self._font_size = kwargs.get('font_size', None)
        self._handler_event = kwargs.get('handler_event', None)
        self._fg = kwargs.get('fg', None)
        self.value = kwargs.get('value', None)
        self._screen = screen
        self.hover = False
        self.x, self.y = kwargs.get('x', None), kwargs.get('y', None)

        bg_image_path = kwargs.get('bg_image', None)
        if bg_image_path:
            self._bg_image = image.load(bg_image_path)
        else:
            self._bg_image = None
            self._font = SysFont("Arial", self._font_size)
            self._bigger_font = SysFont("Arial", self._font_size + 5)

    def handler_event(self, evt):
        self._handler_event(evt)

    @property
    def render(self):
        if self._bg_image:
            return self._bg_image
        if self._hover:
            return self._bigger_font.render(self.text, True, self.fg, self.bg)
        else:
            return self._font.render(self.text, True, self.fg, self.bg)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        if isinstance(text, str):
            self._text = text

    @property
    def fg(self):
        return self._fg

    @property
    def bg(self):
        if self._hover:
            return self._active_color
        else:
            return self._inactive_color

    @property
    def font_size(self):
        return self._font_size

    @font_size.setter
    def font_size(self, val):
        self._font_size = val

    @property
    def hover(self):
        return self._hover

    @hover.setter
    def hover(self, val):
        self._hover = val

    @hover.getter
    def hover(self):
        return self._hover

    def on_button(self, pos):
        x, y = pos
        if self.rect.left <= x <= self.rect.right and \
                self.rect.top <= y <= self.rect.bottom:
            self.hover = True
        else:
            self.hover = False
        return self.hover

    @property
    def width(self):
        return self.render.get_rect().width

    @property
    def height(self):
        return self.render.get_rect().height

    @property
    def rect(self):
        if self.x is None:
            # 没有设定x, 居中
            self.x = self._screen.get_rect().centerx - self.width // 2
        if self.y is None:
            # 没有设定y, 居中
            self.y = self._screen.get_rect().centery - self.height // 2
        return self.render.get_rect().move(self.x, self.y)

    def update(self, evt):
        raise NotImplementedError

    def draw(self) -> None:

        self._screen.blit(self.render, (self.x, self.y))


class Bullet(Sprite):
    player_bullet_up_image = image.load("img/player-bullet-up.png")
    player_bullet_down_image = image.load("img/player-bullet-down.png")
    player_bullet_left_image = image.load("img/player-bullet-left.png")
    player_bullet_right_image = image.load("img/player-bullet-right.png")
    npc_bullet_up_image = image.load("img/npc-bullet-up.png")
    npc_bullet_down_image = image.load("img/npc-bullet-down.png")
    npc_bullet_left_image = image.load("img/npc-bullet-left.png")
    npc_bullet_right_image = image.load("img/npc-bullet-right.png")
    bullet_size = npc_bullet_right_image.get_rect().width

    def __init__(self, location: Tuple, direction: Direction,
                 bullet_type: Optional[str] = 'user', **kwargs):
        global SCALE
        Sprite.__init__(self)
        self.location = [location[0] + self.bullet_size // 2 + 2,
                         location[1] + self.bullet_size // 2 + 2]
        self.direction = direction
        self._bullet_type = bullet_type
        self.max_w = kwargs['max_w']
        self.max_h = kwargs['max_h']
        self.status = 'alive'

    @property
    def image(self):
        if self._bullet_type == 'user':
            return {Direction.up: self.player_bullet_up_image,
                    Direction.down: self.player_bullet_down_image,
                    Direction.left: self.player_bullet_left_image,
                    Direction.right: self.player_bullet_right_image,
                    }.get(self.direction)
        else:
            return {Direction.up: self.npc_bullet_up_image,
                    Direction.down: self.npc_bullet_down_image,
                    Direction.left: self.npc_bullet_left_image,
                    Direction.right: self.npc_bullet_right_image,
                    }.get(self.direction)

    @property
    def rect(self) -> Rect:
        return self.image.get_rect().move(self.location[0], self.location[1])

    def update(self) -> None:
        x, y = self.location
        if self.direction == Direction.right:
            x += SCALE
        elif self.direction == Direction.down:
            y += SCALE
        elif self.direction == Direction.left:
            x -= SCALE
        elif self.direction == Direction.up:
            y -= SCALE
        else:
            raise Exception('no such direction {}'.format(self.direction))

        self.location = x, y

        if 0 <= self.rect.left and self.rect.right <= self.max_w and \
                0 <= self.rect.top and self.rect.bottom <= self.max_h:
            pass
        else:
            self.kill()

    def kill(self) -> None:
        Sprite.kill(self)

    @property
    def type(self):
        return self._bullet_type


class Bomb(Sprite):

    def __init__(self, pos: Tuple, surface: Surface):
        super().__init__()
        self.bomb_num = 0
        self.pos = [pos[0] - 28, pos[1] - 28]
        self.surface = surface

    @property
    def image(self) -> Surface:
        return image.load(
            "img/bomb/bomb-{}.png".format(self.bomb_num))

    def update(self) -> None:
        self.bomb_num += 1
        self.draw()

    def draw(self) -> None:
        if self.bomb_num > 14:
            self.kill()
            return
        self.surface.blit(self.image, self.pos)


class HardWall(Sprite):
    _image = image.load("img/map/hard_wall.png")

    def __init__(self, location: Tuple, surface: Surface):
        super().__init__()
        self.location = location
        self.surface = surface

    @property
    def rect(self):
        return self.image.get_rect().move(self.location[0], self.location[1])

    @property
    def image(self) -> Surface:
        return self._image

    def update(self) -> None:
        self.draw()

    def draw(self) -> None:
        self.surface.blit(self.image, self.location)


class SoftWall(Sprite):
    _image = image.load("img/map/soft_wall.png")

    def __init__(self, location: Tuple, surface: Surface):
        super().__init__()
        self.location = location
        self.surface = surface

    @property
    def rect(self):
        return self.image.get_rect().move(self.location[0], self.location[1])

    @property
    def image(self) -> Surface:
        return self._image

    def update(self) -> None:
        self.draw()

    def draw(self) -> None:
        self.surface.blit(self.image, self.location)


class GreenLand(Sprite):
    _image = image.load("img/map/green_land.png")

    def __init__(self, location: Tuple, surface: Surface):
        super().__init__()
        self.location = location
        self.surface = surface

    @property
    def rect(self):
        return self.image.get_rect().move(self.location[0], self.location[1])

    @property
    def image(self) -> Surface:
        return self._image

    def update(self) -> None:
        self.draw()

    def draw(self) -> None:
        self.surface.blit(self.image, self.location)


class Player(Sprite):
    player_right = image.load("img/player-right.png")
    player_down = image.load("img/player-down.png")
    player_left = image.load("img/player-left.png")
    player_up = image.load("img/player-up.png")

    def __init__(self, location: List, bullet_list: Group, surface: Surface,
                 **kwargs):
        super().__init__()
        global SCALE
        direction = kwargs.get('direction', None)
        if direction is None:
            self.direction = Direction.up
        else:
            self.direction = direction
        self.location = location
        self.bullet_tick = 0
        self.bullet_interval = 5
        self.max_w = kwargs['max_w']
        self.max_h = kwargs['max_h']
        self.scale = SCALE
        self.bullet_list = bullet_list
        self.surface = surface

    def turn_up(self, battle_field) -> None:
        self.direction = Direction.up
        next_rect = self.next_tank.rect
        loc1 = pos2index(next_rect.left + 1), pos2index(
            next_rect.top)
        loc2 = pos2index(next_rect.centerx), pos2index(
            next_rect.top)
        loc3 = pos2index(next_rect.right - 1), pos2index(
            next_rect.top)
        next_item1 = battle_field.get(*loc1)
        next_item2 = battle_field.get(*loc2)
        next_item3 = battle_field.get(*loc3)

        if (next_item1 in noway) or (next_item2 in noway) or \
                (next_item3 in noway) or self.location[1] <= 0:
            pass
        else:
            self.location[1] = self.location[1] - self.scale

    def turn_down(self, battle_field) -> None:
        self.direction = Direction.down
        next_rect = self.next_tank.rect
        loc1 = pos2index(next_rect.left + 1), pos2index(
            next_rect.bottom - 1)
        loc2 = pos2index(next_rect.centerx), pos2index(
            next_rect.bottom - 1)
        loc3 = pos2index(next_rect.right - 1), pos2index(
            next_rect.bottom - 1)
        next_item1 = battle_field.get(*loc1)
        next_item2 = battle_field.get(*loc2)
        next_item3 = battle_field.get(*loc3)
        if (next_item1 in noway) or (next_item2 in noway) or \
                (next_item3 in noway) or self.rect.bottom + 1 > self.max_w:
            pass
        else:
            self.location[1] = self.location[1] + self.scale

    def turn_left(self, battle_field) -> None:
        self.direction = Direction.left
        next_rect = self.next_tank.rect
        loc1 = pos2index(next_rect.left), pos2index(next_rect.top)
        loc2 = pos2index(next_rect.left), pos2index(
            next_rect.centery)
        loc3 = pos2index(next_rect.left), pos2index(
            next_rect.bottom - 1)
        next_item1 = battle_field.get(*loc1)
        next_item2 = battle_field.get(*loc2)
        next_item3 = battle_field.get(*loc3)
        if (next_item1 in noway) or (next_item2 in noway) or (
                next_item3 in noway) or self.rect.left == 0:
            pass
        else:
            self.location[0] = self.location[0] - self.scale

    def turn_right(self, battle_field) -> None:
        self.direction = Direction.right
        next_rect = self.next_tank.rect
        loc1 = pos2index(next_rect.right - 1), pos2index(next_rect.top)
        loc2 = pos2index(next_rect.right - 1), pos2index(next_rect.centery)
        loc3 = pos2index(next_rect.right - 1), pos2index(
            next_rect.bottom - 1)
        next_item1 = battle_field.get(*loc1)
        next_item2 = battle_field.get(*loc2)
        next_item3 = battle_field.get(*loc3)
        if (next_item1 in noway) or (next_item2 in noway) or \
                (next_item3 in noway) or self.rect.right + 1 > self.max_w:
            pass
        else:
            self.location[0] = self.location[0] + self.scale

    @property
    def next_tank(self) -> Sprite:
        if self.direction == Direction.right:
            next_pos = [self.location[0] + self.scale, self.location[1]]
        elif self.direction == Direction.down:
            next_pos = [self.location[0], self.location[1] + self.scale]
        elif self.direction == Direction.left:
            next_pos = [self.location[0] - self.scale, self.location[1]]
        elif self.direction == Direction.up:
            next_pos = [self.location[0], self.location[1] - self.scale]
        else:
            raise Exception('no such direction {}'.format(self.direction))

        return Player(next_pos, self.bullet_list, self.surface,
                      direction=self.direction,
                      max_h=self.max_h,
                      max_w=self.max_w)

    def shot(self) -> None:
        """
        player shot
        """
        if self.bullet_tick != 0:
            return
        self.bullet_tick += 1
        bullet_pos = []
        if self.direction == Direction.right:
            bullet_pos.append(self.rect.right - self.rect.h // 3)
            bullet_pos.append(self.rect.top + self.rect.h // 3)
        elif self.direction == Direction.down:
            bullet_pos.append(self.rect.left + self.rect.h // 3)
            bullet_pos.append(self.rect.bottom - self.rect.h // 3)
        elif self.direction == Direction.left:
            bullet_pos.append(self.rect.left)
            bullet_pos.append(self.rect.top + self.rect.h // 3)
        elif self.direction == Direction.up:
            bullet_pos.append(self.rect.left + self.rect.h // 3)
            bullet_pos.append(self.rect.top)
        else:
            raise Exception("no such direction {}".format(self.direction))
        self.bullet_list.add(Bullet(bullet_pos, self.direction,
                                    max_h=self.max_h, max_w=self.max_w))

    @property
    def image(self) -> Surface:
        if self.direction == Direction.right:
            return self.player_right
        if self.direction == Direction.down:
            return self.player_down
        if self.direction == Direction.left:
            return self.player_left
        if self.direction == Direction.up:
            return self.player_up

    @property
    def rect(self) -> Rect:
        return self.image.get_rect().move(self.location[0], self.location[1])

    def draw(self) -> None:
        if self.bullet_tick > 0:
            self.bullet_tick += 1
        if self.bullet_tick > self.bullet_interval:
            self.bullet_tick = 0
        self.surface.blit(self.image, self.rect)


class Tank(Sprite):
    tank_right = image.load("img/tank-right.png")
    tank_down = image.load("img/tank-down.png")
    tank_left = image.load("img/tank-left.png")
    tank_up = image.load("img/tank-up.png")
    tank_size = tank_up.get_rect().width

    def __init__(self, surface: Surface, npc_bullet_list: Group, **kwargs):
        global SCALE
        super().__init__()
        self.scale = SCALE
        self.bullet_tick = 0
        self.bullet_interval = 5
        self.direction = kwargs.get('direction') or randint(0, 3)
        self.location = kwargs.get('location') or [randint(0, 12) * self.scale,
                                                   randint(0, 12) * self.scale]

        self.status = 'patrol'
        self.rest_life = 3
        self.max_w = kwargs['max_w']
        self.max_h = kwargs['max_h']
        bullet = kwargs.get('bullet', None)
        self.npc_bullet_list = npc_bullet_list
        if not bullet:
            self.bullet = None
        else:
            self.bullet = Bullet(bullet['location'], bullet['direction'],
                                 max_h=self.max_h, max_w=self.max_w,
                                 bullet_type='npc')
            self.npc_bullet_list.add(self.bullet)

        self.surface = surface

    def find_enemy(self, enemy_rect: Rect,
                   battle_field: List[List[Any]]) -> bool:

        if self.rect.centerx == enemy_rect.centerx:
            if enemy_rect.centery > self.rect.centery:
                self.direction = Direction.down
            else:
                self.direction = Direction.up
            return True
        if self.rect.centery == enemy_rect.centery:
            if enemy_rect.centerx < self.rect.centerx:
                self.direction = Direction.left
            else:
                self.direction = Direction.right
            return True
        return False

    def update(self, enemy: Sprite, battle_field: List[List[Any]]) -> None:
        """
            这里是一个 Tank 有限状态自动机
            npc在攻击、逃跑和巡逻之间切换
            每个npc发射一发子弹后必须等到子弹命中或超出屏幕才能发射下一发
        """
        if enemy:
            enemy_rect = enemy.rect
        else:
            return

        if self.status == 'patrol':
            if not self.find_enemy(enemy_rect, battle_field):
                # 没有情况继续巡逻
                pass
            else:
                # 巡逻状态，看见敌人，进入攻击模式
                self.status = 'attack'

        elif self.status == 'attack':
            # 攻击状态，如果敌人在视野内，继续攻击

            if self.find_enemy(enemy_rect, battle_field):
                self.shot()
            else:
                # 进入巡逻模式
                self.status = 'patrol'

        # 更新位置
        self.move(battle_field)
        # 绘画
        self.draw()

    def move(self, battle_field) -> None:
        # 根据当前状态行动
        move_x, move_y = 0, 0
        x, y = self.location
        noway = (MapItem.hard_wall, MapItem.soft_wall)
        if self.status == 'patrol':
            # 向原有方向前进一个单元，或者转向90度
            if self.direction == Direction.right:
                next_rect = self.next_tank.rect
                loc1 = pos2index(next_rect.right - 1), pos2index(next_rect.top)
                loc2 = pos2index(next_rect.right - 1), pos2index(
                    next_rect.centery)
                loc3 = pos2index(next_rect.right - 1), pos2index(
                    next_rect.bottom - 1)
                next_item1 = battle_field.get(*loc1)
                next_item2 = battle_field.get(*loc2)
                next_item3 = battle_field.get(*loc3)

                if (next_item1 in noway) or (next_item2 in noway) or \
                        (next_item3 in noway) or \
                        self.rect.right + 1 > self.max_w:
                    self.direction = Direction.left
                else:
                    move_x += self.scale
            elif self.direction == Direction.down:
                next_rect = self.next_tank.rect
                loc1 = pos2index(next_rect.left + 1), pos2index(
                    next_rect.bottom - 1)
                loc2 = pos2index(next_rect.centerx), pos2index(
                    next_rect.bottom - 1)
                loc3 = pos2index(next_rect.right - 1), pos2index(
                    next_rect.bottom - 1)
                next_item1 = battle_field.get(*loc1)
                next_item2 = battle_field.get(*loc2)
                next_item3 = battle_field.get(*loc3)
                if (next_item1 in noway) or (next_item2 in noway) or \
                        (next_item3 in noway) or \
                        self.rect.bottom + 1 > self.max_w:
                    self.direction = Direction.up
                else:
                    move_y += self.scale
            elif self.direction == Direction.left:
                next_rect = self.next_tank.rect
                loc1 = pos2index(next_rect.left), pos2index(next_rect.top)
                loc2 = pos2index(next_rect.left), pos2index(
                    next_rect.centery)
                loc3 = pos2index(next_rect.left), pos2index(
                    next_rect.bottom - 1)
                next_item1 = battle_field.get(*loc1)
                next_item2 = battle_field.get(*loc2)
                next_item3 = battle_field.get(*loc3)
                if (next_item1 in noway) or (next_item2 in noway) or \
                        (next_item3 in noway) or x <= 0:
                    self.direction = Direction.right
                else:
                    move_x -= self.scale
            elif self.direction == Direction.up:
                next_rect = self.next_tank.rect
                loc1 = pos2index(next_rect.left + 1), pos2index(
                    next_rect.top)
                loc2 = pos2index(next_rect.centerx), pos2index(
                    next_rect.top)
                loc3 = pos2index(next_rect.right - 1), pos2index(
                    next_rect.top)
                next_item1 = battle_field.get(*loc1)
                next_item2 = battle_field.get(*loc2)
                next_item3 = battle_field.get(*loc3)

                if (next_item1 in noway) or (next_item2 in noway) or \
                        (next_item3 in noway) or y <= 0:
                    self.direction = Direction.down
                else:
                    move_y -= self.scale
            else:
                raise Exception('no such direction {}'.format(self.direction))
            self.location[0] += move_x
            self.location[1] += move_y
            # random turn
            if randint(1, 10) == 10:
                self.direction = Direction((self.direction + 1) % 4)
            if randint(1, 15) == 15:
                self.shot()

    @property
    def image(self) -> Surface:
        if self.direction == Direction.right:
            return self.tank_right
        if self.direction == 1:
            return self.tank_down
        if self.direction == 2:
            return self.tank_left
        if self.direction == 3:
            return self.tank_up

    @property
    def rect(self) -> Rect:
        return self.image.get_rect().move(self.location[0], self.location[1])

    @property
    def next_tank(self) -> Sprite:
        if self.direction == Direction.right:
            next_pos = [self.location[0] + self.scale, self.location[1]]
        elif self.direction == Direction.down:
            next_pos = [self.location[0], self.location[1] + self.scale]
        elif self.direction == Direction.left:
            next_pos = [self.location[0] - self.scale, self.location[1]]
        elif self.direction == Direction.up:
            next_pos = [self.location[0], self.location[1] - self.scale]
        else:
            raise Exception('no such direction {}'.format(self.direction))

        return Tank(self.surface, self.npc_bullet_list, location=next_pos,
                    direction=self.direction,
                    max_h=self.max_h,
                    max_w=self.max_w)

    def shot(self) -> None:
        """
        npc tank shot
        :return:
        """
        if self.bullet and self.bullet.alive():
            return

        bullet_pos = []
        if self.direction == Direction.right:
            bullet_pos.append(self.rect.right - self.rect.h // 3)
            bullet_pos.append(self.rect.top + self.rect.h // 3)
        elif self.direction == Direction.down:
            bullet_pos.append(self.rect.left + self.rect.h // 3)
            bullet_pos.append(self.rect.bottom - self.rect.h // 3)
        elif self.direction == Direction.left:
            bullet_pos.append(self.rect.left)
            bullet_pos.append(self.rect.top + self.rect.h // 3)
        elif self.direction == Direction.up:
            bullet_pos.append(self.rect.left + self.rect.h // 3)
            bullet_pos.append(self.rect.top)
        else:
            raise Exception("no such direction {}".format(self.direction))
        self.bullet = Bullet(bullet_pos, self.direction, max_h=self.max_h,
                             max_w=self.max_w, bullet_type='npc')
        self.npc_bullet_list.add(self.bullet)

    def draw(self) -> None:
        self.surface.blit(self.image, self.rect)


# TODO 制作关卡编辑器


class Game(object):

    def __init__(self):
        game_init()
        display.set_caption('坦克大战')
        mixer_music.load('music/bgm.mp3')
        if not debug:
            mixer_music.play(-1)
        self.bomb_sound = mixer.Sound('music/bomb.ogg')
        global SCALE
        self.click_down_pos = None
        self.black = 0, 0, 0
        self.white = 255, 255, 255
        self.fg = 250, 240, 230
        self.bg = 5, 5, 5
        self.wincolor = 40, 40, 90
        self.font_size = 100
        self.smaller_font_size = 60
        self.edit_btn_font_size = 40
        self.size = self.width, self.height, = 780, 780

        self.scale = 10
        self.tank_size = Tank.tank_size

        self.playing_win_size = self.width + self.tank_size * 4, self.height
        self.edit_win_size = self.width + self.tank_size * 7, self.height

        self.replay_btn_left, self.replay_btn_top = None, 350
        self.replay_btn_right, self.replay_btn_down = None, None

        # game status
        self.score = None
        self.intro = True
        self.cur_level = None
        self.battle_field = None
        self.edit = False
        self.drawing = False
        self.playing_area = None

        self.screen = display.set_mode(self.size)
        # edit map relevant property
        self.edit_area = None
        self.editing_data_map = None
        self._hard_wall = None
        self._soft_wall = None
        self._green_land = None
        self._empty = None
        self._tank = None
        # game sprite etc
        self.bullet_list = Group()
        self.npc_tanks = Group()
        self.npc_bullets = Group()
        self.bombs = Group()
        self.hard_wall_group = Group()
        self.soft_wall_group = Group()
        self.green_land_group = Group()
        # main menu property
        self.intro_button_list = list()
        self.new_game_btn = None
        self.load_game_btn = None
        self.edit_level_btn = None
        self.about_me_btn = None
        self.screen.fill(self.wincolor)
        self.init_intro_button()  # init menu button
        # btn when playing
        self.playing_btn = list()

        self.edit_button_list = list()
        self.map_file = 'map'
        self.record = 'record'
        self.status_btn = None
        self.score_btn = None
        self.save_progress_btn = None
        self.back_btn = None

        self.last_level_btn = None
        self.next_level_btn = None
        self.edit_old_level_btn = None
        self.editing_level = None

        self.new_level_btn = None
        self.exit_edit_btn = None
        self.hard_wall_btn = None
        self.soft_wall_btn = None
        self.green_land_btn = None
        self.empty_btn = None
        self.tank_btn = None
        self.save_level_btn = None

        self.init_edit_button()
        self.editing_tool = None

        self.player_group = Group()
        self.init_player()
        # property about draw stage over
        self.draw_pos = 0, 0
        self.draw_direction = Direction.right
        self.clock = game_time.Clock()

    @property
    def min_unit_size(self):
        return self.tank_size // 2

    @property
    def player(self) -> Any:
        if len(self.player_group) > 0:
            return self.player_group.sprites()[0]
        return None

    def init_intro_button(self) -> None:

        self.new_game_btn = Button(self.screen, text=u' NEW GAME ',
                                   inactive_color=self.wincolor,
                                   active_color=self.wincolor,
                                   handler_event=self.new_game_handler,
                                   font_size=self.smaller_font_size,
                                   fg=self.fg,
                                   )
        self.load_game_btn = Button(self.screen, text=u'LOAD GAME',
                                    inactive_color=self.wincolor,
                                    active_color=self.wincolor,
                                    handler_event=self.load_game_handler,
                                    font_size=self.smaller_font_size,
                                    fg=self.fg)

        self.edit_level_btn = Button(self.screen, text=u'EDIT  LEVEL',
                                     inactive_color=self.wincolor,
                                     active_color=self.wincolor,
                                     handler_event=self.edit_level_handler,
                                     font_size=self.smaller_font_size,
                                     fg=self.fg)

        self.about_me_btn = Button(self.screen, text=u'ABOUT ME',
                                   inactive_color=self.wincolor,
                                   active_color=self.wincolor,
                                   handler_event=self.about_me_handler,
                                   font_size=self.smaller_font_size,
                                   fg=self.fg)
        self.intro_button_list += [self.new_game_btn, self.load_game_btn,
                                   self.edit_level_btn, self.about_me_btn]

        # new_game, load game, Edit level, about me

        screen_height = self.height

        btn_height = self.new_game_btn.rect.height

        start_y = (screen_height - btn_height * len(
            self.intro_button_list)) // 2

        for btn in self.intro_button_list:
            btn.y = start_y
            start_y += btn.rect.height

    def init_edit_button(self) -> None:
        self.status_btn = Button(self.screen, text=u"""     """,
                                 inactive_color=self.wincolor,
                                 active_color=self.wincolor,
                                 handler_event=self.nothing_handler,
                                 font_size=self.edit_btn_font_size,
                                 fg=self.fg)
        self.score_btn = Button(self.screen, text=u"""Score: 0""",
                                inactive_color=self.wincolor,
                                active_color=self.wincolor,
                                handler_event=self.nothing_handler,
                                font_size=self.edit_btn_font_size,
                                fg=self.fg)
        self.save_progress_btn = Button(self.screen, text=u"""save""",
                                        inactive_color=self.wincolor,
                                        active_color=self.wincolor,
                                        handler_event=self.save_game,
                                        font_size=self.edit_btn_font_size,
                                        fg=self.fg)
        self.back_btn = Button(self.screen, text=u"""back to menu""",
                               inactive_color=self.wincolor,
                               active_color=self.wincolor,
                               handler_event=self.back_intro,
                               font_size=self.edit_btn_font_size,
                               fg=self.fg)
        self.last_level_btn = Button(self.screen, text=""" <= """,
                                     inactive_color=self.wincolor,
                                     active_color=self.wincolor,
                                     handler_event=self.last_level_btn_handler,
                                     font_size=self.edit_btn_font_size,
                                     fg=self.fg)
        self.next_level_btn = Button(self.screen, text=""" => """,
                                     inactive_color=self.wincolor,
                                     active_color=self.wincolor,
                                     handler_event=self.next_level_btn_handler,
                                     font_size=self.edit_btn_font_size,
                                     fg=self.fg)
        self.edit_old_level_btn = Button(self.screen, text=u"""edit""",
                                         inactive_color=self.wincolor,
                                         active_color=self.wincolor,
                                         handler_event=self.edit_old_level,
                                         font_size=self.edit_btn_font_size,
                                         fg=self.fg, value=1)
        self.new_level_btn = Button(self.screen, text=u"""new level""",
                                    inactive_color=self.wincolor,
                                    active_color=self.wincolor,
                                    handler_event=self.new_level_handler,
                                    font_size=self.edit_btn_font_size,
                                    fg=self.fg)
        self.exit_edit_btn = Button(self.screen, text=u"""quit edit""",
                                    inactive_color=self.wincolor,
                                    active_color=self.wincolor,
                                    handler_event=self.exit_edit_handler,
                                    font_size=self.edit_btn_font_size,
                                    fg=self.fg)
        self.hard_wall_btn = Button(self.screen,
                                    bg_image='img/map/hard_wall_btn.png',
                                    handler_event=self.hard_wall_handler)
        self.soft_wall_btn = Button(self.screen,
                                    bg_image='img/map/soft_wall_btn.png',
                                    handler_event=self.soft_wall_handler)
        self.green_land_btn = Button(self.screen,
                                     bg_image='img/map/green_land_btn.png',
                                     handler_event=self.green_land_handler)
        self.empty_btn = Button(self.screen,
                                bg_image='img/map/empty_btn.png',
                                handler_event=self.empty_handler)

        self.tank_btn = Button(self.screen,
                               bg_image='img/tank-up.png',
                               handler_event=self.tank_handler)

        self.save_level_btn = Button(self.screen, text=u"""save level""",
                                     inactive_color=self.wincolor,
                                     active_color=self.wincolor,
                                     handler_event=self.save_level_handler,
                                     font_size=self.edit_btn_font_size,
                                     fg=self.fg)

    def new_game_handler(self, evt):
        if self.be_clicked(self.new_game_btn, evt):
            self.screen = display.set_mode(self.playing_win_size)
            self.score = 0
            self.intro = False
            self.cur_level = 1
            self.battle_field = self.get_level_map(1)
            self.load_level()
            self.init_player()
            # load level 1

    def load_level(self):
        self.hard_wall_group.empty()
        self.soft_wall_group.empty()
        self.green_land_group.empty()
        self.npc_tanks.empty()
        if self.cur_level > self.game_levels:
            # stage clear
            self.battle_field = DataMap(self.width // Tank.tank_size,
                                        self.height // Tank.tank_size)
            self.player_group.empty()
            return

        for x in range(self.battle_field.width):
            for y in range(self.battle_field.height):
                item = self.battle_field.get(x, y)
                location = (x * self.min_unit_size, y * self.min_unit_size)
                if item == MapItem.hard_wall:
                    self.hard_wall_group.add(HardWall(location, self.screen))
                elif item == MapItem.soft_wall:
                    self.soft_wall_group.add(SoftWall(location, self.screen))
                elif item == MapItem.green_land:
                    self.green_land_group.add(GreenLand(location, self.screen))
                elif item == MapItem.tank:
                    self.npc_tanks.add(
                        Tank(self.screen, npc_bullet_list=self.npc_bullets,
                             location=[x * self.min_unit_size,
                                       y * self.min_unit_size],
                             max_w=self.width,
                             max_h=self.height))

    def clear_all_sprites(self):
        self.soft_wall_group.empty()
        self.green_land_group.empty()
        self.hard_wall_group.empty()
        self.npc_tanks.empty()
        self.npc_bullets.empty()
        self.player_group.empty()
        self.bullet_list.empty()

    def load_game_handler(self, evt):
        if self.be_clicked(self.load_game_btn, evt):
            # load game record
            if not os.path.exists(self.record + '.db'):
                self.load_game_btn.text = 'no data to load!'
                return
            with shelve.open(self.record, 'c') as db:

                self.score = db.get('score')
                self.battle_field = db.get('map')
                self.cur_level = db.get('level')
                soft_wall = db['soft_wall']
                hard_wall = db['hard_wall']
                green_land = db['green_land']
                location = db['location']
                npc = db['npc_tank']
                bullet = db['bullet']
                bomb = db['bomb']
            self.intro = False

            self.screen = display.set_mode(self.playing_win_size)
            self.init_player()
            self.player.location = location
            for item in soft_wall:
                self.soft_wall_group.add(SoftWall(item, self.screen))
            for item in hard_wall:
                self.hard_wall_group.add(HardWall(item, self.screen))
            for item in green_land:
                self.green_land_group.add(GreenLand(item, self.screen))
            for item in npc:
                new_npc = Tank(self.screen,
                               npc_bullet_list=self.npc_bullets,
                               bullet=item['bullet'],
                               location=item['location'], max_w=self.width,
                               max_h=self.height)

                self.npc_tanks.add(new_npc)
            for item in bullet:
                self.bullet_list.add(Bullet(item['location'],
                                            item['direction'],
                                            bullet_type='user',
                                            max_h=self.height,
                                            max_w=self.width))
            for item in bomb:
                new_bomb = Bomb(item['pos'], self.screen)
                new_bomb.bomb_num = item['bomb_num']
                self.bombs.add(new_bomb)

    def edit_level_handler(self, evt):
        if self.be_clicked(self.edit_level_btn, evt):
            self.intro = False
            self.edit = True
            self.screen = display.set_mode(self.edit_win_size)
            display.set_caption('地图编辑模式')

    def high_score_handler(self, evt):
        if self.be_clicked(self.high_score_btn, evt):
            pass

    def about_me_handler(self, evt):
        if self.be_clicked(self.about_me_btn, evt):
            webbrowser.open('https://github.com/zhou-jia-ming/my_game', new=0,
                            autoraise=True)

    def nothing_handler(self, evt):
        pass

    def save_game(self, evt):
        # save player's record
        self.load_game_btn.text = 'LOAD GAME'
        if self.be_clicked(self.save_progress_btn, evt):
            with shelve.open(self.record, 'c') as db:
                db['map'] = self.battle_field
                db['level'] = self.cur_level
                db['location'] = self.player.location
                db['score'] = self.score
                # save map
                soft_wall, hard_wall, green_land = list(), list(), list()
                for sprite in self.soft_wall_group.sprites():
                    soft_wall.append(sprite.location)
                for sprite in self.hard_wall_group.sprites():
                    hard_wall.append(sprite.location)
                for sprite in self.green_land_group.sprites():
                    green_land.append(sprite.location)
                db['soft_wall'] = soft_wall
                db['hard_wall'] = hard_wall
                db['green_land'] = green_land
                # save npc things
                npc, bullet, bombs = list(), list(), list()
                for sprite in self.npc_tanks.sprites():
                    if sprite.bullet:
                        npc.append({'location': sprite.location,
                                    'direction': sprite.direction,
                                    'bullet':
                                        {'location': sprite.bullet.location,
                                         'direction': sprite.bullet.direction,
                                         }})
                for sprite in self.bullet_list.sprites():
                    bullet.append({'location': sprite.location,
                                   'direction': sprite.direction})
                for sprite in self.bombs.sprites():
                    bombs.append({'pos': sprite.pos,
                                  'bomb_num': sprite.bomb_num})
                db['npc_tank'] = npc
                db['bullet'] = bullet
                db['bomb'] = bombs
            self.intro = True
            self.screen = display.set_mode(self.size)
            self.clear_all_sprites()

    def back_intro(self, evt):
        if self.be_clicked(self.back_btn, evt):
            self.intro = True
            self.screen = display.set_mode(self.size)
            self.clear_all_sprites()

    def record_hover(self, btn, evt):
        if evt.type == MOUSEMOTION:
            btn.on_button(evt.pos)
        elif evt.type == MOUSEBUTTONDOWN:
            self.click_down_pos = evt.pos

    def be_clicked(self, btn, evt):
        self.record_hover(btn, evt)
        if evt.type == MOUSEBUTTONUP:
            if btn.hover and btn.on_button(
                    evt.pos):
                return True
        return False

    def last_level_btn_handler(self, evt):
        if self.be_clicked(self.last_level_btn, evt):
            if self.edit_old_level_btn.value > 1:
                self.edit_old_level_btn.value -= 1

    def next_level_btn_handler(self, evt):
        if self.be_clicked(self.next_level_btn, evt):
            if self.edit_old_level_btn.value < self.game_levels:
                self.edit_old_level_btn.value += 1

    def edit_old_level(self, evt):
        # handler edit old level
        if self.be_clicked(self.edit_old_level_btn, evt):
            # load old map
            level = self.edit_old_level_btn.value
            self.editing_level = level
            self.editing_data_map = self.get_level_map(level)

    def new_level_handler(self, evt):
        if self.be_clicked(self.new_level_btn, evt):
            self.editing_level = self.game_levels + 1
            self.editing_tool = None
            self.editing_data_map = DataMap(
                self.width // self.min_unit_size,
                self.height // self.min_unit_size)

    def exit_edit_handler(self, evt):
        if self.be_clicked(self.exit_edit_btn, evt):
            self.editing_tool = None
            self.edit = False
            self.intro = True
            # resize
            self.screen = display.set_mode(self.size)
            display.set_caption('坦克大战')

    def hard_wall_handler(self, evt):
        if self.be_clicked(self.hard_wall_btn, evt):
            # change tool
            self.editing_tool = MapItem.hard_wall

    def soft_wall_handler(self, evt):
        if self.be_clicked(self.soft_wall_btn, evt):
            self.editing_tool = MapItem.soft_wall

    def green_land_handler(self, evt):
        if self.be_clicked(self.green_land_btn, evt):
            self.editing_tool = MapItem.green_land

    def empty_handler(self, evt):
        if self.be_clicked(self.empty_btn, evt):
            self.editing_tool = MapItem.empty

    def tank_handler(self, evt):
        if self.be_clicked(self.tank_btn, evt):
            self.editing_tool = MapItem.tank

    def save_level_handler(self, evt):
        if self.be_clicked(self.save_level_btn, evt):
            if self.save():
                self.editing_data_map = None

    @property
    def game_levels(self):
        with shelve.open(self.map_file, 'c') as db:
            level_list = [k for k in db.keys()]
        return len(level_list)

    def get_level_map(self, n):
        with shelve.open(self.map_file, 'c') as db:
            return db.get(str(n))

    def save(self):
        if self.editing_data_map.is_empty():
            return False

        if not self.editing_data_map.is_connected():
            return False

        with shelve.open(self.map_file, 'c') as db:
            db[str(self.editing_level)] = self.editing_data_map
        self.edit_old_level_btn.value = self.editing_level
        return True

    def edit_area_handler_event(self, evt):

        if evt.type == MOUSEBUTTONDOWN and evt.button == 1:
            x, y = evt.pos
            if x < self.width - self.min_unit_size and \
                    y < self.height - self.min_unit_size and \
                    isinstance(self.editing_tool, MapItem):
                self.drawing = True
                x, y = x + self.min_unit_size // 2, y + self.min_unit_size // 2
                x_index = x // self.min_unit_size
                y_index = y // self.min_unit_size
                self.editing_data_map.set(x_index, y_index,
                                          self.editing_tool)

        elif evt.type == MOUSEBUTTONUP:
            self.drawing = False

        elif evt.type == MOUSEMOTION:
            x, y = evt.pos
            if self.drawing and isinstance(self.editing_tool, MapItem):
                if x < self.width - self.min_unit_size and \
                        y < self.height - self.min_unit_size:
                    x = x + self.min_unit_size // 2
                    y = y + self.min_unit_size // 2
                    x_index = x // (self.tank_size // 2)
                    y_index = y // (self.tank_size // 2)
                    self.editing_data_map.set(x_index, y_index,
                                              self.editing_tool)

    def init_player(self) -> None:
        start_pos = [(self.width - self.tank_size) // 2,
                     self.height - self.tank_size]
        player = Player(start_pos, self.bullet_list, self.screen,
                        max_w=self.width, max_h=self.height)
        self.player_group.empty()
        self.player_group.add(player)

    def refresh_player(self) -> None:
        start_pos = [(self.width - self.tank_size) // 2,
                     self.height - self.tank_size]
        player = Player(start_pos, self.bullet_list, self.screen,
                        max_w=self.height, max_h=self.width)
        self.player_group.add(player)

    def start(self) -> None:
        while True:
            self.game_loop()
            self.clock.tick(10)  # 每秒循环10次

    @staticmethod
    def end() -> None:
        game_quit()
        sys.exit()

    def game_loop(self) -> None:

        # 监听用户事件
        for evt in event.get():
            if evt.type == QUIT:
                self.end()
            if self.intro:

                for btn in self.intro_button_list:
                    btn.handler_event(evt)
            elif self.edit:
                self.edit_area_handler_event(evt)
                for btn in self.edit_button_list:
                    btn.handler_event(evt)

            elif not self.player_group and self.cur_level <= self.game_levels:
                # game over
                self.handler_click(evt)
            elif self.cur_level <= self.game_levels and len(
                    self.player_group) == 1:
                # playing
                for btn in self.playing_btn:
                    btn.handler_event(evt)
            else:
                # stage clear
                btns = [self.back_btn]
                for btn in btns:
                    btn.handler_event(evt)

        if self.intro:
            self.draw_intro()
        elif self.edit:
            self.draw_edit()
        elif len(
                self.player_group) == 0 and self.cur_level <= self.game_levels:
            self.draw_game_over()
            mixer_music.stop()

        else:

            keys = key.get_pressed()
            self.handler_user_input(keys)
            if not mixer_music.get_busy():
                if not debug:
                    mixer_music.play(-1)
            # draw map

            if self.cur_level > self.game_levels:
                finished = self.draw_stage_clear()
                self.draw_level_clear_btn()

            else:
                self.draw_playing()
                self.draw_game_area()
                self.compute_bullet_pos()

                self.collision_detect()
                self.compute_npc_tank_pos()
                self.compute_player_tank_pos(keys)

                self.bombs.update()
        self.finish()

    @staticmethod
    def finish() -> None:
        display.update()

    # def gen_tank(self) -> None:
    #     if len(self.npc_tanks) == 0:
    #         for i in range(5):
    #             self.npc_tanks.add(
    #                 Tank(self.screen, self.npc_bullets, max_w=self.width,
    #                      max_h=self.height))

    def collision_detect(self) -> None:
        # NPC坦克之间的碰撞检测
        for i, tankA in enumerate(self.npc_tanks):
            for j, tankB in enumerate(self.npc_tanks):
                if i >= j:
                    continue
                else:
                    # 碰撞逻辑， A的下一步会和B的下一步重合

                    if collide_mask(tankA.next_tank,
                                    tankB.next_tank):
                        tankA.direction = (tankA.direction + 2) % 4
                        tankB.direction = (tankA.direction + 2) % 4

    def compute_player_tank_pos(self, keys) -> None:
        """
        更新玩家状态并绘画
        :param keys:
        :return:
        """
        if self.player:
            self.player.update(keys)
            self.player.draw()

    def compute_bullet_pos(self) -> None:
        """
        更新子弹状态并绘画
        :return:
        """
        if len(self.bullet_list) and len(self.soft_wall_group):
            # player bullet hit soft wall
            groupcollide(self.bullet_list, self.soft_wall_group,
                         dokilla=True, dokillb=True, collided=self.play_bomb)
        if len(self.bullet_list) and len(self.hard_wall_group):
            # player bullet hit hard wall
            groupcollide(self.bullet_list, self.hard_wall_group,
                         dokilla=True, dokillb=False, collided=self.play_bomb)
        if len(self.npc_bullets) and len(self.soft_wall_group):
            # npc bullet hit soft wall
            groupcollide(self.npc_bullets, self.soft_wall_group,
                         dokilla=True, dokillb=True, collided=self.play_bomb)
        if len(self.npc_bullets) and len(self.hard_wall_group):
            # npc bullet hit hard wall
            groupcollide(self.npc_bullets, self.hard_wall_group,
                         dokilla=True, dokillb=False, collided=self.play_bomb)
        if len(self.bullet_list) and len(self.npc_bullets):
            # npc和玩家的子弹互相抵消
            groupcollide(self.npc_bullets, self.bullet_list,
                         dokilla=True, dokillb=True)

        if len(self.bullet_list) != 0:
            # 玩家子弹和NPC坦克的碰撞检测
            groupcollide(self.bullet_list, self.npc_tanks,
                         dokilla=True, dokillb=True,
                         collided=self.play_bomb)
            self.bullet_list.update()
            self.bullet_list.draw(self.screen)
        if len(self.npc_bullets) != 0:
            # npc子弹和玩家坦克的碰撞检测
            groupcollide(self.npc_bullets, self.player_group,
                         dokilla=True, dokillb=True,
                         collided=self.play_bomb)
            self.npc_bullets.update()
            self.npc_bullets.draw(self.screen)

    def play_bomb(self, obj_a: Bullet, obj_b: Sprite) -> bool:
        if collide_rect(obj_a, obj_b):
            self.bombs.add(
                Bomb((obj_a.rect.left, obj_a.rect.top), self.screen))
            if not debug:
                self.bomb_sound.play()
            if isinstance(obj_b, SoftWall):
                x, y = obj_b.location[0] // self.min_unit_size, obj_b.location[
                    1] // self.min_unit_size
                self.battle_field.set(x, y, MapItem.empty)
            if obj_a.type == 'user' and isinstance(obj_b, Tank):
                self.score += 10
                if len(self.npc_tanks) == 1:
                    self.cur_level += 1
                    self.battle_field = self.get_level_map(self.cur_level)
                    self.load_level()
                    self.init_player()
            return True
        return False

    def compute_npc_tank_pos(self) -> None:
        self.npc_tanks.update(self.player, self.battle_field)
        self.npc_tanks.draw(self.screen)

    def detect_if_quit(self, keys) -> None:

        if keys[K_ESCAPE]:
            self.end()

    def handler_user_input(self, keys) -> None:
        self.detect_if_quit(keys)
        if self.player:
            if keys[K_j]:
                bullet = self.player.shot()
                if bullet:
                    self.bullet_list.add(bullet)
            if keys[K_w]:
                self.player.turn_up(self.battle_field)
            if keys[K_a]:
                self.player.turn_left(self.battle_field)
            if keys[K_s]:
                self.player.turn_down(self.battle_field)
            if keys[K_d]:
                self.player.turn_right(self.battle_field)

    def replay(self):
        self.refresh_player()
        self.bullet_list.empty()
        self.npc_bullets.empty()
        self.bombs.empty()

    def handler_click(self, evt):
        if evt.type == MOUSEBUTTONDOWN:
            x, y = evt.pos
            if self.player:
                pass
            elif self.replay_btn_top <= y <= self.replay_btn_down \
                    and self.replay_btn_left <= x <= self.replay_btn_right:
                self.replay()

    def draw_game_over(self):
        self.screen.fill(self.wincolor)
        # `game over`
        font = SysFont("Arial", self.font_size)
        text = ' Game Over '
        ren = font.render(text, 0, self.fg, self.bg)
        left = self.screen.get_rect().width / 2 - ren.get_rect().width / 2
        self.screen.blit(ren, (left, 200))
        # `play again`
        font = SysFont("Arial", self.smaller_font_size)
        text = 'play again?'
        ren = font.render(text, 0, self.fg, self.bg)
        self.replay_btn_left = (self.screen.get_width() - ren.get_width()) / 2
        self.replay_btn_right = ren.get_width() + self.replay_btn_left
        self.replay_btn_down = ren.get_height() + self.replay_btn_top

        self.screen.blit(ren, (self.replay_btn_left, self.replay_btn_top))

    def draw_intro(self):
        self.screen.fill(self.wincolor)
        for btn in self.intro_button_list:
            btn.draw()

    def draw_playing(self):
        self.screen.fill(self.wincolor)
        self.playing_area = Surface(self.size)
        self.playing_area.fill(self.black)

        self.screen.blit(self.playing_area, (0, 0))
        # button
        self.score_btn.text = "Score: {}".format(self.score)
        self.status_btn.text = "Level: {}".format(self.cur_level)

        self.playing_btn = [self.score_btn, self.status_btn,
                            self.save_progress_btn]
        # draw btn
        start_x, start_y = self.width, 0
        for btn in self.playing_btn:
            btn.y = start_y
            btn.x = self.width + (self.playing_win_size[
                                      0] - self.width - btn.rect.width) // 2
            start_y += btn.rect.height + 10
            btn.draw()

    def draw_level_clear_btn(self):
        btns = [self.back_btn]
        # draw btn
        start_x, start_y = self.width, 0
        for btn in btns:
            btn.y = start_y
            btn.x = self.width + (self.playing_win_size[
                                      0] - self.width - btn.rect.width) // 2
            start_y += btn.rect.height + 10
            btn.draw()

    def draw_edit(self):

        self.screen.fill(self.wincolor)
        self.edit_area = Surface(self.size)

        self.edit_area.fill(self.black)

        if not self.editing_data_map:
            if self.game_levels == 0:
                self.status_btn.text = "no level create one!"
                self.edit_button_list = [self.status_btn, self.new_level_btn,
                                         self.exit_edit_btn]
            else:
                self.status_btn.text = " total {} level".format(
                    self.game_levels)
                self.edit_old_level_btn.text = "edit level {}".format(
                    self.edit_old_level_btn.value)
                self.edit_button_list = [self.status_btn, self.last_level_btn,
                                         self.edit_old_level_btn,
                                         self.next_level_btn,
                                         self.new_level_btn,
                                         self.exit_edit_btn]

        else:
            if self.editing_data_map.is_empty():
                self.status_btn.text = 'map is empty!'
            elif not self.editing_data_map.is_connected():
                self.status_btn.text = 'empty is not connected!'
            else:
                self.status_btn.text = "editing level {}".format(
                    self.editing_level)

            self.edit_button_list = [self.status_btn, self.hard_wall_btn,
                                     self.soft_wall_btn,
                                     self.green_land_btn, self.empty_btn,
                                     self.tank_btn, self.save_level_btn,
                                     self.exit_edit_btn]
            # draw map
            self.draw_edit_area(self.edit_area, self.editing_data_map)
            # draw map on screen

        self.screen.blit(self.edit_area, (0, 0))

        # draw cursor
        x, y = mouse.get_pos()
        max_x = self.width - self.min_unit_size
        max_y = self.height - self.min_unit_size
        if x <= max_x and y <= max_y:
            cursor_img = None
            if self.editing_tool == MapItem.hard_wall:

                cursor_img = self.hard_wall
            elif self.editing_tool == MapItem.soft_wall:
                cursor_img = self.soft_wall
            elif self.editing_tool == MapItem.green_land:
                cursor_img = self.green_land
            elif self.editing_tool == MapItem.empty:
                cursor_img = self.empty
            elif self.editing_tool == MapItem.tank:
                cursor_img = self.tank
            else:
                pass
            if cursor_img:
                mouse.set_visible(False)
                self.screen.blit(cursor_img, (x, y))
            else:
                mouse.set_visible(True)
        else:
            mouse.set_visible(True)

        # draw btn
        start_x, start_y = self.width, 0
        for btn in self.edit_button_list:
            btn.y = start_y
            btn.x = self.width + (self.edit_win_size[
                                      0] - self.width - btn.rect.width) // 2
            start_y += btn.rect.height + 10
            btn.draw()

    def draw_edit_area(self, surface: Surface, data_map):

        for y_num in range(data_map.height):
            for x_num in range(data_map.width):
                item = data_map.get(x_num, y_num)
                cur_img = {
                    MapItem.hard_wall: self.hard_wall,
                    MapItem.green_land: self.green_land,
                    MapItem.soft_wall: self.soft_wall,
                    MapItem.tank: self.tank
                }.get(item, None)
                if cur_img:
                    surface.blit(source=cur_img, dest=(
                        x_num * self.min_unit_size,
                        y_num * self.min_unit_size))

        return

    def draw_stage_clear(self):

        actually_pos = [self.draw_pos[0] * Tank.tank_size,
                        self.draw_pos[1] * Tank.tank_size]
        if self.draw_pos == (0, 0):
            self.battle_field.set(x=self.draw_pos[0], y=self.draw_pos[1],
                                  val=MapItem.dummy)
            self.player_group.add(
                Player(actually_pos, self.bullet_list, self.screen,
                       max_w=self.width, max_h=self.height,
                       direction=self.draw_direction))
        full = True
        for y in range(self.battle_field.height):
            for x in range(self.battle_field.width):
                item = self.battle_field.get(x, y)
                if item == MapItem.empty:
                    full = False
                    break
            if not full:
                break
        if not full:
            x, y = self.draw_pos
            direction = self.draw_direction
            if direction == Direction.right:
                next_pos = x + 1, y
            elif direction == Direction.down:
                next_pos = x, y + 1
            elif direction == Direction.left:
                next_pos = x - 1, y
            else:
                next_pos = x, y - 1

            x1, y1 = next_pos

            if 0 <= x1 < self.battle_field.width \
                    and 0 <= y1 < self.battle_field.height \
                    and self.battle_field.get(*next_pos) == MapItem.empty:
                self.draw_pos = next_pos

            else:
                direction = Direction((direction + 1) % 4)
                if direction == Direction.right:
                    next_pos = x + 1, y
                elif direction == Direction.down:
                    next_pos = x, y + 1
                elif direction == Direction.left:
                    next_pos = x - 1, y
                else:
                    next_pos = x, y - 1
                self.draw_pos = next_pos
                self.draw_direction = direction
            actually_pos = [self.draw_pos[0] * Tank.tank_size,
                            self.draw_pos[1] * Tank.tank_size]
            if self.draw_pos != (0, 0):
                self.battle_field.set(x=self.draw_pos[0], y=self.draw_pos[1],
                                      val=MapItem.dummy)
                self.player_group.add(
                    Player(actually_pos, self.bullet_list, self.screen,
                           max_w=self.width, max_h=self.height,
                           direction=self.draw_direction))
        self.screen.fill(self.wincolor)
        draw_area = Surface(self.size)

        draw_area.fill(self.black)
        self.screen.blit(draw_area, (0, 0))
        for player in self.player_group.sprites():
            player.draw()
        return full

    def draw_game_area(self):
        self.green_land_group.update()
        self.soft_wall_group.update()
        self.hard_wall_group.update()

    @property
    def hard_wall(self):
        if not self._hard_wall:
            self._hard_wall = image.load('img/map/hard_wall.png')
        return self._hard_wall

    @property
    def soft_wall(self):
        if not self._soft_wall:
            self._soft_wall = image.load('img/map/soft_wall.png')
        return self._soft_wall

    @property
    def green_land(self):
        if not self._green_land:
            self._green_land = image.load('img/map/green_land.png')
        return self._green_land

    @property
    def empty(self):
        if not self._empty:
            self._empty = image.load('img/map/empty.png')
        return self._empty

    @property
    def tank(self):
        if not self._tank:
            self._tank = image.load('img/tank-up.png')
        return self._tank


if __name__ == '__main__':
    game = Game()
    game.start()
