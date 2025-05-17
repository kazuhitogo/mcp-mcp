import asyncio
import sys
import os
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import boto3

import json

# 親ディレクトリをパスに追加して、logger.pyをインポートできるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import Logger

# ロガーの初期化 - クライアント用のログディレクトリを指定
logger = Logger("mcp_client", logging.INFO, "client/logs")

def load_config(config_path):
    """JSONファイルからMCPサーバー設定を読み込む"""
    logger.info(f"設定ファイルを読み込み中: {config_path}")
    if not os.path.exists(config_path):
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        logger.debug(f"設定ファイルの内容: {json.dumps(config, indent=2, ensure_ascii=False)}")
        return config


@dataclass
class Message:
    """チャットメッセージを表現するクラス"""
    role: str  # ユーザーかアシスタントかを示す
    content: List[Dict[str, Any]]  # メッセージの内容

    @classmethod
    def user(cls, text: str) -> 'Message':
        """ユーザーメッセージを作成"""
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant(cls, text: str) -> 'Message':
        """アシスタントメッセージを作成"""
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def tool_result(cls, tool_use_id: str, content: dict) -> 'Message':
        """ツール実行結果のメッセージを作成"""
        return cls(
            role="user",
            content=[
                {
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"json": {"text": content[0].text}}],
                    }
                }
            ],
        )

    @classmethod
    def tool_request(cls, tool_use_id: str, name: str, input_data: dict) -> 'Message':
        """ツール実行リクエストのメッセージを作成"""
        return cls(
            role="assistant",
            content=[
                {
                    "toolUse": {
                        "toolUseId": tool_use_id,
                        "name": name,
                        "input": input_data,
                    }
                }
            ],
        )

    @staticmethod
    def to_bedrock_format(tools_list: List[Dict]) -> List[Dict]:
        """ツールリストをBedrock APIの形式に変換"""
        return [
            {
                "toolSpec": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": tool["input_schema"]["properties"],
                            "required": tool["input_schema"]["required"],
                        }
                    },
                }
            }
            for tool in tools_list
        ]


