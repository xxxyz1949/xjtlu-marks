import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt


MAX_SCORE = 99.0


def generate_plot(
	score1: float,
	score2: float,
	rho: float = 0.75,
	mu1: float = 68,
	std1: float = 20.06,
	mu2: float = 73,
	std2: float = 14.03,
):
	"""Generate ranking distribution plot under quantified model (99 -> 1)."""
	q_score1 = score1 / MAX_SCORE
	q_score2 = score2 / MAX_SCORE
	q_avg_score = (q_score1 + q_score2) / 2

	q_mu1 = mu1 / MAX_SCORE
	q_std1 = std1 / MAX_SCORE
	q_mu2 = mu2 / MAX_SCORE
	q_std2 = std2 / MAX_SCORE

	q_mu_s = (q_mu1 + q_mu2) / 2
	q_var_s = (q_std1**2 + q_std2**2 + 2 * rho * q_std1 * q_std2) / 4
	q_std_s = q_var_s ** 0.5

	x = np.linspace(0, 1.0, 1000)
	fig, ax = plt.subplots(figsize=(12, 6))

	ax.plot(
		x,
		stats.norm.pdf(x, q_mu1, q_std1),
		label=f"MTH007 $\\mu={q_mu1:.3f}, \\sigma={q_std1:.3f}$",
		color="blue",
		linestyle="--",
	)
	ax.plot(
		x,
		stats.norm.pdf(x, q_mu2, q_std2),
		label=f"MTH013 $\\mu={q_mu2:.3f}, \\sigma={q_std2:.3f}$",
		color="green",
		linestyle="--",
	)

	y_s = stats.norm.pdf(x, q_mu_s, q_std_s)
	ax.plot(
		x,
		y_s,
		label=f"Quantized model $Q \\sim N({q_mu_s:.3f}, {q_std_s:.3f}^2)$",
		color="red",
		linewidth=3,
	)

	ax.axvline(q_avg_score, color="purple", linestyle="-", linewidth=2, label=f"Your q-avg: {q_avg_score:.3f}")

	x_fill_left = np.linspace(0, q_avg_score, 500)
	y_fill_left = stats.norm.pdf(x_fill_left, q_mu_s, q_std_s)
	ax.fill_between(
		x_fill_left,
		y_fill_left,
		alpha=0.3,
		color="orange",
		label="Students below your score",
	)

	x_fill_right = np.linspace(q_avg_score, 1.0, 100)
	y_fill_right = stats.norm.pdf(x_fill_right, q_mu_s, q_std_s)
	ax.fill_between(
		x_fill_right,
		y_fill_right,
		alpha=0.6,
		color="red",
		label="Higher-score tail (your rank)",
	)

	ax.set_title(rf"Quantized Rank Model (99 -> 1, $\rho={rho:.2f}$)", fontsize=16)
	ax.set_xlabel("Quantized score (score / 99)")
	ax.set_ylabel("Probability density")
	ax.legend(loc="upper left")
	ax.grid(True, alpha=0.3)

	return fig


if __name__ == "__main__":
	output_path = "E:/GradeEstimate/distribution_visual.png"
	chart = generate_plot(99, 99, rho=0.75)
	chart.savefig(output_path, dpi=300)
	print(f"Saved plot to: {output_path}")
