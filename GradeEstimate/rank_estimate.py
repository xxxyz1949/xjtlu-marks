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


def calculate_rank(score1: float, score2: float, rho: float = 0.75) -> dict:
    """根据两科成绩和相关系数，返回排名估计结果。"""
    stats_base = _compute_base_stats()
    avg_score = (score1 + score2) / 2

    var_s = (
        stats_base["var1"]
        + stats_base["var2"]
        + 2 * rho * stats_base["std1"] * stats_base["std2"]
    ) / 4
    std_s = np.sqrt(var_s)
    z = (avg_score - stats_base["mu_s"]) / std_s
    upper_tail = 1 - stats.norm.cdf(z)
    beat_ratio = 1 - upper_tail
    rank = int(stats_base["total_students"] * upper_tail) + 1

    return {
        "score1": score1,
        "score2": score2,
        "avg_score": avg_score,
        "rho": rho,
        "rank": rank,
        "beat_ratio": beat_ratio,
        "upper_tail": upper_tail,
        "std_s": std_s,
        "mu_s": stats_base["mu_s"],
        "total_students": stats_base["total_students"],
        "std1": stats_base["std1"],
        "std2": stats_base["std2"],
    }


if __name__ == "__main__":
    score1 = 93
    score2 = 93
    rhos = [0.5, 0.6, 0.7, 0.75, 0.8, 0.9]
    base = _compute_base_stats()

    print(f"MTH007 -> mean: {MU1}, std(est): {base['std1']:.2f}")
    print(f"MTH013 -> mean: {MU2}, std(est): {base['std2']:.2f}")
    print(f"Your average score: {(score1 + score2) / 2:.2f}")
    print("-" * 40)
    print(
        f">>> Estimated ranking under different rho values (base students: {base['total_students']}) <<<"
    )

    for rho in rhos:
        result = calculate_rank(score1, score2, rho=rho)
        print(
            f"rho = {rho:.2f}: std(avg)={result['std_s']:.2f}, "
            f"beat={result['beat_ratio'] * 100:.2f}%, rank≈#{result['rank']}"
        )
