import streamlit as st


st.set_page_config(page_title="Cloud Checklist", page_icon="✅", layout="centered")

st.title("Streamlit Cloud 发布 Checklist")
st.caption("最简上线流程（适配 xjtlu-marks 仓库）")

st.markdown("### 1) 代码准备")
st.checkbox("app.py 在 GradeEstimate 目录内")
st.checkbox("requirements.txt 已包含 streamlit/numpy/scipy/matplotlib")
st.checkbox("preflight_check.py 本地检查通过")

st.markdown("### 2) GitHub")
st.checkbox("代码已 push 到仓库 xxxyz1949/xjtlu-marks")
st.checkbox("默认分支包含最新提交")

st.markdown("### 3) Streamlit Community Cloud")
st.checkbox("已登录并绑定 GitHub")
st.checkbox("Main file path 设置为 GradeEstimate/app.py")
st.checkbox("点击 Deploy 后状态为 Running")

st.markdown("### 4) 上线后验证")
st.checkbox("移动端可打开页面")
st.checkbox("输入 93 / 93 返回约第 240 名")
st.checkbox("图表正常渲染，无字体方块问题")

st.info("建议发布前在命令行执行: python GradeEstimate/preflight_check.py")
