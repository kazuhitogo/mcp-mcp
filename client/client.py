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
    parser = argparse.ArgumentParser()
    parser.add_argument('--mcp', type=str, help='mcp.json のパス')
    return parser.parse_args()

def load_mcp_clients():
    args = parse_arguments()
    with open(args.mcp, 'r') as f:
        mcp_settings = json.load(f)["mcpServers"]
    mcp_clients = []
    for key in mcp_settings.keys():
        mcp_client = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command=mcp_settings[key]["command"], 
                    args=mcp_settings[key]["args"]
                )
            )
        )
        mcp_clients.append(mcp_client)
    return mcp_clients

def strands_callback_handler(**kwargs):
    if "data" in kwargs:
        logger.debug(f"Strands output: {kwargs['data']}")
    elif "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        logger.debug(f"Strands using tool: {tool.get('name', 'unknown')}")


def main():
    mcp_clients = load_mcp_clients()
    with ExitStack() as stack:
        clients = [stack.enter_context(mcp_client) for mcp_client in mcp_clients]
        tools = [capture, image_reader]
        for client in clients:
            tools.extend(client.list_tools_sync())
        
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
まずフィールド全体を air で埋めた後、湖と巨大なダム、そしてその下を流れる川を作ってください。
"""
        agent(message)
        

if __name__ == "__main__":
    logger.info("Minecraft Agent 開始...")
    main()
