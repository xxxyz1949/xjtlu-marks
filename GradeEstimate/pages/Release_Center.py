from pathlib import Path
import datetime as dt

import streamlit as st

from release_tools import generate_release_assets


st.set_page_config(page_title="Release Center", page_icon="🏷️", layout="centered")

st.title("版本与更新摘要")
st.caption("一键生成 VERSION 与 CHANGELOG_SUMMARY.md")

bump_level = st.selectbox("版本提升级别", ["patch", "minor", "major"], index=0)

if st.button("一键生成版本号与更新日志摘要", use_container_width=True):
    project_dir = Path(__file__).resolve().parents[1]
    result = generate_release_assets(project_dir, bump=bump_level)

    st.success(f"已生成版本: {result['version']}")
    st.code(f"VERSION -> {result['version_file']}\nCHANGELOG -> {result['changelog_file']}", language="text")

version_file = Path(__file__).resolve().parents[1] / "VERSION"
changelog_file = Path(__file__).resolve().parents[1] / "CHANGELOG_SUMMARY.md"
today = dt.datetime.now().strftime("%Y%m%d")

if version_file.exists():
    st.subheader("当前版本")
    current_version = version_file.read_text(encoding="utf-8").strip()
    st.code(current_version, language="text")

    suggested_tag = f"v{current_version}-{today}"
    st.subheader("自动标签建议")
    st.code(suggested_tag, language="text")

    st.subheader("建议发布命令")
    release_cmd = (
        f"git tag {suggested_tag}\n"
        f"git push origin {suggested_tag}"
    )
    st.code(release_cmd, language="bash")

    st.subheader("完整发布命令（可一键复制）")
    full_publish_cmd = (
        "python GradeEstimate/release_tools.py\n"
        "git add GradeEstimate/VERSION GradeEstimate/CHANGELOG_SUMMARY.md\n"
        f"git commit -m \"chore: release {suggested_tag}\"\n"
        "git push origin master\n"
        f"git tag {suggested_tag}\n"
        f"git push origin {suggested_tag}"
    )
    st.code(full_publish_cmd, language="bash")
    st.caption("提示：代码块右上角复制图标可直接复制完整命令。")

if changelog_file.exists():
    st.subheader("当前更新摘要")
    st.text(changelog_file.read_text(encoding="utf-8"))
