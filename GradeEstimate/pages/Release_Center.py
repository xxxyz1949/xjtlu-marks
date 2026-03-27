from pathlib import Path

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

if version_file.exists():
    st.subheader("当前版本")
    st.code(version_file.read_text(encoding="utf-8"), language="text")

if changelog_file.exists():
    st.subheader("当前更新摘要")
    st.text(changelog_file.read_text(encoding="utf-8"))
