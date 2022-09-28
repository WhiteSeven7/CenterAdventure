import itertools
import os
import json
import sys
from math import ceil
from random import randint
from random import sample, choice
from typing import Tuple, Union

import pygame

screen_size = (400, 600)
full_size = (500, 750)
display_size = (1600, 900)
triple_size = (1280, 720)  # 显示器尺寸的80%
brick_len = 40
FPS = 60


def get_asset(path=None):
    if path is None:
        asset = {
            'player': {
                'image': {
                    'up': pygame.image.load('image/player/up.png'),
                    'down': pygame.image.load('image/player/down.png'),
                    'left': pygame.image.load('image/player/left.png'),
                    'right': pygame.image.load('image/player/right.png')
                }
            },
            'brick': {
                'soil': {},
                'stone': {}
            }
        }
        ...


def pixel_units(gird_pos: list[int, int]) -> list[int, int]:
    """将gird_pos（格子位置）换算成pos（像素位置）"""
    x = gird_pos[0] * brick_len
    y = gird_pos[1] * brick_len
    return [x, y]


def play_sound(sound: Tuple[pygame.mixer.Sound, ...]) -> None:
    """播放给定音效包的随机音效"""
    sound[randint(0, len(sound) - 1)].play()


def write_archive(archive: dict):
    """将内存中的存档，以文件形式保存在硬盘"""
    with open('archive.json', 'w') as f:
        f.write(json.dumps(archive, indent=2))


def read_archive() -> dict:
    """从硬盘读取存档，储存在内内存中"""
    if not os.path.exists('archive.json'):
        return {}
    with open('archive.json', 'r') as f:
        archive = json.loads(str_) if (str_ := f.read()) else {}
    return archive


def get_relative_pos(pos_: list[int, int]) -> tuple:
    """
    用于获得在屏幕上绘制的位置
    :rtype: object
    :param pos_: pos（像素位置）
    :return: rect.top_left（屏幕位置）
    """
    return pos_[0], pos_[1] - Player.get_inst().pos[1] + Player.get_inst().offset


def _get_pla(player: 'Player') -> dict:
    return {
        'gird_pos': player.gird_pos,
        'pos': player.pos,
        'status': player.status,
        'health': player.health,
        'on_brick': player.on_brick,
        'move_time': player.move_time,
        'destroy_time': player.destroy_time,
        'offset': player.offset,
        'at_sub': player.at_sub,
        'moving': player.moving,
        'moving_u': player.moving_u
    }


def _get_bri(brick: Union['Soil', 'Stone', int]) -> Union[int, Tuple[int, int], None]:
    if type(brick) == int:
        return None
    elif hasattr(brick, 'health'):
        return brick.color, brick.health
    else:
        return brick.color


def _get_cry(cry: 'Crystal') -> dict:
    return {'color': cry.color, 'gird_pos': cry.gird_pos, 'pos': cry.pos, 'on_brick': cry.on_brick}


def _get_fra(sprite) -> dict:
    fra: 'Fragment' = sprite
    return {'color': fra.color, 'pos': fra.pos, 'speed': fra.speed, 'vertical_speed': fra.vertical_speed,
            'stepx': fra.stepx, 'stepy': fra.stepy}


def _get_lev() -> int:
    return 1 if Level.get_inst().status == 0 else Level.get_inst().status


def get_archive() -> dict:
    """获取存档，并储存在内存中"""
    player = Player.get_inst()
    bricks = Bricks.get_inst()
    crystals = Crystals.get_inst()
    backpack = Backpack.get_inst()
    fragments = Fragments.get_inst()
    return {
        'player': _get_pla(player),
        'bricks': {
            'b_list2': [list(map(_get_bri, bricks.b_list2[_])) for _ in range(10)],
            'floor': bricks.floor,
            'colors': bricks.colors
        },
        'crystals': list(map(_get_cry, crystals.group)),
        'backpack': [cry.num for cry in backpack.bag_crystals],
        'fragments': list(map(_get_fra, fragments.sprites()))
    }


def get_archives() -> dict:
    dict_ = get_archive()
    dict_['level_status'] = _get_lev()
    return dict_


def load_cry(data: dict):
    cry = Crystal(data['color'], data['gird_pos'])
    cry.pos = data['pos']
    cry.on_brick = data['on_brick']
    return cry


