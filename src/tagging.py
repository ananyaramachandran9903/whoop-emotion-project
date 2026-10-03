"""
Phase 4 - Tag each post with an ownership stage and one or more themes, using
transparent keyword rules (no model). Rules are deliberately simple so they can be
explained in one line each and hand-checked.

STAGE (one per post, or "untagged"). If several match, the first in this order wins:
    cancelling > first_weeks > daily_habit > considering
  - e.g. "Been using it 2 years, finally cancelling" -> cancelling
  - "switched to <this subreddit's own brand>" is joining, not leaving, so it is not
    counted as cancelling.

THEMES (any number per post): sleep, recovery, strain & training, HRV, accuracy,
battery & comfort, price & subscription, app & coaching.
"""

import re

import pandas as pd

STAGE_ORDER = ["considering", "first_weeks", "daily_habit", "cancelling"]
STAGE_LABELS = {
    "considering": "Considering",
    "first_weeks": "First weeks",
    "daily_habit": "Daily habit",
    "cancelling": "Cancelling",
}
_PRIORITY = ["cancelling", "first_weeks", "daily_habit", "considering"]

COMPETITORS = (r"(?:whoop|oura|garmin|apple watch|fitbit|pixel|samsung|galaxy watch|polar|coros|suunto|amazfit|"
               r"ultrahuman|ringconn|bevel|wahoo|google)")
# "cancel" phrases that are not about leaving; removed before the cancelling rules run
CANCEL_NOISE_RE = re.compile(
    r"cancel\w* (?:the|my|an|this|that|your|it)?\s?(?:order|alert|workout|activity|run|alarm|incident|in time|before)\b", re.I)
_TITLE_CANCEL_RE = re.compile(r"^\W*cancel\w*\b", re.I)  # post titles like "Cancel subscription…"

