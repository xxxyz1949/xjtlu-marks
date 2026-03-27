import subprocess
from pathlib import Path
import re
import datetime as dt

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


def classify_cloud_log(log_text: str) -> list[dict]:
    """Return matched categories with confidence scoring."""
    text = log_text.lower()
    matched: list[dict] = []

    rules = [
        (
            "missing_module",
            "依赖缺失",
            r"modulenotfounderror|no module named",
            0.25,
        ),
        (
            "missing_entry",
            "入口文件路径错误",
            r"file not found|no such file|can't open file.*app\.py|main file path",
            0.20,
        ),
        (
            "pip_install_failed",
            "依赖安装失败",
            r"failed building wheel|pip.*error|could not build wheels",
            0.22,
        ),
        (
            "syntax_error",
            "代码语法错误",
            r"syntaxerror|indentationerror|taberror",
            0.28,
        ),
        (
            "runtime_import",
            "运行时导入异常",
            r"importerror|dll load failed",
            0.20,
        ),
    ]

    for code, title, pattern, weight in rules:
        hit_count = len(re.findall(pattern, text))
        if hit_count > 0:
            confidence = min(0.45 + 0.12 * hit_count + weight, 0.98)
            if confidence >= 0.8:
                level = "高"
            elif confidence >= 0.6:
                level = "中"
            else:
                level = "低"
            matched.append(
                {
                    "code": code,
                    "title": title,
                    "pattern": pattern,
                    "hits": hit_count,
                    "confidence": confidence,
                    "level": level,
                }
            )

    return matched


def fix_commands_for(code: str) -> list[str]:
    mapping = {
        "missing_module": [
            "python -m pip install -r GradeEstimate/requirements.txt",
            "python GradeEstimate/preflight_check.py",
        ],
        "missing_entry": [
            "# Streamlit Cloud Main file path 应设为 GradeEstimate/app.py",
            "git ls-files | rg \"GradeEstimate/app.py\"",
        ],
        "pip_install_failed": [
            "python -m pip install -U pip",
            "python -m pip install -r GradeEstimate/requirements.txt",
        ],
        "syntax_error": [
            "python -m py_compile GradeEstimate/app.py",
            "python GradeEstimate/preflight_check.py",
        ],
        "runtime_import": [
            "python GradeEstimate/preflight_check.py",
            "python -m streamlit run GradeEstimate/app.py",
        ],
    }
    return mapping.get(code, ["python GradeEstimate/preflight_check.py"])


def build_repair_checklist(categories: list[dict]) -> str:
    if not categories:
        return "[1] 先粘贴 Cloud 部署日志\n[2] 点击分析日志\n[3] 根据建议执行修复命令"

    lines = ["# Repair Checklist", ""]
    priority = 1
    used = set()
    for item in categories:
        code = item["code"]
        title = item["title"]
        lines.append(f"{priority}. [{title}]")
        for cmd in fix_commands_for(code):
            if cmd not in used:
                lines.append(f"   - {cmd}")
                used.add(cmd)
        priority += 1
    return "\n".join(lines)


def build_diagnosis_report(log_source: str, categories: list[dict], raw_log: str) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Deployment Diagnosis Report",
        f"Generated at: {now}",
        f"Log source: {log_source}",
        f"Log size: {len(raw_log)} chars",
        "",
        "## Detected Categories",
    ]

    if not categories:
        lines.append("- None")
    else:
        for idx, item in enumerate(categories, start=1):
            lines.append(
                f"{idx}. {item['title']} | confidence={item['confidence']:.2f} ({item['level']}) | hits={item['hits']}"
            )

    lines.append("")
    lines.append("## Suggested Commands")
    used = set()
    for item in categories:
        for cmd in fix_commands_for(item["code"]):
            if cmd not in used:
                lines.append(f"- {cmd}")
                used.add(cmd)
    if not used:
        lines.append("- python GradeEstimate/preflight_check.py")

    lines.append("")
    lines.append("## Raw Log (first 2000 chars)")
    lines.append(raw_log[:2000] if raw_log else "(empty)")

    return "\n".join(lines) + "\n"


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

st.subheader("Cloud 日志半自动诊断")
uploaded_log = st.file_uploader(
    "上传 Cloud 日志文件（.txt / .log）",
    type=["txt", "log"],
    accept_multiple_files=False,
)

uploaded_text = ""
if uploaded_log is not None:
    uploaded_text = uploaded_log.getvalue().decode("utf-8", errors="replace")
    st.success(f"已读取日志文件：{uploaded_log.name}")

cloud_log = st.text_area(
    "粘贴 Streamlit Cloud deployment logs",
    height=220,
    placeholder="把 Cloud 日志原文粘贴到这里，然后点击下方按钮分析。",
    value=uploaded_text,
)

active_log = cloud_log.strip()
if active_log:
    with st.expander("日志预览（前40行）"):
        preview = "\n".join(active_log.splitlines()[:40])
        st.code(preview, language="text")

if st.button("分析日志并生成修复清单", use_container_width=True):
    if not active_log:
        st.warning("请先粘贴日志内容。")
    else:
        categories = classify_cloud_log(active_log)
        st.session_state["diag_categories"] = categories
        st.session_state["diag_source"] = uploaded_log.name if uploaded_log is not None else "textbox"
        st.session_state["diag_report"] = build_diagnosis_report(
            st.session_state["diag_source"], categories, active_log
        )

if "diag_categories" in st.session_state:
    categories = st.session_state["diag_categories"]
    if categories:
        st.error(f"识别到 {len(categories)} 类可疑错误")
        for idx, item in enumerate(categories, start=1):
            st.markdown(
                f"{idx}. **{item['title']}** | 置信度: {item['confidence']:.2f} ({item['level']}) | 命中: {item['hits']}"
            )
            st.caption(f"匹配规则: /{item['pattern']}/")
    else:
        st.info("未识别到标准错误模式，建议先执行 preflight 与本地启动验证。")

    st.markdown("**建议修复命令模板**")
    cmd_lines = []
    for item in categories:
        cmd_lines.extend(fix_commands_for(item["code"]))
    if cmd_lines:
        st.code("\n".join(dict.fromkeys(cmd_lines)), language="bash")

    st.markdown("**可复制修复清单（按优先级）**")
    st.code(build_repair_checklist(categories), language="text")

    report_text = st.session_state.get("diag_report", "")
    if report_text:
        st.download_button(
            "下载诊断报告",
            data=report_text,
            file_name="deployment_diagnosis_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

st.subheader("可复制排障命令")
troubleshoot_cmds = """python GradeEstimate/preflight_check.py
python -m streamlit run GradeEstimate/app.py
git status --short -- GradeEstimate
git log --max-count=10 --oneline
"""
st.code(troubleshoot_cmds.strip(), language="bash")
st.caption("可直接复制以上命令到终端，逐条执行定位问题。")

st.info("若 Cloud 仍失败，请把 Deployment logs 复制到这里继续诊断。")
