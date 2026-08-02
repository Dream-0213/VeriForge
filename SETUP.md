# VeriForge 从零启动指南

本文档面向新环境，按顺序执行即可跑通 VeriForge。

## 环境要求

- Python 3.10+（推荐 3.11）
- 一个可用的 OpenAI-Compatible API（DeepSeek / OpenAI / 本地 vLLM 均可）
- 支持原生 function calling 的模型（如 deepseek-v4-flash、gpt-4o-mini）

## 第一步：获取项目

```bash
git clone <你的仓库地址> VeriForge
cd VeriForge
```

如果是本地已有代码：

```bash
cd /path/to/VeriForge
```

## 第二步：创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate
```

## 第三步：安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

依赖只有三个：`python-dotenv`、`openai`、`langsmith`。

## 第四步：配置模型

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
# openai 兼容的 API KEY
API_KEY=你的key

# API 地址
BASE_URL=https://api.deepseek.com

# 模型名（必须支持 function calling）
MODEL_NAME=deepseek-v4-flash

# 单次模型请求超时（秒）
LLM_TIMEOUT_SECONDS=120

# 最大 Token 数
MAX_TOKENS=8192

# LangSmith 追踪（可选，默认关闭）
LANGCHAIN_TRACING_V2=false
```

如果使用本地 vLLM，改成：

```bash
BASE_URL=http://127.0.0.1:8000/v1
MODEL_NAME=你的模型名
API_KEY=EMPTY
```

## 第五步：运行

```bash
python3 main_agent.py
```

程序会提示输入任务：

```
请输入你的任务/查询:
```

输入一个任务，比如：

```
读取 tools/core/service.py 并总结它做了什么
```

## 第六步：看结果

- Planner-Agent 会先规划任务
- Executor-Agent 执行并提交结论
- Validator-Agent 独立验证，通过后任务标记 DONE
- 完整日志实时打印，最终结论在输出末尾

## 常见问题

### Q: 报错 `Thinking mode does not support this tool_choice`

项目已内置兼容处理：检测到该错误会自动把 `tool_choice` 从 `required` 降级为 `auto` 重试，无需手动处理。

### Q: 报错 `Insufficient Balance` / 401 / 404

检查 `.env` 里的 API_KEY、BASE_URL、MODEL_NAME 是否正确，模型名必须支持 function calling。

### Q: 任务 600 秒还没跑完

在 `domain/types.py` 的 `AgentRuntime` 中调整预算：

```python
max_plan_iterations: int = 8      # Planner 最大轮数
max_generator_steps: int = 20     # Executor 单任务最大步数
max_validate_steps: int = 8       # Validator 最大步数
max_task_retries: int = 3         # 任务最大重试次数
max_total_runtime_seconds: int = 600  # 总运行预算
```

### Q: 模型一次返回多个 function call

项目已支持多动作解码：一次返回多个 read/bash 时会逐个执行并写入工作记忆，不会丢弃。

## 目录速查

```
VeriForge/
├── main_agent.py        # 程序入口
├── bootstrap/           # 运行时装配
├── engine/              # Planner/Executor/Validator 编排
├── llm/                 # 模型调用 + Prompt + 动作协议
├── domain/              # 任务模型 + 状态机
├── memory/              # 工作记忆 + 会话记忆
├── tools/               # 工具系统
├── skills/              # skill 仓库
└── use_case/            # 示例与运行日志
```
