#!/usr/bin/env python3
"""
Step 3 of 3: draw the Fork Files figures as PNGs and print the headline stats.

Reads:   doughboys_forks.csv, doughboys_forks_long.csv (from parse_scores.py)
Writes:  figures/01_histograms.png        score distribution for Nick, Mitch, guests
         figures/02_agreement.png         Nick x Mitch grid; diagonal = exact tie
         figures/03_gap.png               Nick minus Mitch on the same episode
         figures/04_by_year.png           yearly averages
         figures/05_live.png              studio vs live averages
         figures/06_feuds.png             biggest host disagreements
         figures/07_guests.png            repeat guests vs the hosts
         figures/08_off_the_scale.png     every score above 5 forks
         figures/09_worst.png             lowest host averages

Setup:  pip install pandas matplotlib scipy
Run:    python make_figures.py            (add --dark for a dark-background set)
"""
import argparse, os, textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from scipy.stats import wilcoxon

ap = argparse.ArgumentParser()
ap.add_argument("--dark", action="store_true")
ap.add_argument("--out", default="figures")
args = ap.parse_args()

# ---------- palette (same as the web page) ----------
if args.dark:
    BG, PANEL, INK, INK2, MUTED, GRID, RULE = "#161719", "#1f2023", "#f4f4f1", "#c3c2b7", "#8e8e88", "#2a2b2e", "#2e2f33"
    NICK, MITCH, GUEST, NEUTRAL = "#3987e5", "#d95926", "#199e70", "#5a5b5f"
    SEQ = ["#1d2330", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"]
else:
    BG, PANEL, INK, INK2, MUTED, GRID, RULE = "#f6f6f3", "#ffffff", "#15171c", "#4f5158", "#7b7d84", "#ecece8", "#e3e3de"
    NICK, MITCH, GUEST, NEUTRAL = "#2a78d6", "#eb6834", "#1baf7a", "#b9b9b2"
    SEQ = ["#eef4fc", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
COLOR = {"Nick": NICK, "Mitch": MITCH, "Guest": GUEST}

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "axes.edgecolor": RULE, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.titlepad": 12, "legend.frameon": False,
})
os.makedirs(args.out, exist_ok=True)


