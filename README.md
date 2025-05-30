# mcp-mcp
Model Context Protocol を使って MineCraft Playing する MCP サーバー

## How to Use
1. `sudo apt install awscli -y`
1. `aws configure` して bedrock を使えるようにしておく
1. 任意の Raspberry PI に clone
1. cd ~/{path/to/clone/directory}/client
1. `uv run client.py --mcp ../server/mcp.json`

## インタラクティブチャット機能
- 起動後、コマンドラインでMinecraftに関する指示を入力できます
- 「exit」または「quit」と入力すると終了します
- AIエージェントはリアルタイムでツール使用状況と生成テキストを表示します

## 注意
`uv` コマンドをインストールしてあること
