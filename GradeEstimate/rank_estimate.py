import numpy as np
from functools import lru_cache


# === 基础统计常量（由分段表估算） ===
MIDPOINTS = np.array([17, 37, 45, 55, 65, 75, 85, 95])
BIN_EDGES = np.array([0, 30, 40, 50, 60, 70, 80, 90, 100])
MAX_SCORE = 99.0
SECOND_CALIBRATION_THRESHOLD = 82.0
SECOND_CALIBRATION_ALPHA = 4.2
SECOND_CALIBRATION_GAMMA = 0.9
RANK_CURVE_POINTS = 260

PROFILE_CONFIGS = {
    "mth007_013": {
        "subject1": "MTH007",
        "subject2": "MTH013",
        "n1": 3500,
        "mu1": 68,
        "freq1": np.array([176, 116, 348, 526, 584, 658, 607, 485]),
        "n2": 3009,
        "mu2": 73,
        "freq2": np.array([43, 16, 123, 270, 555, 937, 887, 178]),
    },
    "mth017_029": {
        "subject1": "MTH017",
        "subject2": "MTH029",
        "n1": 583,
        "mu1": 67,
        "freq1": np.array([17, 6, 53, 113, 111, 151, 105, 27]),
        "n2": 540,
        "mu2": 74,
        "freq2": np.array([6, 3, 29, 44, 88, 138, 178, 54]),
    },
}


def get_profile_meta(profile: str = "mth017_029") -> dict:
    if profile not in PROFILE_CONFIGS:
        raise ValueError(f"Unsupported profile: {profile}")
    cfg = PROFILE_CONFIGS[profile]
    return {
        "profile": profile,
        "subject1": cfg["subject1"],
        "subject2": cfg["subject2"],
        "n1": cfg["n1"],
        "n2": cfg["n2"],
    }


def _get_profile_config(profile: str) -> dict:
    if profile not in PROFILE_CONFIGS:
        raise ValueError(f"Unsupported profile: {profile}")
    return PROFILE_CONFIGS[profile]


@lru_cache(maxsize=8)
def _build_joint_avg_distribution(profile: str) -> dict:
    """
    基于两科分段频率构建联合平均分离散分布。
    采用独立近似：P(S1=i,S2=j)=P1(i)*P2(j)。
    每个分段内部按整数均匀展开，再做卷积得到平均分分布。
    """
    def build_subject_pmf(freq: np.ndarray) -> np.ndarray:
        pmf = np.zeros(int(MAX_SCORE) + 1, dtype=float)
        total = float(freq.sum())

        for i, f in enumerate(freq):
            left = int(BIN_EDGES[i])
            right = int(BIN_EDGES[i + 1])
            width = right - left
            if width <= 0:
                continue
            pmf[left:right] += (float(f) / total) / width

        pmf /= pmf.sum()
        return pmf

    cfg = _get_profile_config(profile)
    pmf1 = build_subject_pmf(cfg["freq1"])
    pmf2 = build_subject_pmf(cfg["freq2"])

    sum_pmf = np.convolve(pmf1, pmf2)
    sum_scores = np.arange(sum_pmf.size)
    scores = sum_scores / 2.0
    probs = sum_pmf / sum_pmf.sum()
    cdf = np.cumsum(probs)

    return {
        "scores": scores,
        "probs": probs,
        "cdf": cdf,
    }


def get_distribution(profile: str = "mth017_029") -> dict:
    return _build_joint_avg_distribution(profile)


def _compute_base_stats(profile: str) -> dict:
    cfg = _get_profile_config(profile)
    var1 = np.sum(cfg["freq1"] * (MIDPOINTS - cfg["mu1"]) ** 2) / cfg["n1"]
    std1 = np.sqrt(var1)
    var2 = np.sum(cfg["freq2"] * (MIDPOINTS - cfg["mu2"]) ** 2) / cfg["n2"]
    std2 = np.sqrt(var2)

    return {
        "var1": var1,
        "std1": std1,
        "var2": var2,
        "std2": std2,
        "mu_s": (cfg["mu1"] + cfg["mu2"]) / 2,
        "total_students": min(cfg["n1"], cfg["n2"]),
    }


def _quantize(score: float) -> float:
    """Map score to quantified value in [0, 1] where 99 -> 1."""
    return float(score) / MAX_SCORE