def save(fig, name):
    fig.savefig(os.path.join(args.out, name), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def subtitle(fig, text):
    fig.text(0.01, 0.995, text, ha="left", va="bottom", color=MUTED, fontsize=10, transform=fig.transFigure)


# ---------- data ----------
df = pd.read_csv("doughboys_forks.csv", parse_dates=["date"])
lg = pd.read_csv("doughboys_forks_long.csv")
lg = lg[lg.episode.isin(df.episode)]
df["year"] = df.date.dt.year
scores = {r: lg[lg.role == r].forks for r in ("Nick", "Mitch", "Guest")}
gap = df.nick - df.mitch

# ---------- stats ----------
g = df.dropna(subset=["guest_avg"])
host_avg = (g.nick + g.mitch) / 2
print(f"\n{len(df)} episodes")
for r, s in scores.items():
    print(f"  {r:6s} mean {s.mean():.2f}  median {s.median():.2f}  n={len(s):4d}  "
          f"5+ {100 * (s >= 5).mean():.1f}%  <=1 {100 * (s <= 1).mean():.1f}%  >5: {(s > 5).sum()}")
print(f"  Mitch higher {(gap < 0).sum()}, Nick higher {(gap > 0).sum()}, tied {(gap == 0).sum()} "
      f"({100 * (gap == 0).mean():.0f}%)")
print(f"  Mean Nick - Mitch {gap.mean():+.3f}, Wilcoxon p = {wilcoxon(df.nick, df.mitch).pvalue:.3f}")
print(f"  Mean guest - hosts {(g.guest_avg - host_avg).mean():+.3f}, "
      f"Wilcoxon p = {wilcoxon(g.guest_avg, host_avg).pvalue:.4f}\n")

# ---------- 01 histograms ----------
bins = np.arange(0, 6.01, 0.5)
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
ymax = 0
counts = {}
for r, s in scores.items():
    b = np.minimum(6, np.round(s * 2) / 2)  # nearest half-fork; 6+ grouped
    counts[r] = np.array([(b == x).sum() for x in bins]) / len(s) * 100
    ymax = max(ymax, counts[r].max())
for ax, r in zip(axes, scores):
    s = scores[r]
    ax.bar(bins, counts[r], width=0.42, color=COLOR[r], edgecolor=PANEL, linewidth=1)
    ax.axvline(s.mean(), color=INK, lw=1.4, ls="--")
    ax.text(s.mean() - 0.08, ymax * 1.06, f"mean {s.mean():.2f}", ha="right", va="top", fontsize=10, color=INK)
    ax.set_title(f"{'Guests' if r == 'Guest' else r}   n = {len(s)}", color=COLOR[r])
    ax.set_xticks(range(7), ["0", "1", "2", "3", "4", "5", "6+"])
    ax.set_xlim(-0.4, 6.4); ax.set_ylim(0, ymax * 1.12)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[0].set_ylabel("Share of that person's scores")
fig.suptitle("Everyone lives at 3.5 to 4 forks", x=0.01, ha="left", fontsize=15, fontweight="bold", y=1.04)
save(fig, "01_histograms.png")

# ---------- 02 agreement grid ----------
steps = np.arange(0, 6.01, 0.5)
idx = {v: i for i, v in enumerate(steps)}
grid = np.zeros((len(steps), len(steps)), int)
for n, m in zip(np.round(df.nick * 2) / 2, np.round(df.mitch * 2) / 2):
    grid[idx[m], idx[n]] += 1
fig, ax = plt.subplots(figsize=(7.2, 7.2))
edges = [0, 1, 3, 8, 20, 45, grid.max() + 1]
cmap, norm = ListedColormap(SEQ), BoundaryNorm(edges, len(SEQ))
ax.imshow(grid, origin="lower", cmap=cmap, norm=norm, extent=(-0.25, 6.25, -0.25, 6.25))
for i, m in enumerate(steps):
    for j, n in enumerate(steps):
        c = grid[i, j]
        if c:
            strong = norm(c) >= 4  # two darkest (light mode) / brightest (dark mode) steps
            ax.text(n, m, c, ha="center", va="center", fontsize=8.5,
                    color=(BG if args.dark else "#ffffff") if strong else INK)
        if i == j:
            ax.add_patch(plt.Rectangle((n - 0.25, m - 0.25), 0.5, 0.5, fill=False, ec=INK, lw=1))
ax.set_xticks(range(7)); ax.set_yticks(range(7)); ax.grid(False)
ax.set_xlabel("Nick's forks", color=NICK, fontweight="semibold")
ax.set_ylabel("Mitch's forks", color=MITCH, fontweight="semibold")
ax.set_title(f"The hosts tie {100 * (gap == 0).mean():.0f}% of the time (outlined diagonal)")
save(fig, "02_agreement.png")

# ---------- 03 gap ----------
d = np.round(gap * 2) / 2
vals = np.arange(d.min(), d.max() + 0.01, 0.5)
cnt = np.array([(d == v).sum() for v in vals])
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.bar(vals, cnt, width=0.42, color=[MITCH if v < 0 else NICK if v > 0 else NEUTRAL for v in vals])
ax.axvline(gap.mean(), color=INK, lw=1.4, ls="--")
ax.set_xticks(np.arange(np.floor(vals.min()), vals.max() + 1), [f"{v:+.0f}" if v else "0" for v in np.arange(np.floor(vals.min()), vals.max() + 1)])
ax.grid(axis="x", visible=False)
ax.set_xlabel("Nick's forks minus Mitch's forks, same episode"); ax.set_ylabel("Episodes")
ax.set_title(f"Mitch higher {(gap < 0).sum()}  ·  Nick higher {(gap > 0).sum()}  ·  tied {(gap == 0).sum()}"
             f"  ·  mean gap {gap.mean():+.2f}")
save(fig, "03_gap.png")

# ---------- 04 by year ----------
yr = df.groupby("year").agg(nick=("nick", "mean"), mitch=("mitch", "mean"), guest=("guest_avg", "mean"),
                            n=("nick", "size")).dropna(subset=["nick"])
fig, ax = plt.subplots(figsize=(11, 4.6))
ends = []
for k, lab, c in (("nick", "Nick", NICK), ("mitch", "Mitch", MITCH), ("guest", "Guests", GUEST)):
    ax.plot(yr.index, yr[k], color=c, lw=2, marker="o", ms=6, mec=PANEL, mew=1.5)
    ends.append([yr[k].iloc[-1], lab, c])
ends.sort()
for i in range(1, len(ends)):  # keep end labels from overlapping
    ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.04)
for y, lab, c in ends:
    ax.text(yr.index[-1] + 0.25, y, lab, color=c, va="center", fontweight="semibold")
ax.set_xticks(yr.index.astype(int)); ax.set_xlim(yr.index.min() - 0.4, yr.index.max() + 1.1)
ax.set_ylabel("Average forks")
ax.set_title(f"Average score by year  ({int(yr.index.max())} is a partial year)")
save(fig, "04_by_year.png")

# ---------- 05 live vs studio ----------
lv = df.groupby("live")[["nick", "mitch", "guest_avg"]].mean()
fig, ax = plt.subplots(figsize=(9, 3.2))
for i, (k, lab, c) in enumerate((("guest_avg", "Guests", GUEST), ("mitch", "Mitch", MITCH), ("nick", "Nick", NICK))):
    a, b = lv.loc[False, k], lv.loc[True, k]
    ax.plot([a, b], [i, i], color=c, lw=2, zorder=1)
    ax.scatter([a], [i], s=90, facecolor=PANEL, edgecolor=c, linewidth=2, zorder=2)
    ax.scatter([b], [i], s=90, color=c, edgecolor=PANEL, linewidth=1.5, zorder=2)
    ax.text(b + 0.03, i, f"{a:.2f} → {b:.2f}", va="center", fontsize=10, color=INK2)
