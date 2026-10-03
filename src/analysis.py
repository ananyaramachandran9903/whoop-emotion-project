"""
Phase 4 - Full emotion run, tagging, summary tables and hypothesis tests.

Data rules (from Phase 2):
  - Overall shares and brand comparisons use sample == "random" only.
  - Within-stage comparisons use random + stage_boost (all rows).
  - Every share is "% of posts that express the emotion" (multi-label), with n and a
    95% Wilson interval. Cells with n < MIN_N are flagged as too small to read.
"""

import math
from pathlib import Path

import pandas as pd

import emotions
import tagging

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean" / "clean_reddit.csv"
SCORES = ROOT / "data" / "clean" / "emotion_scores_full.csv"   # id + 28 scores (no text)
TABLES = ROOT / "outputs" / "tables"
MIN_N = 30

GROUPS = list(emotions.CORE_GROUPS)
FLAG = {g: f"expresses_{g}" for g in GROUPS}


# ---------------------------------------------------------------- full run
def score_full(clf, clean, chunk=256, batch_size=16):
    """Scores every clean row, saving progress so a rerun resumes instead of restarting."""
    done = pd.read_csv(SCORES) if SCORES.exists() else pd.DataFrame(columns=["id", *emotions.LABELS])
    todo = clean[~clean["id"].isin(set(done["id"]))]
    print(f"{len(done):,} already scored, {len(todo):,} to go")
    for start in range(0, len(todo), chunk):
        part = todo.iloc[start:start + chunk]
        sc = emotions.score_texts(clf, part["text_model"], batch_size=batch_size)
        sc.insert(0, "id", part["id"].values)
        done = pd.concat([done, sc], ignore_index=True)
        done.to_csv(SCORES, index=False)
        print(f"  scored {min(start + chunk, len(todo)):,}/{len(todo):,}")
    done[emotions.LABELS] = done[emotions.LABELS].astype(float)
    return done


def build(clean, scores):
    """One analysis table: clean rows + emotion flags + stage + themes."""
    scores = scores.drop_duplicates("id").astype({lab: float for lab in emotions.LABELS})
    df = clean.merge(scores, on="id", how="inner", validate="one_to_one")
    if len(df) < len(clean):
        print(f"Note: {len(clean) - len(df):,} clean rows have no scores yet - run score_full again")
    flags = emotions.add_core_emotions(df[emotions.LABELS], texts=df["text_model"])
    keep = [c for c in flags.columns if c not in emotions.LABELS]
    df = pd.concat([df.reset_index(drop=True), flags[keep].reset_index(drop=True)], axis=1)
    df = tagging.tag_themes(tagging.tag_stage(df))
    return df