def _exact_higher_ratio(avg_score: float, profile: str) -> tuple[float, float]:
    """离散查表（A）：返回严格高于比例与小于等于比例。"""
    dist = get_distribution(profile)
    scores = dist["scores"]
    cdf = dist["cdf"]

    idx = np.searchsorted(scores, avg_score, side="right") - 1
    if idx < 0:
        cdf_leq = 0.0
    else:
        cdf_leq = float(cdf[idx])

    higher_ratio = max(0.0, min(1.0, 1.0 - cdf_leq))
    return higher_ratio, cdf_leq


def _smoothed_higher_ratio(avg_score: float, profile: str) -> tuple[float, float]:
    """段内线性插值（B）：在分段点之间平滑CDF。"""
    dist = get_distribution(profile)
    scores = dist["scores"]
    cdf = dist["cdf"]

    low_anchor_x = 0.0
    high_anchor_x = MAX_SCORE
    low_score = float(scores[0])
    high_score = float(scores[-1])
    cdf_low = float(cdf[0])
    cdf_high = float(cdf[-1])

    if avg_score <= low_anchor_x:
        return 1.0, 0.0

    if avg_score >= high_anchor_x:
        return 0.0, 1.0

    if avg_score < low_score:
        t = (avg_score - low_anchor_x) / (low_score - low_anchor_x)
        cdf_leq = t * cdf_low
        higher_ratio = max(0.0, min(1.0, 1.0 - cdf_leq))
        return higher_ratio, cdf_leq

    if avg_score > high_score:
        # 将 95~99 之间外推到 cdf=1，避免高分段直接坍缩到 rank 1。
        t = (avg_score - high_score) / (high_anchor_x - high_score)
        cdf_leq = cdf_high + t * (1.0 - cdf_high)
        higher_ratio = max(0.0, min(1.0, 1.0 - cdf_leq))
        return higher_ratio, cdf_leq

    # 命中离散分值时，不做插值，确保同分同名次
    if np.any(np.isclose(scores, avg_score, atol=1e-12)):
        return _exact_higher_ratio(avg_score, profile)

    right = int(np.searchsorted(scores, avg_score, side="right"))
    left = right - 1

    x0 = float(scores[left])
    x1 = float(scores[right])
    y0 = float(cdf[left])
    y1 = float(cdf[right])

    t = (avg_score - x0) / (x1 - x0)
    cdf_leq = y0 + t * (y1 - y0)
    higher_ratio = max(0.0, min(1.0, 1.0 - cdf_leq))
    return higher_ratio, cdf_leq


def get_rank_curve(
    total_students: int = 3006,
    smooth: bool = True,
    use_second_calibration: bool = True,
    profile: str = "mth017_029",
) -> dict:
    """返回可用于绘图的离散/平滑排名曲线数据。"""
    x = np.linspace(0, MAX_SCORE, RANK_CURVE_POINTS)
    higher = []
    rank = []
    for xi in x:
        h, _ = (
            _smoothed_higher_ratio(xi, profile)
            if smooth
            else _exact_higher_ratio(xi, profile)
        )
        if use_second_calibration:
            h = _apply_second_calibration(float(xi), h)
        higher.append(h)
        rank.append(int(total_students * h) + 1)

    dist = get_distribution(profile)

    return {
        "x": x,
        "higher_ratio": np.array(higher),
        "rank": np.array(rank),
        "scores": dist["scores"],
        "probs": dist["probs"],
        "cdf": dist["cdf"],
        "second_calibration": use_second_calibration,
        "profile": profile,
    }


def _apply_second_calibration(avg_score: float, upper_tail: float) -> float:
    """二次校准：高分段尾部膨胀，避免 98/99 等样例在小样本下塌缩到 rank 1。"""
    if avg_score < SECOND_CALIBRATION_THRESHOLD:
        return upper_tail

    span = MAX_SCORE - SECOND_CALIBRATION_THRESHOLD
    if span <= 0:
        return upper_tail

    t = (avg_score - SECOND_CALIBRATION_THRESHOLD) / span
    t = max(0.0, min(1.0, t))
    multiplier = 1.0 + SECOND_CALIBRATION_ALPHA * (t ** SECOND_CALIBRATION_GAMMA)
    calibrated = upper_tail * multiplier
    return max(0.0, min(1.0, calibrated))


