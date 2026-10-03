"""
Emotion labeling with a GoEmotions-trained model (used in Phase 3 sample and Phase 4 full run).

Model: SamLowe/roberta-base-go_emotions (Hugging Face). It is multi-label: it gives
each of the 28 GoEmotions labels its own 0-1 score, so one post can show several
emotions at once.

How we turn 28 labels into the project's core emotions:
  - A core emotion's score = the highest score among its member labels.
  - A post "expresses" a core emotion if that score >= THRESHOLD (multi-label flags).
  - Anxiety / worry is ALSO flagged when the text uses explicit worry language
    (WORRY_RE). The model rarely scores fear/nervousness on this data (1% of the
    Phase 3 sample), and misses plain worry like "Is this normal? my recovery has
    been in the red". The word list is hand-checked in Phase 4.
  - Its primary emotion = the core emotion with the highest score, if >= THRESHOLD;
    otherwise "none" (usually neutral or an emotion outside our groups).
THRESHOLD is a judgment call, checked against the hand-checked samples.

Groups were set in Phase 3 from the 200-post sample (Oct 1, 2026): pride scored
0% (max 0.05) so it is merged into Pride & joy; confusion (17.5%) became its own
group; disapproval joined Frustration & disappointment.
"""

import re

import numpy as np
import pandas as pd

MODEL = "SamLowe/roberta-base-go_emotions"
THRESHOLD = 0.30

LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion",
    "curiosity", "desire", "disappointment", "disapproval", "disgust", "embarrassment",
    "excitement", "fear", "gratitude", "grief", "joy", "love", "nervousness", "optimism",
    "pride", "realization", "relief", "remorse", "sadness", "surprise", "neutral",
]

# Final groups (decided in Phase 3)
CORE_GROUPS = {
    "Anxiety / worry": ["fear", "nervousness"],
    "Confusion / doubt": ["confusion"],
    "Frustration & disappointment": ["annoyance", "anger", "disapproval", "disappointment"],
    "Pride & joy": ["joy", "excitement", "pride", "optimism", "admiration"],
    "Curiosity / help-seeking": ["curiosity"],
}
ANXIETY = "Anxiety / worry"

# Explicit worry language. "stress" and "strain" are deliberately excluded: they are
# Garmin / WHOOP metric names, not feelings.
WORRY_RE = re.compile(
    r"\b(?:worr(?:y|ied|ies|ying)|anxi(?:ous|ety)|scared|scary|terrified|nervous|afraid|"
    r"panic(?:king|ked)?|freak(?:ed|ing) (?:me )?out|paranoid|obsess(?:ing|ive)|obsessed (?:over|about)|"
    r"alarm(?:ed|ing)|concerned|concerning|is (?:this|that|it) normal|should i be worried)\b", re.I)
# Phrases that use the words but mean the opposite. Removed before matching.
# Added after the Phase 4 hand check (5 of 10 worry matches were real worry; the misses
# were negations like "not so worried", "without getting obsessed", "I don't have the anxiety").
_APOS = "['\u2019]"  # straight or curly apostrophe
WORRY_NEGATED_RE = re.compile(
    r"\b(?:no worries|no worry|nothing to worry about|something to worry about|"
    rf"(?:don{_APOS}?t|do not|didn{_APOS}?t|did not|won{_APOS}?t|wouldn{_APOS}?t|never|not|no longer|not as|not so|"
    r"not too|not that|not really|without|stop|stopped)\s+(?:\w+\s+){0,3}?"
    r"(?:worr\w*|anxi\w*|obsess\w*|nervous|scared|concerned|panic\w*)(?:\s+(?:about|over)\s+(?:\w+\s?){0,3})?)",
    re.I)


def worry_flag(texts):
    """True where a text uses explicit worry language (ignoring 'no worries' style phrases)."""
    t = pd.Series(list(texts)).fillna("").astype(str)
    return t.str.replace(WORRY_NEGATED_RE, " ", regex=True).str.contains(WORRY_RE).to_numpy()


def load_model(model=MODEL):
    """Hugging Face pipeline on Apple GPU (mps) if available, else CPU."""
    import torch
    from transformers import pipeline
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = 0
    else:
        device = -1
    print(f"Loading {model} on {device if device != -1 else 'cpu'} "
          "(first run downloads about 500 MB)...")
    return pipeline("text-classification", model=model, top_k=None, device=device)


def _to_score_dict(result):
    # Pipelines return [{"label", "score"}, ...] per text; some versions nest one level deeper.
    if result and isinstance(result[0], list):
        result = result[0]
    return {d["label"]: float(d["score"]) for d in result}


def score_texts(clf, texts, batch_size=16):
    """DataFrame with one column per GoEmotions label (scores 0-1), same order as `texts`."""
    texts = [str(t) for t in texts]
    out = clf(texts, batch_size=batch_size, truncation=True, max_length=512)
    rows = [_to_score_dict(r) for r in out]
    return pd.DataFrame(rows).reindex(columns=LABELS).fillna(0.0)


def add_core_emotions(scores, groups=None, threshold=THRESHOLD, texts=None):
    """Adds core-emotion scores, flags (expresses_<group>), primary_emotion and top labels.

    Pass `texts` (same order as `scores`) to add the worry word list to Anxiety / worry.
    """
    groups = groups or CORE_GROUPS
    scores = scores[LABELS].astype(float)
    out = scores.copy()
    core = pd.DataFrame({g: scores[members].max(axis=1) for g, members in groups.items()})
    worry = None
    if texts is not None and ANXIETY in groups:
        worry = pd.Series(worry_flag(texts), index=scores.index)
        out["worry_words"] = worry
        # A worry-word post counts as anxiety even when the model score is low
        core[ANXIETY] = core[ANXIETY].where(~worry, core[ANXIETY].clip(lower=threshold))
    for g in groups:
        out[f"core_{g}"] = core[g]
        out[f"expresses_{g}"] = core[g] >= threshold
    best = core.idxmax(axis=1)
    out["primary_emotion"] = best.where(core.max(axis=1) >= threshold, "none")
    vals = scores[LABELS].to_numpy(dtype=float)
    idx = np.argsort(-vals, axis=1)[:, :3]
    out["top_labels"] = [", ".join(f"{LABELS[j]} {vals[i, j]:.2f}" for j in row) for i, row in enumerate(idx)]
    out["top_is_neutral"] = scores[LABELS].idxmax(axis=1) == "neutral"
    return out


def label_distribution(scores, threshold=THRESHOLD):
    """Share of texts where each of the 28 labels is >= threshold, plus how often it is the top label."""
    scores = scores[LABELS].astype(float)
    above = (scores[LABELS] >= threshold).mean().rename("share_above_threshold")
    top = scores[LABELS].idxmax(axis=1).value_counts(normalize=True).rename("share_as_top_label")
    grouped = {lab: g for g, members in CORE_GROUPS.items() for lab in members}
    dist = pd.concat([above, top], axis=1).fillna(0.0)
    dist["core_group"] = [grouped.get(lab, "") for lab in dist.index]
    return dist.sort_values("share_above_threshold", ascending=False)
