"""
Phase 3a - Clean the raw Reddit data.

Input : data/raw/raw_reddit.csv          (from collect_reddit.py)
Output: data/clean/clean_reddit.csv      (git-ignored: contains post text)
        outputs/cleaning_funnel.csv      (aggregate counts only: safe to publish)

Steps, in order (each step's row count is recorded per brand):
  1. duplicate_id      same Reddit id twice
  2. removed_deleted   body is [removed] / [deleted]
  3. bot_text          automated replies ("I am a bot", RemindMe, ...)
  4. duplicate_text    same text posted more than once (copy-paste, crossposts)
  5. under_15_words    fewer than MIN_WORDS words after removing links
  6. non_english       langdetect says the text isn't English

Usage (from the repo root):  python src/clean_data.py
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "raw_reddit.csv"
CLEAN = ROOT / "data" / "clean" / "clean_reddit.csv"
FUNNEL = ROOT / "outputs" / "cleaning_funnel.csv"

MIN_WORDS = 15

REMOVED_RE = re.compile(r"^\s*\[(?:removed|deleted)\]\s*$", re.I)
BOT_RE = re.compile(
    r"i am a bot|i'm a bot|this action was performed automatically|beep boop|"
    r"!?remindme!?", re.I)
URL_RE = re.compile(r"https?://\S+|www\.\S+")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")  # [text](url) -> text


def body_of(text, kind):
    """For posts, text is 'title\\n\\nselftext'; the body is the selftext part."""
    if kind == "post" and "\n\n" in text:
        return text.split("\n\n", 1)[1]
    return text


def model_text(text):
    """Text as the emotion model will see it: links removed, whitespace tidied."""
    t = MD_LINK_RE.sub(r"\1", text)
    t = URL_RE.sub(" ", t)
    t = t.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<")
    return re.sub(r"\s+", " ", t).strip()


def is_english(text):
    from langdetect import DetectorFactory, LangDetectException, detect
    DetectorFactory.seed = 0  # langdetect is random by default; fix it for reproducibility
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False


def clean(raw: pd.DataFrame):
    df = raw.copy()
    df["text"] = df["text"].fillna("").astype(str)
    # Random-sample rows first, so when duplicates are dropped the random copy is kept
    df["_order"] = (df["sample"] != "random").astype(int)
    df = df.sort_values(["_order", "brand", "date"], kind="stable").drop(columns="_order")

    steps = [("raw", df)]

    df = df.drop_duplicates("id")
    steps.append(("duplicate_id", df))

    df = df[~df.apply(lambda r: bool(REMOVED_RE.match(body_of(r.text, r.type))) or not r.text.strip(), axis=1)]
    steps.append(("removed_deleted", df))

    df = df[~df["text"].str.contains(BOT_RE)]
    steps.append(("bot_text", df))

    norm = df["text"].str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
    df = df[~norm.duplicated()]
    steps.append(("duplicate_text", df))

    df = df.assign(text_model=df["text"].map(model_text))
    df = df.assign(word_count=df["text_model"].str.split().str.len())
    df = df[df["word_count"] >= MIN_WORDS]
    steps.append(("under_15_words", df))

    print(f"  checking language on {len(df):,} rows (about a minute)...")
    df = df[df["text_model"].map(is_english)]
    steps.append(("non_english", df))

    # Funnel: rows remaining after each step, by brand
    funnel = pd.DataFrame({name: d.groupby("brand").size() for name, d in steps}).T.fillna(0).astype(int)
    funnel.index.name = "after_step"
    funnel["all_brands"] = funnel.sum(axis=1)
    return df.reset_index(drop=True), funnel


def final_counts(df):
    counts = df.groupby(["brand", "sample"]).size().unstack(fill_value=0)
    counts["total"] = counts.sum(axis=1)
    counts.loc["All brands"] = counts.sum()
    return counts


def main():
    raw = pd.read_csv(RAW)
    print(f"Loaded {len(raw):,} raw rows from {RAW.relative_to(ROOT)}")
    df, funnel = clean(raw)

    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    FUNNEL.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN, index=False)
    funnel.to_csv(FUNNEL)

    print("\nCleaning funnel (rows left after each step):")
    print(funnel)
    print("\nFinal clean counts (the resume number is the All brands total):")
    print(final_counts(df))
    print(f"\nSaved {len(df):,} rows to {CLEAN.relative_to(ROOT)} and the funnel to {FUNNEL.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
