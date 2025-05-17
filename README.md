# mcp-mcp
Model Context Protocol を使って MineCraft Playing する MCP サーバー

## How to Use
1. `sudo apt install awscli -y`
1. `aws configure` して bedrock を使えるようにしておく
1. 任意の Raspberry PI に clone
1. cd ~/{path/to/clone/directory}/client
1. `uv run main.py ../server/mcp.json`

## 注意
`uv` コマンドをインストールしてあること
