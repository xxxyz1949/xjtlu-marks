import matplotlib.pyplot as plt

from rank_estimate import DIST, MAX_SCORE, get_rank_curve


def generate_plot(
	score1: float,
	score2: float,
	total_students: int = 3006,
	smooth: bool = True,
	use_second_calibration: bool = True,
	rho: float = 0.75,
):
	"""Generate ranking plot under discrete distribution model."""
	avg_score = (score1 + score2) / 2
	rank_curve = get_rank_curve(
		total_students=total_students,
		smooth=smooth,
		use_second_calibration=use_second_calibration,
	)

	scores = DIST["scores"]
	probs = DIST["probs"]
	x = rank_curve["x"]
	higher_ratio = rank_curve["higher_ratio"]

	fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

	ax1.bar(scores, probs, width=2.0, color="#2f80ed", alpha=0.85, label="Discrete probability mass")
	ax1.axvline(avg_score, color="#d1495b", linestyle="-", linewidth=2, label=f"Your avg score: {avg_score:.2f}")
	ax1.set_ylabel("Probability")
	ax1.set_title("Discrete Average-Score Distribution (from grouped frequencies)")
	ax1.grid(True, alpha=0.25)
	ax1.legend(loc="upper left")

	ax2.plot(x, higher_ratio, color="#f18f01", linewidth=2.5, label="Higher-score ratio")
	ax2.axvline(avg_score, color="#d1495b", linestyle="-", linewidth=2)
	ax2.fill_between(x, 0, higher_ratio, where=(x >= avg_score), alpha=0.2, color="#f18f01")
	ax2.set_xlabel("Average score")
	ax2.set_ylabel("P(score > x)")
	ax2.set_xlim(0, MAX_SCORE)
	ax2.set_ylim(0, 1)
	ax2.grid(True, alpha=0.25)
	ax2.legend(loc="upper right")

	model_label = "A+B (discrete + linear interpolation)" if smooth else "A (discrete step lookup)"
	if use_second_calibration:
		model_label += " + Cal2(high-score tail)"
	fig.suptitle(f"Discrete Rank Model | {model_label} | rho(display only)={rho:.2f}", fontsize=14)
	fig.tight_layout()
	return fig


if __name__ == "__main__":
	output_path = "E:/GradeEstimate/distribution_visual.png"
	chart = generate_plot(100, 100, total_students=3006, smooth=True, use_second_calibration=True, rho=0.75)
	chart.savefig(output_path, dpi=300)
	print(f"Saved plot to: {output_path}")
