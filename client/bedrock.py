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
        
        if not command:
            logger.error("サーバー設定にコマンドが指定されていません")
            raise ValueError("サーバー設定にコマンドが指定されていません")
        
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
        except FileNotFoundError as e:
            logger.error(f"指定されたコマンドが見つかりません: {command}")
            raise FileNotFoundError(f"指定されたコマンドが見つかりません: {command}") from e
        except PermissionError as e:
            logger.error(f"コマンド実行の権限がありません: {command}")
            raise PermissionError(f"コマンド実行の権限がありません: {command}") from e
        except asyncio.TimeoutError:
            logger.error("サーバー接続がタイムアウトしました")
            raise TimeoutError("サーバー接続がタイムアウトしました。サーバーが正常に動作しているか確認してください。")
        except Exception as e:
            logger.error(f"サーバー接続エラー: {str(e)}")
            raise RuntimeError(f"サーバー接続エラー: {str(e)}") from e

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("リソースをクリーンアップ中...")
        await self.exit_stack.aclose()
        logger.info("クリーンアップ完了")

    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """Bedrock APIにリクエストを送信"""
        logger.debug(f"Bedrock APIにリクエスト送信中 (モデル: {self.MODEL_ID})")
        try:
            return self.bedrock.converse(
                modelId=self.MODEL_ID,
                messages=messages,
                inferenceConfig={"maxTokens": 1000, "temperature": 0},
                toolConfig={"tools": tools},
            )
        except self.bedrock.exceptions.ModelNotReadyException:
            logger.error(f"モデル {self.MODEL_ID} は現在利用できません")
            raise RuntimeError(f"モデル {self.MODEL_ID} は現在利用できません。しばらく経ってから再試行してください。")
        except self.bedrock.exceptions.ValidationException as e:
            logger.error(f"Bedrock APIリクエストのバリデーションエラー: {str(e)}")
            raise ValueError(f"Bedrock APIリクエストが無効です: {str(e)}")
        except self.bedrock.exceptions.ThrottlingException:
            logger.error("Bedrock APIのレート制限に達しました")
            raise RuntimeError("Bedrock APIのレート制限に達しました。しばらく経ってから再試行してください。")
        except self.bedrock.exceptions.AccessDeniedException:
            logger.error("Bedrock APIへのアクセスが拒否されました")
            raise PermissionError("Bedrock APIへのアクセス権限がありません。AWS認証情報を確認してください。")
        except Exception as e:
            logger.error(f"Bedrock APIリクエスト中に予期しないエラーが発生: {str(e)}")
            raise RuntimeError(f"Bedrock APIリクエスト中にエラーが発生しました: {str(e)}")

    async def process_query(self, query: str) -> str:
        """ユーザークエリを処理して応答を返す"""
        logger.info(f"クエリを処理中: {query}")
        
        if not query or not query.strip():
            logger.warning("空のクエリが送信されました")
            return "クエリが空です。質問や指示を入力してください。"
            
        if not self.session:
            logger.error("セッションが初期化されていません")
            return "エラー: サーバーとの接続が確立されていません。"
            
        try:
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

            if not available_tools:
                logger.warning("利用可能なツールがありません")
                return "警告: サーバーに利用可能なツールがありません。サーバーの設定を確認してください。"

            # BedrockAPI用のツール形式に変換
            bedrock_tools = Message.to_bedrock_format(available_tools)

            # Bedrockにリクエスト送信
            logger.info("Bedrock APIにリクエスト送信中...")
            response = self._make_bedrock_request(messages, bedrock_tools)
            logger.info("Bedrock APIからレスポンスを受信")

            # レスポンスを処理して結果を返す
            return await self._process_response(response, messages, bedrock_tools)
        except asyncio.TimeoutError:
            error_msg = "リクエスト処理がタイムアウトしました"
            logger.error(error_msg)
            return f"エラー: {error_msg}"
        except Exception as e:
            error_msg = f"クエリ処理中にエラーが発生: {str(e)}"
            logger.error(error_msg)
            return f"エラー: {error_msg}"

    async def _process_response(
        self, response: Dict, messages: List[Dict], bedrock_tools: List[Dict]
    ) -> str:
        """Bedrockからのレスポンスを処理"""
        # 最終的な応答テキストを格納するリスト
        final_text = []
        MAX_TURNS = 100  # 最大対話ターン数
        turn_count = 0

        if not response:
            logger.error("Bedrockからの応答が空です")
            return "エラー: AIモデルからの応答が空です。"
            
        if 'stopReason' not in response:
            logger.error("Bedrockからの応答に停止理由がありません")
            return "エラー: AIモデルからの応答が不正な形式です。"

        logger.info(f"レスポンス処理開始 (停止理由: {response['stopReason']})")

        try:
            while True:
                # ツール使用リクエストの場合
                if response['stopReason'] == 'tool_use':
                    logger.info("ツール使用リクエストを受信")
                    final_text.append("received toolUse request")
                    
                    if 'output' not in response or 'message' not in response['output'] or 'content' not in response['output']['message']:
                        logger.error("ツール使用リクエストの形式が不正です")
                        final_text.append("[Error: Invalid tool use request format]")
                        break
                        
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
                            try:
                                response = self._make_bedrock_request(messages, bedrock_tools)
                            except Exception as e:
                                logger.error(f"ツール結果を含めた再リクエスト中にエラーが発生: {str(e)}")
                                final_text.append(f"[Error during follow-up request: {str(e)}]")
                                break
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
                    if 'output' in response and 'message' in response['output'] and 'content' in response['output']['message'] and response['output']['message']['content']:
                        if 'text' in response['output']['message']['content'][0]:
                            final_text.append(response['output']['message']['content'][0]['text'])
                        else:
                            logger.warning("応答にテキストが含まれていません")
                            final_text.append("[Response contains no text]")
                    else:
                        logger.error("応答の形式が不正です")
                        final_text.append("[Error: Invalid response format]")
                    break
                else:
                    logger.warning(f"不明な停止理由: {response['stopReason']}")
                    final_text.append(f"[Unknown stop reason: {response['stopReason']}]")
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
            
        except KeyError as e:
            error_msg = f"レスポンス処理中にキーエラーが発生: {str(e)}"
            logger.error(error_msg)
            return f"エラー: レスポンス処理中に問題が発生しました: {str(e)}"
        except Exception as e:
            error_msg = f"レスポンス処理中に予期しないエラーが発生: {str(e)}"
            logger.error(error_msg)
            return f"エラー: {error_msg}"

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
            logger.info(f"ツール実行成功: {tool_name} {result}")
            
            # メッセージリストにツールリクエストと結果を追加
            messages.append(
                Message.tool_request(tool_use_id, tool_name, tool_args).__dict__
            )
            
            if not result or not result.content:
                logger.warning(f"ツール {tool_name} からの応答が空です")
                error_result = {"text": f"ツール {tool_name} からの応答が空です"}
                messages.append(Message.tool_result(tool_use_id, [error_result]).__dict__)
                return [f"[Tool {tool_name} returned empty response]"]
            
            messages.append(Message.tool_result(tool_use_id, result.content).__dict__)
            
            # ツール呼び出しのログを返す
            return [f"[Calling tool {tool_name} with args {tool_args}]"]
        except asyncio.TimeoutError:
            error_msg = f"ツール {tool_name} の実行がタイムアウトしました"
            logger.error(error_msg)
            error_result = {"text": error_msg}
            messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
            messages.append(Message.tool_result(tool_use_id, [error_result]).__dict__)
            return [f"[Error: {error_msg}]"]
        except KeyError as e:
            error_msg = f"ツール {tool_name} の呼び出しに必要なパラメータが不足しています: {str(e)}"
            logger.error(error_msg)
            error_result = {"text": error_msg}
            messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
            messages.append(Message.tool_result(tool_use_id, [error_result]).__dict__)
            return [f"[Error: {error_msg}]"]
        except Exception as e:
            error_msg = f"ツール実行エラー: {str(e)}"
            logger.error(error_msg)
            error_result = {"text": error_msg}
            messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
            messages.append(Message.tool_result(tool_use_id, [error_result]).__dict__)
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
        config = load_config(config_path)
        if 'mcpServers' not in config:
            logger.error("設定ファイルに 'mcpServers' キーがありません")
            print("Error: Invalid configuration file. 'mcpServers' key is missing.")
            sys.exit(1)
            
        server_config = config['mcpServers']
        logger.info(f"設定ファイルから {len(server_config.keys())} 個のサーバーを読み込みました")
        
        if not server_config:
            logger.error("設定ファイルにサーバー設定がありません")
            print("Error: No server configurations found in the config file.")
            sys.exit(1)
        
        mcp_servers = []
        
        # 各サーバーに接続
        for key in server_config.keys():
            mcp_server = {
                "server_name" : key,
                "config" : server_config[key],
            }
            logger.info(f"サーバー {mcp_server['server_name']} に接続を試みます")
            print(f"サーバー {mcp_server['server_name']} に接続します...")
            client = MCPClient()
            mcp_servers.append(mcp_server)
            try: 
                # サーバーに接続してチャットループを開始
                await client.connect_to_server(mcp_server["config"])
                await client.chat_loop()
            except FileNotFoundError as e:
                logger.error(f"サーバー {mcp_server['server_name']} のコマンドが見つかりません: {str(e)}")
                print(f"Error: Command not found for {mcp_server['server_name']}: {str(e)}")
            except PermissionError as e:
                logger.error(f"サーバー {mcp_server['server_name']} のコマンド実行権限がありません: {str(e)}")
                print(f"Error: Permission denied for {mcp_server['server_name']}: {str(e)}")
            except TimeoutError as e:
                logger.error(f"サーバー {mcp_server['server_name']} との接続がタイムアウトしました: {str(e)}")
                print(f"Error: Connection timeout for {mcp_server['server_name']}: {str(e)}")
            except Exception as e:
                logger.error(f"サーバー {mcp_server['server_name']} との接続中にエラーが発生: {str(e)}")
                print(f"Error connecting to {mcp_server['server_name']}: {str(e)}")
            finally:
                # 終了時にリソースをクリーンアップ
                logger.info(f"サーバー {mcp_server['server_name']} との接続をクリーンアップ")
                await client.cleanup()
        
        logger.info("すべてのサーバー処理が完了しました")
            
    except json.JSONDecodeError as e:
        logger.error(f"設定ファイルのJSONパースエラー: {str(e)}")
        print(f"Error: Invalid JSON in config file: {str(e)}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"設定ファイルが見つかりません: {str(e)}")
        print(f"Error: Config file not found: {str(e)}")
        sys.exit(1)
    except PermissionError as e:
        logger.error(f"設定ファイルの読み取り権限がありません: {str(e)}")
        print(f"Error: Permission denied when reading config file: {str(e)}")
        sys.exit(1)
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
    except asyncio.CancelledError:
        logger.info("非同期タスクがキャンセルされました")
        print("\nAsync task cancelled")
    except Exception as e:
        logger.critical(f"予期しないエラーが発生: {str(e)}")
        print(f"Critical error: {str(e)}")
        import traceback
        logger.critical(f"スタックトレース: {traceback.format_exc()}")
    finally:
        logger.info("プログラムを終了")