class Player:
    _instance: 'Player' = None

    def __new__(cls, *args, **kwargs):
        # 1.判断类属性是否为空对象，若为空说明第一个对象还没被创建
        if cls._instance is None:
            # 2.对第一个对象没有被创建，我们应该调用父类的方法，为第一个对象分配空间
            cls._instance = super().__new__(cls)
        # 3.把类属性中保存的对象引用返回给python的解释器
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    def __init__(self, gx: int, gy: int):
        self.gird_pos = [gx, gy]
        self.pos = pixel_units(self.gird_pos)
        self.status = 'down'
        self.image_dict = {
            'up': pygame.image.load('image/player/up.png').convert_alpha(),
            'down': pygame.image.load('image/player/down.png').convert_alpha(),
            'left': pygame.image.load('image/player/left.png').convert_alpha(),
            'right': pygame.image.load('image/player/right.png').convert_alpha()
        }
        self.image = self.image_dict[self.status]
        self.rect = self.image.get_rect()
        self.health = 255
        self.on_brick = False
        # 移动、破坏方块冷却
        self.move_cool = 18
        self.move_time = 2 * self.move_cool
        self.destroy_cool = 15
        self.destroy_time = 2 * self.destroy_cool
        # 偏移，player相对于窗口最上顶的距离
        self.offset = 7 * brick_len
        # 玩家是否到这一层底部。
        self.at_sub = False
        self.moving: int = 0  # 0：不动，1：左，2：右
        self.moving_u = False
        # 速度、下落速度，单位是每帧移动像素数。
        self.speed = 4
        self.fall_speed = 4
        self.off_speed = 3

    def load(self, data: dict):
        self.gird_pos = data['gird_pos']
        self.pos = data['pos']
        self.status = data['status']
        self.health = data['health']
        self.on_brick = data['on_brick']
        self.destroy_time = data['destroy_time']
        self.offset = data['offset']
        self.at_sub = data['at_sub']
        self.moving = data['moving']
        self.moving_u = data['moving_u']

    def destroy_begin(self):
        self.destroy_time = self.destroy_cool

    def move_begin(self):
        self.move_time = self.move_cool

    def destroy(self, status: str):
        Level.get_inst().input_idle = 0
        if self.destroy_time != 0:
            return
        self.destroy_begin()
        # 以下为根据player方向改变
        if status == 'left' and Bricks.c_get_brick(self.gird_pos[0] - 1, self.gird_pos[1]):
            Bricks.get_inst().destroy_brick(self.gird_pos[0] - 1, self.gird_pos[1])
        elif status == 'right' and Bricks.c_get_brick(self.gird_pos[0] + 1, self.gird_pos[1]):
            Bricks.get_inst().destroy_brick(self.gird_pos[0] + 1, self.gird_pos[1])
        elif status == 'up' and Bricks.c_get_brick(self.gird_pos[0], self.gird_pos[1] - 1):
            Bricks.get_inst().destroy_brick(self.gird_pos[0], self.gird_pos[1] - 1)
        elif status == 'down' and Bricks.c_get_brick(self.gird_pos[0], self.gird_pos[1] + 1):
            Bricks.get_inst().destroy_brick(self.gird_pos[0], self.gird_pos[1] + 1)
        else:
            return
        self.health -= 1

    def input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.destroy(self.status)
        if keys[pygame.K_UP]:
            self.status = 'up'
            Level.get_inst().input_idle = 0
        elif keys[pygame.K_DOWN]:
            self.status = 'down'
            Level.get_inst().input_idle = 0
        if keys[pygame.K_LEFT]:
            self.decide_move_left()
        elif keys[pygame.K_RIGHT]:
            self.decide_move_right()

    # 是否触地的检测，由fall调用
    def _detect_on_break(self):
        self.on_brick = True if self.moving_u else bool(Bricks.c_get_brick(self.gird_pos[0], self.gird_pos[1] + 1))

    # 落入下一格，由fall调用
    def _fall_next(self):
        if not self.on_brick:
            if self.pos[1] < (self.gird_pos[1] + 1) * brick_len:
                self.pos[1] += self.fall_speed
            else:
                self.gird_pos[1] += 1
                self.pos[1] = self.gird_pos[1] * brick_len

    def fall(self):
        self._detect_on_break()
        self._fall_next()

    # 向右向移动决定，由input调用
    def decide_move_right(self):
        self.status = 'right'
        if self.move_time == 0 and self.gird_pos[0] < 9 and self.on_brick:
            if not Bricks.c_get_brick(self.gird_pos[0] + 1, self.gird_pos[1]):
                self.moving = 2
            elif not Bricks.c_get_brick(self.gird_pos[0] + 1, self.gird_pos[1] - 1) \
                    and not Bricks.c_get_brick(self.gird_pos[0], self.gird_pos[1] - 1):
                self.moving = 2
                self.moving_u = True
            self.move_begin()
        Level.get_inst().input_idle = 0

    # 向左方向移动决定，由input调用
    def decide_move_left(self):
        self.status = 'left'
        if self.move_time == 0 and self.gird_pos[0] > 0 and self.on_brick:
            if not Bricks.c_get_brick(self.gird_pos[0] - 1, self.gird_pos[1]):
                self.moving = 1
            elif not Bricks.c_get_brick(self.gird_pos[0] - 1, self.gird_pos[1] - 1) \
                    and not Bricks.c_get_brick(self.gird_pos[0], self.gird_pos[1] - 1):
                self.moving = 1
                self.moving_u = True
            self.move_begin()
        Level.get_inst().input_idle = 0

    # 向右移动，由move调用
    def move_right(self):
        if self.pos[0] < (self.gird_pos[0] + 1) * brick_len:
            self.pos[0] += self.speed  # 最后一个100是帧率
        else:
            self.moving = 0
            self.gird_pos[0] += 1
            self.pos[0] = self.gird_pos[0] * brick_len

    # 向左移动，由move调用
    def move_left(self):
        if self.pos[0] > (self.gird_pos[0] - 1) * brick_len:
            self.pos[0] -= self.speed  # 最后一个100是帧率
        else:
            self.moving = 0
            self.gird_pos[0] -= 1
            self.pos[0] = self.gird_pos[0] * brick_len

    # 向上移动，由move调用
    def move_up(self):
        if self.pos[1] > (self.gird_pos[1] - 1) * brick_len:
            self.pos[1] -= self.speed
        else:
            self.moving_u = False
            self.gird_pos[1] -= 1
            self.pos[1] = self.gird_pos[1] * brick_len

    def move(self):
        if self.moving == 2:
            self.move_right()
        elif self.moving == 1:
            self.move_left()
        if self.moving_u:
            self.move_up()

    def set_offset(self):
        if self.at_sub:
            # 2 状态
            if self.gird_pos[1] >= 92:
                self.offset = max(self.pos[1] - 85 * brick_len, 7 * brick_len)
            # 2 -> 1 状态
            elif self.offset > 7 * brick_len:
                self.offset -= self.off_speed
            else:
                # 正式进入 1
                self.at_sub = False
                self.offset = 7 * brick_len
        # 1 -> 2
        elif self.gird_pos[1] >= 92:
            self.at_sub = True

    def cooling_down(self):
        self.move_time -= 1
        self.move_time = max(self.move_time, 0)
        self.destroy_time -= 1
        self.destroy_time = max(self.destroy_time, 0)

    def draw(self, surface: pygame.Surface):
        self.image = self.image_dict[self.status]
        self.rect.topleft = get_relative_pos(self.pos)
        surface.blit(self.image, self.rect)

    def update(self):
        self.fall()
        self.move()
        self.set_offset()
        self.cooling_down()


class Brick:
    def __init__(self, color: int, gird_pos: list[int, int]):
        self.color: int = color
        self.gird_pos = gird_pos
        self.pos = pixel_units(gird_pos)
        # 所属的链，用于连锁破坏。0代表不属于任何链
        self.belong_chain = 0


class Soil(Brick):
    soil_image: Tuple[pygame.Surface] = (
        pygame.image.load('image/brick/red.png'),
        pygame.image.load('image/brick/yellow.png'),
        pygame.image.load('image/brick/green.png'),
        pygame.image.load('image/brick/blue.png'),
        pygame.image.load('image/brick/purple.png'),
        pygame.image.load('image/brick/orange.png'),
        pygame.image.load('image/brick/pink.png'),
        pygame.image.load('image/brick/indigo.png'),
    )
    sub_image: pygame.Surface = pygame.image.load('image/brick/sub_brick.png')

    def __init__(self, color: int, gird_pos: list[int, int]):
        super().__init__(color, gird_pos)
        if self.color == 31:
            self.image = self.__class__.sub_image.convert()
        else:
            self.image = self.__class__.soil_image[self.color].convert()
        self.rect = self.image.get_rect()

    def draw(self, surface: pygame.Surface):
        self.rect.topleft = get_relative_pos(self.pos)
        surface.blit(self.image, self.rect)


class Stone(Brick):
    images: Tuple[pygame.Surface] = (
        pygame.image.load('image/brick/stone/Stone5-1.png'),
        pygame.image.load('image/brick/stone/Stone5-2.png'),
        pygame.image.load('image/brick/stone/Stone5-3.png'),
        pygame.image.load('image/brick/stone/Stone5-4.png'),
        pygame.image.load('image/brick/stone/Stone5-5.png')
    )

    def __init__(self, color: int, gird_pos: list[int, int]):
        super().__init__(color, gird_pos)
        self.health = 5
        self.image = self.__class__.images[self.health - 1].convert()
        self.rect = self.image.get_rect()

    def draw(self, surface: pygame.Surface):
        self.image = self.__class__.images[self.health - 1].convert()
        self.rect.topleft = get_relative_pos(self.pos)
        surface.blit(self.image, self.rect)


def create_brick(color: int, gird_pos: [int, int]):
    return Stone(color, gird_pos) if color == 8 else Soil(color, gird_pos)


