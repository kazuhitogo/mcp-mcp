from mcp.server.fastmcp import FastMCP
import subprocess
import os
import logging
import sys
import pathlib

# 親ディレクトリをパスに追加して、logger.pyをインポートできるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import Logger

# ロガーの初期化（デフォルトはINFO）
# ログレベルは必要に応じて変更可能: DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = Logger("minecraft_tools", logging.INFO, "server/logs")

mcp = FastMCP("minecraft")

this_file_path = os.path.abspath(__file__)
this_file_dir = os.path.dirname(this_file_path)

@mcp.tool()
def setBlocks(x0:int, y0: int, z0: int, x1: int, y1: int ,z1: int, blockType:int) -> str:
    """
    A function that places Blocks within the range of a 3D bounding box specified by arguments (defined by coordinates 1(x,y,z) and 2(x,y,z)) in Minecraft.
    
    Args:
        x0: x value of coordinate 0, required , int
        y0: y value of coordinate 0, required , int
        z0: z value of coordinate 0, required , int
        x1: x value of coordinate 1, required , int
        y1: y value of coordinate 1, required , int
        z1: z value of coordinate 1, required , int
        BlockType: required
            Air is 0
            Stone is 1
            Grass is 2
            Dirt is 3
            Cobblestone is 4
            Oak Wood Plank is 5
            Oak Sapling is 6
            Bedrock is 7
            Flowing Water is 8
            Still Water is 9
            Flowing Lava is 10
            Still Lava is 11
            Sand is 12
            Gravel is 13
            Gold Ore is 14
            Iron Ore is 15
            Coal Ore is 16
            Oak Wood is 17
            Sponge is 19
            Glass is 20
            Lapis Lazuli Ore is 21
            Lapis Lazuli Block is 22
            Dispenser is 23
            Sandstone is 24
            Note Block is 25
            Bed is 26
            Powered Rail is 27
            Detector Rail is 28
            Sticky Piston is 29
            Cobweb is 30
            Dead Shrub is 31
            Dead Bush is 32
            Piston is 33
            Piston Head is 34
            White Wool is 35
            Dandelion is 37
            Poppy is 38
            Brown Mushroom is 39
            Red Mushroom is 40
            Gold Block is 41
            Iron Block is 42
            Double Stone Slab is 43
            Stone Slab is 44
            Bricks is 45
            TNT is 46
            Bookshelf is 47
            Moss Stone is 48
            Obsidian is 49
            Torch is 50
            Fire is 51
            Monster Spawner is 52
            Oak Wood Stairs is 53
            Chest is 54
            Redstone Wire is 55
            Diamond Ore is 56
            Diamond Block is 57
            Crafting Table is 58
            Wheat Crops is 59
            Farmland is 60
            Furnace is 61
            Burning Furnace is 62
            Standing Sign Block is 63
            Oak Door Block is 64
            Ladder is 65
            Rail is 66
            Cobblestone Stairs is 67
            Wallmounted Sign Block is 68
            Lever is 69
            Stone Pressure Plate is 70
            Iron Door Block is 71
            Wooden Pressure Plate is 72
            Redstone Ore is 73
            Glowing Redstone Ore is 74
            Redstone Torch Off is 75
            Redstone Torch On is 76
            Stone Button is 77
            Snow is 78
            Ice is 79
            Snow Block is 80
            Cactus is 81
            Clay is 82
            Sugar Canes is 83
            Jukebox is 84
            Oak Fence is 85
            Pumpkin is 86
            Netherrack is 87
            Soul Sand is 88
            Glowstone is 89
            Nether Portal is 90
            Jack O'Lantern is 91
            Cake Block is 92
            Redstone Repeater Block Off is 93
            Redstone Repeater Block On is 94
            White Stained Glass is 95
            Wooden Trapdoor is 96
            Stone Monster Egg is 97
            Stone Bricks is 98
            Brown Mushroom Block is 99
            Red Mushroom Block is 100
            Iron Bars is 101
            Glass Pane is 102
            Melon Block is 103
            Pumpkin Stem is 104
            Melon Stem is 105
            Vines is 106
            Oak Fence Gate is 107
            Brick Stairs is 108
            Stone Brick Stairs is 109
            Mycelium is 110
            Lily Pad is 111
            Nether Brick is 112
            Nether Brick Fence is 113
            Nether Brick Stairs is 114
            Nether Wart is 115
            Enchantment Table is 116
            Brewing Stand is 117
            Cauldron is 118
            End Portal is 119
            End Portal Frame is 120
            End Stone is 121
            Dragon Egg is 122
            Redstone Lamp Inactive is 123
            Redstone Lamp Active is 124
            Double Oak Wood Slab is 125
            Oak Wood Slab is 126
            Cocoa is 127
            Sandstone Stairs is 128
            Emerald Ore is 129
            Ender Chest is 130
            Tripwire Hook is 131
            Tripwire is 132
            Emerald Block is 133
            Spruce Wood Stairs is 134
            Birch Wood Stairs is 135
            Jungle Wood Stairs is 136
            Command Block is 137
            Beacon is 138
            Cobblestone Wall is 139
            Flower Pot is 140
            Carrots is 141
            Potatoes is 142
            Wooden Button is 143
            Mob Head is 144
            Anvil is 145
            Trapped Chest is 146
            Weighted Pressure Plate Light is 147
            Weighted Pressure Plate Heavy is 148
            Redstone Comparator Inactive is 149
            Redstone Comparator Active is 150
            Daylight Sensor is 151
            Redstone Block is 152
            Nether Quartz Ore is 153
            Hopper is 154
            Quartz Block is 155
            Quartz Stairs is 156
            Activator Rail is 157
            Dropper is 158
            White Hardened Clay is 159
            White Stained Glass Pane is 160
            Acacia Leaves is 161
            Acacia Wood is 162
            Acacia Wood Stairs is 163
            Dark Oak Wood Stairs is 164
            Slime Block is 165
            Barrier is 166
            Iron Trapdoor is 167
            Prismarine is 168
            Sea Lantern is 169
            Hay Bale is 170
            White Carpet is 171
            Hardened Clay is 172
            Block of Coal is 173
            Packed Ice is 174
            Sunflower is 175
            Freestanding Banner is 176
            Wallmounted Banner is 177
            Inverted Daylight Sensor is 178
            Red Sandstone is 179
            Red Sandstone Stairs is 180
            Double Red Sandstone Slab is 181
            Red Sandstone Slab is 182
            Spruce Fence Gate is 183
            Birch Fence Gate is 184
            Jungle Fence Gate is 185
            Dark Oak Fence Gate is 186
            Acacia Fence Gate is 187
            Spruce Fence is 188
            Birch Fence is 189
            Jungle Fence is 190
            Dark Oak Fence is 191
            Acacia Fence is 192
            Spruce Door Block is 193
            Birch Door Block is 194
            Jungle Door Block is 195
            Acacia Door Block is 196
            Dark Oak Door Block is 197
            End Rod is 198
            Chorus Plant is 199
            Chorus Flower is 200
            Purpur Block is 201
            Purpur Pillar is 202
            Purpur Stairs is 203
            Purpur Double Slab is 204
            Purpur Slab is 205
            End Stone Bricks is 206
            Beetroot Block is 207
            Grass Path is 208
            End Gateway is 209
            Repeating Command Block is 210
            Chain Command Block is 211
            Frosted Ice is 212
            Magma Block is 213
            Nether Wart Block is 214
            Red Nether Brick is 215
            Bone Block is 216
            Structure Void is 217
            Observer is 218
            White Shulker Box is 219
            Orange Shulker Box is 220
            Magenta Shulker Box is 221
            Light Blue Shulker Box is 222
            Yellow Shulker Box is 223
            Lime Shulker Box is 224
            Pink Shulker Box is 225
            Gray Shulker Box is 226
            Light Gray Shulker Box is 227
            Cyan Shulker Box is 228
            Purple Shulker Box is 229
            Blue Shulker Box is 230
            Brown Shulker Box is 231
            Green Shulker Box is 232
            Red Shulker Box is 233
            Black Shulker Box is 234
            White Glazed Terracotta is 235
            Orange Glazed Terracotta is 236
            Magenta Glazed Terracotta is 237
            Light Blue Glazed Terracotta is 238
            Yellow Glazed Terracotta is 239
            Lime Glazed Terracotta is 240
            Pink Glazed Terracotta is 241
            Gray Glazed Terracotta is 242
            Light Gray Glazed Terracotta is 243
            Cyan Glazed Terracotta is 244
            Purple Glazed Terracotta is 245
            Blue Glazed Terracotta is 246
            Brown Glazed Terracotta is 247
            Green Glazed Terracotta is 248
            Red Glazed Terracotta is 249
            Black Glazed Terracotta is 250
            White Concrete is 251
            White Concrete Powder is 252
            Structure Block is 255
    
    Returns:
        result text
    """
    script_path = os.path.join(this_file_dir,"tools/setBlocks.py")
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path)
    command = f"uv run {script_name} --x0 {x0} --y0 {y0} --z0 {z0} --x1 {x1} --y1 {y1} --z1 {z1} --blockType {blockType}"
    
    # コマンドの実行をログに記録
    logger.info(f"Executing command: {command}")
    
    try:
        result = subprocess.run(
            command.split(),
            cwd=script_dir,
            capture_output=True, 
            text=True
        )
        
        # 実行結果をログに記録
        if result.returncode == 0:
            logger.info(f"Command executed successfully: {result.stdout.strip()}")
        else:
            logger.error(f"Command failed with error: {result.stderr.strip()}")
        
        return result.stdout
    except Exception as e:
        # 例外が発生した場合はエラーログを記録
        error_msg = f"Exception occurred while executing command: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
    
if __name__ == "__main__":
    # ログレベルを変更したい場合はここで設定できます
    # 例: logger = Logger("minecraft_tools", logging.DEBUG)
    
    logger.info("Starting Minecraft Tool Server")
    mcp.run(transport='stdio')
    logger.info("Minecraft Tool Server stopped")