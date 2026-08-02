"""VeriForge Web UI - Gradio 前端。

把 Planner / Executor / Validator 的三层协作过程实时展示在浏览器里：
- 输入任务
- 实时刷新运行日志
- 实时显示当前阶段与最近动作（Planner / Executor / Validator）
- 任务结束后展示任务面板（DONE / FAILED / BLOCKED）
"""

import io
import contextlib
import queue
import sys
import threading
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

import gradio as gr

from bootstrap.runtime import build_runtime_for_query
from engine.main_loop import run_main_loop


def _parse_status_line(line: str, status: dict):
    """根据日志行更新当前运行状态。"""
    if "🔄" in line and "第" in line and "次迭代" in line:
        status["stage"] = "Planner"
        status["step"] = re.search(r"第 (\d+) 次迭代", line).group(1)
    elif "🔧" in line and "第" in line and "步" in line:
        status["stage"] = "Executor"
        status["step"] = re.search(r"第 (\d+) 步", line).group(1)
    elif "🔍" in line and "第" in line and "步" in line:
        status["stage"] = "Validator"
        status["step"] = re.search(r"第 (\d+) 步", line).group(1)
    elif "选择工具:" in line:
        status["action"] = line.split("选择工具:")[-1].strip()
    elif "验证结果:" in line:
        status["action"] = line.strip()
    elif "已完成并通过验证" in line:
        status["stage"] = "完成"
        status["action"] = "任务验证通过"
    elif "总运行时间已达到预算上限" in line or "规划预算耗尽" in line:
        status["stage"] = "停止"
        status["action"] = "预算耗尽"
    elif "程序异常退出" in line:
        status["stage"] = "错误"
        status["action"] = line.strip()


def _format_status(status: dict) -> str:
    return (
        f"阶段: {status['stage']}\n"
        f"步骤: {status['step']}\n"
        f"最近动作: {status['action']}"
    )


def _extract_panel(log_text: str) -> str:
    panel_lines = []
    for line in log_text.splitlines():
        if ("===" in line and "任务" in line) or "📌" in line:
            panel_lines.append(line)
            continue
        if panel_lines:
            panel_lines.append(line)
    return "\n".join(panel_lines) if panel_lines else "（无任务面板输出）"


def _run_task(user_query: str):
    """流式执行任务：状态栏实时更新，日志逐行追加，结束后返回任务面板。"""
    if not user_query or not user_query.strip():
        yield "请输入任务", "阶段: 等待输入\n步骤: -\n最近动作: -", ""
        return

    log_queue: queue.Queue = queue.Queue()
    done_queue: queue.Queue = queue.Queue()
    buffer = io.StringIO()

    class TeeStdout:
        def write(self, text):
            buffer.write(text)
            log_queue.put(text)
            return len(text)

        def flush(self):
            pass

    def worker():
        try:
            runtime = build_runtime_for_query(user_query.strip())
            with contextlib.redirect_stdout(TeeStdout()):
                run_main_loop(runtime)
        except Exception as exc:
            buffer.write(f"\n程序异常退出: {exc}\n")
            log_queue.put(f"\n程序异常退出: {exc}\n")
        done_queue.put(buffer.getvalue())

    threading.Thread(target=worker, daemon=True).start()

    status = {"stage": "启动中", "step": "-", "action": "正在装配运行时"}
    yield (
        "⏳ 任务运行中（Planner → Executor → Validator）...\n",
        _format_status(status),
        "",
    )

    partial = []
    while True:
        try:
            chunk = log_queue.get(timeout=1)
            partial.append(chunk)
            for line in chunk.splitlines():
                _parse_status_line(line, status)
            yield "".join(partial), _format_status(status), ""
        except queue.Empty:
            if not done_queue.empty():
                break
            continue

    full_log = done_queue.get()
    yield full_log, _format_status(status), _extract_panel(full_log)


def create_ui():
    with gr.Blocks(title="VeriForge") as demo:
        gr.Markdown(
            "# VeriForge\n"
            "规划-执行-验证三层闭环的多智能体 Harness。"
        )

        with gr.Row():
            query_box = gr.Textbox(
                label="任务输入",
                placeholder="例如：读取 tools/core/service.py 并总结它做了什么",
                lines=3,
                scale=3,
            )
            run_btn = gr.Button("运行", variant="primary", scale=1)

        with gr.Row():
            status_box = gr.Textbox(
                label="当前状态",
                lines=3,
                interactive=False,
                scale=1,
            )
            log_box = gr.Textbox(
                label="运行日志",
                lines=28,
                interactive=False,
                scale=3,
            )

        panel_box = gr.Textbox(
            label="任务面板",
            lines=8,
            interactive=False,
        )

        run_btn.click(fn=_run_task, inputs=query_box, outputs=[log_box, status_box, panel_box])
        query_box.submit(fn=_run_task, inputs=query_box, outputs=[log_box, status_box, panel_box])

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.queue()
    demo.launch(server_name="0.0.0.0", server_port=7861, share=False)