class Bricks:
    _instance: 'Bricks' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    @classmethod
    def c_get_brick(cls, gx: int, gy: int) -> Union['Soil', 'Stone', None, int]:
        """
        为了区分该方法与对象的get_brick方法，在函数名开头加c，表示是类方法
        :param gx:
        :param gy:
        :return:
        """
        return cls._instance.get_brick(gx, gy)

    def __init__(self):
        # 添加brick发生在level的set_floor里
        self.b_list2: list[list[Union['Soil', 'Stone', int]]] = []
        self.chain2: list[list['Soil', 'Stone']] = []
        self.chain_order = 0
        # 层数
        self.floor = 0
        self.colors: list[int, ...] = sample(range(9), 5)
        # 设置音效
        self.soil_sound = (
            pygame.mixer.Sound('sound/soil/01.wav'),
            pygame.mixer.Sound('sound/soil/02.wav'),
            pygame.mixer.Sound('sound/soil/03.wav'),
            pygame.mixer.Sound('sound/soil/04.wav')
        )
        self.stone_sound = (
            pygame.mixer.Sound('sound/stone/01.wav'),
            pygame.mixer.Sound('sound/stone/02.wav'),
            pygame.mixer.Sound('sound/stone/03.wav'),
            pygame.mixer.Sound('sound/stone/04.wav')
        )
        self.broken_sound = (
            pygame.mixer.Sound('sound/stone/broken/01.wav'),
            pygame.mixer.Sound('sound/stone/broken/02.wav')
        )
        self.set_volumes()

    # 设置音量
    def set_volumes(self):
        for sound_ in self.soil_sound:
            sound_.set_volume(0.3)
        for sound_ in self.stone_sound:
            sound_.set_volume(0.5)
        for sound_ in self.broken_sound:
            sound_.set_volume(0.3)

    def load_bricks(self, b_list2_):
        for gx, list1_ in enumerate(b_list2_):
            b_list1: list[Union['Soil', 'Stone', int]] = []
            for gy, brick_ in enumerate(list1_):
                if type(brick_) == int:
                    brick = create_brick(brick_, [gx, gy])
                elif type(brick_) in (list, tuple):
                    brick = create_brick(brick_[0], [gx, gy])
                    brick.health = brick_[1]
                else:
                    brick = 0
                b_list1.append(brick)
            self.b_list2.append(b_list1)

    def load(self, data: dict):
        self.floor = data['floor']
        self.colors = data['colors']
        self.load_bricks(data['b_list2'])
        self.update_chain2()

    # 返回指定brick
    def get_brick(self, gx: int, gy: int) -> Union['Soil', 'Stone', None, int]:
        return self.b_list2[gx][gy] if 0 <= gx <= 9 and 0 <= gy <= 99 else None

    # 摧毁单个，无视血量。在血量<=0时或使用水晶时调用，调用前要先判断是否为0
    def destroy_one(self, gx: int, gy: int):
        aim_brick = self.b_list2[gx][gy]
        # 产生粒子
        if not aim_brick:
            return
        Fragment.produce(aim_brick.color, aim_brick.pos)
        self.b_list2[gx][gy] = 0

    # 摧毁石头，由destroy_brick调用
    def destroy_stone_chain1(self, chain1: list['Stone', ...]):
        # 扣血
        be_broken = False
        for brick in chain1:
            brick.health -= 1
            if brick.health <= 0:
                be_broken = True
                self.destroy_one(brick.gird_pos[0], brick.gird_pos[1])
        # 播放声音
        if be_broken:
            play_sound(self.broken_sound)
        else:
            play_sound(self.stone_sound)

    # 玩家摧毁方块，调用前要先判断是否为0
    def destroy_brick(self, gx: int, gy: int):
        chain1 = self.chain2[self.b_list2[gx][gy].belong_chain]
        if isinstance(chain1[0].color, Stone):
            stone_chain1: list['Stone', ...] = chain1
            self.destroy_stone_chain1(stone_chain1)
        else:
            if chain1[0].color == 31:
                Level.get_inst().need_next = True
            for brick in chain1:
                self.destroy_one(brick.gird_pos[0], brick.gird_pos[1])
            play_sound(self.soil_sound)

    # 通过update_chain1调用，为一个chain1（不是chain2）添加所有应添加的brick，并更新这些brick的belong_chain
    def update_chain1(self, gx: int, gy: int, ch_index: int):
        # 赋值
        self.b_list2[gx][gy].belong_chain = ch_index
        self.chain2[ch_index].append(self.b_list2[gx][gy])
        color = self.b_list2[gx][gy].color

        # 链锁赋值判定
        # 左。不是左边界，左边是brick，左边颜色和自己相同，左边没chain
        if gx > 0 and self.b_list2[gx - 1][gy] \
                and self.b_list2[gx - 1][gy].color == color \
                and not self.b_list2[gx - 1][gy].belong_chain:
            self.update_chain1(gx - 1, gy, ch_index)

        # 右
        if gx < len(self.b_list2) - 1 and self.b_list2[gx + 1][gy] \
                and self.b_list2[gx + 1][gy].color == color \
                and not self.b_list2[gx + 1][gy].belong_chain:
            self.update_chain1(gx + 1, gy, ch_index)

        # 上
        if gy > 0 and self.b_list2[gx][gy - 1] \
                and self.b_list2[gx][gy - 1].color == color \
                and not self.b_list2[gx][gy - 1].belong_chain:
            self.update_chain1(gx, gy - 1, ch_index)

        # 下
        if gy < len(self.b_list2[gx]) - 1 and self.b_list2[gx][gy + 1] \
                and self.b_list2[gx][gy + 1].color == color \
                and not self.b_list2[gx][gy + 1].belong_chain:
            self.update_chain1(gx, gy + 1, ch_index)

    # 更新chain2
    def update_chain2(self):
        # 初始化
        if not self.b_list2:
            return
        self.chain_order = 0
        # chain2的每一个元素为chain1
        self.chain2 = [None]
        for gx, _ in enumerate(self.b_list2):
            for gy, brick in enumerate(_):
                if not brick or brick.belong_chain:
                    continue
                self.chain_order += 1
                self.chain2.append([])
                self.update_chain1(gx, gy, self.chain_order)

    def update(self):
        ...
        # for _ in self.b_list2:
        #     for brick in _:
        #         if brick:
        #             brick.update()
        # self.update_chain2()

    def draw(self, surface: pygame.Surface):
        for _ in self.b_list2:
            for brick in _:
                if brick:
                    brick.draw(surface)


