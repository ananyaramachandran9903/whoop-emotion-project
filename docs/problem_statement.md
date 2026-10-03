# Problem statement and hypotheses

*Independent student project. Not affiliated with, sponsored by, or endorsed by WHOOP.*

## Problem statement

Fitness wearables promise empowerment: know your body, train smarter, sleep better. But the same data that motivates some people can make others anxious. A low recovery score, a "bad" night of sleep or an HRV dip can feel like a verdict instead of a guide. How people *feel* about their data may shape whether they buy a wearable, build a habit around it or walk away.

This project asks: **which emotions are associated with adopting, keeping and abandoning a fitness wearable, and how could WHOOP build its brand around empowerment rather than uncertainty?**

I analyze public Reddit discussion from the past 12 months (Sep 28, 2025 to Sep 28, 2026) in four brand communities: r/whoop (the focal brand) and r/ouraring, r/Garmin and r/AppleWatch (comparisons). A GoEmotions-trained language model labels the emotion in each post. Keyword rules tag the owner's stage (considering, first weeks, daily habit, cancelling) and the topic (sleep, recovery, HRV, price and subscription, and so on). The output is three insights and a one-page, empowerment-led campaign brief.

## Hypotheses

Each hypothesis names what I will measure and what would count as support. These are correlations in a self-selected sample, not causal claims.

**H1: Anxiety peaks early.**
Among WHOOP posts, the share labeled *anxiety* (fear, nervousness) is higher in first-weeks posts than in daily-habit posts.
- Measure: anxiety share by stage, WHOOP only.
- Supported if first-weeks anxiety share is clearly above daily-habit share and both stages have at least 30 posts.

**H2: Pride grows with the habit.**
Among WHOOP posts, *pride* and *joy* make up a larger share of daily-habit posts than of first-weeks posts.
- Measure: pride + joy share by stage, WHOOP only.
- Supported if the daily-habit share is higher than the first-weeks share, with at least 30 posts in each stage.

**H3: Leaving is about value, not the data.**
Cancelling posts are dominated by *frustration* and *disappointment*, and WHOOP cancelling posts mention price or subscription more often than Garmin and Apple Watch cancelling posts do.
- Measure: emotion mix of cancelling posts by brand; share of cancelling posts tagged with the price-and-subscription theme, by brand.
- Supported if frustration + disappointment is the largest emotion group in cancelling posts, and WHOOP's price/subscription share is above Garmin's and Apple Watch's.

## Scope and guardrails

- **Scope:** 4 brands, Reddit only, 5–6 core emotion groups. Anything else goes on a "next steps" list.
- **Claims:** "associated with," never "causes."
- **Sample bias:** Reddit skews toward enthusiasts and complainers. Stated in every write-up.
- **Privacy:** no usernames stored, aggregate results only, never infer an individual's health. Raw post text stays out of the public repo.
- **Tone:** anxiety is a challenge for the whole category, not an accusation against WHOOP.
- **Branding:** no WHOOP logos or anything that could look official.
- **AI use:** every model and tool used, and what for, is listed in the README and the post.
