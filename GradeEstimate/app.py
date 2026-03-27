import streamlit as st
import datetime as dt

from analytics import register_prediction, register_visit, snapshot
from rank_estimate import calculate_rank
from plot_visual import generate_plot


def apply_page_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(1200px 500px at 10% -20%, #d7eefb 0%, transparent 60%),
                radial-gradient(900px 450px at 100% 0%, #ffe9c7 0%, transparent 60%),
                #f8fafc;
        }
        .hero-card {
            background: linear-gradient(135deg, #0f4c81 0%, #1d7ab6 60%, #38a3d1 100%);
            border-radius: 18px;
            padding: 20px 22px;
            color: #ffffff;
            box-shadow: 0 10px 24px rgba(15, 76, 129, 0.22);
            margin-bottom: 14px;
        }
        .hero-title {
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 6px;
        }
        .hero-sub {
            font-size: 1rem;
            opacity: 0.95;
            margin: 0;
        }
        .hint-card {
            background: #ffffff;
            border: 1px solid #dbe7ef;
            border-radius: 12px;
            padding: 10px 12px;
            color: #1f2a37;
            margin-bottom: 10px;
        }
        @media (max-width: 768px) {
            .hero-card {
                padding: 16px;
                border-radius: 14px;
            }
            .hero-title {
                font-size: 1.4rem;
            }
            .hero-sub {
                font-size: 0.95rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">XJTLU 双科成绩排名估算</div>
            <p class="hero-sub">输入 MTH007 与 MTH013 分数，快速获得预估名次、超越比例与分布图。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="hint-card">
            固定模型参数：rho = 0.75，参考人数 3009。采用 99 分封顶量化（score/99），即 99 → 1。
        </div>
        """,
        unsafe_allow_html=True,
    )


def validate_scores(score1: float, score2: float):
    errors = []
    warnings = []

    if not (0 <= score1 <= 99):
        errors.append("MTH007 分数必须在 0 到 99 之间。")
    if not (0 <= score2 <= 99):
        errors.append("MTH013 分数必须在 0 到 99 之间。")

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
        f"量化均分: {result['q_avg_score']:.4f} (99→1) | 量化联合标准差: {result['q_std_s']:.4f}"
    )

    report_text = (
        "XJTLU Marks Rank Estimator Report\n"
        f"MTH007: {result['score1']:.2f}\n"
        f"MTH013: {result['score2']:.2f}\n"
        f"Average score: {result['avg_score']:.2f}\n"
        f"Quantized average(score/99): {result['q_avg_score']:.4f}\n"
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
    register_visit()
    apply_page_style()
    render_header()

    with st.sidebar:
        st.subheader("导航")
        st.write("可在左侧页面列表打开 Cloud Checklist 页面。")
        st.write("发布前可运行 preflight_check.py 进行一键检查。")
        stats = snapshot()
        st.divider()
        st.subheader("轻量访问统计")
        st.metric("运行期总访问", stats["total_visits"])
        st.metric("运行期总预测", stats["total_predictions"])
        st.metric("本会话预测次数", stats["session_predictions"])
        start_text = dt.datetime.fromtimestamp(stats["session_start_ts"]).strftime("%H:%M:%S")
        st.caption(f"会话开始: {start_text}")
        st.caption(f"会话停留: {stats['session_elapsed_sec']} 秒")

    with st.form("score_form"):
        left, right = st.columns([1, 1], gap="small")
        score1 = left.number_input("MTH007 分数", min_value=0.0, max_value=99.0, value=93.0, step=0.5)
        score2 = right.number_input("MTH013 分数", min_value=0.0, max_value=99.0, value=93.0, step=0.5)
        submitted = st.form_submit_button("一键估算排名", use_container_width=True)

    if submitted:
        errors, warnings = validate_scores(score1, score2)
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            for msg in warnings:
                st.warning(msg)
            register_prediction()
            render_result(score1, score2, rho=0.75)
    else:
        st.info("填写分数后点击“一键估算排名”查看结果。")


if __name__ == "__main__":
    main()
