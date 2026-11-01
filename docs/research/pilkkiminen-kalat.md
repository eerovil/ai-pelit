# Fish of a Finnish lake under ice: research for Pilkkiminen

Research notes for `games/pilkki/` (written against v3, `games/pilkki/v3/index.html`): how
perch, roach, ruffe, bream, zander, burbot and pike behave under ice in daytime, and what that
suggests for the game's constants. Gathered 2026-11-01.

How to read it:

- Each claim has its source link and a confidence word: **high** (a peer-reviewed paper or an
  official body, with the number read in the paper's full text or abstract), **medium** (an
  abstract or database entry read but not its full text, or a field study from another kind of
  lake or season), **low** (a secondary report, a newspaper, a search-engine summary that could
  not be checked against the original, or a lone grey-literature report).
- Many publisher sites (Springer, Wiley, ScienceDirect, journals.biologists.com, Luke's Jukuri,
  hu-berlin.de, PMC) refused automated access. Two papers were read in full: Turesson & Brönmark
  2004 and Ranåker et al. 2014. Most of the rest comes from abstracts, read through the OpenAlex
  API, and from FishBase.
- "Not found" means that no reliable number turned up. It does not mean that none exists.
- Almost all behaviour studies are from summer, from aquaria at 16–20 °C, or from lakes south of
  Finland. Few measure fish under ice at 2–4 °C. Each section says when a number comes from
  other conditions.

---

## 1. Winter habitat: depth by day and night

