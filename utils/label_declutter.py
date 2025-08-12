# utils/label_declutter.py
"""Label decluttering (repulsion). Tries adjustText if available, else a small fallback.

Usage in app.py (after placing texts = [ax.text(...), ...]):

from utils.label_declutter import declutter_texts

_ = declutter_texts(ax, texts)  # modifies positions in-place
"""
from __future__ import annotations
from typing import List


def declutter_texts(ax, texts: List, max_iter: int = 200) -> bool:
    """Attempt to reduce overlaps for a list of matplotlib Text objects on ax.
    Returns True if adjustText was used, False if fallback ran.
    """
    try:
        from adjustText import adjust_text  # optional dependency
        adjust_text(
            texts,
            ax=ax,
            only_move={"points": "y", "texts": "xy"},
            autoalign=True,
            expand_points=(1.05, 1.2),
            expand_text=(1.05, 1.2),
            force_points=0.2,
            force_text=0.2,
            arrowprops=dict(arrowstyle="-", lw=0.6, alpha=0.7),
        )
        return True
    except Exception:
        # lightweight fallback: iterative bbox repulsion
        fig = ax.figure
        renderer = fig.canvas.get_renderer()
        for _ in range(max_iter):
            moved = False
            bbs = [t.get_window_extent(renderer=renderer).expanded(1.05, 1.2) for t in texts]
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    if bbs[i].overlaps(bbs[j]):
                        xi, yi = texts[i].get_position()
                        xj, yj = texts[j].get_position()
                        dx, dy = (xi - xj), (yi - yj)
                        if dx == 0 and dy == 0:
                            dx, dy = 0.0005, 0.0005
                        s = 0.002
                        texts[i].set_position((xi + s * dx, yi + s * dy))
                        texts[j].set_position((xj - s * dx, yj - s * dy))
                        moved = True
            if not moved:
                break
        return False
