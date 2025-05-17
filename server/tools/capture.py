from Xlib import display, X
from PIL import Image
import numpy as np

d = display.Display()
root = d.screen().root

window_ids = root.get_full_property(
    d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType
).value

for window_id in window_ids:
    window = d.create_resource_object('window', window_id)
    window_title = window.get_wm_name()
    if window_title == 'Minecraft: Pi Edition: Reborn (Client)':
        # ウィンドウの絶対位置を取得する
        geom = window.get_geometry()
        
        # ウィンドウ自体から画像を取得する（ルートではなく）
        try:
            raw = window.get_image(
                0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff
            )
            print(f"Successfully captured image of size {geom.width}x{geom.height}")
            
            # 画像データを処理してPNGとして保存
            image_data = raw.data
            
            # 画像データをnumpy配列に変換
            # XlibのZPixmapは通常BGRXフォーマット（4バイト/ピクセル）
            image_array = np.frombuffer(image_data, dtype=np.uint8)
            image_array = image_array.reshape(geom.height, geom.width, 4)
            
            # BGRXからRGBに変換
            rgb_array = image_array[:, :, :3][:, :, ::-1]  # BGRをRGBに反転
            
            # PILイメージに変換
            img = Image.fromarray(rgb_array)
            
            # PNGとして保存
            img.save('image.png')
            print("Image saved as image.png")
            
            # 最初に見つかったMinecraftウィンドウだけを処理して終了
            break
            
        except Exception as e:
            print(f"Failed to capture window: {e}")