class Fragment(pygame.sprite.Sprite):
    f_kind = (
        pygame.image.load('image/fragment/red.png'),
        pygame.image.load('image/fragment/yellow.png'),
        pygame.image.load('image/fragment/green.png'),
        pygame.image.load('image/fragment/blue.png'),
        pygame.image.load('image/fragment/purple.png'),
        pygame.image.load('image/fragment/orange.png'),
        pygame.image.load('image/fragment/pink.png'),
        pygame.image.load('image/fragment/indigo.png'),
        pygame.image.load('image/fragment/stone_five.png')
    )

    @classmethod
    def produce(cls, color: int, pos: list[int, int]):
        if color != 31:
            cls(color, pos)
            cls(color, pos)

    def __init__(self, color: int, pos: list[int, int]):
        super().__init__(Fragments.get_inst())
        self.color = color
        # pos为中心位置，要传入stone.pos
        self.pos = [pos[0] + brick_len // 2, pos[1] + brick_len // 2]
        self.image = self.__class__.f_kind[color]
        self.rect = self.image.get_rect()
        self.speed = randint(-7, 7) * 5
        self.vertical_speed = 0
        self.stepx = 0
        self.stepy = 0
        self.gravity = 3

    def miss(self):
        if self.rect.y >= screen_size[1] + 50:
            self.kill()

    def move_x(self):
        self.stepx += self.speed
        if self.stepx // 10 != 0:
            self.pos[0] += self.stepx // 10
            self.stepx -= self.stepx // 10 * 10

    def move_y(self):
        self.vertical_speed += self.gravity
        self.stepy += self.vertical_speed
        if self.stepy // 10 != 0:
            self.pos[1] += self.stepy // 10
            self.stepy %= 10

    def move(self):
        self.move_x()
        self.move_y()
        self.rect.center = get_relative_pos(self.pos)

    def update(self):
        self.miss()
        self.move()


class Fragments(pygame.sprite.Group):
    _instance: 'Fragments' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    def load(self, data: list[dict]):
        for fra_ in data:
            fra = Fragment(fra_['color'], fra_['pos'])
            fra.speed = fra_['speed']
            fra.vertical_speed = fra_['vertical_speed']
            fra.stepx = fra_['stepx']
            fra.stepy = fra_['stepy']
            self.add(fra)


class Crystal:
    c_kind = (
        pygame.image.load('image/crystal/CrystalRed.png'),
        pygame.image.load('image/crystal/CrystalYellow.png'),
        pygame.image.load('image/crystal/CrystalGreen.png'),
        pygame.image.load('image/crystal/CrystalBlue.png'),
        pygame.image.load('image/crystal/CrystalPurple.png'),
        pygame.image.load('image/crystal/CrystalOrange.png'),
        pygame.image.load('image/crystal/CrystalPink.png'),
        pygame.image.load('image/crystal/CrystalIndigo.png'),
        pygame.image.load('image/crystal/Crystal_stone_five.png')
    )

    def __init__(self, color: int, gird_pos: list[int, int]):
        Crystals.get_inst().group.append(self)
        self.color = color
        self.gird_pos: list[int, int] = gird_pos
        self.pos = pixel_units(self.gird_pos)
        self.image = self.__class__.c_kind[self.color].convert_alpha()
        self.rect = self.image.get_rect()
        # 吸收音效
        self.eat_sound = (
            pygame.mixer.Sound('sound/crystal/get/01.wav'),
            pygame.mixer.Sound('sound/crystal/get/02.wav'),
            pygame.mixer.Sound('sound/crystal/get/03.wav'),
            pygame.mixer.Sound('sound/crystal/get/04.wav')
        )
        for sound_ in self.eat_sound:
            sound_.set_volume(0.8)
        self.on_brick = True
        self.fall_speed = 4

    # 玩家吸收水晶
    def be_eaten(self):
        # 玩家处在水晶的位置，且背包未满
        if self.gird_pos == Player.get_inst().gird_pos and \
                Backpack.get_inst().crystal_num < Backpack.get_inst().max_value:
            # 向背包里添加水晶
            Backpack.get_inst().add_crystal(self.color, 1)
            # 移除场地的水晶
            Crystals.get_inst().group.remove(self)
            # 播放吸收音效
            play_sound(self.eat_sound)

    # 是否触地的检测，由fall调用
    def detect_on_break(self):
        self.on_brick = bool(Bricks.c_get_brick(self.gird_pos[0], self.gird_pos[1] + 1))

    # 落入下一格，由fall调用
    def fall_next(self):
        if not self.on_brick:
            if self.pos[1] < (self.gird_pos[1] + 1) * brick_len:
                self.pos[1] += self.fall_speed
            else:
                self.gird_pos[1] += 1
                self.pos[1] = self.gird_pos[1] * brick_len

    # 下落模块，由update调用
    def fall(self):
        self.detect_on_break()
        self.fall_next()

    def draw(self, surface: pygame.Surface):
        self.rect.topleft = get_relative_pos(self.pos)
        surface.blit(self.image, self.rect)

    def update(self):
        self.be_eaten()
        self.fall()


class Crystals:
    _instance: 'Crystals' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    def __init__(self):
        self.group: list['Crystal'] = []

    def load(self, data: list[dict]):
        self.group = list(map(load_cry, data))

    def update(self):
        for crystal_ in self.group:
            crystal_.update()

    def draw(self, surface):
        for crystal_ in self.group:
            crystal_.draw(surface)


class BagCrystal:
    c_kind = Crystal.c_kind

    def __init__(self, color: int):
        self.color = color
        self.num = 1
        self.font = pygame.font.SysFont('方正粗黑宋简体', 40)
        self.icon_image = self.__class__.c_kind[self.color].convert_alpha()
        self.icon_rect: pygame.Rect = self.icon_image.get_rect(
            topleft=(30 + self.color % 2 * 150, 30 + self.color // 2 * 75))
        self.num_image = self.font.render(str(self.num), True, (0, 0, 0))
        self.num_rect = self.num_image.get_rect(center=(self.icon_rect.right + 30, self.icon_rect.centery))
        if self.color == 8:
            self.sound = (
                pygame.mixer.Sound('sound/stone/broken/01.wav'),
                pygame.mixer.Sound('sound/stone/broken/02.wav')
            )
        else:
            self.sound = (
                pygame.mixer.Sound('sound/soil/01.wav'),
                pygame.mixer.Sound('sound/soil/02.wav'),
                pygame.mixer.Sound('sound/soil/03.wav'),
                pygame.mixer.Sound('sound/soil/04.wav')
            )
        for _ in self.sound:
            _.set_volume(0.3)

    # 用水晶破坏方块，由magic调用
    def crystal_destroy(self):
        have_brick = False
        for x, y in itertools.product(range(10), range(-7, 8)):
            d_brick = Bricks.c_get_brick(x, Player.get_inst().gird_pos[1] + y)
            # destroyed_brick可能为0（空位置），或者None（边界外），要先判断
            if d_brick and d_brick.color == self.color:
                have_brick = True
                Bricks.get_inst().destroy_one(x, Player.get_inst().gird_pos[1] + y)
        if have_brick:
            play_sound(self.sound)

    # 使用水晶
    def magic(self):
        if self.num <= 0:
            return
        self.num -= 1
        self.crystal_destroy()

    def update(self):
        self.num_image = self.font.render(str(self.num), True, (0, 0, 0))
        self.num_rect = self.num_image.get_rect(center=(self.icon_rect.right + 30, self.icon_rect.centery))

    def draw(self, surface: pygame.Surface):
        surface.blit(self.icon_image, self.icon_rect)
        surface.blit(self.num_image, self.num_rect)


class Backpack:
    _instance: 'Backpack' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    def __init__(self):
        self.image = pygame.image.load('image/backpack.png').convert()
        self.image_copy = self.image.copy()
        self.rect = self.image.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2))
        self.bag_crystals: list['BagCrystal'] = [BagCrystal(_) for _ in range(9)]
        self.selection = 0
        self.arrow_image = pygame.image.load('image/arrow.png').convert_alpha()
        self.arrow_rect: pygame.Rect = self.arrow_image.get_rect(
            midright=self.bag_crystals[self.selection].icon_rect.midleft)
        self.max_value = 32
        self.crystal_num = 0

    def load(self, data: list[int]):
        for order, num in enumerate(data):
            self.bag_crystals[order].num = num

    def re_init(self):
        self.selection = 0
        self.arrow_rect = self.bag_crystals[self.selection].icon_rect.midleft

    def correct_selection(self):
        """
        矫正selection的值
        :return: None
        """
        if self.selection < 0:
            self.selection += len(self.bag_crystals)
        elif self.selection >= len(self.bag_crystals):
            self.selection -= len(self.bag_crystals)
        self.arrow_rect.midright = self.bag_crystals[self.selection].icon_rect.midleft

    def select(self, key: int):
        if key == pygame.K_ESCAPE:
            Level.get_inst().status = 1 if Level.get_inst().status == 2 else 0
        elif key == pygame.K_z:
            Level.get_inst().status = 0
        elif key == pygame.K_SPACE:
            self.bag_crystals[self.selection].magic()
            Level.get_inst().status = 0
            Player.get_inst().destroy_begin()
        elif key == pygame.K_UP:
            self.selection -= 2
        elif key == pygame.K_DOWN:
            self.selection += 2
        elif key == pygame.K_LEFT:
            self.selection -= 1
        elif key == pygame.K_RIGHT:
            self.selection += 1
        else:
            return
        self.correct_selection()

    def add_crystal(self, color: int, number: int):
        self.bag_crystals[color].num += number

    def update(self):
        self.crystal_num = 0
        for bag_crystal in self.bag_crystals:
            self.crystal_num += bag_crystal.num
            bag_crystal.update()

    def draw(self, surface: pygame.Surface):
        self.image_copy = self.image.copy()
        for bag_crystal in self.bag_crystals:
            bag_crystal.draw(self.image_copy)
        self.image_copy.blit(self.arrow_image, self.arrow_rect)
        surface.blit(self.image_copy, self.rect)


class PauseButton:
    def __init__(self, name: str, order: int):
        self.image = pygame.image.load(f'image/pause/{name}.png')
        self.rect = self.image.get_rect(midtop=(PauseMenu.half_width(), 70 + order * 55))


class PauseButtons:
    def __init__(self):
        self.group: list['PauseButton'] = [PauseButton('back', 0), PauseButton('bag', 1), PauseButton('menu', 2)]

    def get_pos(self) -> list[Tuple[int, int]]:
        return [bon.rect.midleft for bon in self.group]

    def draw(self, surface: pygame.Surface):
        surface.blits([(bon.image, bon.rect) for bon in self.group], False)


class PauseMenu:
    _instance: 'PauseMenu' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def half_width(cls) -> int:
        return cls._instance.rect.width // 2

    def __init__(self):
        self.image = pygame.image.load('image/pause/background.png').convert_alpha()
        self.image_copy = self.image.copy()
        self.rect = self.image.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2))
        self.buttons = PauseButtons()
        self.buttons_pos = self.buttons.get_pos()
        self.selection = 0
        self.arrow_image = pygame.image.load('image/arrow.png')
        self.a_rect = self.arrow_image.get_rect(midright=self.buttons_pos[self.selection])
        self.a_speed = -1

    def re_init(self):
        self.selection = 0
        self.a_rect = self.arrow_image.get_rect(midright=self.buttons_pos[self.selection])

    def _press_button(self):
        if self.selection == 0:
            Level.get_inst().status = 0
            Player.get_inst().destroy_begin()
        elif self.selection == 1:
            Level.get_inst().status = 2
            Backpack.get_inst().selection = 0
        elif self.selection == 2:
            Game.get_inst().status = 0

    def select(self, key: int):
        if key == pygame.K_ESCAPE:
            Level.get_inst().status = 0
        elif key == pygame.K_SPACE:
            self._press_button()
        elif key == pygame.K_UP:
            self.selection -= 1
        elif key == pygame.K_DOWN:
            self.selection += 1
        else:
            return
        self.selection %= 3
        self.a_rect = self.arrow_image.get_rect(midright=self.buttons_pos[self.selection])

    def swing(self):
        self.a_rect.x += self.a_speed
        if 0 <= self.buttons_pos[self.selection][0] - self.a_rect.right <= self.a_rect.width // 2:
            return
        self.a_speed *= -1

    def update(self):
        self.swing()

    def draw(self, surface: pygame.Surface):
        self.image_copy = self.image.copy()
        self.buttons.draw(self.image_copy)
        self.image_copy.blit(self.arrow_image, self.a_rect)
        surface.blit(self.image_copy, self.rect)


