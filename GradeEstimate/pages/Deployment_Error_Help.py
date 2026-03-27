import subprocess
from pathlib import Path

import streamlit as st


LAST_REPORT_FILE = Path(__file__).resolve().parents[1] / ".preflight_last.txt"


def parse_fail_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith("[FAIL]")]


def suggest_fixes(fail_lines: list[str]) -> list[str]:
    suggestions = []
    joined = "\n".join(fail_lines).lower()

    if "module import" in joined:
        suggestions.append("运行 `python -m pip install -r GradeEstimate/requirements.txt` 重新安装依赖。")
    if "missing file" in joined:
        suggestions.append("确认缺失文件已提交到仓库，并检查 Cloud Main file path 为 GradeEstimate/app.py。")
    if "app entry" in joined:
        suggestions.append("检查 app.py 是否包含 `def main()` 与 `if __name__ == \"__main__\"`。")

    if not suggestions and fail_lines:
        suggestions.append("先执行下方可复制排障命令，再把完整日志贴回排障页分析。")

    return suggestions


st.set_page_config(page_title="Deployment Error Help", page_icon="🛠️", layout="centered")

st.title("部署失败排障页")
st.caption("可视化定位 Streamlit Community Cloud 常见失败原因")

st.markdown(
    """
    <style>
    .help-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-left: 6px solid #d97706;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .help-title {
        font-weight: 700;
        margin-bottom: 6px;
    }
    .ok-card {
        border-left-color: #059669;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="help-card ok-card">
      <div class="help-title">优先检查（1分钟）</div>
      1) 仓库是否包含 GradeEstimate/app.py<br/>
      2) Main file path 是否填 GradeEstimate/app.py<br/>
      3) requirements.txt 是否包含 streamlit/numpy/scipy/matplotlib
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="help-card">
      <div class="help-title">错误类型 A：ModuleNotFoundError</div>
      现象：日志里提示找不到 streamlit / scipy / numpy。<br/>
      处理：检查 GradeEstimate/requirements.txt 是否存在并包含依赖。
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="help-card">
      <div class="help-title">错误类型 B：File not found</div>
      现象：日志提示找不到 app.py。<br/>
      处理：Cloud 设置里 Main file path 必须是 GradeEstimate/app.py。
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="help-card">
      <div class="help-title">错误类型 C：Runtime error</div>
      现象：应用启动后白屏或崩溃。<br/>
      处理：先在本地执行 preflight_check.py，再运行 streamlit 本地验证。
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("一键本地预检查")
if st.button("运行 preflight_check.py", use_container_width=True):
    cmd = ["python", "GradeEstimate/preflight_check.py"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2])
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

    if proc.returncode == 0:
        st.success("Preflight 通过")
    else:
        st.error("Preflight 未通过，请按上方错误类型逐项排查")
    st.code(output.strip() or "(no output)", language="text")

st.subheader("最近一次 Preflight 报告")
if LAST_REPORT_FILE.exists():
    last_report = LAST_REPORT_FILE.read_text(encoding="utf-8")
    fail_lines = parse_fail_lines(last_report)

    if fail_lines:
        st.error(f"检测到 {len(fail_lines)} 个失败项")
        for item in fail_lines:
            st.markdown(f"- :red[{item}]")

        st.markdown("**最可能修复步骤**")
        for step in suggest_fixes(fail_lines):
            st.markdown(f"- {step}")
    else:
        st.success("最近一次检查无失败项")

    st.code(last_report.strip(), language="text")
else:
    st.info("尚无历史 preflight 报告，先点击上方按钮执行一次。")

st.subheader("可复制排障命令")
troubleshoot_cmds = """python GradeEstimate/preflight_check.py
python -m streamlit run GradeEstimate/app.py
git status --short -- GradeEstimate
git log --max-count=10 --oneline
"""
st.code(troubleshoot_cmds.strip(), language="bash")
st.caption("可直接复制以上命令到终端，逐条执行定位问题。")

st.info("若 Cloud 仍失败，请把 Deployment logs 复制到这里继续诊断。")
