import streamlit as st
import datetime as dt
from io import BytesIO

from analytics import register_prediction, register_visit, snapshot
from rank_estimate import calculate_rank


FIXED_TOTAL_STUDENTS = 3006


@st.cache_data(show_spinner=False)
def build_plot_png(score1: int, score2: int, rho: float) -> bytes:
    from plot_visual import generate_plot
    import matplotlib.pyplot as plt

    fig = generate_plot(
        score1,
        score2,
        total_students=FIXED_TOTAL_STUDENTS,
        smooth=True,
        use_second_calibration=True,
        rho=rho,
    )
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


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
            当前采用离散分布模型（先查表后段内线性插值），名次规则为并列名次（competition rank）。
            已启用二次校准：高分段尾部拉开，避免 98/99 与 99/99 过度重叠。
            已启用 83-87 分段聚集修正：体现该分段人数偏多、名次更拥挤。
            固定展示参数：rho = 0.75；评分口径仍为 99 分封顶量化（score/99）。
        </div>
        """,
        unsafe_allow_html=True,
    )


def validate_scores(score1: int, score2: int):
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


def render_result(score1: int, score2: int, rho: float = 0.75) -> None:
    try:
        result = calculate_rank(score1, score2, total_students=FIXED_TOTAL_STUDENTS, rho=rho)
    except Exception:
        st.error("预测结果计算失败，请点击“一键估算排名”重试。")
        return

    st.subheader("预测结果")
    col1, col2, col3 = st.columns(3)
    col1.metric("预估名次", f"第 {result['rank']} 名")
    col2.metric("超越比例", f"{result['beat_ratio'] * 100:.2f}%")
    col3.metric("参考人数", f"{result['total_students']}")

    st.caption(
        f"双科平均分: {result['avg_score']:.2f} | 相关系数 rho: {result['rho']:.2f} | "
        f"量化均分: {result['q_avg_score']:.4f} (99→1) | 模型: {result['model_mode']}"
    )
    st.caption("并列名次规则：同分同名次，后续名次按人数跳号。")

    report_text = (
        "XJTLU Marks Rank Estimator Report\n"
        f"MTH007: {result['score1']}\n"
        f"MTH013: {result['score2']}\n"
        f"Average score: {result['avg_score']:.2f}\n"
        f"Quantized average(score/99): {result['q_avg_score']:.4f}\n"
        f"rho: {result['rho']:.2f}\n"
        f"Model mode: {result['model_mode']}\n"
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

    with st.expander("分布图（按需加载，手机端建议需要时再展开）", expanded=False):
        st.caption("图表加载失败不会影响上方名次结果。")
        try:
            with st.spinner("正在生成分布图..."):
                chart_png = build_plot_png(score1, score2, rho)
            st.image(chart_png, use_container_width=True)
        except Exception:
            st.warning("分布图生成失败，请稍后重试；名次结果已正常给出。")


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

    left, right = st.columns([1, 1], gap="small")
    score1 = left.number_input("MTH007 分数", min_value=0, max_value=99, value=0, step=1, format="%d")
    score2 = right.number_input("MTH013 分数", min_value=0, max_value=99, value=0, step=1, format="%d")
    st.caption(f"总人数固定为 {FIXED_TOTAL_STUDENTS}（不可修改）")
    submitted = st.button("一键估算排名", use_container_width=True, type="primary")

    if "last_submitted_input" not in st.session_state:
        st.session_state["last_submitted_input"] = None
    if "last_valid_result_input" not in st.session_state:
        st.session_state["last_valid_result_input"] = None

    last_submitted = st.session_state["last_submitted_input"]
    last_valid_result = st.session_state["last_valid_result_input"]
    current_input = {
        "score1": int(score1),
        "score2": int(score2),
    }

    if submitted:
        errors, warnings = validate_scores(score1, score2)
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            st.session_state["last_submitted_input"] = current_input
            st.session_state["last_valid_result_input"] = current_input
            for msg in warnings:
                st.warning(msg)
            register_prediction()
            render_result(score1, score2, rho=0.75)
    else:
        if last_valid_result is None:
            st.info("填写分数后点击“一键估算排名”查看结果。")
        elif current_input != last_valid_result:
            st.info("你已修改输入，但尚未重新估算。当前展示的是上一次有效预测结果。")
            render_result(last_valid_result["score1"], last_valid_result["score2"], rho=0.75)
        else:
            st.info("当前输入与上次预测一致，已展示最新结果。")
            render_result(current_input["score1"], current_input["score2"], rho=0.75)


if __name__ == "__main__":
    main()
