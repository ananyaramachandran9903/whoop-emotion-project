# Data collection, cleaning and method notes (Phases 2–4)

Run finished Wed Sep 30, 2026 (local). Source: Arctic Shift public Reddit archive API (not Reddit's official API). Window: Sep 28, 2025 to Sep 28, 2026 (53 weekly windows). 1,495 API requests, 91 minutes, 1 slice skipped after retries (r/Garmin comments, late in the window).

## Raw counts

| Brand | Random posts | Random comments | Random total | Stage-boost posts | Stage-boost comments | Stage-boost total | All rows |
|---|---|---|---|---|---|---|---|
| WHOOP (r/whoop) | 1,060 | 1,325 | 2,385 | 712 | 423 | 1,135 | 3,520 |
| Oura (r/ouraring) | 1,060 | 1,325 | 2,385 | 716 | 325 | 1,041 | 3,426 |
| Garmin (r/Garmin) | 1,060 | 1,325 | 2,385 | 740 | 254 | 994 | 3,379 |
| Apple Watch (r/AppleWatch, fitness-filtered) | 1,060 | 1,325 | 2,385 | 384 | 68 | 452 | 2,837 |
| **Total** | | | **9,540** | | | **3,622** | **13,162** |

## Cleaning funnel (Phase 3, Oct 1, 2026)

Rows left after each step:

| Step | Apple Watch | Garmin | Oura | WHOOP | All |
|---|---|---|---|---|---|
| Raw | 2,837 | 3,379 | 3,426 | 3,520 | 13,162 |
| Duplicate id | 2,837 | 3,379 | 3,426 | 3,520 | 13,162 |
| Removed / deleted | 2,802 | 3,242 | 3,333 | 3,429 | 12,806 |
| Bot text | 2,802 | 3,242 | 3,333 | 3,429 | 12,806 |
| Duplicate text | 2,794 | 3,235 | 3,318 | 3,409 | 12,756 |
| Under 15 words | 2,524 | 2,545 | 2,696 | 2,663 | 10,428 |
| Non-English | 2,517 | 2,538 | 2,692 | 2,659 | 10,406 |

Bot text removed 0 rows because bots were already dropped at collection. The 15-word minimum is the biggest filter (2,328 rows).

## Final clean counts

| Brand | Random | Stage boost | Total |
|---|---|---|---|
| Apple Watch | 2,082 | 435 | 2,517 |
| Garmin | 1,586 | 952 | 2,538 |
| Oura | 1,730 | 962 | 2,692 |
| WHOOP | 1,604 | 1,055 | 2,659 |
| **All brands** | **7,002** | **3,404** | **10,406** |

**Resume number: 10,406 Reddit posts and comments analyzed across 4 brand communities.**

Note: clean random counts differ by brand (Apple Watch keeps more because its fitness filter already favored longer posts). Compare brands with shares (%), never raw counts.

## Emotion model first pass (Phase 3)
- Model: SamLowe/roberta-base-go_emotions, threshold 0.30, 200-post random sample (50 per brand).
- Hand check: 20 posts (5 per brand), model labels made sense for 15 of 20 (75%), checked by one person.
- Label frequencies in the 200-post sample (share >= 0.30): neutral 40%, curiosity 28%, confusion 17.5%, approval 11.5%, disappointment 6%, amusement 6%, gratitude 5%, admiration 4.5%, joy 2.5%, disapproval 2.5%, annoyance 2%, fear 1%, nervousness 0%, anger 0%, excitement 0%, pride 0% (highest pride score in the sample: 0.05).
- Patterns seen: questions almost always labeled curiosity (often help-seeking, not curiosity); pride rarely detected (labeled joy instead); confusion common; critical posts sometimes read as approval ("I agree... this is crazy"); about 45% of posts get no core emotion (mostly neutral advice/info).

## Final emotion groups (decided Oct 1, 2026)

| Group | GoEmotions labels | Share in 200-post sample |
|---|---|---|
| Curiosity / help-seeking | curiosity | 28% |
| Confusion / doubt | confusion | 17.5% |
| Frustration & disappointment | annoyance, anger, disapproval, disappointment | 10% |
| Pride & joy | joy, excitement, pride, optimism, admiration | 9.5% |
| Anxiety / worry | fear, nervousness + worry word list | 3.5% |

- Why: the plan's original groups gave Anxiety 1% and Pride 0%, too small to test H1/H2. Pride merged into Pride & joy; confusion added as its own group; disapproval added to frustration.
- Worry word list (worried, anxious, scared, nervous, afraid, panic, freaking out, paranoid, obsessed, concerned, "is this normal", "should I be worried"; ignores "no worries" / "don't worry"). "Stress" and "strain" excluded because they are Garmin/WHOOP metric names. About 3 in 5 matches were real worry in the sample; hand-checked again in Phase 4.

## Phase 4 method decisions
- Stage rules (keywords), one stage per post, priority cancelling > first weeks > daily habit > considering. "Switched to <this subreddit's own brand>" counts as joining, not cancelling.
- Themes (keywords, multi-label): sleep, recovery, strain & training, HRV, accuracy, battery & comfort, price & subscription, app & coaching. Chose keyword groups over BERTopic for transparency and time.
- H3 uses a separate "price as a reason" measure (price, cost, $, expensive, afford, worth the money, ...), NOT the price & subscription theme. The theme includes "membership / cancel subscription", which nearly every WHOOP cancellation mentions (membership-only brand), so it would bias H3 toward WHOOP.
- Tests: two-proportion z-tests; "supported" = right direction, p < 0.05, n >= 30 per group. Shares reported with 95% Wilson intervals; cells with n < 30 flagged.

## Rules for analysis
- Overall emotion shares and brand comparisons: use `sample == "random"` only.
- Within-stage comparisons (first weeks, cancelling, ...): use random + stage_boost.
- Stage boost is about a third of clean rows, so never mix it into overall shares.