class MCPClient:
    """MCPクライアントの実装クラス"""
    MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # 使用するモデルID

    def __init__(self):
        """クライアントの初期化"""
        logger.info("MCPClientを初期化中...")
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()  # リソース管理用のスタック
        self.bedrock = boto3.client(
            service_name='bedrock-runtime', region_name='us-west-2'
        )  # AWS Bedrockクライアント
        logger.info("Bedrock クライアントを初期化しました (region: us-west-2)")

    async def connect_to_server(self, server_config):
        """サーバー設定からMCPサーバーに接続する"""
        logger.info(f"サーバーに接続中: {server_config.get('command')}")
        command = server_config.get("command")  # 実行コマンド
        args = server_config.get("args", [])    # コマンド引数
        env = server_config.get("env")          # 環境変数
        
        logger.debug(f"コマンド: {command}")
        logger.debug(f"引数: {args}")
        
        # サーバーパラメータを設定
        server_params = StdioServerParameters(
            command=command, args=args, env=env
        )

        # 標準入出力を通じてサーバーと接続
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            await self.session.initialize()  # セッション初期化
            logger.info("サーバーセッションを初期化しました")

            # 利用可能なツールを取得
            response = await self.session.list_tools()
            tools = [tool.name for tool in response.tools]
            logger.info(f"利用可能なツール: {tools}")
            print(
                "\nConnected to server with tools:", tools
            )
        except Exception as e:
            logger.error(f"サーバー接続エラー: {str(e)}")
            raise

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("リソースをクリーンアップ中...")
        await self.exit_stack.aclose()
        logger.info("クリーンアップ完了")

    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """Bedrock APIにリクエストを送信"""
        logger.debug(f"Bedrock APIにリクエスト送信中 (モデル: {self.MODEL_ID})")
        return self.bedrock.converse(
            modelId=self.MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 1000, "temperature": 0},
            toolConfig={"tools": tools},
        )

    async def process_query(self, query: str) -> str:
        """ユーザークエリを処理して応答を返す"""
        logger.info(f"クエリを処理中: {query}")
        # ユーザーメッセージを作成
        messages = [Message.user(query).__dict__]
        # 利用可能なツールのリストを取得
        response = await self.session.list_tools()

        # ツール情報を整形
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]
        logger.debug(f"利用可能なツール数: {len(available_tools)}")

        # BedrockAPI用のツール形式に変換
        bedrock_tools = Message.to_bedrock_format(available_tools)

        # Bedrockにリクエスト送信
        logger.info("Bedrock APIにリクエスト送信中...")
        response = self._make_bedrock_request(messages, bedrock_tools)
        logger.info("Bedrock APIからレスポンスを受信")

        # レスポンスを処理して結果を返す
        return await self._process_response(response, messages, bedrock_tools)

    async def _process_response(
        self, response: Dict, messages: List[Dict], bedrock_tools: List[Dict]
    ) -> str:
        """Bedrockからのレスポンスを処理"""
        # 最終的な応答テキストを格納するリスト
        final_text = []
        MAX_TURNS = 10  # 最大対話ターン数
        turn_count = 0

        logger.info(f"レスポンス処理開始 (停止理由: {response['stopReason']})")

        while True:
            # ツール使用リクエストの場合
            if response['stopReason'] == 'tool_use':
                logger.info("ツール使用リクエストを受信")
                final_text.append("received toolUse request")
                for item in response['output']['message']['content']:
                    if 'text' in item:
                        logger.debug(f"思考テキスト: {item['text']}")
                        final_text.append(f"[Thinking: {item['text']}]")
                        messages.append(Message.assistant(item['text']).__dict__)
                    elif 'toolUse' in item:
                        # ツール呼び出しを処理
                        tool_info = item['toolUse']
                        logger.info(f"ツール呼び出し: {tool_info['name']}")
                        result = await self._handle_tool_call(tool_info, messages)
                        final_text.extend(result)

                        # ツール結果を含めて再度リクエスト
                        logger.info("ツール結果を含めて再度リクエスト送信")
                        response = self._make_bedrock_request(messages, bedrock_tools)
            # 各種停止理由に応じた処理
            elif response['stopReason'] == 'max_tokens':
                logger.warning("最大トークン数に達しました")
                final_text.append("[Max tokens reached, ending conversation.]")
                break
            elif response['stopReason'] == 'stop_sequence':
                logger.info("停止シーケンスに達しました")
                final_text.append("[Stop sequence reached, ending conversation.]")
                break
            elif response['stopReason'] == 'content_filtered':
                logger.warning("コンテンツがフィルタリングされました")
                final_text.append("[Content filtered, ending conversation.]")
                break
            elif response['stopReason'] == 'end_turn':
                logger.info("ターン終了")
                final_text.append(response['output']['message']['content'][0]['text'])
                break

            turn_count += 1
            logger.debug(f"ターン数: {turn_count}/{MAX_TURNS}")

            # 最大ターン数に達した場合は終了
            if turn_count >= MAX_TURNS:
                logger.warning("最大ターン数に達しました")
                final_text.append("\n[Max turns reached, ending conversation.]")
                break
        
        # 最終的な応答テキストを返す
        logger.info("レスポンス処理完了")
        return "\n\n".join(final_text)

    async def _handle_tool_call(
        self, tool_info: Dict, messages: List[Dict]
    ) -> List[str]:
        """ツール呼び出しを処理"""
        # ツール情報を取得
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        logger.info(f"ツール呼び出し: {tool_name}")
        logger.debug(f"ツール引数: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")
        logger.debug(f"ツール使用ID: {tool_use_id}")

        try:
            # MCPサーバーでツールを実行
            result = await self.session.call_tool(tool_name, tool_args)
            logger.info(f"ツール実行成功: {tool_name}")
            
            # メッセージリストにツールリクエストと結果を追加
            messages.append(
                Message.tool_request(tool_use_id, tool_name, tool_args).__dict__
            )
            messages.append(Message.tool_result(tool_use_id, result.content).__dict__)
            
            # ツール呼び出しのログを返す
            return [f"[Calling tool {tool_name} with args {tool_args}]"]
        except Exception as e:
            error_msg = f"ツール実行エラー: {str(e)}"
            logger.error(error_msg)
            return [f"[Error calling tool {tool_name}: {str(e)}]"]

    async def chat_loop(self):
        """対話ループを実行"""
        logger.info("チャットループを開始")
        print("\nMCP Client Started!\nType your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    logger.info("ユーザーが終了を要求")
                    break
                logger.info(f"ユーザークエリ: {query}")
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                error_msg = f"エラー発生: {str(e)}"
                logger.error(error_msg)
                print(f"\nError: {str(e)}")
        logger.info("チャットループを終了")


async def main():
    """メイン関数"""
    logger.info("MCPクライアントを起動中...")
    if len(sys.argv) < 2:
        logger.error("設定ファイルのパスが指定されていません")
        print("Usage: python client.py <path_to_config.json>")
        sys.exit(1)

    config_path = sys.argv[1]
    logger.info(f"設定ファイルパス: {config_path}")
    
    try:
        # 設定ファイルを読み込む
        config = load_config(config_path)['mcpServers']
        logger.info(f"設定ファイルから {len(config.keys())} 個のサーバーを読み込みました")
        
        mcp_servers = []
        
        # 各サーバーに接続
        for key in config.keys():
            mcp_server = {
                "server_name" : key,
                "config" : config[key],
            }
            logger.info(f"サーバー {mcp_server['server_name']} に接続を試みます")
            print(f"サーバー {mcp_server['server_name']} に接続します...")
            client = MCPClient()
            mcp_servers.append(mcp_server)
            try: 
                # サーバーに接続してチャットループを開始
                await client.connect_to_server(mcp_server["config"])
                await client.chat_loop()
            except Exception as e:
                logger.error(f"サーバー {mcp_server['server_name']} との接続中にエラーが発生: {str(e)}")
                print(f"Error connecting to {mcp_server['server_name']}: {str(e)}")
            finally:
                # 終了時にリソースをクリーンアップ
                logger.info(f"サーバー {mcp_server['server_name']} との接続をクリーンアップ")
                await client.cleanup()
        
        logger.info("すべてのサーバー処理が完了しました")
            
    except Exception as e:
        logger.error(f"メイン処理でエラーが発生: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("プログラムを開始")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("キーボード割り込みによりプログラムを終了")
        print("\nProgram terminated by user")
    except Exception as e:
        logger.critical(f"予期しないエラーが発生: {str(e)}")
        print(f"Critical error: {str(e)}")
    finally:
        logger.info("プログラムを終了")