STAGE_PATTERNS = {
    "considering": [
        r"should i (?:buy|go with)", r"should i get (?:one|it|a |an |the (?:whoop|oura|garmin|apple|ring|watch|band|new))",
        r"worth it", r"(?:help|struggling to|trying to) choos\w*", r"choosing between", r"worth the (?:money|price|cost)",
        r"thinking (?:of|about) (?:getting|buying|switching)", r"considering (?:getting|buying)",
        r"(?:deciding|debating|torn) between", r"pull the trigger", r"before i buy",
        r"planning (?:to|on) (?:buy|get)", r"which (?:one|model|watch|ring) should",
    ],
    "first_weeks": [
        r"just (?:got|bought|received|started (?:using|wearing))", r"new to (?:whoop|oura|garmin|apple watch|wearables|smart (?:rings?|watches)|(?:this|the) (?!sub|subreddit|group|community|forum|reddit)\w+)",
        r"(?:first|1st) (?:week|few days|few weeks|month|night|day)s?", r"new user", r"newbie",
        r"(?:got|bought|received) (?:my|it|one|mine) (?:yesterday|today|last week|this week|a week ago|a few days ago)",
        r"day (?:one|two|three|1|2|3) (?:with|of)", r"(?:week|day)s? in\b",
    ],
    "daily_habit": [
        r"been (?:using|wearing|tracking with) (?:it|mine|my \w+|whoop|oura|garmin|the \w+)? ?for",
        r"(?:months|years) in\b",
        # device use every day, not just any "every night" (which is often about bedtime)
        r"(?:check|wear|use|look at|open)\w* (?:it |mine |my \w+ |the app |my data )?every (?:morning|day|night|single day)",
        r"every (?:morning|day) (?:i|when i) (?:check|look|open|wake up and check)",
        r"(?:\d+|a few|several|many|two|three|four|five|six) (?:months|years) (?:now|of|with|using|wearing)",
        r"long[- ]?time user",
        # tenure statements in months or years: "had my whoop for about a year", "member since 2023"
        r"(?:had|have had|owned|worn|wearing|using) (?:it|mine|my \w+|the \w+|whoop|oura|a garmin|an apple watch|one) "
        r"(?:for (?:(?:over|almost|nearly|about|around|like) )?(?:a|an|one|two|three|four|five|six|\d+|a few|several|many) "
        r"(?:\w+ )?(?:months?|years?)|since 20[12]\d)",
        r"(?:been )?(?:a )?(?:member|subscriber|user) (?:for (?:(?:over|almost|nearly|about) )?(?:a|an|one|two|three|\d+|a few|several) "
        r"(?:\w+ )?(?:months?|years?)|since 20[12]\d)",
        r"(?:\d+|one|two|three|four|five|a few|several) (?:months?|years?) of (?:wearing|using|tracking|data)", r"(?:since|from) (?:launch|day one|20[12]\d)", r"my streak",
        r"daily (?:habit|routine)", r"part of my routine",
    ],
    "cancelling": [
        # Phase 4 hand check: the old rule (any "cancel", "switched to", "refund") was right for only
        # 14 of 30 posts. These need first person, an account object, or a competitor.
        r"(?:i|i'?ve|i'?m|i am|we|we'?ve|finally)\b(?:\W+\w+){0,5}?\W+(?:cancel\w*|return(?:ed|ing)|refund\w*)",
        r"cancel\w* (?:my|our) (?:membership|subscription|account|plan|whoop|oura|ring|watch|trial|renewal)",
        r"return(?:ed|ing) (?:it|mine|the (?:watch|ring|band|strap|device|whoop|oura))\b",
        r"membership (?:ended|expired|expires|ends)", r"not (?:going to |gonna )?renew(?:ing)?",
        r"(?:want|request\w*|ask\w* for|demand\w*|get|got|getting|offered|issued) (?:\w+ ){0,3}refund", r"full refund",
        r"(?:sold|selling) (?:my|mine|it)", r"gave up on", r"giving up on",
        r"done with (?:whoop|oura|garmin|apple watch|it|this)", r"ditch(?:ed|ing)?",
        r"(?:thinking|considering|planning|ready|going|about)(?: of| about| to)? (?:leav\w*|cancel\w*|switch\w*|mov\w* (?:away|platforms|on))",
        r"switch\w* (?:back )?(?:to|over to) (?:a |an |the )?(?:different|another|other) (?:wearable|watch|ring|tracker|device|brand|platform)",
        r"(?:switch\w*|mov\w*|gone|going|went) (?:back )?(?:to|over to) (?:a |an |the )?" + COMPETITORS,
    ],
}
STAGE_RES = {s: re.compile(r"\b(?:" + "|".join(ps) + r")", re.I) for s, ps in STAGE_PATTERNS.items()}
_SWITCH_RE = re.compile(r"\bswitch(?:ed|ing)? (?:back )?(?:to|over to) (?:the |a |an |my )?([a-z0-9 ]{2,20})", re.I)
OWN_BRAND = {
    "WHOOP": ["whoop"],
    "Oura": ["oura"],
    "Garmin": ["garmin", "fenix", "forerunner", "venu", "epix"],
    "Apple Watch": ["apple", "aw ", "ultra", "series"],
}

