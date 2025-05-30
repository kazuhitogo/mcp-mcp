import sys, os
# 親ディレクトリをパスに追加して、logger.pyをインポートできるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
from logger import Logger
import json
import argparse
from strands.tools.mcp import MCPClient
from strands import Agent
from contextlib import ExitStack
from mcp import stdio_client, StdioServerParameters
from tools import capture
from strands_tools import image_reader

# ロガーの初期化 - クライアント用のログディレクトリを指定
logger = Logger("mcp_client", logging.INFO, "client/logs")

def parse_arguments():
    """コマンドライン引数を解析する"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--mcp', type=str, help='mcp.json のパス')
    args = parser.parse_args()
    logger.debug(f"コマンドライン引数: mcp={args.mcp}")
    return args

def load_mcp_clients():
    """MCP設定ファイルからクライアントを読み込む"""
    args = parse_arguments()
    logger.info(f"MCP設定ファイル '{args.mcp}' を読み込み中...")
    
    try:
        with open(args.mcp, 'r') as f:
            mcp_settings = json.load(f)["mcpServers"]
        
        logger.debug(f"MCP設定: {len(mcp_settings)} サーバーが見つかりました")
        
        mcp_clients = []
        for key in mcp_settings.keys():
            logger.debug(f"MCPクライアント '{key}' を初期化中...")
            mcp_client = MCPClient(
                lambda: stdio_client(
                    StdioServerParameters(
                        command=mcp_settings[key]["command"], 
                        args=mcp_settings[key]["args"]
                    )
                )
            )
            mcp_clients.append(mcp_client)
            logger.debug(f"MCPクライアント '{key}' の初期化完了")
        
        logger.info(f"{len(mcp_clients)}個のMCPクライアントを読み込みました")
        return mcp_clients
    except FileNotFoundError:
        logger.error(f"MCP設定ファイル '{args.mcp}' が見つかりません")
        raise
    except json.JSONDecodeError:
        logger.error(f"MCP設定ファイル '{args.mcp}' の解析に失敗しました")
        raise
    except KeyError as e:
        logger.error(f"MCP設定ファイルに必要なキー '{e}' がありません")
        raise

def strands_callback_handler(**kwargs):
    """Strandsからのコールバックを処理する"""
    if "data" in kwargs:
        logger.debug(f"Strands出力: {kwargs['data']}")
    elif "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        tool_name = tool.get('name', 'unknown')
        logger.debug(f"Strandsツール使用: {tool_name}")


def main():
    """メイン処理"""
    logger.info("MCPクライアントを読み込み中...")
    mcp_clients = load_mcp_clients()
    
    with ExitStack() as stack:
        logger.info("クライアントコンテキストを設定中...")
        clients = [stack.enter_context(mcp_client) for mcp_client in mcp_clients]
        
        logger.info("ツールを準備中...")
        tools = [capture, image_reader]
        
        for client in clients:
            logger.debug("クライアントからツールを取得中...")
            client_tools = client.list_tools_sync()
            tools.extend(client_tools)
            logger.debug(f"{len(client_tools)}個のツールを追加しました")
        
        logger.info(f"合計{len(tools)}個のツールを使用可能")
        
        logger.info("Agentを初期化中...")
        agent = Agent(
            system_prompt = """
You are a professional at creating structures in Minecraft. Please use the given tools to meet user requests.
However, user requests may be rough and lack information. In such cases, proceed by assuming what the user wants as a professional.
Before starting work, during work, and at the end, please use the capture tool and image_reader, setPlayerPos tools to understand the situation in the Minecraft field.
Since the player's perspective is fixed in a bird's-eye view, it is important to check if everything looks appropriate from above. 
Frequent checks improve the accuracy of your work, so they need to be done often.
""",
            tools = tools,
            callback_handler=strands_callback_handler
        )
        
        message = """
水を草で埋めて更地にしたあと、巨大でかっこいいピラミッドを作って。
とくに素材は元のピラミッドの素材にこだわることなく現代的なアートを意識して。
"""
        logger.info("ユーザーリクエストを処理中...")
        logger.debug(f"リクエスト内容: {message.strip()}")
        
        agent(message)
        logger.info("処理が完了しました")


if __name__ == "__main__":
    logger.info("Minecraft Agent 開始...")
    try:
        main()
    except Exception as e:
        logger.exception(f"実行中にエラーが発生しました: {e}")
        raise
