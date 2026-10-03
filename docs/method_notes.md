# Method notes

*Independent student project. Not affiliated with, sponsored by, or endorsed by WHOOP, Oura, Garmin or Apple.*

This file records how the data was collected and cleaned, and why each analysis choice was made. Results are added in the README once the analysis is final.

## 1 · Data source and window

- **Source:** public Reddit posts and comments via the [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift) archive API, not Reddit's official API (new Reddit API access now requires approval).
- **Communities:** r/whoop (focal), r/ouraring, r/Garmin, r/AppleWatch (comparisons).
- **Window:** Sep 28, 2025 to Sep 28, 2026, split into 53 weekly windows. Same window for every brand.
- **Run:** collected Sep 30, 2026; 1,495 API requests; 1 slice skipped after retries (r/Garmin comments, late in the window).

## 2 · Sampling

- **Random sample:** per brand, per week, 20 posts (random) and 25 comments (highest score). Drawn from the start of the week plus 2 random 100-item slices in busy weeks (4 for r/AppleWatch). Every brand hit the weekly cap in every week, so the sample is spread evenly across the year.
- **Stage boost:** from each week's leftover candidates, up to 15 posts and 15 comments that mention an ownership stage ("just got", "worth it", "cancel", "switching to", ...). Labeled `sample = stage_boost` and used only for within-stage comparisons.
- **r/AppleWatch** is filtered to fitness and health keywords, since most of that subreddit is off-topic.
- **Bots** (AutoModerator, `*bot` accounts) dropped. Usernames were used only for that check and never saved.

### Raw counts

| Brand | Random | Stage boost | Total |
|---|---|---|---|
| WHOOP | 2,385 | 1,135 | 3,520 |
| Oura | 2,385 | 1,041 | 3,426 |
| Garmin | 2,385 | 994 | 3,379 |
| Apple Watch | 2,385 | 452 | 2,837 |
| **Total** | **9,540** | **3,622** | **13,162** |

## 3 · Cleaning

Rows left after each step (`outputs/cleaning_funnel.csv`):

| Step | Apple Watch | Garmin | Oura | WHOOP | All |
|---|---|---|---|---|---|
| Raw | 2,837 | 3,379 | 3,426 | 3,520 | 13,162 |
| Duplicate id | 2,837 | 3,379 | 3,426 | 3,520 | 13,162 |
| Removed / deleted | 2,802 | 3,242 | 3,333 | 3,429 | 12,806 |
| Bot text | 2,802 | 3,242 | 3,333 | 3,429 | 12,806 |
| Duplicate text | 2,794 | 3,235 | 3,318 | 3,409 | 12,756 |
| Under 15 words | 2,524 | 2,545 | 2,696 | 2,663 | 10,428 |
| Non-English | 2,517 | 2,538 | 2,692 | 2,659 | 10,406 |

### Final clean counts

| Brand | Random | Stage boost | Total |
|---|---|---|---|
| Apple Watch | 2,082 | 435 | 2,517 |
| Garmin | 1,586 | 952 | 2,538 |
| Oura | 1,730 | 962 | 2,692 |
| WHOOP | 1,604 | 1,055 | 2,659 |
| **All brands** | **7,002** | **3,404** | **10,406** |

Clean random counts differ by brand, so brands are always compared with shares (%), never raw counts.

## 4 · Emotion labels

