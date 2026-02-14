"""Generate SIR spaghetti plot overlay for social cards."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from epydemix import load_predefined_model
from pathlib import Path

OUTPUT = Path(__file__).parent / "spaghetti.png"

# Simulate SIR dynamics
model = load_predefined_model("SIR", transmission_rate=0.35)
results = model.run_simulations(
    start_date="2020-02-10",
    end_date="2020-04-01",
    percentage_in_agents=10 / model.population.Nk.sum(),
    Nsim=1000,
)
st = results.get_stacked_transitions()
infections = st["Susceptible_to_Infected_total"]

# Plot trajectories (white on transparent)
fig = plt.figure(figsize=(12, 6.3), dpi=200)
ax = fig.add_axes([0, 0, 1, 1])
ax.patch.set_alpha(0)
fig.patch.set_alpha(0)

for i in range(infections.shape[0]):
    ax.plot(infections[i], color="white", alpha=0.1, linewidth=0.4)

ax.set_xlim(0, infections.shape[1] - 1)
ax.set_ylim(5, infections.max() * 1.15)
ax.axis("off")

fig.savefig(OUTPUT, dpi=200, transparent=True)
plt.close()

# Downscale to card size (1200x630) and reduce overall opacity to 25%
img = PILImage.open(OUTPUT).convert("RGBA")
img = img.resize((1200, 630), PILImage.LANCZOS)
r, g, b, a = img.split()
a = a.point(lambda x: int(x * 0.25))
img = PILImage.merge("RGBA", (r, g, b, a))
img.save(OUTPUT)
print(f"Saved {OUTPUT} ({img.size[0]}x{img.size[1]})")