THEME_PATTERNS = {
    "Sleep": [r"sleep\w*", r"slept", r"nap\w*", r"bedtime", r"insomnia", r"\brem\b", r"woke", r"wake up"],
    "Recovery": [r"recover\w*", r"readiness", r"body battery", r"rest day\w*"],
    "Strain & training": [r"strain", r"training", r"workout\w*", r"\brun\b", r"\bruns\b", r"running", r"lift\w*",
                          r"\bgym\b", r"cardio", r"vo2", r"zone ?2", r"marathon", r"\brace\b", r"cycling",
                          r"exercise\w*", r"\bsteps\b", r"calorie\w*", r"training load"],
    "HRV": [r"\bhrv\b", r"heart rate variability", r"\brhr\b", r"resting heart rate"],
    "Accuracy": [r"accura\w*", r"inaccura\w*", r"\bwrong\b", r"\boff by\b", r"overestimat\w*",
                 r"underestimat\w*", r"reliab\w*", r"unreliab\w*", r"chest strap", r"discrepanc\w*",
                 r"is (?:this|that|it) (?:right|correct|real)"],
    "Battery & comfort": [r"battery", r"charg(?:e|es|ed|ing|er)", r"comfort\w*", r"uncomfortable", r"rash",
                          r"itch\w*", r"\bband\b", r"sizing", r"\bsize\b", r"bulky", r"wrist"],
    "Price & subscription": [r"price\w*", r"\bcost\w*", r"\$\d", r"subscri\w*", r"membership", r"renew\w*",
                             r"refund", r"expensive", r"cheap\w*", r"\bfee\b", r"\bpay\w*", r"\bpaid\b",
                             r"monthly", r"yearly", r"annual\w*", r"worth the money"],
    "App & coaching": [r"\bapp\b", r"\bapps\b", r"update\w*", r"\bsync\w*", r"coach\w*", r"\bai\b",
                       r"insight\w*", r"journal", r"feature\w*", r"notification\w*", r"\bbug\w*",
                       r"crash\w*", r"interface", r"\bui\b"],
}
# (?<![a-z]) = keyword must start a word, so "itch" doesn't match "switched", "rash" not "crash"
THEME_RES = {t: re.compile(r"(?<![a-z])(?:" + "|".join(ps) + r")", re.I) for t, ps in THEME_PATTERNS.items()}
THEMES = list(THEME_PATTERNS)

# For H3 only: money language as a REASON for leaving. Excludes membership / subscription /
# renew / refund, which describe the act of cancelling (and are near-universal for
# membership brands like WHOOP), not why someone left.
PRICE_REASON_RE = re.compile(
    r"(?<![a-z])(?:price\w*|cost\w*|\$\d|expensive|overpriced|cheap\w*|afford\w*|fee\b|fees\b|"
    r"pay(?:ing)? for|paid for|worth the (?:money|price|cost)|not worth it|too much money|price (?:hike|increase))",
    re.I)


def _is_joining(text, brand):
    """True if every 'switched to X' in the text names this subreddit's own brand."""
    targets = [m.group(1).lower() + " " for m in _SWITCH_RE.finditer(text)]
    own = OWN_BRAND.get(brand, [])
    return bool(targets) and all(any(o in t for o in own) for t in targets)


def stage_flags(text, brand):
    flags = {st: bool(r.search(text)) for st, r in STAGE_RES.items() if st != "cancelling"}
    t = CANCEL_NOISE_RE.sub(" ", text)
    cancel = bool(STAGE_RES["cancelling"].search(t)) or bool(_TITLE_CANCEL_RE.match(t))
    if cancel and _is_joining(t, brand):
        # the only leaving-language is "switched to <this subreddit's own brand>": joining, not leaving
        non_switch = [p for p in STAGE_PATTERNS["cancelling"] if "switch" not in p and "mov" not in p]
        cancel = bool(re.search(r"\b(?:" + "|".join(non_switch) + r")", t, re.I)) or bool(_TITLE_CANCEL_RE.match(t))
    flags["cancelling"] = cancel
    return flags


def tag_stage(df, text_col="text_model"):
    """Adds stage_<name> flags and a single `stage` column (or 'untagged')."""
    flags = pd.DataFrame([stage_flags(t, b) for t, b in zip(df[text_col].fillna(""), df["brand"])], index=df.index)
    out = df.copy()
    for s in STAGE_ORDER:
        out[f"stage_{s}"] = flags[s]
    stage = pd.Series("untagged", index=df.index)
    for s in reversed(_PRIORITY):  # lowest priority first, so higher priority overwrites
        stage = stage.where(~flags[s], s)
    out["stage"] = stage
    return out


def tag_themes(df, text_col="text_model"):
    """Adds theme_<name> boolean columns and a readable `themes` column."""
    out = df.copy()
    t = df[text_col].fillna("")
    for theme, rx in THEME_RES.items():
        out[f"theme_{theme}"] = t.str.contains(rx)
    out["price_reason"] = t.str.contains(PRICE_REASON_RE)
    cols = [f"theme_{th}" for th in THEMES]
    out["themes"] = out[cols].apply(lambda r: ", ".join(th for th, v in zip(THEMES, r) if v), axis=1)
    return out