ax.set_yticks(range(3), ["Guests", "Mitch", "Nick"])
for t, c in zip(ax.get_yticklabels(), (GUEST, MITCH, NICK)):
    t.set_color(c); t.set_fontweight("semibold")
ax.set_ylim(-0.6, 2.6); ax.grid(axis="y", visible=False)
ax.set_xlabel("Average forks   (○ studio   ● live)")
ax.set_title(f"Everyone rates higher live ({int(df.live.sum())} live episodes)")
save(fig, "05_live.png")

# ---------- 06 feuds ----------
top = df.assign(absgap=gap.abs()).sort_values(["absgap", "episode"], ascending=[False, True]).head(12)[::-1]
fig, ax = plt.subplots(figsize=(11, 6.2))
for i, r in enumerate(top.itertuples()):
    ax.plot([r.nick, r.mitch], [i, i], color=NEUTRAL, lw=2, zorder=1)
    ax.scatter([r.nick], [i], s=80, color=NICK, edgecolor=PANEL, zorder=2)
    ax.scatter([r.mitch], [i], s=80, color=MITCH, edgecolor=PANEL, zorder=2)
ax.set_yticks(range(len(top)), [textwrap.shorten(t, 55, placeholder="…") for t in top.episode])
ax.set_xlim(-0.2, 6.2); ax.grid(axis="y", visible=False); ax.set_xlabel("Forks")
ax.scatter([], [], color=NICK, label="Nick"); ax.scatter([], [], color=MITCH, label="Mitch")
ax.legend(loc="lower right", ncol=2)
ax.set_title("The biggest host splits")
save(fig, "06_feuds.png")

# ---------- 07 guests ----------
gm = lg[lg.role == "Guest"].merge(df[["episode", "nick", "mitch"]], on="episode")
gm["rel"] = gm.forks - (gm.nick + gm.mitch) / 2
gs = gm.groupby("person").agg(n=("forks", "size"), mean=("forks", "mean"), rel=("rel", "mean")) \
       .query("n >= 3").sort_values("rel")
fig, ax = plt.subplots(figsize=(9, 0.26 * len(gs) + 1.4))
y = np.arange(len(gs))
cols = [MUTED if v < 0 else GUEST for v in gs.rel]
ax.hlines(y, 0, gs.rel, color=[NEUTRAL if v < 0 else GUEST for v in gs.rel], lw=2)
ax.scatter(gs.rel, y, s=30, color=cols, zorder=2)
for yi, (v, n) in enumerate(zip(gs.rel, gs.n)):
    ax.text(v + (0.04 if v >= 0 else -0.04), yi, f"×{n}", va="center", ha="left" if v >= 0 else "right",
            fontsize=8, color=MUTED)
ax.axvline(0, color=INK, lw=1)
ax.set_yticks(y, gs.index, fontsize=9); ax.set_ylim(-0.8, len(gs) - 0.2)
ax.grid(axis="y", visible=False)
ax.set_xlabel("Guest's score minus the hosts' average, same episodes")
ax.set_title("Repeat guests (3+ episodes): ← harsher than the hosts · kinder →")
save(fig, "07_guests.png")


# ---------- 08 / 09 tables ----------
def table_fig(rows, cols, title, name, colors=None, widths=None):
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(rows) + 1.1))
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="upper left", cellLoc="left", colLoc="left",
                 colWidths=widths)
    t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 1.6)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(RULE); cell.visible_edges = "B"
        cell.set_facecolor(PANEL if r else BG)
        cell.get_text().set_color(MUTED if r == 0 else INK)
        if r == 0:
            cell.get_text().set_fontsize(9)
        if colors and r and c == 1:
            cell.get_text().set_color(colors[r - 1]); cell.get_text().set_fontweight("semibold")
    ax.set_title(title)
    save(fig, name)


over = lg[lg.forks > 5].merge(df[["episode", "year"]], on="episode").sort_values(["year", "episode"])
if len(over):
    who = lambda r: r.person if r.role != "Mitch" or "Mitchell" in r.person else f"Mitch, as {r.person}"
    table_fig([[textwrap.shorten(r.episode, 52, placeholder="…"), who(r), f"{r.forks:g}", f"{r.year:.0f}"]
               for r in over.itertuples()],
              ["Episode", "Given by", "Forks", "Year"],
              f"Off the scale: {len(over)} scores above 5 forks ({(over.role == 'Mitch').sum()} of them from Mitch)",
              "08_off_the_scale.png", colors=[COLOR.get(r, INK) for r in over.role], widths=[0.5, 0.32, 0.09, 0.09])

worst = df.assign(h=(df.nick + df.mitch) / 2).nsmallest(8, "h")
table_fig([[textwrap.shorten(r.episode, 60, placeholder="…"), f"{r.nick:g}", f"{r.mitch:g}", "–" if pd.isna(r.guest_avg) else f"{r.guest_avg:.2f}"]
           for r in worst.itertuples()],
          ["Episode", "Nick", "Mitch", "Guests"], "The worst meals on record (lowest host average)",
          "09_worst.png", widths=[0.64, 0.12, 0.12, 0.12])
print(f"\nFigures in ./{args.out}/")
