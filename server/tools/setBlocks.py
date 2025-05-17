import argparse
import sys
from mcpi.minecraft import Minecraft

def main():
    parser = argparse.ArgumentParser(
        description='指定された3D範囲にTNTブロックを設置します。',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # 座標の開始点を定義
    parser.add_argument('--x0', type=int, required=True, help='X coordinate of the starting point')
    parser.add_argument('--y0', type=int, required=True, help='Y coordinate of the starting point')
    parser.add_argument('--z0', type=int, required=True, help='Z coordinate of the starting point')
    
    # 座標の終了点を定義
    parser.add_argument('--x1', type=int, required=True, help='X coordinate of the ending point')
    parser.add_argument('--y1', type=int, required=True, help='Y coordinate of the ending point')
    parser.add_argument('--z1', type=int, required=True, help='Z coordinate of the ending point')
    
    # ブロックタイプを定義
    parser.add_argument('--blockType', type=int, required=True, help='Type of block to set')
    
    try:
        args = parser.parse_args()
        print(args)
        
        if args.blockType < 0 and args.blockType > 255:
            raise ValueError("blockTypeは0以上255以下の整数である必要があります")
        
        try:
            mc = Minecraft.create()
        except Exception:
            raise ConnectionError("Minecraftサーバーに接続できませんでした。サーバーが起動しているか確認してください。")
        
        mc.setBlocks(args.x0, args.y0, args.z0, args.x1, args.y1, args.z1, args.blockType)
        # 成功メッセージを標準出力に出力
        print(f"ブロック(ID: {args.blockType})を ({args.x0},{args.y0},{args.z0}) から ({args.x1},{args.y1},{args.z1}) の範囲に設置しました")
        return 0
              
    except ValueError as e:
        print(f"エラー: 値が無効です - {e}", file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(f"接続エラー: {e}", file=sys.stderr)
        return 2
    except argparse.ArgumentError as e:
        print(f"引数エラー: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}", file=sys.stderr)
        return 4
    
    return f"ブロック(ID: {args.blockType})を ({args.x0},{args.y0},{args.z0}) から ({args.x1},{args.y1},{args.z1}) の範囲に設置しました"

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)