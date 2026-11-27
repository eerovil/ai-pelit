# Seittisankari: kiipeily ja seittiheilunta pilvenpiirtäjissä

3D-peli (#529). v1 toi vapaan kaupungin ja kavereiden kanssa pelaamisen (Eeron valinta), v2 tehtävät ("mene tänne", nuoli näyttää suunnan), v3 vetoseitin (#560: tähtää, ammu seinään ja vedä itsesi sinne, myös ilmasta), v4 rosvojen kiinnioton (#561: katon rosvot, karkuriauto ja karkurihelikopteri ammutaan seitillä): pelaaja juoksee kadulla ja katoilla, kiipeää minkä tahansa talon seinää pitkin ja heilahtaa seitillä talosta toiseen noin 1,7 km leveässä kaupungissa. Kavereiden kanssa kisataan satunnaisen talon katolle samasta lähtöpaikasta, tai liikutaan vapaasti yhdessä.

```mermaid
flowchart TD
    A[Valikko: Kaupunkiin tai Pelaa kavereiden kanssa] --> B{Paikka tallessa?}
    B -- Kyllä --> C[Jatka samasta kohdasta]
    B -- Ei --> D[Alku kadulla keskustassa]
    C --> Y
    D --> Y[Tehtävä vuorollaan: katto, katon rosvot, karkuriauto, tornin huippu, karkurihelikopteri]
    Y --> E[Ohjaus: tikku, Hyppy, pidä Seitti, Veto, kameran veto]
    E --> P1[Pidä Veto: tähtäin, sormen liu'utus kääntää kameraa]
    P1 --> P2{Irrota: osuuko säde 60 m sisällä?}
    P2 -- Seinään --> P3[Veto 30 m/s suoraan osumakohtaan]
    P2 -- Kattoon --> P3
    P2 -- Ei osu tai katuun --> P4[Seitti lentää ohi, ei muuta]
    P2 -- Rosvo, auto tai helikopteri tähtäimessä --> Q1[Kiinni: seitti nappaa sen, sankari jää paikalleen]
    Q1 --> Q2{Yksin: kaikki tehtävän rosvot kiinni?}
    Q2 -- Kyllä --> ZA
    P3 --> P5{Hyppy kesken vedon?}
    P5 -- Kyllä --> K
    P5 -- Ei, perillä seinässä --> H
    P5 -- Ei, perillä katolla --> G
    E --> F{Missä sankari on?}
    F -- Kadulla tai katolla --> G[Juoksu ja hyppy]
    F -- Seinässä kiinni --> H[Kiipeily seinää pitkin, reunalta katolle]
    F -- Ilmassa --> I{Seitti pohjassa, 1 s irrotuksesta ja taivas ulottuvilla?}
    I -- Kyllä --> J[Heiluri: köysi taivaalle kameran suuntaan]
    I -- Ei --> K[Lento: painovoima, vähän ohjausta]
    J --> L[Irrota tai Hyppy: hyppy ja voltti taaksepäin]
    L --> K
    K --> M{Osuu seinään?}
    M -- Kyllä --> H
    M -- Ei --> N{Osuu katuun tai kattoon?}
    N -- Kyllä --> G
    E --> T[Tallenna paikka 2 s välein ja valikkoon mennessä]
    A --> R[Huone: tekijä valitsee Kilpa katolle tai Vapaa]
    R --> S[Kaikki samasta lähtöpaikasta, 220 m merkitystä katosta]
    S --> E
    G --> Z{Yksin: seisoo merkityllä katolla?}
    Z -- Kyllä --> ZA[Perillä tai kiinni: aika, laskuri +1, uusi tehtävä]
    ZA --> Y
    G --> U{Kilpa: seisoo merkityllä katolla?}
    U -- Kyllä --> V[Tekijä hyväksyy: voittaja, sama tulos kaikille]
    U -- Ei --> W{3 min kulunut?}
    W -- Kyllä --> X[Tulos: aika tai korkeus]
    class A,B,C,D blue
    class Y,Z,ZA,Q1,Q2 rose
    class E,G,H violet
    class I,J,K,L,M,N teal
    class P1,P2,P3,P4,P5 teal
    class R,S,U,V,W,X green
    class T amber
```

## Colours

- **blue**: valikko ja alku
- **violet**: pelaajan ohjaus, juoksu ja kiipeily
- **teal**: seitti, heilunta ja lento
- **green**: kavereiden kanssa: kisa katolle
- **rose**: yksin pelattavat tehtävät (v2, rosvot v4)
- **amber**: tallennus

## Boxes

- **Valikko: Kaupunkiin tai Pelaa kavereiden kanssa**: `#free` ja `#friends` tiedostossa `games/seittisankari/v4/index.html`; ei ilmapalloja eikä ennätyslistaa.
- **Ohjaus: tikku, Hyppy, pidä Seitti, Veto, kameran veto**: vasen peukalo liikuttaa (tikku syntyy kosketuskohtaan), oikean alakulman napit Hyppy, Seitti ja Veto (v3), toinen peukalo pidetyn Seitin vieressä hyppää, veto muualla kääntää kameraa, ja v4:ssä myös pidetyn Seitin liu'utus (#561) (`games/seittisankari/v4/ui.js`). Ensimmäisellä kerralla ohjeet näkyvät 16 s (`ai-pelit:seittisankari:ohje`).
- **Kiipeily seinää pitkin, reunalta katolle**: seinään osuessa sankari tarttuu siihen ja kiipeää 6 m/s kädet edellä; yläreunassa hän nousee katolle, Hyppy ponnistaa irti (`stepHero()` tiedostossa `games/seittisankari/v4/world.js`).
- **Seitti pohjassa, 1 s irrotuksesta ja taivas ulottuvilla?**: v3:ssa vähintään 1 s edellisestä irrotuksesta (`WEB_CD`). `aimAnchor()`: seitti tarttuu taivaalle 45 m eteen kameran suuntaan ja 180 m ylös, enintään 160 m lähitalojen yläpuolelle (vähintään 280 m); jos kohta jäisi alle 6 m sankarin yläpuolelle, seittiä ei tule. Seinässä seitti lähtee seinästä poispäin.
- **Heiluri: köysi taivaalle kameran suuntaan**: köysi pitää pituutensa, eikä heilahdus lisää vauhtia tyhjästä; v3:ssa uusi seitti ei jarruta: köyden suuntainen vauhti käännetään heilahduksen suuntaan samansuuruisena (`carryMomentum()`), joten vauhti jatkuu seitistä toiseen; matalalla köysi kelautuu 20 m/s, jotta sankari ei raahaa katua. Seitti lähtee sankarin oikeasta kädestä (`games/seittisankari/v4/draw3d.js`).
- **Pidä Veto: tähtäin, sormen liu'utus kääntää kameraa**: Veto-nappi Seitin vieressä (`buttons()` tiedostossa `games/seittisankari/v4/ui.js`). Pohjassa kamera siirtyy lähemmäs sankarin oikean olan yli (`aimEye()` tiedostossa `world.js`, `place()` tiedostossa `draw3d.js`), ja tähtäin näkyy osumakohdassa: vihreä kun osuu seinään tai kattoon, harmaa kun ei. Samalla sormella liu'uttaessa kamera kääntyy, ja ylöspäin voi katsoa jyrkemmin kuin tavallisesti. Seinässä kamera kääntyy noin 0,3 s:ssa suoraan seinästä poispäin ja vaakatasoon (`aimTurn` ja `stepCam()` tiedostossa `ui.js`), ja kamera siirtyy 1,8 m irti seinästä, jottei se mene talon sisään.
- **Irrota: osuuko säde 60 m sisällä?**: `aimPull()` tiedostossa `games/seittisankari/v4/world.js`: säde kameran suuntaan sankarin rinnasta, ensimmäinen talo 60 m sisällä.
- **Veto 30 m/s suoraan osumakohtaan**: tila `pull` `stepHero()`:ssa: ei painovoimaa, seitti piirtyy kädestä osumakohtaan (myös kavereille). Kesken heilunnan, kiipeilyn, hypyn tai juoksun.
- **Seitti lentää ohi, ei muuta**: lyhyt seittiviiva ilmaan, sankarin liike ei muutu.
- **Irrota tai Hyppy: hyppy ja voltti taaksepäin**: Seitin irrotus tai Hyppy heilunnan aikana hyppää aina (`webJump()`: pystyvauhtiin +14,6 m/s, vähintään tavallisen hypyn 18,2 m/s), ja sankari tekee voltin taaksepäin 0,7 s:ssa. Seuraava heiluriseitti tarttuu vasta 1 s:n päästä (`WEB_CD`), jottei toistuvilla painalluksilla voi nousta taivaalle; Seitti-nappi on sen ajan harmaa (`poseHero()` tiedostossa `draw3d.js`, myös kavereiden ruudulla). Hypyt nousevat v3:ssa kolme kertaa v2:n korkeuden, noin 5,9 m. Seitistä kovalla vauhdilla laskeutuessa vauhti säilyy maassa 0,5 s (`slideT`), ja silloin hypätessä se jatkuu ilmassa.
- **Hyppy kesken vedon?**: Hyppy irrottaa vedosta voltilla ja vauhti jatkuu (linko). Katolta ammuttu veto ei pysähdy omaan kattoon (`pullFrom`), ja katolle ammuttu nousee katolle, vaikka reitti hipaisee reunaa. Vedon aikana pidetty Seitti vaatii uuden painalluksen. Kavereiden kanssa tähtäin ja Veto-ohje näkyvät myös. Perillä sankari tarttuu seinään osumakohdassa tai laskeutuu katolle.
- **Tehtävä vuorollaan: katto, katon rosvot, karkuriauto, tornin huippu, karkurihelikopteri**: v4:ssä (#561) tehtävät tulevat aina tässä viiden järjestyksessä (`KINDS`, `startMission()` tiedostossa `games/seittisankari/v4/round.js`). Katon rosvot: kolme rosvoa kävelee merkityllä katolla eivätkä lähde sieltä. Karkuriauto: 150–250 m päästä, ajaa katuja 20 m/s ja kääntyy risteyksissä enimmäkseen sankarista poispäin. Karkurihelikopteri: lentää 70–90 m korkeudella 15 m/s suoria matkoja, jotka on tarkistettu talojen yli vapaiksi. Autossa ja helikopterissa on punainen valopylväs, joka häviää lähellä. Mikään ei pääse karkuun. Ruudulla "Ota rosvot kiinni! N/3 · N m", "Pysäytä karkuriauto! N m" tai "Pysäytä karkurihelikopteri! N m" ja nuoli lähimpään. Kunkin lajin ensimmäisellä kerralla kaksi ohjeriviä (`ai-pelit:seittisankari:ohje4`). Katto: `pickTarget()`: talo 20–150 m korkea, ei torni, vähintään 20 m kaupungin reunasta; tornin vuorolla aina torni, oli se kuinka kaukana tahansa (tavallinen katto vain, jos sankari seisoo jo tornin huipulla); jos sopivaa ei ole, lähin vähintään 120 m päässä oleva talo, eikä koskaan juuri saavutettu katto. Katolla lippu ja valopylväs, ruudulla "Mene merkitylle katolle! N m" (lähellä "↑ N m", katon yläpuolella "↓ N m"), nuoli kameran suunnasta, aika ja ✔-laskuri (`drawGoal()` tiedostossa `ui.js`).
- **Kiinni: seitti nappaa sen, sankari jää paikalleen**: `aimCrook()` tiedostossa `round.js`: rosvo, auto tai helikopteri 60 m sisällä voittaa sen takana olevan seinän; osuu, jos säde menee enintään 1,5 m sen ohi. Tähtäin on silloin punainen. Irrottaessa seitti lentää siihen heti (`catchCrook()`): rosvo kääriytyy valkoiseen seittiin, auto luisuu pysähdyksiin kadulle ja helikopteri lentää omalla korkeudellaan lähimmän sen alla olevan katon (ei tornin) päälle ja laskeutuu sille, tai suoraan alas, jos sellaista ei ole.
- **Yksin: kaikki tehtävän rosvot kiinni?**: kolmen rosvon tehtävä päättyy kolmanteen osumaan, auto ja helikopteri yhteen. Kiinni jääneet näkyvät vielä 10 s. Kavereiden kanssa rosvoja ei ole.
- **Yksin: seisoo merkityllä katolla?**: `onTop()`: sankari seisoo katolla (ei seinässä eikä ilmassa) talon rajojen sisällä.
- **Perillä tai kiinni: aika, laskuri +1, uusi tehtävä**: "Perillä!" (tornissa "Tornin huipulla!", rosvoista "Rosvot kiinni!", "Karkuriauto pysäytetty!" tai "Helikopteri pysäytetty!") 2,5 s, laskuri `ai-pelit:seittisankari:tehtavat`, uusi kohde merkitään heti.
- **Tallenna paikka 2 s välein ja valikkoon mennessä**: `ai-pelit:seittisankari:kierros2` = `{h: sankarin paikka, g: merkitty talo, gt: aika}` (oma avain, jotta puhelimen välimuistissa vielä oleva v1 ei kirjoita sen yli), joten uudelleenlataus jatkaa samasta kohdasta ja samalla kohteella; jos v2 ei ole vielä tallentanut, v1:n `ai-pelit:seittisankari:kierros` (`{h}`) aukeaa, ja v2 merkitsee uuden kohteen. v4:ssä `ai-pelit:seittisankari:tehtava4` = `{k: tehtävän laji, gt: aika}`: kesken jäänyt rosvotehtävä alkaa uusilla rosvoilla, ja aika jatkuu. Rosvotehtävän aikana `g` on -1, joten tallessa oleva katto on aina kattotehtävä: myös v3:n katto pidetään ajan kanssa, vaikka laskuri osuisi rosvojen vuoroon. Puhelimen kääntö pitää kierroksen.
- **Huone: tekijä valitsee Kilpa katolle tai Vapaa**: `NET_MODES` tiedostossa `games/seittisankari/v4/net.js`; kilpa kestää 180 s.
- **Kaikki samasta lähtöpaikasta, 220 m merkitystä katosta**: `pickGoal()` arpoo talon (30–140 m, ei torni, kaukana reunasta), `startSpot()` laittaa kaikki samaan katukohtaan riviin 1,5 m välein kadun suuntaan. Vapaassa tilassa sama paikka 30 m tornista. Katolla on lippu ja keltainen valopylväs, ja ruudulla nuoli osoittaa sinne.
- **Tekijä hyväksyy: voittaja, sama tulos kaikille**: katolla seisova puhelin pyytää voittoa 0,5 s välein; tekijä hyväksyy, jos sankari on sen omassa näkymässä katon päällä (`hostClaim()`), eikä kierros ole tauolla tai ohi. Tulos lähtee kaikille `deliver()`-viestinä.
- **Tulos: aika tai korkeus**: katolle ehtineet ajan mukaan, muut korkeuden mukaan (`standings()`).
