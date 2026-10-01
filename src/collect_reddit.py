"""
Phase 2 - Collect Reddit posts and comments for the WHOOP emotion project.

Source: Arctic Shift public Reddit archive API
        https://github.com/ArthurHeitmann/arctic_shift  (free service - be polite)

What it does, per brand (subreddit), over one fixed 12-month window:
  1. RANDOM SAMPLE (sample="random")
     - Splits the window into weeks so no single busy week dominates.
     - For each week it reads the start of the week plus a few randomly placed
       100-item slices (seeded, so reruns give the same sample).
     - Posts: keeps a random POSTS_PER_WEEK. Comments: keeps the top
       COMMENTS_PER_WEEK by score ("top comments").
  2. STAGE BOOST (sample="stage_boost")
     - From each week's leftover candidates, also keeps up to BOOST_PER_WEEK
       items mentioning a stage ("just got", "cancel", ...) so Phase 4 has
       enough first-weeks and cancelling posts. Matched locally, no extra calls.
     - Kept in a separate `sample` label: use only "random" rows for overall
       shares, and both for within-stage comparisons.
  3. r/AppleWatch is filtered to fitness/health keywords before sampling.
  4. Bots (AutoModerator, *bot accounts) are dropped. Usernames are used only
     for that check and are never written to disk.

Output: data/raw/raw_reddit.csv
    id, brand, subreddit, type, sample, date, score, text
plus data/raw/raw_<subreddit>.csv checkpoints and outputs/collection_log.json.

Usage (from the repo root):
    python src/collect_reddit.py --quick      # 2-week smoke test, ~1 minute
    python src/collect_reddit.py              # full run, roughly 45-60 minutes
    python src/collect_reddit.py --refresh    # ignore checkpoints and re-pull
"""

import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------- settings
BASE = "https://arctic-shift.photon-reddit.com/api"
HEADERS = {"User-Agent": "whoop-emotion-student-project/0.3 (non-commercial research)"}

START = "2025-09-28"  # same fixed window for every brand -> reproducible
END = "2026-09-28"

BRANDS = {  # brand -> subreddit
    "WHOOP": "whoop",
    "Oura": "ouraring",
    "Garmin": "Garmin",
    "Apple Watch": "AppleWatch",
}

POSTS_PER_WEEK = 20      # ~53 weeks -> up to ~1,060 posts per brand
COMMENTS_PER_WEEK = 25   # ~53 weeks -> up to ~1,325 comments per brand
EXTRA_SLICES = 2         # random 100-item slices per busy week, on top of week start
EXTRA_SLICES_FILTERED = 4  # more for r/AppleWatch, since the keyword filter drops most
SEED = 42

FITNESS_FILTER = {"AppleWatch"}
FITNESS_KEYWORDS = [
    "workout", "workouts", "fitness", "run", "runs", "running", "ran", "walk",
    "walking", "hike", "hiking", "marathon", "gym", "training", "exercise",
    "cycling", "swim", "swimming", "steps", "calorie", "calories", "sleep",
    "heart rate", "hrv", "vo2", "vo2 max", "resting", "zone", "zones", "rings",
    "activity ring", "health", "recovery", "strain", "whoop", "oura", "garmin",
]
FITNESS_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, FITNESS_KEYWORDS)) + r")\b", re.I)

# Stage boost: from each week's candidates that were NOT picked for the random
# sample, also keep items that mention an ownership stage. Matching is done
# locally (no extra API calls); the Phase 4 stage rules decide the final stage.
STAGE_PATTERNS = {
    "considering": [r"should i (?:buy|get)", r"worth it", r"thinking (?:of|about) getting"],
    "first_weeks": [r"just got", r"first (?:week|few days|month)", r"new to"],
    "cancelling": [r"cancel(?:l?ed|l?ing)?", r"returned", r"returning", r"switch(?:ed|ing) to",
                   r"membership ended", r"refund"],
}
STAGE_RE = re.compile(
    r"\b(?:" + "|".join(p for ps in STAGE_PATTERNS.values() for p in ps) + r")\b", re.I)
BOOST_PER_WEEK = 15  # per type (posts, comments)

BOT_NAMES = {"automoderator"}

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
LOG_PATH = ROOT / "outputs" / "collection_log.json"

POST_FIELDS = "id,author,created_utc,score,title,selftext"
COMMENT_FIELDS = "id,author,created_utc,score,body"

