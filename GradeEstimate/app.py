import streamlit as st
import datetime as dt
from io import BytesIO

from analytics import register_prediction, register_visit, snapshot
import rank_estimate


PROFILE_TOTAL_STUDENTS = {
    "mth007_013": 3006,
    "mth017_029": 540,
}
PROFILE_ORDER = ["mth007_013", "mth017_029"]
PROFILE_META_FALLBACK = {
    "mth007_013": {"subject1": "MTH007", "subject2": "MTH013"},
    "mth017_029": {"subject1": "MTH017", "subject2": "MTH029"},
}


def _get_profile_meta_safe(profile: str) -> dict:
    getter = getattr(rank_estimate, "get_profile_meta", None)
    if callable(getter):
        return getter(profile)
    if profile in PROFILE_META_FALLBACK:
        meta = PROFILE_META_FALLBACK[profile]
        return {
            "profile": profile,
            "subject1": meta["subject1"],
            "subject2": meta["subject2"],
            "n1": PROFILE_TOTAL_STUDENTS.get(profile, 3006),
            "n2": PROFILE_TOTAL_STUDENTS.get(profile, 3006),
        }
    raise ValueError(f"Unsupported profile: {profile}")


@st.cache_data(show_spinner=False)
def build_plot_png(score1: int, score2: int, rho: float, profile: str) -> bytes:
    from plot_visual import generate_plot
    import matplotlib.pyplot as plt

    fig = generate_plot(
        score1,
        score2,
        total_students=PROFILE_TOTAL_STUDENTS.get(profile, 3006),
        smooth=True,
        use_second_calibration=True,
        rho=rho,
        profile=profile,
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
            section[data-testid="stSidebar"] {
                display: none;
            }
            button[data-testid="collapsedControl"] {
                display: none;
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
            <p class="hero-sub">同时输入 MTH007+MTH013 与 MTH017+MTH029 分数，分别获得两组预估名次。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="hint-card">
            当前采用离散分布模型（先查表后段内线性插值），名次规则为并列名次（competition rank）。
            已启用二次校准：高分段尾部拉开，避免 98/99 与 99/99 过度重叠。
            当前页面同时展示两组课程：MTH007+MTH013 与 MTH017+MTH029。
            固定展示参数：rho = 0.75；评分口径仍为 99 分封顶量化（score/99）。
        </div>
        """,
        unsafe_allow_html=True,
    )


def validate_scores(score1: int, score2: int, subject1: str, subject2: str):
    errors = []
    warnings = []

    if not (0 <= score1 <= 99):
        errors.append(f"{subject1} 分数必须在 0 到 99 之间。")
    if not (0 <= score2 <= 99):
        errors.append(f"{subject2} 分数必须在 0 到 99 之间。")

    if score1 < 20:
        warnings.append(f"{subject1} 分数较低，请确认是否输入正确。")
    if score2 < 20:
        warnings.append(f"{subject2} 分数较低，请确认是否输入正确。")

    return errors, warnings


def render_result(
    score1: int,
    score2: int,
    profile: str,
    section_title: str,
    key_prefix: str,
    rho: float = 0.75,
) -> None:
    meta = _get_profile_meta_safe(profile)
    total_students = PROFILE_TOTAL_STUDENTS.get(profile, 3006)
    try:
        result = rank_estimate.calculate_rank(
            score1,
            score2,
            total_students=total_students,
            rho=rho,
            profile=profile,
        )
    except Exception:
        st.error(f"{section_title} 预测结果计算失败，请点击“一键估算排名”重试。")
        return

    st.subheader(f"{section_title} 预测结果")
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
        f"Profile: {profile}\n"
        f"{meta['subject1']}: {result['score1']}\n"
        f"{meta['subject2']}: {result['score2']}\n"
        f"Average score: {result['avg_score']:.2f}\n"
        f"Quantized average(score/99): {result['q_avg_score']:.4f}\n"
        f"rho: {result['rho']:.2f}\n"
        f"Model mode: {result['model_mode']}\n"
        f"Estimated rank: #{result['rank']}\n"
        f"Beat ratio: {result['beat_ratio'] * 100:.2f}%\n"
        f"Base students: {result['total_students']}\n"
    )
    st.download_button(
        f"下载 {section_title} 预测结果",
        data=report_text,
        file_name=f"rank_prediction_report_{profile}.txt",
        mime="text/plain",
        key=f"download_{key_prefix}",
    )

    with st.expander(f"{section_title} 分布图（按需加载，手机端建议需要时再展开）", expanded=False):
        st.caption("图表加载失败不会影响上方名次结果。")
        try:
            with st.spinner("正在生成分布图..."):
                chart_png = build_plot_png(score1, score2, rho, profile)
            st.image(chart_png, use_container_width=True)
        except Exception:
            st.warning("分布图生成失败，请稍后重试；名次结果已正常给出。")


def main() -> None:
    st.set_page_config(
        page_title="XJTLU Marks Rank Estimator",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    register_visit()
    apply_page_style()
    render_header()

    with st.sidebar:
        st.subheader("导航")
        st.write("可在左侧页面列表打开 Cloud Checklist 页面。")
        st.write("发布前可运行 preflight_check.py 进行一键检查。")
        st.divider()
        show_stats = st.checkbox("显示运行统计", value=False)
        if show_stats:
            stats = snapshot()
            st.subheader("轻量访问统计")
            st.metric("运行期总访问", stats["total_visits"])
            st.metric("运行期总预测", stats["total_predictions"])
            st.metric("本会话预测次数", stats["session_predictions"])
            start_text = dt.datetime.fromtimestamp(stats["session_start_ts"]).strftime("%H:%M:%S")
            st.caption(f"会话开始: {start_text}")
            st.caption(f"会话停留: {stats['session_elapsed_sec']} 秒")

    p1_left, p1_right = st.columns([1, 1], gap="small")
    score_007 = p1_left.number_input("MTH007 分数", min_value=0, max_value=99, value=0, step=1, format="%d")
    score_013 = p1_right.number_input("MTH013 分数", min_value=0, max_value=99, value=0, step=1, format="%d")

    p2_left, p2_right = st.columns([1, 1], gap="small")
    score_017 = p2_left.number_input("MTH017 分数", min_value=0, max_value=99, value=0, step=1, format="%d")
    score_029 = p2_right.number_input("MTH029 分数", min_value=0, max_value=99, value=0, step=1, format="%d")

    st.caption(
        f"总人数固定：MTH007+MTH013 = {PROFILE_TOTAL_STUDENTS['mth007_013']}；"
        f"MTH017+MTH029 = {PROFILE_TOTAL_STUDENTS['mth017_029']}（不可修改）"
    )
    submitted = st.button("一键估算排名（两组同时）", use_container_width=True, type="primary")

    if "last_valid_result_input" not in st.session_state:
        st.session_state["last_valid_result_input"] = None

    last_valid_result = st.session_state["last_valid_result_input"]
    current_input = {
        "mth007_013": {
            "score1": int(score_007),
            "score2": int(score_013),
        },
        "mth017_029": {
            "score1": int(score_017),
            "score2": int(score_029),
        },
    }

    if submitted:
        errors = []
        warnings = []
        for profile in PROFILE_ORDER:
            meta = _get_profile_meta_safe(profile)
            pair_input = current_input[profile]
            e, w = validate_scores(pair_input["score1"], pair_input["score2"], meta["subject1"], meta["subject2"])
            errors.extend(e)
            warnings.extend(w)

        if errors:
            for msg in errors:
                st.error(msg)
        else:
            st.session_state["last_valid_result_input"] = current_input
            for msg in warnings:
                st.warning(msg)
            register_prediction()
            render_result(
                current_input["mth007_013"]["score1"],
                current_input["mth007_013"]["score2"],
                profile="mth007_013",
                section_title="MTH007 + MTH013",
                key_prefix="mth007_013",
                rho=0.75,
            )
            render_result(
                current_input["mth017_029"]["score1"],
                current_input["mth017_029"]["score2"],
                profile="mth017_029",
                section_title="MTH017 + MTH029",
                key_prefix="mth017_029",
                rho=0.75,
            )
    else:
        if last_valid_result is None:
            st.info("填写分数后点击“一键估算排名”查看结果。")
        elif current_input != last_valid_result:
            st.info("你已修改输入，但尚未重新估算。当前展示的是上一次有效预测结果（两组）。")
            render_result(
                last_valid_result["mth007_013"]["score1"],
                last_valid_result["mth007_013"]["score2"],
                profile="mth007_013",
                section_title="MTH007 + MTH013",
                key_prefix="mth007_013_last",
                rho=0.75,
            )
            render_result(
                last_valid_result["mth017_029"]["score1"],
                last_valid_result["mth017_029"]["score2"],
                profile="mth017_029",
                section_title="MTH017 + MTH029",
                key_prefix="mth017_029_last",
                rho=0.75,
            )
        else:
            st.info("当前输入与上次预测一致，已展示两组最新结果。")
            render_result(
                current_input["mth007_013"]["score1"],
                current_input["mth007_013"]["score2"],
                profile="mth007_013",
                section_title="MTH007 + MTH013",
                key_prefix="mth007_013_now",
                rho=0.75,
            )
            render_result(
                current_input["mth017_029"]["score1"],
                current_input["mth017_029"]["score2"],
                profile="mth017_029",
                section_title="MTH017 + MTH029",
                key_prefix="mth017_029_now",
                rho=0.75,
            )


if __name__ == "__main__":
    main()
