from Xlib import display, X
from PIL import Image
import numpy as np
import os
import datetime
import sys 
from strands import tool
import logging
from logger import Logger

# ロガーの初期化
logger = Logger("capture_tool", logging.INFO)

@tool
def capture():
    """
    This function takes a screenshot of Minecraft and returns the image file path.
    
    Args:
        None
    Returns:
        Screenshot file path
    """

    # 保存先ディレクトリを設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(script_dir, "..", "images")

    # 保存先ディレクトリが存在しない場合は作成
    os.makedirs(save_dir, exist_ok=True)
    logger.debug(f"スクリーンショット保存先ディレクトリ: {save_dir}")

    # 現在の日時を取得してファイル名を生成
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_time}.png"
    save_path = os.path.join(save_dir, filename)
    logger.debug(f"スクリーンショットファイル名: {filename}")

    try:
        d = display.Display()
        root = d.screen().root

        window_ids = root.get_full_property(
            d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType
        ).value

        logger.debug(f"ウィンドウ数: {len(window_ids)}")
        
        for window_id in window_ids:
            window = d.create_resource_object('window', window_id)
            window_title = window.get_wm_name()
            logger.debug(f"ウィンドウ検出: {window_title}")
            
            if window_title == 'Minecraft: Pi Edition: Reborn (Client)':
                logger.info(f"Minecraftウィンドウを検出しました: {window_title}")
                # ウィンドウの絶対位置を取得する
                geom = window.get_geometry()
                logger.debug(f"ウィンドウサイズ: {geom.width}x{geom.height}")
                
                # ウィンドウ自体から画像を取得する（ルートではなく）
                try:
                    raw = window.get_image(
                        0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff
                    )
                    logger.info(f"画像キャプチャ成功: {geom.width}x{geom.height}")
                    
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
                    img.save(save_path)
                    logger.info(f"スクリーンショットを保存しました: {save_path}")
                    return (save_path)
                    
                except Exception as e:
                    logger.error(f"ウィンドウキャプチャ失敗: {e}")
                    return None
        
        logger.warning("Minecraftウィンドウが見つかりませんでした")
        return None
        
    except Exception as e:
        logger.error(f"スクリーンショット取得中にエラーが発生しました: {e}")
        return None