# ---------------------------------------------------------------- stats helpers
def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def share_table(df, by, groups=GROUPS):
    """Long table: one row per (by..., emotion) with n, k, share, 95% CI, small-n flag."""
    by = [by] if isinstance(by, str) else list(by)
    rows = []
    for key, g in df.groupby(by, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        n = len(g)
        for emo in groups:
            k = int(g[FLAG[emo]].sum())
            lo, hi = wilson(k, n)
            rows.append({**dict(zip(by, key)), "emotion": emo, "n": n, "k": k,
                         "share": k / n if n else float("nan"), "ci_low": lo, "ci_high": hi,
                         "small_n": n < MIN_N})
    return pd.DataFrame(rows)


def wide(long, index, value="share"):
    """Pivot a share_table to emotions-as-columns for display."""
    w = long.pivot_table(index=index, columns="emotion", values=value, observed=True)[GROUPS]
    n = long.groupby(index, observed=True)["n"].first()
    w.insert(0, "n", n)
    return w


def two_prop_test(k1, n1, k2, n2):
    """Two-sided two-proportion z-test. Returns (difference p1 - p2, z, p-value)."""
    if min(n1, n2) == 0:
        return (float("nan"),) * 3
    p1, p2, p = k1 / n1, k2 / n2, (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (p1 - p2, float("nan"), float("nan"))
    z = (p1 - p2) / se
    return (p1 - p2, z, math.erfc(abs(z) / math.sqrt(2)))


def compare(df, mask_a, mask_b, flag_col, label_a, label_b):
    a, b = df[mask_a], df[mask_b]
    k1, n1, k2, n2 = int(a[flag_col].sum()), len(a), int(b[flag_col].sum()), len(b)
    diff, z, p = two_prop_test(k1, n1, k2, n2)
    return {"group_a": label_a, "n_a": n1, "share_a": k1 / n1 if n1 else float("nan"),
            "group_b": label_b, "n_b": n2, "share_b": k2 / n2 if n2 else float("nan"),
            "difference_pts": diff * 100 if diff == diff else diff, "z": z, "p_value": p,
            "enough_data": min(n1, n2) >= MIN_N}


# ---------------------------------------------------------------- the analysis
def summaries(df):
    """All summary tables (aggregates only: safe to publish)."""
    rnd = df[df["sample"] == "random"]
    staged = df[df["stage"] != "untagged"].copy()
    staged["stage"] = pd.Categorical(staged["stage"], tagging.STAGE_ORDER, ordered=True)

    theme_long = []
    for th in tagging.THEMES:
        t = share_table(rnd[rnd[f"theme_{th}"]], "brand")
        t.insert(0, "theme", th)
        theme_long.append(t)
    theme_long = pd.concat(theme_long, ignore_index=True)

    cancel = staged[staged["stage"] == "cancelling"]
    price_in_cancel = (cancel.groupby("brand")["price_reason"]
                       .agg(n="size", k="sum").assign(share=lambda x: x.k / x.n))

    return {
        "overall_by_brand": share_table(rnd, "brand"),
        "stage_counts": (staged.groupby(["brand", "stage"], observed=True).size()
                         .unstack(fill_value=0)),
        "stage_by_brand": share_table(staged, ["brand", "stage"]),
        "theme_by_brand": theme_long,
        "cancelling_by_brand": share_table(cancel, "brand"),
        "price_in_cancelling": price_in_cancel,
    }


def hypothesis_tests(df):
    staged = df[df["stage"] != "untagged"]
    w = staged[staged["brand"] == "WHOOP"]
    pos = FLAG["Pride & joy"]
    anx = FLAG["Anxiety / worry"]
    conf = FLAG["Confusion / doubt"]
    rows = [
        {"hypothesis": "H1 WHOOP: anxiety higher in first weeks than daily habit",
         **compare(w, w.stage == "first_weeks", w.stage == "daily_habit", anx, "first weeks", "daily habit")},
        {"hypothesis": "H1 all brands: anxiety higher in first weeks than daily habit",
         **compare(staged, staged.stage == "first_weeks", staged.stage == "daily_habit", anx, "first weeks", "daily habit")},
        {"hypothesis": "H1b WHOOP: confusion higher in first weeks than daily habit",
         **compare(w, w.stage == "first_weeks", w.stage == "daily_habit", conf, "first weeks", "daily habit")},
        {"hypothesis": "H2 WHOOP: pride & joy higher in daily habit than first weeks",
         **compare(w, w.stage == "daily_habit", w.stage == "first_weeks", pos, "daily habit", "first weeks")},
    ]
    cancel = staged[staged["stage"] == "cancelling"]
    for other in ["Garmin", "Apple Watch", "Oura"]:
        rows.append({"hypothesis": f"H3 cancelling posts give price as a reason: WHOOP vs {other}",
                     **compare(cancel, cancel.brand == "WHOOP", cancel.brand == other,
                               "price_reason", "WHOOP", other)})
    frus = FLAG["Frustration & disappointment"]
    rows.append({"hypothesis": "H3a all brands: frustration & disappointment higher in cancelling than other stages",
                 **compare(staged, staged.stage == "cancelling", staged.stage != "cancelling", frus,
                           "cancelling", "other stages")})
    out = pd.DataFrame(rows)
    out["supported (p<0.05, right direction, enough data)"] = (
        (out["p_value"] < 0.05) & (out["difference_pts"] > 0) & out["enough_data"])
    return out


def handcheck_sheet(df, n_random=20, n_worry=10, seed=11):
    """30 posts for the Phase 4 hand check: 20 random (5 per brand) + 10 worry-word matches."""
    cols = ["brand", "type", "stage", "themes", "text_model", "top_labels", "emotions"]
    d = df.copy()
    d["emotions"] = d[[FLAG[g] for g in GROUPS]].apply(
        lambda r: ", ".join(g for g, v in zip(GROUPS, r) if v) or "none", axis=1)
    rnd = d[d["sample"] == "random"].groupby("brand").sample(n=n_random // 4, random_state=seed)
    worry = d[d["worry_words"] & ~d.index.isin(rnd.index)]
    worry = worry.sample(n=min(n_worry, len(worry)), random_state=seed)
    sheet = pd.concat([rnd.assign(check_type="random"), worry.assign(check_type="worry_words")])
    return sheet[["check_type", *cols]].assign(emotions_ok="", stage_ok="").reset_index(drop=True)


def save_tables(tables, tests):
    TABLES.mkdir(parents=True, exist_ok=True)
    for name, t in tables.items():
        t.to_csv(TABLES / f"{name}.csv", index=not isinstance(t.index, pd.RangeIndex))
    tests.to_csv(TABLES / "hypothesis_tests.csv", index=False)
    return TABLES