class CaverFra(pygame.sprite.Sprite):
    f_kind = Fragment.f_kind

    @classmethod
    def produce(cls, color: int, pos: list[int, int], creator: 'ScreenSaver'):
        if color != 31:
            cls(color, pos, creator)
            cls(color, pos, creator)

    def __init__(self, color: int, pos: list[int, int], creator: 'ScreenSaver'):
        super().__init__(creator.fra_s)
        self.color = color
        self.image = self.__class__.f_kind[color]
        self.rect = self.image.get_rect(center=pos)
        self.speed = randint(-7, 7) * 5
        self.vertical_speed = 0
        self.stepx = 0
        self.stepy = 0
        self.gravity = 3

    def miss(self):
        if self.rect.y >= screen_size[1] + 50:
            self.kill()

    def move(self):
        self.stepx += self.speed
        if self.stepx // 10 != 0:
            self.rect.x += self.stepx // 10
            self.stepx -= self.stepx // 10 * 10
        self.vertical_speed += self.gravity
        self.stepy += self.vertical_speed
        if self.stepy // 10 != 0:
            self.rect.y += self.stepy // 10
            self.stepy %= 10

    def update(self):
        self.miss()
        self.move()


class SaverBrick:
    images: Tuple[pygame.Surface, ...] = Soil.images + Stone.images

    @staticmethod
    def random_pos(size: Tuple[int, int]) -> Tuple[int, int]:
        if randint(0, 1):
            x = choice([-25, 25])
            y = choice(range(-25, size[1] + 25))
        else:
            x = choice(range(-25, size[0] + 25))
            y = choice([-25, 25])
        return x, y

    @staticmethod
    def set_speed(pos: Tuple[int, int]) -> Tuple[int, int]:
        if pos[0] <= 0:
            sx = randint(1, 2)
        elif pos[0] >= screen_size[0]:
            sx = randint(-2, -1)
        else:
            sx = choice([-2, -1, 1, 2])
        if pos[1] <= 0:
            sy = randint(1, 2)
        elif pos[1] >= screen_size[1]:
            sy = randint(-2, -1)
        else:
            sy = choice([-2, -1, 1, 2])
        return sx, sy

    def __init__(self, creator: 'ScreenSaver'):
        """boundary的可选项"""
        self.creator = creator
        self.creator.group.append(self)
        self.color = randint(0, 8)
        self.image: pygame.Surface = self.__class__.images[self.color]
        self.rect = self.image.get_rect(center=self.__class__.random_pos(creator.size))
        self.speed_x, self.speed_y = self.__class__.set_speed(self.rect.center)

    def change(self):
        """撞到边界变向"""
        if self.rect.left < 0 and self.speed_x < 0 or self.rect.right > self.creator.size[0] and self.speed_x > 0:
            self.speed_x = -self.speed_x
            self.broken()
        if self.rect.top < 0 and self.speed_y < 0 or self.rect.bottom > self.creator.size[1] and self.speed_y > 0:
            self.speed_y = -self.speed_y
            self.broken()

    def move(self):
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

    def broken(self):
        """随机损坏，在碰到边界时调用"""
        max_ = max(20 - len(self.creator.group), 0)
        if not randint(0, max_):
            CaverFra.produce(self.color, [self.rect.centerx, self.rect.centery], self.creator)
            self.creator.del_g.append(self)

    def update(self):
        self.change()
        self.move()

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)


class ScreenSaver:
    @classmethod
    def change(cls, size: Tuple[int, int], alpha: int):
        inst: 'ScreenSaver' = cls(size)
        inst.alpha = alpha
        Level.get_inst().cv_copy = pygame.Surface(size)
        return inst

    def __init__(self, size: Tuple[int, int]):
        self.group: list['SaverBrick'] = []
        self.size = size
        self.canvas = pygame.Surface(size)
        self.del_g: list['SaverBrick'] = []
        self.fra_s = pygame.sprite.Group()
        self.alpha = 0
        self.ap_speed = 1
        self.alpha_max = 255

    def random_add(self):
        """随机生成砖块"""
        if not randint(0, len(self.group) * 5):
            SaverBrick(self)

    def remove_brick(self):
        """移除砖块"""
        for bri in self.del_g:
            self.group.remove(bri)
        self.del_g.clear()

    def appear(self):
        if self.alpha < self.alpha_max:
            self.alpha += self.ap_speed
            self.alpha = min(self.alpha, self.alpha_max)

    def draw(self, surface: pygame.Surface):
        self.canvas.fill('black')
        for s_brick in self.group:
            s_brick.draw(self.canvas)
        self.fra_s.draw(self.canvas)
        if self.alpha < self.alpha_max:
            self.canvas.set_alpha(self.alpha)
        surface.blit(self.canvas, (0, 0))

    def update(self):
        self.appear()
        self.random_add()
        for s_brick in self.group:
            s_brick.update()
        self.fra_s.update()
        self.remove_brick()


class Info:
    def __init__(self, creator: 'Level'):
        self.creator = creator
        self.font = pygame.font.SysFont('', 40)
        self.hp_bg1 = pygame.rect.Rect(0, 0, 120, 40)
        self.hp_bg2 = self.hp_bg1.inflate(-10, -10)
        self.hp_image = self.font.render(f'HP: {self.creator.player.health}', True, 'black')
        self.hp_rect = self.hp_image.get_rect(center=self.hp_bg2.center)
        self.dp_bg1 = pygame.rect.Rect(screen_size[0] - 120, 0, 120, 40)
        self.dp_bg2 = self.dp_bg1.inflate(-10, -10)
        self.dp_value = (creator.bricks.floor - 1) * 100 + self.creator.player.gird_pos[1] + 1
        self.dp_image = self.font.render(f'DP: {self.dp_value}', True, 'black')
        self.dp_rect = self.dp_image.get_rect(center=self.dp_bg1.center)

    def draw(self, surface):
        # HP
        pygame.draw.rect(surface, 'black', self.hp_bg1)
        pygame.draw.rect(surface, 'white', self.hp_bg2)
        surface.blit(self.hp_image, self.hp_rect)
        # DP
        pygame.draw.rect(surface, 'black', self.dp_bg1)
        pygame.draw.rect(surface, 'white', self.dp_bg2)
        surface.blit(self.dp_image, self.dp_rect)

    def update(self):
        # HP
        self.hp_image = self.font.render(f'HP: {self.creator.player.health}', True, 'black')
        self.hp_rect = self.hp_image.get_rect(center=self.hp_bg2.center)
        # DP
        self.dp_value = (self.creator.bricks.floor - 1) * 100 + self.creator.player.gird_pos[1] + 1
        self.dp_image = self.font.render(f'DP: {self.dp_value}', True, 'black')
        self.dp_rect = self.dp_image.get_rect(center=self.dp_bg1.center)