| Species | Finding | Source | Conf. |
|---|---|---|---|
| Perch | Lake Constance in winter (no ice there): perch left the littoral in autumn and overwintered between the 42 and 69 m depth contours in January, below 6 °C for about six months. They rested **on the bottom by day** and swam **up to 25 m off the bottom at night**. Light was the proximate cause. From January they moved shallower by 0.25 m a day. | [Eckmann & Imbrock 1996, Ann. Zool. Fennici 33](http://nbn-resolving.de/urn:nbn:de:bsz:352-opus-39692) | high (abstract; very deep lake, not ice-covered) |
| Perch | In a shallow Danish lake, large perch (27–37 cm) tracked monthly through winter were active **in daytime**, with peaks at dawn and dusk or at midday. At night they were generally inactive (a visual forager). | [Jacobsen et al. 2002, Freshwater Biology 47](https://doi.org/10.1046/j.1365-2427.2002.01005.x) | high (abstract) |
| Perch | General: depth 1–30 m, usually about 3–4 m. A diurnal feeder that hunts mostly at sunrise and sunset. | [FishBase, Perca fluviatilis](https://www.fishbase.se/summary/Perca-fluviatilis.html) | medium |
| Roach | Overwinters "in backwaters or in deep parts of lakes" (Kottelat & Freyhof 2007, via FishBase). | [FishBase, Rutilus rutilus](https://www.fishbase.se/summary/Rutilus-rutilus.html) | medium |
| Roach, bream | Finnish fisheries background note: catches are best in autumn, winter or spring, "when bream and roach can form large schools in a small area". | [WWF/Metsähallitus Freshabit, Särki ja lahna (2019), p. 2](https://www.metsa.fi/wp-content/uploads/2023/04/sarki_ja_lahna.pdf) | medium |
| Roach, perch (summer) | In a Finnish lake's Nordic test nets, small perch dominated the 3–6 m depth zone and roach the water under 3 m. These are summer nets, not winter. | [Kytäjärvi Nordic test-netting 2019, Hyvinkää](https://www.hyvinkaa.fi/globalassets/asuminen-ja-ymparisto/julkaisuja-ja-raportteja/liitteet/kytajarvi_nordic_verkkokoekalastus_2019.pdf) | medium |
| Ruffe | In deep lakes it lives in deeper layers than perch. It can feed at night, in the dark, with its lateral line. Depth range 2–85 m. | [FishBase, Gymnocephalus cernua](https://www.fishbase.se/summary/Gymnocephalus-cernua.html) | medium |
| Ruffe | It went on eating zoobenthos all winter in Lake Constance and ended winter heavier, while perch, short of light for zooplankton feeding, lost mass. | [Eckmann 2004, J. Fish Biol. 65](https://doi.org/10.1111/j.0022-1112.2004.00553.x) | high (abstract) |
| Bream | Wintering in an 8 m-deep reservoir, it stayed active and presumably fed in a 3–5 m layer of warmer, oxygenated water below an inverse thermocline. It avoided the cold shallows and the deepest area by the dam. | [Jurajda et al. 2018, Fish. Manag. Ecol. (record)](https://asep.lib.cas.cz/arl-cav/en/detail-cav_un_epca-0489656-Winter-activity-of-common-bream-Abramis-brama-L-in-a-European-reservoir/) | medium |
| Bream | "Bream generally form large, relatively static shoals in winter", though lake populations stay active all year. | [Bournemouth Univ., Hydrobiologia 2025 (PDF)](https://eprints.bournemouth.ac.uk/40959/7/s10750-025-05883-5.pdf) | medium |
| Zander | Adults live in large turbid rivers and eutrophic lakes. Depth 2–30 m, usually 2–3 m (FishBase; not winter-specific). | [FishBase, Sander lucioperca](https://www.fishbase.se/summary/Sander-lucioperca.html) | medium |
| Zander | A nocturnal predator, less dependent on sight than perch and pike, that can follow prey by its lateral line in darkness. In trials its activity rose as light fell. | [Turesson & Brönmark 2004, J. Fish Biol. 65: 363–375 (full text)](https://lup.lub.lu.se/search/files/2802910/624603.pdf) | high |
| Zander | No study of zander under ice was found: its depth by day and night in winter is **not found**. | – | – |
| Burbot | Two Alaskan lakes (archival tags): under ice they stayed in the profundal zone, then in February–March (the presumed spawning period) moved from it to **≤5 m depth**, at a mean body temperature of 2.1 °C. They made diel vertical movements, with activity peaking at **dawn and dusk**. | [Scannell 2016, MSc thesis, Univ. of Alaska Fairbanks](https://scholarworks.alaska.edu/uaf_grad_fisheries/167) | medium |
| Burbot | Adults migrate into shallow water at night (Kinbasket Reservoir, Canada). | [Harrison 2015, PhD thesis, Univ. of Waterloo](https://uwspace.uwaterloo.ca/) (abstract via OpenAlex) | medium |
| Burbot | Crepuscular and nocturnal. Depth 1–700 m. | [FishBase, Lota lota](https://www.fishbase.se/summary/Lota-lota.html) | medium |
| Pike | In a 25 ha German lake under ice, pike moved significantly less than in summer, had **no pronounced daytime activity peaks**, and chose places significantly **closer to shore**. | [Kobler et al. 2008, Hydrobiologia 601](https://doi.org/10.1007/s10750-007-9263-2) (abstract via search summary) | medium |
| Pike | Three Minnesota lakes: in winter pike used all available depths more fully than in summer. Low oxygen (<3 mg/L) limited depth choice in winter. | [Pierce et al. 2013, Trans. Am. Fish. Soc. 142](https://doi.org/10.1080/00028487.2013.822422) | high (abstract) |
| Pike | In a Wisconsin lake under ice and in open water, pike preferred macrophyte areas 5–10 ft (1.5–3 m) deep. | [Margenau 1986, Wisconsin DNR (PDF)](https://asset.library.wisc.edu/1711.dl/6WHLUD7XAUDWM8Q/E/file-31864.pdf?dl) | medium |
| Pike | General: depth 0–30 m, usually 1–5 m; clear, vegetated lakes. | [FishBase, Esox lucius](https://www.fishbase.se/summary/Esox-lucius.html) | medium |

Light and oxygen: perch and pike hunt by sight and are active by day (Jacobsen 2002; Baktoft
2012 below). Ruffe, zander and burbot are dim-light or night feeders (Schleuter 2006 below;
Turesson & Brönmark 2004; FishBase). Under ice, pike avoid water below about 3 mg/L of oxygen
(Pierce 2013). No measured figures were found for how much light under snow-covered ice changes
any of these species' activity.

---

## 2. Schooling

| Species | Finding | Source | Conf. |
|---|---|---|---|
| Perch | In Finnish ice-fishing data, perch formed shoals by fish size, and perch size varied more between places in one lake than between lakes. This came from a search summary of the Luke-hosted paper. The full text was not reachable, so this is not verified. | [Turunen et al. 2022, Fish. Manag. Ecol. 29](https://doi.org/10.1111/fme.12603) | low |
| Perch, ruffe | Both are "shoaling percids". In respirometry, a fish alone used up to **twice the oxygen** of a fish in a group of eight. Perch were more active by day, ruffe by night. Twilight metabolism was highest in both. | [Schleuter 2006 / Schleuter & Eckmann (abstract via OpenAlex)](https://kops.uni-konstanz.de/) | medium |
| Perch vs zander and pike | Attacking a school, perch suffer a confusion effect: 3% capture success against 2+ prey vs 20% against single prey, so they split schools first. Zander and pike showed no confusion effect. Roach prey "remained schooled on all occasions, except during direct attacks when schools split up". | [Turesson & Brönmark 2004 (full text)](https://lup.lub.lu.se/search/files/2802910/624603.pdf) | high (aquarium, summer temperatures) |
| Roach | In tracked roach in an experimental pond, nearest-neighbour distances were **smaller by day than at night**. The figure's values were not retrievable. | [Brönmark et al. 2023, Movement Ecology 11 (fig. 5)](https://doi.org/10.1186/s40462-023-00419-9) | medium |
| Bream, roach | Large winter schools in a small area (WWF/Metsähallitus above); "travel in large shoals" (FishBase, Abramis brama). | [FishBase, Abramis brama](https://www.fishbase.se/summary/Abramis-brama.html) | medium |
| Pike | "Typically solitary and highly territorial." | [FishBase, Esox lucius](https://www.fishbase.se/summary/Esox-lucius.html) | medium |
| Burbot | Solitary outside spawning. At spawning it forms "a ball about 60 cm in diameter". | [FishBase, Lota lota](https://www.fishbase.se/summary/Lota-lota.html) | medium |
| General | In tracked fish groups, near-neighbour encounters peaked **between one and two body lengths** from a focal fish (species not given in the snippet). Shoal membership is often defined as being within 4–5 body lengths. | [Royal Society Open Science 2017 (DOAJ)](https://doaj.org/article/6a2c3c9208c8426a8b6fa76f6f6ac0eb); [Miller & Gerlai 2008](https://millerlab.ca/labsite/docs/pubs/2008_Miller_Gerlai.pdf) | low |

**Not found:** winter school sizes in fish counts for any of the seven species; nearest-neighbour
distance in body lengths or metres measured for perch, roach or bream; how often their schools
split or merge. Hydroacoustic papers report fish densities, not school counts. Finnish
hydroacoustic surveys (e.g. Malinen et al.) may hold the counts but were not found here.

---

## 3. Movement: speeds, ranges, daily pattern

| Species | Finding | Source | Conf. |
|---|---|---|---|
| Perch | Winter: "perch moved at the **same average speed** in the wintertime, but did so for **shorter periods** than in summer because of shorter day lengths". Total distance per day tracked temperature. | [Jacobsen et al. 2002](https://doi.org/10.1046/j.1365-2427.2002.01005.x) | high (abstract; the speed itself is in the full text, not read) |
| Perch | Tagged perch averaged **6.0 cm/s at night** and **10.4 cm/s by day** (Lake Banyoles, Spain). The season was not stated in the snippet, and the paper could not be opened. | [Zamora & Moreno-Amich 2002, Hydrobiologia 483](https://doi.org/10.1023/A:1021396016424) | low |
| Perch | In winter perch shifted shallower at 0.25 m/day (Lake Constance). | [Eckmann & Imbrock 1996](http://nbn-resolving.de/urn:nbn:de:bsz:352-opus-39692) | high |
| Roach | Juvenile roach swimming speed and critical speed peaked near **25 °C** in tests at 7–31 °C. Cold values are not in the abstract. | [J. Ichthyology 2020 (Springer)](https://link.springer.com/article/10.1134/S0032945220020186) | medium |
| Ruffe | More active at night than by day. | Schleuter 2006 (above) | medium |
| Bream | Active all winter; in a Danish lake, bream activity drove turbidity at water temperatures below 15 °C. | [Hansen et al. 2019, J. Limnol. 78](https://doi.org/10.4081/jlimnol.2019.1883) | high (abstract) |
| Zander | Päijänne system telemetry: some zander stayed within a radius of a couple of kilometres, others moved over 20 km. The same fish repeated its pattern in successive years. | [Keskinen 2008, PhD thesis, Univ. of Jyväskylä](https://jyx.jyu.fi/) (abstract via OpenAlex) | medium |
| Burbot | Home range grew after ice formation in December and through March, peaking in mid-March (spawning). | [Space use within burbot home range, N. Am. J. Fish. Manage.](https://openpolar.no/Record/crwiley:10.1002%2Fnafm.10980) | medium |
| Burbot | 44 acoustically tagged burbot ranged from "resident" fish (small home range, little movement) to "mobile" ones. | [Harrison et al. 2014, Behav. Ecol. 26](https://doi.org/10.1093/beheco/aru216) | high (abstract) |
| Pike | Winter **home ranges 0.02–0.95 ha** (spring 0.02–0.59 ha); excursion distance correlated with winter home range. | [Knight et al. 2008, J. Fish Biol. (record)](https://staffprofiles.bournemouth.ac.uk/display/journal-article/9581) | medium |
| Pike | 12 female pike (45–73 cm) in a 25 ha lake: activity centres were **larger in winter than in summer**, overlapping the summer sites. Pike moved away 6 days earlier had all returned home. | [Kobler, Klefoth & Arlinghaus 2008, J. Fish Biol. 73](https://doi.org/10.1111/j.1095-8649.2008.01952.x) | high (abstract) |
| Pike | Positional telemetry, late summer into winter, two years: activity similar between seasons; more active **by day than by night** in all periods. | [Baktoft et al. 2012, Ecol. Freshw. Fish 21](https://doi.org/10.1111/j.1600-0633.2012.00558.x) | high (abstract) |
| Pike | Activity areas generally under 11 acres (about 4.5 ha). | [Margenau 1986](https://asset.library.wisc.edu/1711.dl/6WHLUD7XAUDWM8Q/E/file-31864.pdf?dl) | medium |
| Pike (burst) | Mean maximum fast-start acceleration **120 m/s²** and peak velocity **about 4 m/s** (Harper & Blake 1990, as cited by later work). Pike can fast-start up to about 170 times before exhaustion. | [Frith 2011, thesis, UBC](http://hdl.handle.net/2429/30834) citing Harper & Blake 1990 | medium |

**Not found:** cruising or burst speeds measured at 2–4 °C for any of the seven species.

---

## 4. Pike: how it hunts

| Topic | Finding | Source | Conf. |
|---|---|---|---|
| Ambush vs active | In aquaria (18–22 cm pike, roach prey at 0.30 prey:predator length, 19.7 °C), pike were "immobile most of the time", waiting on the bottom, often by the edge, and did not use the hide. **13.3% of attacks** were sit-and-wait; the rest were pursuits. | [Turesson & Brönmark 2004 (full text)](https://lup.lub.lu.se/search/files/2802910/624603.pdf) | high |
| Capture success | Overall **15%** of attacks (25 of 166); **36%** for sit-and-wait attacks (8/22), **12%** for pursuits (17/144). Success did not depend on prey school size (1–16 prey). By attack sequence, 25% succeeded. Zander: 8.5% per attack; perch 17.6%. | same | high (summer temperature) |
| Strike distance | **0.087–0.439 m** for pike averaging about 0.38 m fork length, shorter when the prey looked bigger (apparent size 2.6–9.9°, r² = 0.75). Actual prey size was unrelated to strike performance. | [Harper & Blake 1991, J. Exp. Biol. 155: 175](https://doi.org/10.1242/jeb.155.1.175) (abstract via search summary) | medium |
| Strike speed | See section 3: about 4 m/s peak, 120 m/s² (Harper & Blake 1990, secondary). | – | medium |
| Prey size | Gape grows linearly with pike length. The absolute gape limit is larger than once thought, and prey **body depth** sets the maximum. Pike preferred shallow-bodied roach to deep-bodied bream, and **small** prey within each species; handling time is the cost. | [Nilsson & Brönmark 2000, Oikos 88: 539](https://doi.org/10.1034/j.1600-0706.2000.880310.x) | high (abstract) |
| Prey size (cannibalism) | Pike eaten by pike were 13.6–43.6% of the cannibal's weight and 42–74% of its length (a Bulgarian study). | [Agrojournal (Bulgaria)](https://www.agrojournal.org/19/01-10s.pdf) | low |
| Selectivity | Pike tended to select shallow-bodied young perch that did not inspect predators. | [Heynen et al. 2016, Curr. Zool. 63](https://doi.org/10.1093/cz/zow056) | high (abstract) |
| Feeding frequency, digestion at 2–4 °C | **Not found.** A pike gastric-evacuation study exists for young-of-year pike ([Annales de Limnologie 1998](https://www.limnology-journal.org/10.1051/limn/1998001)) but its values were not reachable. Feeding intensity was lowest in winter in a Turkish lake ([Ahi Evran Univ.](https://openaccess.ahievran.edu.tr/items/54767e84-f413-4dc7-916f-1b3da948be7c)). | – | – |
| Prey response | Zander and roach/perch (16 °C, brown water): at longer visual range (2 m), **roach began their escape farther away than zander attack distances**, so zander caught none (0%). Perch stayed still, letting the zander come to the closest range, and were caught 100% of the time. At 0.5 m visual range the two prey were alike. The distances are in figures only, not readable as numbers. | [Ranåker et al. 2014, PLoS ONE 9: e102002 (full text)](https://doi.org/10.1371/journal.pone.0102002) | high (zander, not pike) |
| Prey response latency | **Not found** for these species. | – | – |
| Learning | Pike learned to avoid baits after a few angling trials ("strong sequential bait avoidance"), while hunting live prey as before. | [Lucas et al. 2023, Can. J. Fish. Aquat. Sci. 80](https://doi.org/10.1139/cjfas-2023-0004) | high (abstract) |
| After release | Caught-and-released pike swam less and kept to structured habitat afterwards. | [Klefoth et al. 2011, Knowl. Manag. Aquat. Ecosyst. 403](https://doi.org/10.1051/kmae/2011072) | high (abstract) |

---

## 5. Ice fishing: what each species takes, and how

What science says:

- Turunen et al. 2022 ice-fished perch in 11 small boreal (Finnish) lakes with natural baits: the
  catch's **length distribution matched that of Nordic gillnets**, so ice fishing with natural
  bait is "relatively unselective for fish size"; catch per effort did not track abundance.
  [Turunen et al. 2022](https://doi.org/10.1111/fme.12603) — high (abstract).
- A mormyshka is "an effective way to catch roach and European perch when ice fishing". Most
  fish were hooked shallowly in the upper jaw. Barbed and barbless hooks worked equally.
  [Czarkowski & Kapusta 2019, Croat. J. Fish. 77](https://doi.org/10.2478/cjf-2019-0017) — high
  (abstract; size data in the full text, not read).
- Zander catches on Saimaa peaked in **winter** (recreational survey 2014–15), while perch, pike
  and bream peaked in early summer. [Luke, Vapaa-ajan kalastus Saimaalla 2014–2015](https://jukuri.luke.fi/handle/10024/542110) — medium (search summary of the report).
- In the Kallavesi 2023 Omakala data, jigging (pilkki) gave about 20% of catches by number;
  perch, zander and pike were the commonest species. [Olin, Omakala (JYU)](https://www.jyu.fi/fi/file/omakala-kuka-sita-kayttaa-ja-mita-tietoa-silla-kerataan-mikko-olin) — low.
- Burbot: after spawning (into March in the north) it is fished with baited hooks, using minnow,
  perch or roach as bait. [Yle](https://yle.fi/a/3-12298896) — low.

Practitioner sources (not science):

- Retailers and guides: mid-winter perch are "a bit passive" and come most easily to
  **slow-moving lures**; balance jigs are sold "especially for perch ice fishing on large open
  waters"; perch lures 4–10 cm (large lakes 5–7 cm); line 0.20 mm.
  [eumer.fi](https://eumer.fi/en/category/ice-fishing-lures/180),
  [eumer.fi article](https://eumer.fi/en/article/ice-fishing-for-perch-in-raippaluoto/10778) — low.
- The mormyshka is described as best for smaller fish, and fly larvae (maggots) as a popular bait.
  [Prisma guide](https://www.prisma.fi/artikkelit/pilkkiminen) — low.
- Pike teeth and leaders: angler guidance says heavy fluorocarbon resists pike teeth "in most
  situations", with titanium or wire for full bite-off protection.
  [Northern Ontario Travel](https://northernontario.travel/algoma-country/understanding-pike-and-musky-leaders?page=6) — low.

**Not found:** any measured effect of jigging rhythm, speed or pause length on bites, for any
species; bite-off rates of pike on unleadered line; measured bite behaviour (how long a perch
holds a jig). The game's per-species `tempo` and the "too fast scares fish" rule have no
scientific basis to check against, which is no reason to change them.

---

## 6. Sizes, weights and abundance

Sizes (FishBase gives world figures; Finnish records from the national register as reported in
the press):

| Species | Common length (FishBase) | Max weight (FishBase) | Finnish record / large | Sources |
|---|---|---|---|---|
| Perch | 25 cm TL | 4.8 kg | **2.88 kg** (net, Iijoki), record by weight | [FishBase](https://www.fishbase.se/summary/Perca-fluviatilis.html) (medium); [Kaleva](https://www.kaleva.fi/oululainen-matti-hannus-kalasti-iijoesta-suomen-su/11539784) (medium) |
| Roach | 25 cm TL | 1.8 kg | 1.544 kg, from a search summary whose source page was not found (unverified) | [FishBase](https://www.fishbase.se/summary/Rutilus-rutilus.html) (medium); record: low |
| Ruffe | 12 cm TL | 400 g | not found | [FishBase](https://www.fishbase.se/summary/Gymnocephalus-cernua.html) (medium) |
| Bream | 25 cm TL | 6.0 kg | the largest "4–5 kg" (no official record found) | [FishBase](https://www.fishbase.se/summary/Abramis-brama.html) (medium); [Yle 2014](https://yle.fi/a/20-41978) (low) |
| Zander | 50 cm TL | 20 kg | "up to 10 kg" in Finland (WWF); a 13.4 kg fish on a jig reported as the largest jig-caught | [FishBase](https://www.fishbase.se/summary/Sander-lucioperca.html) (medium); [WWF fact sheet 2020](https://www.metsa.fi/wp-content/uploads/2020/02/A7_wwf_fakta2019_kuha-1.pdf) (medium); [MTV](https://www.mtvuutiset.fi/artikkeli/nyt-tarppasi-jattikuha-toni-naki-jarvessa-jotain-joka-vei-younetkin-lahti-aamuneljalta-kalaan-ja-se-kannatti/7402498) (low) |
| Burbot | 40 cm TL | 34 kg | a 7.125 kg, 88 cm fish (Haapajärvi, Iisalmi, 2018) reported near the record | [FishBase](https://www.fishbase.se/summary/Lota-lota.html) (medium); [Kaleva](https://www.kaleva.fi/aihe/ennatyskalat/15313) (low) |
| Pike | 40 cm (male), 55 cm (female) TL | 28.4 kg | **18.8 kg**, 135 cm (net, Oijärvi, Ii, 2009) | [FishBase](https://www.fishbase.se/summary/Esox-lucius.html) (medium); [Kaleva](https://www.kaleva.fi/ruotsalaiskalastaja-sai-yli-20-kiloisen-hauen-suom/1750737) (medium) |

Finnish rules and sizes: inland zander must be at least **42 cm** to keep, and the WWF suggests
eating mid-sized fish of 45–65 cm ([WWF fact sheet](https://www.metsa.fi/wp-content/uploads/2020/02/A7_wwf_fakta2019_kuha-1.pdf), medium).
One length–weight point: a 60 cm zander weighed 1836 g
([Kytäjärvi 2019](https://www.hyvinkaa.fi/globalassets/asuminen-ja-ymparisto/julkaisuja-ja-raportteja/liitteet/kytajarvi_nordic_verkkokoekalastus_2019.pdf), medium).
Burbot has been on Finland's near-threatened list since 2019, its stocks having weakened
([JYU thesis](https://jyx.jyu.fi/handle/123456789/88932), medium).

Abundance:

- **Kytäjärvi (southern Finland), Nordic test nets 2019, 5964 fish:** by number perch 60.9%,
  roach 24.8%, zander 4.8%, ruffe 4.3%, bleak 2.9%, bream 0.8%; by weight roach 38.7%, perch
  27.6%, zander 21.9%, white bream 5.0%, bream 4.1%, ruffe 0.8%. Mean perch weight 10.6 g, with
  only about 5% of perch over 15 cm. The report notes bream are under-caught by these nets.
  [Kytäjärvi 2019](https://www.hyvinkaa.fi/globalassets/asuminen-ja-ymparisto/julkaisuja-ja-raportteja/liitteet/kytajarvi_nordic_verkkokoekalastus_2019.pdf) — medium.
  Nordic nets also catch few pike and burbot, so these two are missing from the list rather
  than absent from the lake.
- In Luke's study of humic lakes, perch and roach were the main species in most of them.
  [Luke luobio 35/2021](https://jukuri.luke.fi/bitstream/10024/547512/1/luke-luobio_35_2021.pdf) — low (search summary).
- Perch biomass in 28 small boreal lakes: **52.4 ± 51.2 kg/ha**.
  [Vainikka et al. 2023, Fish. Res. 264](https://doi.org/10.1016/j.fishres.2023.106922) — high (abstract).
- National recreational catch 2022 (Luke statistics, as reported): just over **36 million kg**;
  **perch and pike over half** of it, zander third (4,320 t). [Kaleva on Luke 2022](https://www.kaleva.fi/vapaa-ajankalastuksen-suosio-kasvaa-yli-puolet-saa/5997835) — medium.

**Not found:** a weight distribution of fish caught by ice fishing in Finland (only that it
matches the lake's own length distribution, Turunen 2022), and a national species breakdown of
the ice-fishing catch.

---

## 7. Burbot in winter

- **Spawning time:** November to March, below 6 °C, at night, in a ball about 60 cm across
  ([FishBase](https://www.fishbase.se/summary/Lota-lota.html), medium). In Lake Southern
  Konnevesi (Finland) one form spawns in **late February in the littoral** and another in **late
  March in the profundal, about 30 m deep** ([Marjomäki et al. 2022, Hydrobiologia 849](https://doi.org/10.1007/s10750-022-04830-y), high, abstract).
  Generally burbot spawn in winter on shallows and shores, some populations in spring in deep
  basins ([JYU thesis](https://jyx.jyu.fi/handle/123456789/88932), medium). In the north,
  spawning runs into March ([Yle](https://yle.fi/a/3-12298896), low).
- **Temperature:** at night, burbot selected 0–2 °C water during spawning (8–10 °C before it,
  12–14 °C in summer) ([Harrison 2015](https://uwspace.uwaterloo.ca/), medium).
- **Activity under ice:** profundal under ice, then up to ≤5 m in February–March, with dawn and
  dusk activity peaks ([Scannell 2016](https://scholarworks.alaska.edu/uaf_grad_fisheries/167), medium).
  Wild burbot moved less but used more energy at peak spawning ([Slavík & Horký 2021, Aquac. Environ. Interact. 13](https://doi.org/10.3354/aei00389), high, abstract).
  Home range peaked in mid-March ([NAJFM](https://openpolar.no/Record/crwiley:10.1002%2Fnafm.10980), medium).
- **Daytime:** all sources agree it is a dusk-and-night fish. A daytime contest catches it
  resting near the bottom, mostly deep.

---

## Suggested game values

The game is a daytime, 5-minute contest. The lake's scale and the readability of the screen
matter as much as realism, so these are suggestions with their sources, not demands.

| Constant (v3) | Current | Suggested | Why, and source |
|---|---|---|---|
| `HABITS.ahven.pace` | 0.45 m/s | 0.10–0.20 m/s | Tagged perch averaged 0.06 m/s at night and 0.10 m/s by day (Zamora 2002, low), and winter perch keep their summer speed (Jacobsen 2002, high). 0.45 m/s is about 4× the measured mean. |
| `HABITS.sarki.pace`, `lahna.pace`, `kuha.pace` | 0.45 / 0.35 / 0.4 m/s | lower in line with perch (e.g. 0.15–0.25) | **Not found** for 2–4 °C. Cyprinid swimming peaks near 25 °C (J. Ichthyology 2020, medium), so cold-water cruising should be slower, not faster, than perch's. A judgement call. |
| `HABITS.*.gap` (ahven 2.6, sarki 3, lahna 3, kiiski 1.6, kuha 4.5 m) | 1.6–4.5 m | 1–2 body lengths, i.e. about 0.2–0.6 m for a 20–30 cm fish, if the screen allows | Near-neighbour encounters peak at 1–2 body lengths (RSOS 2017, low); shoal membership is within 4–5 body lengths (Miller & Gerlai 2008, low). The current 2.6 m is about 13 lengths of a 20 cm perch. Keep a larger gap if tight schools read badly on the phone. |
| `HABITS.*.school` sizes | perch 15–50, roach 25–80, bream 8–25, ruffe 5–15, zander 3–8 | keep; bream perhaps larger | Counts are **not found**. Bream and roach gather in "large schools in a small area" in winter (WWF/Metsähallitus, medium; Bournemouth 2025, medium). |
| `SPECIES.ahven.d` | [0.8, 8] m | bias perch towards the bottom by day (e.g. within ~1 m of it) | Winter perch rest on the bottom by day and rise at night (Eckmann & Imbrock 1996, high; deep lake). |
| `SPECIES.sarki.d` | [0.5, 4] m | deeper in winter, e.g. [2, 10] m | Roach overwinter "in deep parts of lakes" (FishBase/Kottelat & Freyhof, medium). |
| `SPECIES.kiiski` | bottom | keep bottom; deeper than perch | Ruffe lives deeper than perch (FishBase, medium) and keeps feeding on zoobenthos all winter (Eckmann 2004, high). |
| `SPECIES.kuha` `d`/`min` | [5, 12] m, min 5 | keep | No winter data. A daytime zander is a low-light hunter that is less active (Turesson & Brönmark 2004, high). Winter is its best catch season on Saimaa (Luke, medium), so its `p` need not be lowered. |
| `SPECIES.kuha.w` | [400, 4200] g | consider a lower bound near the legal 42 cm | The inland minimum size is 42 cm (WWF, medium); a 60 cm zander weighed 1836 g (Kytäjärvi 2019). No length–weight relation for 42 cm was retrieved here. |
| `SPECIES.made` (`p`, bite) and `HABITS.made` | p 1, pace 0.12, stay 60–180 | keep sparse and slow in daytime; deep by day | Dusk-and-night fish (FishBase; Scannell 2016, medium). The Jan–Feb spawning move to ≤5 m and the 0–2 °C water happen at night (Harrison 2015, medium). In daytime it is right as a rare, slow catch on fish bait. |
| `HABITS.hauki.home` | 25 m | 30–60 m (0.1–0.4 ha), varying by fish | Winter pike home ranges 0.02–0.95 ha (Knight 2008, medium), larger than in summer (Kobler 2008, high). 25 m across is about 0.05 ha, inside the range but at its small end. |
| `SPECIES.hauki.d` | [0.5, 4] m | keep, near shore | Winter pike stay closer to shore (Kobler 2008 Hydrobiologia, medium), usually 1–5 m (FishBase). |
| `hunt()` dart start distance | 2.5 m | about 0.3–1 m (½–1½ pike lengths) | Strike distances were 0.09–0.44 m for 0.38 m pike (Harper & Blake 1991, medium). A pike creeps much closer than 2.5 m before it strikes. |
| `hunt()` dart speed and length | 4.5 m/s for up to 0.9 s | keep ~4 m/s, but over a fraction of a second (the strike covers well under a metre) | Peak about 4 m/s, 120 m/s² (Harper & Blake 1990 via Frith 2011, medium). 0.9 s at 4.5 m/s carries 4 m, about ten times a measured strike. For visibility the game may draw it slower than life. |
| `hunt()` creep speed | 0.5 m/s | slower, e.g. 0.1–0.3 m/s | Pike are "immobile or stalking" most of the time (Turesson & Brönmark 2004, high). No stalking speed was found; the direction is the only evidence. |
| `hunt()` success per dart | 0.35 | keep 0.35 for an unnoticed strike; about 0.12 for one the prey saw coming | Sit-and-wait 36%, pursuit 12%, all attacks 15% (Turesson & Brönmark 2004, high; 20 °C aquarium). |
| `preyOk` weight limit | prey < 0.35 × pike weight | prefer prey of about 0.2–0.35 of pike **length**, small and slim (roach over bream); rare above that | Experiments used 0.30 prey:predator length (Turesson & Brönmark 2004); pike prefer small, shallow-bodied prey (Nilsson & Brönmark 2000, high). 0.35 by weight is near the cannibalism extreme (up to 43.6% of weight, low). By the cube law (a derived figure, not a source), 0.3 of length is about 0.03 of weight. |
| `hunt()` `full` after eating | 60–150 s | longer than the contest (no second meal in 5 min) | Digestion at 2–4 °C is **not found**. Winter feeding intensity is lowest (Turkish lake study, low). A two-minute rest is surely too short for a cold fish, but no number backs a value. |
| fear distances in `steer()` (pike 3 m, darting 6 m, creeping 1.5 m) and the 0.3 s unnoticed start of a dart | as listed | keep the idea; no numbers to put in | In clear water roach start fleeing beyond a predator's attack distance, while perch freeze and let it come close (Ranåker 2014, high, zander). The distances and the reaction latency are **not found**. This suggests roach should flee earlier than perch. |
| bite-off in `fightStep()` (30%, giant 45%) | as listed | keep; a game rule | No measured bite-off rate was found. Anglers use wire, titanium or heavy fluorocarbon leaders for pike (angler guides, low). |
| `SPECIES.*.p` (perch 6, roach 4, ruffe 3, bream 1.5, zander 1.2, burbot 1, pike 0.5) | as listed | perch ≈ 6, roach ≈ 2.5–4, ruffe ≈ 0.4–3, bream ≈ 0.2–1.5, zander ≈ 0.5–1 | Kytäjärvi nets by number: perch 61%, roach 25%, zander 5%, ruffe 4%, bream 1% (medium; one lake, summer nets, bream under-caught). The current order matches; ruffe and bream may be a little common. Perch and pike are half the national recreational catch (Luke 2022, medium). |
| `SPECIES.*.w` | perch 40–480, roach 40–380, ruffe 15–80, bream 300–2600, zander 400–4200, burbot 300–2200, pike 800–6500 g; giant 12–16 kg | keep | They agree with FishBase's common sizes and Finnish records (pike record 18.8 kg, perch 2.88 kg). The skew towards small fish (`r^2.4`) matches netted size structures (Kytäjärvi: mean perch 10.6 g, about 5% over 15 cm). |
| `SPECIES.*.tempo`, `WIN`, the "too fast" scare | as listed | keep | No research on jig rhythm was found. Mid-winter perch take slow lures best (retailer advice, low). |
| `BAITS.*.likes` | as listed | keep | They agree with what was found: mormyshka for roach and perch (Czarkowski 2019, high), fish bait for burbot (low), balance jigs for perch (low). No study rates baits per species. |

Where the data are thinnest: school sizes and spacing in winter, swimming speeds at 2–4 °C,
pike digestion in cold water, prey reaction distances to pike, and anything about jigging rhythm.
A next round could read the full texts behind the paywalls named above (Jacobsen 2002 for winter
perch speed, Kobler 2008 for winter activity-centre hectares, Harper & Blake 1991 for strike
numbers), or look for Finnish winter hydroacoustics (Malinen et al.) and Diana 1979 for pike
winter rations.
