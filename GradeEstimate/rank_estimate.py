import numpy as np
import scipy.stats as stats


# === 基础统计常量（由分段表估算） ===
MIDPOINTS = np.array([17, 37, 45, 55, 65, 75, 85, 95])
N1 = 3500
MU1 = 68
FREQ1 = np.array([176, 116, 348, 526, 584, 658, 607, 485])

N2 = 3009
MU2 = 73
FREQ2 = np.array([43, 16, 123, 270, 555, 937, 887, 178])
MAX_SCORE = 99.0


def _compute_base_stats() -> dict:
    var1 = np.sum(FREQ1 * (MIDPOINTS - MU1) ** 2) / N1
    std1 = np.sqrt(var1)
    var2 = np.sum(FREQ2 * (MIDPOINTS - MU2) ** 2) / N2
    std2 = np.sqrt(var2)

    return {
        "var1": var1,
        "std1": std1,
        "var2": var2,
        "std2": std2,
        "mu_s": (MU1 + MU2) / 2,
        "total_students": min(N1, N2),
    }


def _quantize(score: float) -> float:
    """Map score to quantified value in [0, 1] where 99 -> 1."""
    return float(score) / MAX_SCORE


def calculate_rank(score1: float, score2: float, rho: float = 0.75) -> dict:
    """根据两科成绩和相关系数，返回排名估计结果。"""
    stats_base = _compute_base_stats()
    avg_score = (score1 + score2) / 2

    q_score1 = _quantize(score1)
    q_score2 = _quantize(score2)
    q_avg_score = _quantize(avg_score)

    q_var1 = stats_base["var1"] / (MAX_SCORE**2)
    q_var2 = stats_base["var2"] / (MAX_SCORE**2)
    q_std1 = stats_base["std1"] / MAX_SCORE
    q_std2 = stats_base["std2"] / MAX_SCORE
    q_mu_s = stats_base["mu_s"] / MAX_SCORE

    q_var_s = (
        q_var1
        + q_var2
        + 2 * rho * q_std1 * q_std2
    ) / 4
    q_std_s = np.sqrt(q_var_s)
    z = (q_avg_score - q_mu_s) / q_std_s
    upper_tail = 1 - stats.norm.cdf(z)
    beat_ratio = 1 - upper_tail
    rank = int(stats_base["total_students"] * upper_tail) + 1

    # 业务硬约束：双科都达到最高分(99)时，名次直接判定为第1名。
    if score1 >= MAX_SCORE and score2 >= MAX_SCORE:
        upper_tail = 0.0
        beat_ratio = 1.0
        rank = 1

    return {
        "score1": score1,
        "score2": score2,
        "avg_score": avg_score,
        "rho": rho,
        "rank": rank,
        "beat_ratio": beat_ratio,
        "upper_tail": upper_tail,
        "std_s": q_std_s,
        "mu_s": stats_base["mu_s"],
        "total_students": stats_base["total_students"],
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
    score1 = 99
    score2 = 99
    rhos = [0.5, 0.6, 0.7, 0.75, 0.8, 0.9]
    base = _compute_base_stats()

    print(f"MTH007 -> mean: {MU1}, std(est): {base['std1']:.2f}")
    print(f"MTH013 -> mean: {MU2}, std(est): {base['std2']:.2f}")
    print(f"Your average score: {(score1 + score2) / 2:.2f}")
    print(f"Quantized average (99 -> 1): {((score1 + score2) / 2) / MAX_SCORE:.4f}")
    print("-" * 40)
    print(
        f">>> Estimated ranking under different rho values (base students: {base['total_students']}) <<<"
    )

    for rho in rhos:
        result = calculate_rank(score1, score2, rho=rho)
        print(
            f"rho = {rho:.2f}: quantized std(avg)={result['q_std_s']:.4f}, "
            f"beat={result['beat_ratio'] * 100:.2f}%, rank≈#{result['rank']}"
        )
