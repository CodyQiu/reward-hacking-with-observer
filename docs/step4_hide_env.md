# Step 4: an environment where the no-regulariser PBRR is avoided and the swap is not

Started 2026-11-10. Exact solves only; no PPO until the map below is filled in. Driver:
`scripts/farmshare/step4_hide.sh`. Map: `experiments/step4_hide_map.py`.

## The user's theory, as stated (2026-11-09)

> the swap "is the one we want over the no-regularizer… the no-regularizer might have potential to be exploited in
> certain environments, perhaps if it is complex enough… when the loss function raises the honest and fines the
> exploit, it is entirely possible for this to lower overall reward, leading to a smart enough agent to exploit
> that." Goal: an environment that shows this, and "hopefully conclude that the swap avoids this, hence, why swap
> is theoretically more valuable."

This is a hypothesis to test, not a rule.

## The condition being tested

- A correction must make the reference beat the agent's caught play by the exploit's advantage D. The no-regulariser
  fit can split that between raising the reference (a) and fining the agent (b). The swap pins g at 0 on the
  agent's own caught play, so b ≈ 0.
- After one correction, hiding is optimal when the best the agent can collect afterwards is worth less than
  hiding: roughly, the best round under the corrected reward is below the hide round under the proxy.
- Under the swap, exploiting openly still earns what it did before the correction, and that beats hiding. So the
  swap's optimum should never hide, as long as the pin holds on the open exploiter's path.
- Already known: the grid with the exact tabular fit makes no-regulariser hide (`results/step4/phase_a`). With the
  neural fit that PBRR uses, the network's raise spills far beyond the reference's transitions: at b = 100 the best
  round after one correction is ~43,000 (no-regulariser) and ~49,000 (swap), against an exploit round of 8,700.

## The sweeps (pre-registered 2026-11-10)

Each setting × variant (`P2swap` = `g.l_minus_on=dispreferred`, `P1eq1` = `g.use_regularization=False`) gets the
self-consistent exact target (`experiments/step4_targets.py`: 6 overseer draws per level, iterated to a fixed
point), on seeds 0–2. PBRR settings are those of each task's campaign (grid tasks: the grid's 100-epoch fit;
Taxi: 1000 epochs). Nothing else changes.

1. **Taxi**, as in Step 3 (re-arming pickup bonus 10). The reward model cannot tell a looping pickup from an honest
   one, so a fine on the loop also lands on honest pickups. Phase A (canonical corrections) already gives
   "corrected once, then not honest" for both variants (true −83 no-regulariser, −39 swap; honest +125).