- **Model:** [SamLowe/roberta-base-go_emotions](https://huggingface.co/SamLowe/roberta-base-go_emotions), a multi-label classifier over the 28 GoEmotions labels. Threshold 0.30. Text truncated to 512 tokens.
- **First pass (200-post sample, 50 per brand):** neutral 40%, curiosity 28%, confusion 17.5%, approval 11.5%, disappointment 6%, joy 2.5%, annoyance 2%, fear 1%, nervousness 0%, pride 0% (highest pride score in the sample: 0.05).
- **Hand check (20 posts):** labels made sense for 15 of 20 (75%), checked by one person. Common errors: troubleshooting questions labeled curiosity; pride labeled joy; critical posts that start "I agree" read as approval.

### Core emotion groups

| Group | GoEmotions labels |
|---|---|
| Curiosity / help-seeking | curiosity |
| Confusion / doubt | confusion |
| Frustration & disappointment | annoyance, anger, disapproval, disappointment |
| Pride & joy | joy, excitement, pride, optimism, admiration |
| Anxiety / worry | fear, nervousness, plus a worry word list |

The plan's original six groups gave Anxiety 1% and Pride 0% in the sample, too few to test the hypotheses. Pride was merged into Pride & joy, confusion became its own group, and disapproval joined frustration.

**Worry word list:** worried, anxious, scared, nervous, afraid, panic, freaking out, paranoid, obsessed, concerned, "is this normal", "should I be worried" (ignoring "no worries" / "don't worry"). "Stress" and "strain" are excluded because they are Garmin and WHOOP metric names, not feelings. Matches are hand-checked and the hit rate is reported.

## 5 · Stage and theme tags

- **Stage** (keyword rules, one per post): considering, first weeks, daily habit, cancelling. If several match: cancelling > first weeks > daily habit > considering. "Switched to <this subreddit's own brand>" counts as joining, not cancelling.
- **Themes** (keyword rules, any number per post): sleep, recovery, strain & training, HRV, accuracy, battery & comfort, price & subscription, app & coaching. Keyword groups were chosen over BERTopic for transparency.
- **Price as a reason for leaving (H3):** counts money language only (price, cost, $, expensive, afford, worth the money). It excludes membership / subscription / renew / refund, which describe the act of cancelling and appear in nearly every WHOOP cancellation, so they would bias the comparison.

## 6 · Phase 4 hand checks

All hand checks were labeled by the author with AI assistance (Claude proposed calls with a written reason; the author reviewed them).

**Round 1 (30 posts: 20 random, 5 per brand + 10 worry-word matches)**

| Sample | Emotions reasonable | Stage right |
|---|---|---|
| Random (20) | 16 / 20 | 17 / 20 |
| Worry-word matches (10) | 5 / 10 | 8 / 10 |

Most worry misses were negations ("not so worried", "without getting obsessed", "I don't have the anxiety I would usually have") and "obsessed with my Whoop" (enthusiasm). Fixes: negated phrases (straight or curly apostrophes) are removed before matching; "obsessed" only counts as "obsessed over/about". Stage fixes: daily habit needs device context or a tenure statement in months/years ("had my whoop for a year", "member since 2023"), not just "every night"; "should I get" needs a product after it; "help choosing" counts as considering; "new to this subreddit" no longer counts as a new owner.

**Round 2, after the fixes (same 20 random posts + 10 new worry matches)**

| Sample | Emotions reasonable | Stage right |
|---|---|---|
| Random (20) | 17 / 20 (85%) | 19 / 20 (95%) |
| Worry-word matches (10) | 8 / 10 | 6 / 10 |
| **All (30)** | **25 / 30 (83%)** | **25 / 30 (83%)** |

**Fresh check of the worry word list (10 matches never used for tuning): 6 / 10 real worry.** Combined with round 2, about 70% of worry-word matches are real worry (14 of 20). Remaining false alarms: advice or hypotheticals ("if you are worried about this…", "if they were really concerned"), mentions of anxiety medication, and "is this normal?" used for confusion rather than worry. The anxiety measure is therefore generous: treat anxiety shares as an upper bound, and rely on comparisons between brands and stages more than on the level itself.

**Cancelling tag check (20 WHOOP + 10 Garmin cancelling posts): 14 / 30 were really leaving (WHOOP 10/20, Garmin 4/10).** "Switched to" was right 2 of 9 times (wrist, bicep band, Zyn, AMOLED); "cancel" caught advice, hypotheticals and cancelled store orders. Fix: cancelling now needs first person ("I cancelled", "I'm trying to cancel"), an account object ("cancel my membership"), a post title starting with "Cancel", a refund request, or switching to a named competitor or "a different wearable". Phrases like "cancel the order / alert" are ignored. On the same 30 posts the new rule keeps all 14 real leavers and 2 of 16 false ones. **Fresh check (30 new posts): WHOOP 14 / 20 (70%) really leaving, Garmin 2 / 10 (20%).** Garmin's misses were own-brand moves ("went to Garmin" for a repair, switching between Garmin models, coming back to Garmin) and "I cancelled" for calendar events and training plans. Exit comparisons across brands are therefore indicative only; the analysis uses within-WHOOP comparisons for exits. Across both checks, 13 of 24 real WHOOP exits described trouble cancelling, returning a trial or being billed after cancelling.

**Known limits, not fixed:** the model misses quiet pride ("5K done… no better way to kick off the morning" scored neutral); returning one ring color for another is tagged as cancelling; owners who describe tenure loosely ("loved Oura for years", "had the 4 and the 5MG for over 2 years") are not tagged daily habit.

**Privacy:** several worry matches discuss pregnancy, fertility or mental health. These are counted in aggregates only and are never quoted.

## 7 · Analysis rules

- Overall shares and brand comparisons use the random sample only.
- Within-stage comparisons use random + stage boost.
- Shares are "% of posts expressing the emotion" (a post can express several), reported with 95% Wilson intervals. Cells with fewer than 30 posts are flagged.
- Hypothesis tests are two-proportion z-tests. "Supported" means the difference is in the predicted direction, p < 0.05, and both groups have at least 30 posts.
- All findings are associations in a self-selected sample (Reddit skews toward enthusiasts and people with complaints), not causes.
