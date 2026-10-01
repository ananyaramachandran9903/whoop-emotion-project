# Empowerment vs. Anxiety: The Emotions Behind Fitness Wearables

*An independent student project. Not affiliated with, sponsored by, or endorsed by WHOOP, Oura, Garmin or Apple.*

**Question:** Which emotions are associated with adopting, keeping and abandoning a fitness wearable, and how could WHOOP build its brand around empowerment rather than anxiety?

**Data:** Public Reddit posts and comments from r/whoop, r/ouraring, r/Garmin and r/AppleWatch, Sep 28, 2025 to Sep 28, 2026, collected through the [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift) public Reddit archive.

**Status:** In progress. Results and charts will be added here.

See [docs/problem_statement.md](docs/problem_statement.md) for the full problem statement and hypotheses.

## Repo layout

```
docs/          problem statement, hypotheses, method notes
src/           data collection and cleaning scripts
notebooks/     analysis notebooks, run in order
data/          raw and clean data (git-ignored; not published)
outputs/       charts and aggregate tables
```

## How to reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/collect_reddit.py        # Phase 2: writes data/raw/raw_reddit.csv
```

## Results

*Coming soon.*

## Method (short version)

1. **Collect** posts and top comments from each subreddit over the same 12-month window, sampled evenly by week.
2. **Clean** out duplicates, deleted posts, bots, very short text and non-English text.
3. **Label emotions** with a GoEmotions-trained model from Hugging Face, grouped into 5–6 core emotions.
4. **Tag stage and theme** with keyword rules (considering, first weeks, daily habit, cancelling; sleep, recovery, HRV, price and subscription, and more).
5. **Compare** emotion mix by stage for WHOOP and by theme across all four brands.

## Limitations and ethics

- Reddit over-represents enthusiasts and people with complaints. Results describe these communities, not all wearable owners.
- Findings are associations, not causes.
- Data comes from a third-party archive of public Reddit content, not Reddit's official API.
- No usernames are collected or stored. Only aggregate results are published; raw post text is not in this repo.
- Emotion labels come from a model and can be wrong. A hand-checked error rate is reported.

## AI tools used

*To be completed:* models and assistants used, and what each was used for.