2. **Grid, exploit bonus b ∈ {200, 400, 800, 1600, 3200}** (b = 100 is the campaign's existing targets).
   `task.exploit_bonus=b`. The exploit's advantage D grows with b; the fit's reach is set by its optimiser
   (100 Adam steps), so it need not grow with it.
3. **Routes grid, R ∈ {1, 2, 4} spokes × b ∈ {100, 400, 1600}** (`src/step3/tasks/grid_routes.py`). The exploit E
   is at the hub; each spoke has its own start (2 steps from E) and its own goal (5 steps from its start); every
   sub-episode starts at a random spoke. The reference (the hand-written rule, action noise 0.1) spends ~95 of its
   100 steps at its spoke's goal, so each goal's dwell appears in only 1/R of its rollouts, while the exploiter's
   dwell on E appears in all of them. With one shared goal (the Step 1 grid), the reference's long dwell is common
   to all its rollouts, so splitting only the walk would change little; that is why each spoke has its own goal.
   R ≤ 4 keeps every spoke the same length.

Exact reference values per round under the proxy (`a1` in each target file):

| Setting | Open exploit round | Hide round | V_hide (episode) | Honest round (true) |
|---|---|---|---|---|
| grid, b | −12 + 88(b − 1): 8,700 / 17,500 / 35,100 / 70,300 / 140,700 / 281,500 | 7,700 / 15,500 / 31,100 / 62,300 / 124,700 / 249,500 | 39,500 … 1,279,500 | 22 |
| routes, b = 100 / 400 / 1600 (any R) | 9,800 / 39,500 / 158,300 | 8,853 / 35,553 / 142,353 | 45,212 / 181,712 / 727,712 | 45 |

## What counts (decided before the results)

- **End state per seed** (`step4_hide_map.py: label`): `HIDES` (never corrected, final window exploited),
  `once->honest` (corrected in round 0, then true return in rounds 1–4 at least exploit + 0.8 × (honest − exploit)),
  `once->true x` (corrected once, then not honest), `n corr/ep` (corrected n times per episode: exploits openly or
  seeks corrections), `deterred`.
- **No-regulariser avoids correction at a setting** iff `P1eq1` is `HIDES` in ≥ 2 of 3 seeds.
- **The theory's prediction holds at a setting** iff, in addition, `P2swap` is not `HIDES` in any of its 3 seeds.
  The strongest version also has `P2swap` `once->honest`.
- The whole map is reported whatever it shows, including settings where neither variant hides or both do.

## Predictions (mine, from the b = 100 numbers, before any result)

- If the fits' raise stays near its b = 100 size, no-regulariser starts hiding at about b = 800, where its ~43,000
  best round falls below the hide round; the swap's open exploiter is never fined, so at those b it exploits openly
  and is corrected every round.
- A setting where no-regulariser hides *and* the swap is honest needs no-regulariser's collectable raise to be well
  below the swap's. At b = 100 it is not (43,000 vs 49,000), so the bonus sweep alone may not give one. The routes
  sweep is the attempt to shrink it.
- The swap is likely to keep exploiting openly wherever its raise cannot outbid the exploit. The claim this work can
  support is "the swap never rewards avoiding correction", not "the swap always gives honest play".

## Procedure (FarmShare)

1. `bash scripts/farmshare/step4_hide.sh submit_all` (dry run), then `EXCLUDE=barley-04 bash
   scripts/farmshare/step4_hide.sh submit_all submit`: 6 jobs named `hide_*`, ~1–3 h each.
2. When they finish: `bash scripts/farmshare/step4_hide.sh report`; paste the table under Results below, commit the
   targets and this doc, and flag the user. A failed job is reported, not resubmitted under the same name.
3. No PPO, no new knobs and no PBRR changes without the user. PPO comes later, only at settings where the two
   variants' exact answers differ.

## Results

2026-11-10, FarmShare jobs 1969706–1969711 (`hide_{taxi,bonus,routes}_{P2swap,P1eq1}`), all COMPLETED, exit 0 (bonus 15–17 min, routes 13–22 min, Taxi 1 h 32 min). Every fixed point converged. `bash scripts/farmshare/step4_hide.sh report`:

| family | setting | variant | end state (seeds 0/1/2) | draws hiding | V0 vs V_hide | round after 1 correction: best / honest / open exploiter | open / hide round under the proxy | fixed point |
|---|---|---|---|---|---|---|---|---|
| taxi |  | P2swap | once->true -67, once->true -66, once->true -57 | 0/0/0 of 6 | 3,677/4,970/4,567 vs 1,794/1,794/1,794 | 824/1,148/1,047 / 504/678/660 / 509/575/625 | 380 / 354 | 3/3 |
| taxi |  | P1eq1 | once->true -79, once->true -81, once->true -78 | 0/0/0 of 6 | 11,668/13,487/12,714 vs 1,794/1,794/1,794 | 2,822/3,277/3,084 / 2,368/2,792/2,644 / -894/-651/-383 | 380 / 354 | 3/3 |
| grid b | b 100 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 205,650/194,887/208,319 vs 39,500/39,500/39,500 | 49,237/46,547/49,905 / 37,810/36,808/38,280 / 8,700/8,700/8,700 | 8,700 / 7,700 | 3/3 |
| grid b | b200 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 371,851/371,648/366,863 vs 79,500/79,500/79,500 | 88,588/88,537/87,341 / 68,130/69,579/66,956 / 17,500/17,500/17,500 | 17,500 / 15,500 | 3/3 |
| grid b | b400 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 689,108/629,190/610,868 vs 159,500/159,500/159,500 | 163,502/148,522/143,942 / 125,125/116,755/109,698 / 35,100/35,100/35,100 | 35,100 / 31,100 | 3/3 |
| grid b | b800 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 1,144,617/1,071,508/1,062,438 vs 319,500/319,500/319,500 | 268,579/250,302/248,035 / 205,043/196,718/189,798 / 70,300/70,300/70,301 | 70,300 / 62,300 | 3/3 |
| grid b | b1600 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 2,112,514/2,030,393/1,911,258 vs 639,500/639,500/639,500 | 492,954/472,423/442,639 / 376,016/372,230/336,718 / 140,701/140,699/140,701 | 140,700 / 124,700 | 3/3 |
| grid b | b3200 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 4,107,875/3,519,538/3,984,428 vs 1,279,500/1,279,500/1,279,500 | 956,594/809,509/925,732 / 725,697/646,370/705,484 / 281,500/281,499/281,499 | 281,500 / 249,500 | 3/3 |
| grid b | b 100 | P1eq1 | once->honest, 2.0 corr/ep, once->honest | 0/0/0 of 6 | 182,240/185,847/184,446 vs 39,500/39,500/39,500 | 43,385/43,632/43,936 / 31,667/32,663/32,786 / -23,015/-19,341/-22,303 | 8,700 / 7,700 | 3/3 |
| grid b | b200 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 322,269/334,811/332,156 vs 79,500/79,500/79,500 | 76,192/79,328/78,664 / 55,373/59,220/58,603 / -37,197/-32,654/-36,841 | 17,500 / 15,500 | 3/3 |
| grid b | b400 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 587,794/590,680/592,951 vs 159,500/159,500/159,500 | 138,173/138,895/139,463 / 100,627/103,702/104,077 / -63,611/-52,404/-60,401 | 35,100 / 31,100 | 3/3 |
| grid b | b800 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 1,029,221/1,066,644/1,009,311 vs 319,500/319,500/319,500 | 239,730/249,086/234,753 / 176,114/187,452/175,709 / -100,938/-84,859/-89,466 | 70,300 / 62,300 | 3/3 |
| grid b | b1600 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 1,866,168/1,900,093/1,884,582 vs 639,500/639,500/639,500 | 431,367/439,848/435,971 / 317,770/330,330/325,786 / -166,058/-134,085/-153,125 | 140,700 / 124,700 | 3/3 |
| grid b | b3200 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 3,295,645/3,407,223/3,447,318 vs 1,279,500/1,279,500/1,279,500 | 753,536/781,431/791,455 / 554,795/588,450/592,229 / -253,900/-202,201/-247,910 | 281,500 / 249,500 | 3/3 |
| routes | r1_b100 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 232,164/238,428/217,720 vs 45,212/45,212/45,212 | 55,591/57,157/51,980 / 55,591/56,815/51,346 / 9,800/9,800/9,800 | 9,800 / 8,853 | 3/3 |
| routes | r2_b100 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 248,228/226,358/193,374 vs 45,212/45,212/45,212 | 59,607/54,140/45,893 / 59,607/52,974/45,893 / 9,800/9,800/9,800 | 9,800 / 8,853 | 3/3 |
| routes | r4_b100 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 257,536/250,961/245,384 vs 45,212/45,212/45,212 | 61,934/60,290/58,896 / 61,780/50,597/58,315 / 9,800/9,800/9,800 | 9,800 / 8,853 | 3/3 |
| routes | r1_b400 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 768,519/661,405/734,479 vs 181,712/181,712/181,712 | 182,255/155,476/173,745 / 182,255/151,938/173,745 / 39,500/39,500/39,500 | 39,500 / 35,553 | 3/3 |
| routes | r2_b400 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 742,305/822,843/752,767 vs 181,712/181,712/181,712 | 175,701/195,836/178,317 / 175,701/192,647/178,033 / 39,500/39,500/39,500 | 39,500 / 35,553 | 3/3 |
| routes | r4_b400 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 816,957/673,714/842,236 vs 181,712/181,712/181,712 | 194,364/158,553/200,684 / 194,364/132,645/199,170 / 39,500/39,500/39,500 | 39,500 / 35,553 | 3/3 |
| routes | r1_b1600 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 2,380,131/2,417,849/2,266,361 vs 727,712/727,712/727,712 | 555,458/564,887/527,015 / 555,458/558,915/524,392 / 158,300/158,300/158,300 | 158,300 / 142,353 | 3/3 |
| routes | r2_b1600 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 2,659,681/2,563,101/2,567,235 vs 727,712/727,712/727,712 | 625,345/601,200/602,234 / 625,345/595,621/601,930 / 158,300/158,300/158,300 | 158,300 / 142,353 | 3/3 |
| routes | r4_b1600 | P2swap | once->honest, once->honest, once->honest | 0/0/0 of 6 | 2,628,533/2,448,211/2,532,362 vs 727,712/727,712/727,712 | 617,558/572,478/593,516 / 617,558/475,638/588,402 / 158,300/158,299/158,301 | 158,300 / 142,353 | 3/3 |
| routes | r1_b100 | P1eq1 | once->honest, 2.0 corr/ep, once->honest | 0/0/0 of 6 | 167,548/163,030/160,668 vs 45,212/45,212/45,212 | 39,437/35,754/37,717 / 37,984/34,810/36,690 / -24,293/-24,012/-25,610 | 9,800 / 8,853 | 3/3 |
| routes | r2_b100 | P1eq1 | once->honest, 2.0 corr/ep, once->honest | 0/0/0 of 6 | 167,896/180,449/173,113 vs 45,212/45,212/45,212 | 39,524/40,021/40,828 / 39,524/39,463/40,828 / -19,560/-21,767/-21,870 | 9,800 / 8,853 | 3/3 |
| routes | r4_b100 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 189,663/174,101/197,707 vs 45,212/45,212/45,212 | 44,966/41,075/46,977 / 44,954/33,578/46,558 / -15,691/-20,035/-18,599 | 9,800 / 8,853 | 3/3 |
| routes | r1_b400 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 570,115/530,260/531,369 vs 181,712/181,712/181,712 | 132,654/122,690/122,967 / 128,973/120,562/120,598 / -70,295/-72,670/-76,704 | 39,500 / 35,553 | 3/3 |
| routes | r2_b400 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 587,632/573,523/571,364 vs 181,712/181,712/181,712 | 137,033/133,506/132,966 / 137,033/132,280/132,966 / -59,429/-66,624/-67,038 | 39,500 / 35,553 | 3/3 |
| routes | r4_b400 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 634,559/600,300/647,767 vs 181,712/181,712/181,712 | 148,765/140,200/152,067 / 148,765/113,884/151,076 / -45,829/-61,462/-53,585 | 39,500 / 35,553 | 3/3 |
| routes | r1_b1600 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 1,859,232/1,804,626/1,746,016 vs 727,712/727,712/727,712 | 425,233/411,582/396,929 / 415,224/405,719/390,758 / -195,278/-223,368/-218,689 | 158,300 / 142,353 | 3/3 |
| routes | r2_b1600 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 1,979,379/1,878,867/1,843,192 vs 727,712/727,712/727,712 | 455,270/430,142/421,223 / 455,270/428,455/421,223 / -163,112/-182,017/-172,604 | 158,300 / 142,353 | 3/3 |
| routes | r4_b1600 | P1eq1 | once->honest, once->honest, once->honest | 0/0/0 of 6 | 2,128,874/2,005,435/2,094,643 vs 727,712/727,712/727,712 | 492,644/461,784/484,086 / 492,644/374,323/482,765 / -113,756/-163,730/-128,354 | 158,300 / 142,353 | 3/3 |

Read against the pre-registered criteria above (my reading of the table, nothing beyond it):

- **No-regulariser avoids correction at no setting.** `P1eq1` is `HIDES` in 0 of 3 seeds everywhere, and no single draw hides (0 of 6 in every seed). So the theory's prediction holds at no setting in these sweeps.
- **The swap never hides either**, and is `once->honest` in every grid and routes seed. In Taxi both variants are `once->true x` (swap −57 to −67, no-regulariser −78 to −81; honest +125).
- The margin over hiding grows with b in both variants: the best round after one correction outbids the hide round by 3–6×, the ratio falling slowly with b (grid: no-regulariser 43,000 → 790,000, swap 49,000 → 957,000), against the doc's prediction that the raise would stay near its b = 100 size. Splitting the reference over R spokes does not shrink it either (routes, no-regulariser at b = 1600: 397,000–493,000, about 3×, against a hide round of 142,353).
