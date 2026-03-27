import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt


def generate_plot(
	score1: float,
	score2: float,
	rho: float = 0.75,
	mu1: float = 68,
	std1: float = 20.06,
	mu2: float = 73,
	std2: float = 14.03,
):
	"""Generate ranking distribution plot for two-course average model."""
	avg_score = (score1 + score2) / 2
	mu_s = (mu1 + mu2) / 2
	var_s = (std1**2 + std2**2 + 2 * rho * std1 * std2) / 4
	std_s = var_s ** 0.5

	x = np.linspace(20, 100, 1000)
	fig, ax = plt.subplots(figsize=(12, 6))

	ax.plot(
		x,
		stats.norm.pdf(x, mu1, std1),
		label=f"MTH007 $\\mu={mu1}, \\sigma={std1:.1f}$",
		color="blue",
		linestyle="--",
	)
	ax.plot(
		x,
		stats.norm.pdf(x, mu2, std2),
		label=f"MTH013 $\\mu={mu2}, \\sigma={std2:.1f}$",
		color="green",
		linestyle="--",
	)

	y_s = stats.norm.pdf(x, mu_s, std_s)
	ax.plot(
		x,
		y_s,
		label=f"Combined avg model $S \\sim N({mu_s:.1f}, {std_s:.1f}^2)$",
		color="red",
		linewidth=3,
	)

	ax.axvline(avg_score, color="purple", linestyle="-", linewidth=2, label=f"Your avg: {avg_score:.1f}")

	x_fill_left = np.linspace(20, avg_score, 500)
	y_fill_left = stats.norm.pdf(x_fill_left, mu_s, std_s)
	ax.fill_between(
		x_fill_left,
		y_fill_left,
		alpha=0.3,
		color="orange",
		label="Students below your score",
	)

	x_fill_right = np.linspace(avg_score, 100, 100)
	y_fill_right = stats.norm.pdf(x_fill_right, mu_s, std_s)
	ax.fill_between(
		x_fill_right,
		y_fill_right,
		alpha=0.6,
		color="red",
		label="Higher-score tail (your rank)",
	)

	ax.set_title(rf"Rank Prediction Visualization ($\rho={rho:.2f}$)", fontsize=16)
	ax.set_xlabel("Score")
	ax.set_ylabel("Probability density")
	ax.legend(loc="upper left")
	ax.grid(True, alpha=0.3)

	return fig


if __name__ == "__main__":
	output_path = "E:/GradeEstimate/distribution_visual.png"
	chart = generate_plot(93, 93, rho=0.75)
	chart.savefig(output_path, dpi=300)
	print(f"Saved plot to: {output_path}")