PAUSE = 2.0  # seconds between successful requests

session = requests.Session()
session.headers.update(HEADERS)
N_REQUESTS = 0
SKIPPED = []  # slices that failed even after retries (logged, run continues)


# ---------------------------------------------------------------- API helpers
def get(endpoint, params, retries=5):
    """GET with polite pacing and backoff on 429 / 5xx / server-side errors."""
    global N_REQUESTS
    last = ""
    for attempt in range(retries):
        try:
            r = session.get(f"{BASE}/{endpoint}", params=params, timeout=60)
            N_REQUESTS += 1
            if r.status_code == 200:
                payload = r.json()
                if payload.get("error"):
                    last = payload["error"]
                    wait = 15 * (attempt + 1)
                else:
                    time.sleep(PAUSE)  # free service: stay well under the rate limit
                    return payload.get("data") or []
            elif r.status_code == 429:
                last = "429 rate limited"
                wait = int(float(r.headers.get("X-RateLimit-Reset", 30))) + 1
            elif 400 <= r.status_code < 500:
                body = r.text[:200]
                if re.search(r"timeout|timed out|slow down", body, re.I):
                    # Arctic Shift returns server overload as a 4xx: back off and retry
                    last = f"HTTP {r.status_code} server busy"
                    wait = 15 * (attempt + 1)
                else:  # genuinely bad request: retrying won't help
                    raise RuntimeError(f"{endpoint}: HTTP {r.status_code} {body} params={params}")
            else:
                last = f"HTTP {r.status_code}"
                wait = 10 * (attempt + 1)
        except (requests.RequestException, ValueError) as e:
            last = repr(e)
            wait = 10 * (attempt + 1)
        print(f"    {endpoint}: {last} - retrying in {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"Gave up on {endpoint} ({last}) with params {params}")


def fetch_slice(endpoint, sub, after_ts, before_ts, fields):
    """Up to 100 items created after `after_ts`, oldest first."""
    return get(endpoint, {
        "subreddit": sub, "after": int(after_ts), "before": int(before_ts),
        "limit": 100, "sort": "asc", "fields": fields,
    })


def to_ts(date_str):
    return int(pd.Timestamp(date_str, tz="UTC").timestamp())


def to_date(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def week_windows(start, end):
    s, e = to_ts(start), to_ts(end)
    step = 7 * 24 * 3600
    return [(t, min(t + step, e)) for t in range(s, e, step)]


def is_bot(author):
    a = (author or "").lower()
    return a in BOT_NAMES or a.endswith("bot") or a.endswith("-bot") or a.endswith("_bot")


def text_of(item, kind):
    if kind == "post":
        return f"{item.get('title') or ''}\n\n{item.get('selftext') or ''}".strip()
    return (item.get("body") or "").strip()


def candidates_for_week(endpoint, sub, ws, we, fields, n_extra, rng):
    """Week start slice; if the week is busy, add random slices inside it."""
    def safe_slice(after_ts):
        try:
            return fetch_slice(endpoint, sub, after_ts, we, fields)
        except RuntimeError as e:  # one bad slice shouldn't kill a 40-minute run
            SKIPPED.append({"subreddit": sub, "endpoint": endpoint, "after": to_date(after_ts)})
            print(f"    skipped one {endpoint.split('/')[0]} slice for r/{sub} ({str(e)[:80]})")
            return None

    first = safe_slice(ws)
    items = first or []
    if first is None or len(first) >= 100:  # busy (or unknown) week -> sample across it
        for _ in range(n_extra):
            items += safe_slice(rng.randint(ws, we - 1)) or []
    return list({i["id"]: i for i in items}.values())


def keep(item, kind, sub):
    if is_bot(item.get("author")):
        return False
    if sub in FITNESS_FILTER and not FITNESS_RE.search(text_of(item, kind)):
        return False
    return True


def row(item, kind, brand, sub, sample):
    prefix = "t3_" if kind == "post" else "t1_"
    return {  # NOTE: no author / username field, by design
        "id": prefix + item["id"], "brand": brand, "subreddit": sub, "type": kind,
        "sample": sample, "date": to_date(item["created_utc"]),
        "score": item.get("score"), "text": text_of(item, kind),
    }


# ---------------------------------------------------------------- collection
def collect_brand(brand, sub, start, end):
    rng = random.Random(f"{SEED}-{sub}")
    n_extra = EXTRA_SLICES_FILTERED if sub in FITNESS_FILTER else EXTRA_SLICES
    weeks = week_windows(start, end)
    rows = []
    print(f"\n== {brand} (r/{sub}): {len(weeks)} weeks, {start} to {end} ==")

    boosted = 0
    for w, (ws, we) in enumerate(weeks, 1):
        post_pool = [p for p in candidates_for_week("posts/search", sub, ws, we, POST_FIELDS, n_extra, rng)
                     if keep(p, "post", sub)]
        posts = rng.sample(post_pool, min(POSTS_PER_WEEK, len(post_pool)))

        comment_pool = [c for c in candidates_for_week("comments/search", sub, ws, we, COMMENT_FIELDS, n_extra, rng)
                        if keep(c, "comment", sub)]
        rng.shuffle(comment_pool)  # random tie-break before sorting by score
        comments = sorted(comment_pool, key=lambda c: c.get("score") or 0, reverse=True)[:COMMENTS_PER_WEEK]

        rows += [row(p, "post", brand, sub, "random") for p in posts]
        rows += [row(c, "comment", brand, sub, "random") for c in comments]

        # Stage boost from the leftovers: no extra API calls
        for kind, pool, picked in (("post", post_pool, posts), ("comment", comment_pool, comments)):
            picked_ids = {i["id"] for i in picked}
            extra = [i for i in pool if i["id"] not in picked_ids and STAGE_RE.search(text_of(i, kind))]
            extra = rng.sample(extra, min(BOOST_PER_WEEK, len(extra)))
            rows += [row(i, kind, brand, sub, "stage_boost") for i in extra]
            boosted += len(extra)

        if w % 10 == 0 or w == len(weeks):
            print(f"  week {w}/{len(weeks)}: {len(rows)} rows so far")

    print(f"  stage boost: {boosted} of those rows")
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="2-week smoke test, writes *_quick files")
    ap.add_argument("--refresh", action="store_true", help="ignore per-brand checkpoints")
    args = ap.parse_args()

    start, end = START, END
    suffix = ""
    if args.quick:
        start = (pd.Timestamp(END) - pd.Timedelta(days=14)).strftime("%Y-%m-%d")
        suffix = "_quick"

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    frames = []
    for brand, sub in BRANDS.items():
        ckpt = RAW_DIR / f"raw_{sub}{suffix}.csv"
        if ckpt.exists() and not args.refresh:
            print(f"\n== {brand}: using checkpoint {ckpt.name} (use --refresh to re-pull) ==")
            frames.append(pd.read_csv(ckpt))
            continue
        df = collect_brand(brand, sub, start, end)
        df.to_csv(ckpt, index=False)
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    out = RAW_DIR / f"raw_reddit{suffix}.csv"
    raw.to_csv(out, index=False)

    counts = raw.groupby(["brand", "sample", "type"]).size().unstack(fill_value=0)
    counts["total"] = counts.sum(axis=1)
    print("\nRaw counts (record these for the write-up):")
    print(counts)
    if SKIPPED:
        print(f"\nNote: {len(SKIPPED)} slices were skipped after retries (see log). "
              "A few is fine; if it's dozens, rerun later with --refresh.")
    print(f"\nSaved {len(raw):,} rows to {out.relative_to(ROOT)}  "
          f"({start} to {end}, {N_REQUESTS} API requests, {(time.time() - t0) / 60:.1f} min)")

    if not args.quick:
        log = {
            "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "Arctic Shift API (arctic-shift.photon-reddit.com)",
            "window": {"start": start, "end": end},
            "settings": {
                "posts_per_week": POSTS_PER_WEEK, "comments_per_week": COMMENTS_PER_WEEK,
                "extra_slices": EXTRA_SLICES, "extra_slices_filtered": EXTRA_SLICES_FILTERED,
                "seed": SEED, "fitness_filter": sorted(FITNESS_FILTER),
                "stage_patterns": STAGE_PATTERNS, "boost_per_week": BOOST_PER_WEEK,
            },
            "skipped_slices": SKIPPED,
            "raw_counts": {
                brand: {f"{s}_{t}": int(n) for (s, t), n in g.groupby(["sample", "type"]).size().items()}
                | {"total": int(len(g))}
                for brand, g in raw.groupby("brand")
            },
        }
        LOG_PATH.write_text(json.dumps(log, indent=2))
        print(f"Log written to {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