class SmallMap:
    bri_images: Tuple[pygame.Surface, ...] = (
        pygame.image.load('image/map/brick/red.png'),
        pygame.image.load('image/map/brick/yellow.png'),
        pygame.image.load('image/map/brick/green.png'),
        pygame.image.load('image/map/brick/blue.png'),
        pygame.image.load('image/map/brick/purple.png'),
        pygame.image.load('image/map/brick/orange.png'),
        pygame.image.load('image/map/brick/pink.png'),
        pygame.image.load('image/map/brick/indigo.png'),
        pygame.image.load('image/map/brick/stone.png')
    )
    cry_images: Tuple[pygame.Surface, ...] = (
        pygame.image.load('image/map/crystal/red.png'),
        pygame.image.load('image/map/crystal/yellow.png'),
        pygame.image.load('image/map/crystal/green.png'),
        pygame.image.load('image/map/crystal/blue.png'),
        pygame.image.load('image/map/crystal/purple.png'),
        pygame.image.load('image/map/crystal/orange.png'),
        pygame.image.load('image/map/crystal/pink.png'),
        pygame.image.load('image/map/crystal/indigo.png'),
        pygame.image.load('image/map/crystal/stone.png')
    )

    def __init__(self, creator: 'Level'):
        self.creator = creator
        self.image = pygame.Surface((70, 665))
        self.rect = self.image.get_rect(center=(full_size[0] // 2, full_size[1] // 2))
        self.group2: list[list[Union[int, None]]] = []
        self.flash = 6
        self.player_rect = pygame.Rect(self.creator.player.gird_pos[0] * 7, self.creator.player.gird_pos[1] * 7, 7, 7)
        self.update_time = 0
        self.update_cool = 10
        self._update_map()
        self._update_player()

    def _update_map(self):
        self.group2.clear()
        for g1 in self.creator.bricks.b_list2:
            group1 = []
            for bri in g1:
                if bri == 0:
                    group1.append(None)
                elif bri.color != 31:
                    group1.append(bri.color)
            self.group2.append(group1)
        for cry in self.creator.crystals.group:
            self.group2[cry.gird_pos[0]][cry.gird_pos[1]] = cry.color + 32

    def _update_player(self):
        self.player_rect.x = self.creator.player.gird_pos[0] * 7
        self.player_rect.y = self.creator.player.gird_pos[1] * 7

    def update(self):
        self.update_time += 1
        if self.update_time >= self.update_cool:
            self.update_time = 0
            self.flash -= 1
            if self.flash <= 0:
                self.flash = 6
            self._update_map()
            self._update_player()

    def _draw_map(self):
        for gx, group1 in enumerate(self.group2):
            for gy, color in enumerate(group1):
                if color is None:
                    continue
                if color < 32:
                    self.image.blit(self.__class__.bri_images[color], (gx * 7, gy * 7))
                else:
                    self.image.blit(self.__class__.cry_images[color - 32], (gx * 7, gy * 7))

    def draw(self, surface: pygame.Surface):
        self.image.fill('black')
        self._draw_map()
        if self.flash > 3:
            pygame.draw.rect(self.image, 'white', self.player_rect)
        surface.blit(self.image, self.rect)


class Level:
    _instance: Union['Level', None] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    @classmethod
    def enter(cls):
        instance: 'Level' = cls()
        if Game.get_inst().archive:
            cls._instance.load(Game.get_inst().archive)
        return instance

    def __init__(self):
        self.player = Player(randint(0, 9), -1)
        self.bricks = Bricks()
        self.crystals = Crystals()
        if not Game.get_inst().archive:
            self.set_floor()
        self.backpack = Backpack()
        self.fragments = Fragments()
        self.info = Info(self)
        self.need_next = False
        self.status: int = 0
        self.pause_menu = PauseMenu()
        self.input_idle = 0
        self.sleep_time = 3600
        self.screensaver: Union['ScreenSaver', None] = None
        self.background = pygame.image.load('image/background.png')
        self.bg_large = pygame.transform.scale(self.background, full_size)
        self.canvas = pygame.Surface(screen_size)
        self.triple_black = pygame.Surface(triple_size)
        self.cv_copy = self.canvas.copy()
        self.canvas0 = pygame.Surface(screen_size)
        self.canvas1 = pygame.Surface(screen_size)
        self.canvas2 = pygame.Surface(screen_size)
        self.small_map = SmallMap(self)

    def load(self, archive: dict):
        self.player.load(archive['player'])
        self.bricks.load(archive['bricks'])
        self.crystals.load(archive['crystals'])
        self.backpack.load(archive['backpack'])
        self.fragments.load(archive['fragments'])
        if 'level_status' in archive:
            self.status = archive['level_status']

    def _set_bricks_crystals(self):
        """产生砖块，水晶"""
        self.bricks.b_list2.clear()
        self.crystals.group.clear()
        for gx in range(10):
            b_list1: list[Union['Soil', 'Stone', int]] = []
            for gy in range(100):
                if 95 <= gy < 100:
                    b_list1.append(create_brick(31, [gx, gy]))
                elif randint(0, 99):
                    b_list1.append(create_brick(choice(self.bricks.colors), [gx, gy]))
                else:
                    b_list1.append(0)
                    Crystal(choice(self.bricks.colors), [gx, gy])
            self.bricks.b_list2.append(b_list1)

    def set_floor(self):
        """产生砖块，水晶和砖块的chain"""
        self.bricks.colors = sample(range(9), 5)
        self.bricks.floor += 1
        self._set_bricks_crystals()
        # 设定chain
        self.bricks.update_chain2()

    def next_floor(self):
        """生成下一层"""
        if not self.need_next:
            return
        self.need_next = False
        self._fireworks()
        # 改变玩家位置
        self.player.gird_pos[1] = -6
        self.player.pos = pixel_units(self.player.gird_pos)
        # 重置floor
        self.set_floor()

    def _fireworks(self):
        """目前仅用于在换层时产生粒子效果"""
        for _, __ in itertools.product(range(9), range(-5, -1)):
            Fragment.produce(choice(self.bricks.colors), [_ * brick_len, __ * brick_len])

    def _input_s0(self, key: int):
        """statues是0时的操作"""
        if key == pygame.K_ESCAPE:
            self.status = 1
            self.pause_menu.re_init()
        elif key == pygame.K_z:
            self.status = 3

    def _input_status(self, key: int):
        """依照关卡的不同状态，使用不同组件的控制"""
        if self.status == 0:
            self._input_s0(key)
        elif self.status == 1:
            self.pause_menu.select(key)
        elif self.status in [2, 3]:
            self.backpack.select(key)

    def input(self):
        """包含所有可控制组件的控制模块：level，backpack，player"""
        for event in Game.events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key != pygame.K_F4:
                self.input_idle = 0
            if self.screensaver:
                self.player.move_begin()
                self.player.destroy_begin()
                return
            self._input_status(event.key)
        if self.status == 0:
            self.player.input()

    def _saver_draw_small(self, screen: pygame.Surface):
        if self.screensaver.alpha < 255:
            self.cv_copy = self.canvas.copy()
        self.screensaver.draw(self.cv_copy)
        screen.blit(self.cv_copy, (0, 0))

    def _saver_draw_full(self):
        if self.screensaver.alpha < 255:
            self.cv_copy = self.triple_black.copy()
            self.cv_copy.blit(pygame.transform.scale(self.canvas0, screen_size), (20, 60))
            self.cv_copy.blit(self.canvas1, (440, 60))
            self.cv_copy.blit(self.canvas2, (860, 60))
        self.screensaver.draw(self.cv_copy)

    def _draw_screen(self, screen: pygame.Surface):
        self.canvas = self.background.copy()
        self.bricks.draw(self.canvas)
        self.crystals.draw(self.canvas)
        self.player.draw(self.canvas)
        self.fragments.draw(self.canvas)
        self.info.draw(self.canvas)
        if self.status == 1:
            self.pause_menu.draw(self.canvas)
        if self.status in [2, 3]:
            self.backpack.draw(self.canvas)
        screen.blit(self.canvas, (0, 0))

    def _draw_face0(self, face: pygame.Surface):
        self.canvas0 = self.bg_large.copy()
        self.small_map.draw(self.canvas0)
        face.blit(self.canvas0, (0, 0))

    def _draw_face1(self, face: pygame.Surface):
        self.canvas1 = self.background.copy()
        self.bricks.draw(self.canvas1)
        self.crystals.draw(self.canvas1)
        self.player.draw(self.canvas1)
        self.fragments.draw(self.canvas1)
        self.info.draw(self.canvas1)
        face.blit(pygame.transform.scale(self.canvas1, full_size), (0, 0))

    def _draw_face2(self, face: pygame.Surface):
        self.canvas2 = self.background.copy()
        if self.status == 1:
            self.pause_menu.draw(self.canvas2)
        if self.status in [2, 3]:
            self.backpack.draw(self.canvas2)
        face.blit(pygame.transform.scale(self.canvas2, full_size), (0, 0))

    def _draw_faces(self, faces: Tuple[pygame.Surface, ...]):
        self._draw_face0(faces[0])
        self._draw_face1(faces[1])
        self._draw_face2(faces[2])

    def draw(self, canvas: Union[pygame.Surface, Tuple[pygame.Surface, ...]]):
        if not self.screensaver:
            if type(canvas) == pygame.Surface:
                self._draw_screen(canvas)
            elif type(canvas) == tuple:
                self._draw_faces(canvas)
        elif type(canvas) == pygame.Surface:
            self._saver_draw_small(canvas)
        elif type(canvas) == tuple:
            self._saver_draw_full()

    def _sleep(self, full_status: bool):
        """判定和执行睡眠"""
        self.input_idle += 1
        if self.input_idle < self.sleep_time:
            return
        self.input_idle = self.sleep_time
        if full_status:
            if not self.screensaver:
                self.screensaver = ScreenSaver(triple_size)
            elif self.screensaver.size != triple_size:
                self.screensaver = ScreenSaver.change(triple_size, self.screensaver.alpha)
        elif not self.screensaver:
            self.screensaver = ScreenSaver(screen_size)
        elif self.screensaver.size != screen_size:
            self.screensaver = ScreenSaver.change(screen_size, self.screensaver.alpha)

    def _wake(self):
        """判定和退出睡眠"""
        if self.input_idle == 0:
            self.screensaver = None

    def _update(self):
        self._wake()
        self._sleep(Game.whether_full())
        if not self.screensaver:
            if self.status == 1:
                self.pause_menu.update()
            else:
                self.bricks.update()
                self.crystals.update()
                self.fragments.update()
                self.player.update()
            self.info.update()
            self.backpack.update()
        else:
            self.screensaver.update()

    def _update_full(self):
        if self.status == 0:
            self.small_map.update()

    def update(self):
        self._update()
        if Game.whether_full():
            self._update_full()

    def run(self, canvas: pygame.Surface):
        self.input()
        self.update()
        self.draw(canvas)
        self.next_floor()


class MenuAnimation:
    a_kind: Tuple[pygame.Surface, ...] = Brick.soil_image + Brick.stone_image + Fragment.f_kind + Crystal.c_kind

    def __init__(self):
        self.image = choice(self.__class__.a_kind).convert_alpha()
        self.image.set_alpha(127)
        self.side = choice(('left', 'right'))
        self.rect = self.image.get_rect(center=(0, randint(-20, screen_size[1] + 20)))
        if self.side == 'left':
            self.rect.centerx = -30
        elif self.side == 'right':
            self.rect.centerx = screen_size[0] + 30
        # speed_l代表该速度为每100秒移动的像素数
        self.speed_l = randint(10, 20) * 10
        self._step = 0

    def move(self):
        self._step += self.speed_l
        if self._step >= 100:
            if self.side == 'left':
                self.rect.centerx += self._step // 100
            elif self.side == 'right':
                self.rect.centerx -= self._step // 100
            self._step %= 100

    def kill(self):
        if -50 <= self.rect.centerx <= screen_size[0] + 50:
            return
        MenuAnimations.get_group().remove(self)

    def update(self):
        self.move()
        self.kill()


class MenuAnimations:
    _instance: Union['MenuAnimations', None] = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_group(cls):
        return cls._instance.a_group

    def __init__(self):
        self.a_group: list['MenuAnimation'] = []

    def update(self):
        if not randint(0, 99):
            self.a_group.append(MenuAnimation())
        for anim in self.a_group:
            anim.update()

    def draw(self, surface: pygame.Surface):
        for anim in self.a_group:
            surface.blit(anim.image, anim.rect)


class LogoBrick:
    @staticmethod
    def order_path(order: int) -> str:
        if order == 0:
            return '1/'
        elif order == 3:
            return '2/'
        elif order == 4:
            return '3/'
        elif order == 7:
            return '4/'
        else:
            return '0/'

    def __init__(self, order: int, color: int):
        """依照序号和颜色产生logo上的砖块"""
        self.image = pygame.image.load(f'image/menu/logos/{self.__class__.order_path(order)}{color}.png')
        self.rect = self.image.get_rect(topleft=(60 + order // 2 * 70, 70 + order % 2 * 70))

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)


class Logo:
    def __init__(self):
        """speed: 进入或消失时的移动速度（不是消失速度）"""
        self.image = pygame.image.load('image/menu/logos/bg.png')
        self.rect = self.image.get_rect(center=(screen_size[0] // 2, 140))
        self.bricks: Tuple['LogoBrick', ...] = tuple(LogoBrick(o, c) for o, c in enumerate(Game.get_inst().logo_color))
        self.speed = 2
        if Game.get_inst().bug_pos:
            self.b_image = pygame.transform.flip(
                pygame.image.load('image/menu/player_l.png').convert_alpha(), True, False)
            self.b_rect = self.b_image.get_rect(center=self.bricks[6].rect.topright)
        else:
            self.b_image = pygame.image.load('image/menu/player_l.png').convert_alpha()
            self.b_rect = self.b_image.get_rect(center=self.bricks[0].rect.topleft)
        self.distance = self.speed * ceil(255 / Menu.get_inst().ah_speed)

    def enter(self):
        self.rect.y -= self.distance
        self.b_rect.y -= self.distance
        for lb in self.bricks:
            lb.rect.y -= self.distance

    def disappear(self):
        self.rect.y -= self.speed
        self.b_rect.y -= self.speed
        for lb in self.bricks:
            lb.rect.y -= self.speed

    def appear(self):
        self.rect.y += self.speed
        self.b_rect.y += self.speed
        for lb in self.bricks:
            lb.rect.y += self.speed

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)
        surface.blit(self.b_image, self.b_rect)
        for lb in self.bricks:
            lb.draw(surface)


class Button:
    def __init__(self, name: str, order: int):
        """:param name: 只填不带后缀的文件名"""
        self.image = pygame.image.load(f'image/menu/{name}.png').convert_alpha()
        self.rect = self.image.get_rect(center=(screen_size[0] // 2, screen_size[1] // 2 + order * 100))


class Buttons:
    def __init__(self, speed: int):
        """这里的speed是移动的速度"""
        self.group: list['Button'] = [Button('old_play', 0), Button('new_play', 1), Button('quit', 2)]
        self.speed = speed

    def get_pos(self) -> list[Tuple[int, int]]:
        """一个列表，其中元素为每个按钮的左中位置(x, y)"""
        return [button.rect.midleft for button in self.group]

    def draw(self, surface: pygame.Surface):
        for button in self.group:
            surface.blit(button.image, button.rect)

    def enter(self, dis: int):
        for bon in self.group:
            bon.rect.y += dis

    def disappear(self):
        for bon in self.group:
            bon.rect.y += self.speed

    def appear(self):
        for bon in self.group:
            bon.rect.y -= self.speed


class ButtonComplex:
    _instance: 'ButtonComplex' = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    def __init__(self):
        self.selection = 0
        # 消失或进入时的移动速度
        self.speed = 2
        self.buttons = Buttons(self.speed)
        self.buttons_pos = self.buttons.get_pos()
        self.arrow_image = pygame.image.load('image/menu/arrow.png').convert_alpha()
        self.a_rect = self.arrow_image.get_rect(midright=self.buttons_pos[self.selection])
        self.a_speed = -1
        self.distance = self.speed * ceil(255 / Menu.get_inst().ah_speed)

    def _press_button(self):
        """按下按钮"""
        if self.selection in (0, 1):
            Menu.get_inst().need_disappear = True
        elif self.selection == 2:
            write_archive(Game.get_inst().archive)
            pygame.quit()
            sys.exit()

    def _correct_selection(self):
        self.selection %= len(self.buttons_pos)
        self.a_rect.midright = self.buttons_pos[self.selection]

    def select(self):
        for event in Game.events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_SPACE:
                self._press_button()
                return
            if event.key == pygame.K_UP:
                self.selection -= 1
            elif event.key == pygame.K_DOWN:
                self.selection += 1
            else:
                return
            self._correct_selection()

    def swing(self):
        self.a_rect.x += self.a_speed
        if 0 <= self.buttons_pos[self.selection][0] - self.a_rect.right <= self.a_rect.width // 2:
            return
        self.a_speed *= -1

    def enter(self):
        self.a_rect.y += self.distance
        self.buttons.enter(self.distance)

    def disappear(self):
        self.a_rect.y += self.speed
        self.buttons.disappear()
        self.buttons_pos = self.buttons.get_pos()

    def appear(self):
        self.a_rect.y -= self.speed
        self.buttons.appear()
        self.buttons_pos = self.buttons.get_pos()

    def update(self):
        self.select()
        self.swing()

    def draw(self, surface: pygame.Surface):
        self.buttons.draw(surface)
        surface.blit(self.arrow_image, self.a_rect)


class Menu:
    _instance: 'Menu' = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    @classmethod
    def enter(cls):
        inst = cls()
        inst.logo.enter()
        inst.bon_cx.enter()
        inst.alpha = 0
        return inst

    def __init__(self):
        self.ah_speed = 3
        self.need_disappear = False
        self.animations = MenuAnimations()
        self.logo = Logo()
        self.bon_cx = ButtonComplex()
        self.background = pygame.image.load('image/background.png').convert_alpha()
        self.bg_copy = self.background.copy()
        self.alpha: int = 255

    def dec_alpha(self):
        self.alpha -= self.ah_speed
        if self.alpha <= 0:
            self.alpha = 0
            if self.bon_cx.selection == 1:
                Game.get_inst().archive.clear()
            Game.get_inst().status = 1

    def inc_alpha(self):
        self.alpha += self.ah_speed
        self.alpha = min(self.alpha, 255)

    def disappear(self):
        if self.alpha > 0:
            self.dec_alpha()
            self.logo.disappear()
            self.bon_cx.disappear()

    def appear(self):
        if self.alpha < 255:
            self.inc_alpha()
            self.logo.appear()
            self.bon_cx.appear()

    def _draw_face(self, surface: pygame.Surface):
        self.bg_copy = self.background.copy()
        self.animations.draw(self.bg_copy)
        self.logo.draw(self.bg_copy)
        self.bon_cx.draw(self.bg_copy)
        if self.alpha < 255:
            self.bg_copy.set_alpha(self.alpha)
        if Game.whether_full():
            self.bg_copy = pygame.transform.scale(self.bg_copy, full_size)
        surface.blit(self.bg_copy, (0, 0))

    def draw(self, canvas: Union[pygame.Surface, Tuple[pygame.Surface, ...]]):
        if type(canvas) == pygame.Surface:
            self._draw_face(canvas)
        elif type(canvas) == tuple:
            self._draw_face(canvas[1])

    def run(self, surface: pygame.Surface):
        if self.need_disappear:
            self.disappear()
        else:
            self.appear()
            self.bon_cx.update()
            self.animations.update()
        self.draw(surface)


class Face:
    gap = (display_size[0] - 3 * full_size[0]) // 4
    dist = gap + full_size[0]

    def __init__(self, order: int):
        self.image = pygame.Surface(full_size)
        self.rect = self.image.get_rect(
            midleft=(self.__class__.gap + order * self.__class__.dist, display_size[1] // 2))


class Faces:
    def __init__(self):
        self.face0 = Face(0)
        self.face1 = Face(1)
        self.face2 = Face(2)
        self.group: Tuple['Face', ...] = (self.face0, self.face1, self.face2)

    def draw(self, screen: pygame.Surface):
        for face in self.group:
            screen.blit(face.image, face.rect)

    def draw_on(self, image: pygame.Surface, rect: Union[pygame.Rect, Tuple[int, int]]):
        for face in self.group:
            face.image.blit(image, rect)


class Game:
    events: Union[list[pygame.event.Event], None] = None
    _instance: Union['Game', None] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_inst(cls):
        return cls._instance

    @classmethod
    def whether_full(cls):
        return cls._instance.full_status

    def __init__(self):
        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode(screen_size)
        self.clock = pygame.time.Clock()
        self.bg = pygame.image.load('image/background.png').convert()
        self.bg_large = pygame.transform.scale(self.bg, full_size)
        self.background = self.bg
        pygame.display.set_caption('Center Adventure')
        pygame.display.set_icon(pygame.image.load('image/player/player.png').convert_alpha())
        self.logo_color: list[int] = sample(range(8), 8)
        self.bug_pos: int = randint(0, 1)
        self.archive: dict = read_archive()
        if 'level_status' in self.archive:
            self.status: int = 1
            self.menu: Union['Menu', None] = None
            self.level: Union['Level', None] = Level.enter()
        else:
            self.status: int = 0
            self.menu: Union['Menu', None] = Menu()
            self.level: Union['Level', None] = None
        self.full_status: bool = False
        self.faces = Faces()

    def level_io(self):
        if self.status == 1 and not self.level:
            self.menu = None
            self.level = Level.enter()
        elif self.status == 0 and not self.menu:
            self.menu = Menu.enter()
            self.archive = get_archive()
            self.level = None

    def _quit(self):
        if self.status == 1:
            write_archive(get_archives())
        else:
            write_archive(self.archive)
        pygame.quit()
        sys.exit()

    def _full_change(self):
        if not self.full_status:
            self.full_status = True
            pygame.display.set_mode(display_size, flags=pygame.FULLSCREEN | pygame.HWSURFACE)
            self.screen.fill('black')
        else:
            self.full_status = False
            pygame.display.set_mode(screen_size)

    def control(self):
        for event in self.__class__.events:
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                self._full_change()

    def _get_canvas(self) -> Union[pygame.Surface, Tuple[pygame.Surface, ...]]:
        return tuple(map(lambda face: face.image, self.faces.group)) if self.full_status else self.screen

    def update_draw(self):
        self.screen.fill('black')
        if not self.full_status:
            self.screen.blit(self.background, (0, 0))
        else:
            self.faces.draw_on(self.bg_large, (0, 0))
        if self.level is not None:
            self.level.run(self._get_canvas())
        elif self.menu is not None:
            self.menu.run(self._get_canvas())
        if self.full_status:
            if self.level and self.level.screensaver:
                self.screen.blit(pygame.transform.scale(self.level.cv_copy, display_size), (0, 0))
            else:
                self.faces.draw(self.screen)

    def run(self):
        while True:
            self.__class__.events = pygame.event.get()
            self.control()
            self.level_io()
            self.update_draw()
            self.clock.tick(FPS)
            pygame.display.update()


if __name__ == '__main__':
    game = Game()
    game.run()