def calculate_rank(
    score1: int,
    score2: int,
    total_students: int = 3006,
    rho: float = 0.75,
    use_smoothing: bool = True,
    use_second_calibration: bool = True,
    profile: str = "mth017_029",
) -> dict:
    """根据两科整数成绩和总人数，返回离散模型下的排名估计结果。"""
    stats_base = _compute_base_stats(profile)
    meta = get_profile_meta(profile)
    score1 = int(score1)
    score2 = int(score2)
    total_students = int(total_students)
    avg_score = (score1 + score2) / 2

    q_score1 = _quantize(score1)
    q_score2 = _quantize(score2)
    q_avg_score = _quantize(avg_score)

    q_var1 = stats_base["var1"] / (MAX_SCORE**2)
    q_var2 = stats_base["var2"] / (MAX_SCORE**2)
    q_std1 = stats_base["std1"] / MAX_SCORE
    q_std2 = stats_base["std2"] / MAX_SCORE
    q_mu_s = stats_base["mu_s"] / MAX_SCORE

    q_var_s = (q_var1 + q_var2 + 2 * rho * q_std1 * q_std2) / 4
    q_std_s = np.sqrt(q_var_s)

    if use_smoothing:
        upper_tail, cdf_leq = _smoothed_higher_ratio(avg_score, profile)
    else:
        upper_tail, cdf_leq = _exact_higher_ratio(avg_score, profile)

    raw_upper_tail = upper_tail

    if use_second_calibration:
        upper_tail = _apply_second_calibration(avg_score, upper_tail)
        cdf_leq = 1.0 - upper_tail

    # 并列名次（competition rank）：名次=严格高于你的人数+1
    rank = int(total_students * upper_tail) + 1
    rank = max(1, min(total_students, rank))
    beat_ratio = cdf_leq

    # 业务硬约束：双科都达到最高分(99)时，名次直接判定为第1名。
    if score1 >= MAX_SCORE and score2 >= MAX_SCORE:
        upper_tail = 0.0
        beat_ratio = 1.0
        rank = 1

    return {
        "score1": score1,
        "score2": score2,
        "subject1": meta["subject1"],
        "subject2": meta["subject2"],
        "profile": profile,
        "avg_score": avg_score,
        "rho": rho,
        "rank": rank,
        "beat_ratio": beat_ratio,
        "upper_tail": upper_tail,
        "raw_upper_tail": raw_upper_tail,
        "model_mode": (
            "discrete_smooth_cal2"
            if (use_smoothing and use_second_calibration)
            else "discrete_smooth"
            if use_smoothing
            else "discrete_step_cal2"
            if use_second_calibration
            else "discrete_step"
        ),
        "second_calibration": use_second_calibration,
        "std_s": q_std_s,
        "mu_s": stats_base["mu_s"],
        "total_students": total_students,
        "std1": stats_base["std1"],
        "std2": stats_base["std2"],
        "max_score": MAX_SCORE,
        "q_score1": q_score1,
        "q_score2": q_score2,
        "q_avg_score": q_avg_score,
        "q_mu_s": q_mu_s,
        "q_std_s": q_std_s,
    }


if __name__ == "__main__":
    profile = "mth017_029"
    score1 = 0
    score2 = 0
    total_students = 3006
    rhos = [0.5, 0.6, 0.7, 0.75, 0.8, 0.9]
    base = _compute_base_stats(profile)
    meta = get_profile_meta(profile)

    print(f"{meta['subject1']} -> mean: {PROFILE_CONFIGS[profile]['mu1']}, std(est): {base['std1']:.2f}")
    print(f"{meta['subject2']} -> mean: {PROFILE_CONFIGS[profile]['mu2']}, std(est): {base['std2']:.2f}")
    print(f"Your average score: {(score1 + score2) / 2:.2f}")
    print(f"Quantized average (99 -> 1): {((score1 + score2) / 2) / MAX_SCORE:.4f}")
    print("-" * 40)
    print(f">>> Estimated ranking under different rho values ({meta['subject1']}+{meta['subject2']}, base students: {total_students}) <<<")

    for rho in rhos:
        result = calculate_rank(score1, score2, total_students=total_students, rho=rho, profile=profile)
        print(
            f"rho = {rho:.2f}: quantized std(avg)={result['q_std_s']:.4f}, "
            f"beat={result['beat_ratio'] * 100:.2f}%, rank≈#{result['rank']}"
        )
