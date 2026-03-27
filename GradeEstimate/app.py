import streamlit as st

from rank_estimate import calculate_rank
from plot_visual import generate_plot


def validate_scores(score1: float, score2: float):
    errors = []
    warnings = []

    if not (0 <= score1 <= 100):
        errors.append("MTH007 分数必须在 0 到 100 之间。")
    if not (0 <= score2 <= 100):
        errors.append("MTH013 分数必须在 0 到 100 之间。")

    if score1 < 20:
        warnings.append("MTH007 分数较低，请确认是否输入正确。")
    if score2 < 20:
        warnings.append("MTH013 分数较低，请确认是否输入正确。")

    return errors, warnings


def render_result(score1: float, score2: float, rho: float = 0.75) -> None:
    result = calculate_rank(score1, score2, rho=rho)

    st.subheader("预测结果")
    col1, col2, col3 = st.columns(3)
    col1.metric("预估名次", f"第 {result['rank']} 名")
    col2.metric("超越比例", f"{result['beat_ratio'] * 100:.2f}%")
    col3.metric("参考人数", f"{result['total_students']}")

    st.caption(
        f"双科平均分: {result['avg_score']:.2f} | 相关系数 rho: {result['rho']:.2f} | "
        f"联合分布标准差: {result['std_s']:.2f}"
    )

    report_text = (
        "XJTLU Marks Rank Estimator Report\n"
        f"MTH007: {result['score1']:.2f}\n"
        f"MTH013: {result['score2']:.2f}\n"
        f"Average score: {result['avg_score']:.2f}\n"
        f"rho: {result['rho']:.2f}\n"
        f"Estimated rank: #{result['rank']}\n"
        f"Beat ratio: {result['beat_ratio'] * 100:.2f}%\n"
        f"Base students: {result['total_students']}\n"
    )
    st.download_button(
        "下载本次预测结果",
        data=report_text,
        file_name="rank_prediction_report.txt",
        mime="text/plain",
    )

    fig = generate_plot(score1, score2, rho=rho)
    st.pyplot(fig, clear_figure=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="XJTLU Marks Rank Estimator", page_icon="📊", layout="wide")

    st.title("西浦双科成绩排名估算")
    st.write("输入 MTH007 与 MTH013 分数，系统将基于正态分布模型输出预估排名。")

    with st.form("score_form"):
        left, right = st.columns(2)
        score1 = left.number_input("MTH007 分数", min_value=0.0, max_value=100.0, value=93.0, step=0.5)
        score2 = right.number_input("MTH013 分数", min_value=0.0, max_value=100.0, value=93.0, step=0.5)
        submitted = st.form_submit_button("一键估算排名")

    if submitted:
        errors, warnings = validate_scores(score1, score2)
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            for msg in warnings:
                st.warning(msg)
            render_result(score1, score2, rho=0.75)
    else:
        st.info("填写分数后点击“一键估算排名”查看结果。")


if __name__ == "__main__":
    main()
