# Seittisankari: kiipeily ja seittiheilunta pilvenpiirtäjissä

3D-peli (#529). v1 on vapaa kaupunki ja kavereiden kanssa pelaaminen (Eeron valinta): pelaaja juoksee kadulla ja katoilla, kiipeää minkä tahansa talon seinää pitkin ja heilahtaa seitillä talosta toiseen noin 1,7 km leveässä kaupungissa. Kavereiden kanssa kisataan satunnaisen talon katolle samasta lähtöpaikasta, tai liikutaan vapaasti yhdessä.

```mermaid
flowchart TD
    A[Valikko: Kaupunkiin tai Pelaa kavereiden kanssa] --> B{Paikka tallessa?}
    B -- Kyllä --> C[Jatka samasta kohdasta]
    B -- Ei --> D[Alku kadulla keskustassa]
    C --> E
    D --> E[Ohjaus: tikku, Hyppy, pidä Seitti, kameran veto]
    E --> F{Missä sankari on?}
    F -- Kadulla tai katolla --> G[Juoksu ja hyppy]
    F -- Seinässä kiinni --> H[Kiipeily seinää pitkin, reunalta katolle]
    F -- Ilmassa --> I{Seitti pohjassa ja taivas yläpuolella ulottuvilla?}
    I -- Kyllä --> J[Heiluri: köysi taivaalle kameran suuntaan]
    I -- Ei --> K[Lento: painovoima, vähän ohjausta]
    J --> L[Irrota: vauhti jatkuu]
    L --> K
    K --> M{Osuu seinään?}
    M -- Kyllä --> H
    M -- Ei --> N{Osuu katuun tai kattoon?}
    N -- Kyllä --> G
    E --> T[Tallenna paikka 2 s välein ja valikkoon mennessä]
    A --> R[Huone: tekijä valitsee Kilpa katolle tai Vapaa]
    R --> S[Kaikki samasta lähtöpaikasta, 220 m merkitystä katosta]
    S --> E
    G --> U{Kilpa: seisoo merkityllä katolla?}
    U -- Kyllä --> V[Tekijä hyväksyy: voittaja, sama tulos kaikille]
    U -- Ei --> W{3 min kulunut?}
    W -- Kyllä --> X[Tulos: aika tai korkeus]
    class A,B,C,D blue
    class E,G,H violet
    class I,J,K,L,M,N teal
    class R,S,U,V,W,X green
    class T amber
```

## Colours

- **blue**: valikko ja alku
- **violet**: pelaajan ohjaus, juoksu ja kiipeily
- **teal**: seitti, heilunta ja lento
- **green**: kavereiden kanssa: kisa katolle
- **amber**: tallennus

## Boxes

- **Valikko: Kaupunkiin tai Pelaa kavereiden kanssa**: `#free` ja `#friends` tiedostossa `games/seittisankari/v1/index.html`; v1:ssä ei tehtäviä, ilmapalloja eikä ennätyslistaa.
- **Ohjaus: tikku, Hyppy, pidä Seitti, kameran veto**: vasen peukalo liikuttaa (tikku syntyy kosketuskohtaan), oikean alakulman napit Hyppy ja Seitti, toinen peukalo pidetyn Seitin vieressä hyppää, veto muualla kääntää kameraa (`games/seittisankari/v1/ui.js`). Ensimmäisellä kerralla ohjeet näkyvät 16 s (`ai-pelit:seittisankari:ohje`).
- **Kiipeily seinää pitkin, reunalta katolle**: seinään osuessa sankari tarttuu siihen ja kiipeää 6 m/s kädet edellä; yläreunassa hän nousee katolle, Hyppy ponnistaa irti (`stepHero()` tiedostossa `games/seittisankari/v1/world.js`).
- **Seitti pohjassa ja taivas yläpuolella ulottuvilla?**: `aimAnchor()`: seitti tarttuu taivaalle 45 m eteen kameran suuntaan ja 180 m ylös, enintään 160 m lähitalojen yläpuolelle (vähintään 280 m); jos kohta jäisi alle 6 m sankarin yläpuolelle, seittiä ei tule. Seinässä seitti lähtee seinästä poispäin.
- **Heiluri: köysi taivaalle kameran suuntaan**: köysi pitää pituutensa, eikä heilahdus lisää vauhtia tyhjästä; matalalla köysi kelautuu 20 m/s, jotta sankari ei raahaa katua. Seitti lähtee sankarin oikeasta kädestä (`games/seittisankari/v1/draw3d.js`).
- **Tallenna paikka 2 s välein ja valikkoon mennessä**: `ai-pelit:seittisankari:kierros` = `{h: sankarin paikka}`, joten uudelleenlataus jatkaa samasta kohdasta; puhelimen kääntö pitää kierroksen.
- **Huone: tekijä valitsee Kilpa katolle tai Vapaa**: `NET_MODES` tiedostossa `games/seittisankari/v1/net.js`; kilpa kestää 180 s.
- **Kaikki samasta lähtöpaikasta, 220 m merkitystä katosta**: `pickGoal()` arpoo talon (30–140 m, ei torni, kaukana reunasta), `startSpot()` laittaa kaikki samaan katukohtaan riviin 1,5 m välein kadun suuntaan. Vapaassa tilassa sama paikka 30 m tornista. Katolla on lippu ja keltainen valopylväs, ja ruudulla nuoli osoittaa sinne.
- **Tekijä hyväksyy: voittaja, sama tulos kaikille**: katolla seisova puhelin pyytää voittoa 0,5 s välein; tekijä hyväksyy, jos sankari on sen omassa näkymässä katon päällä (`hostClaim()`), eikä kierros ole tauolla tai ohi. Tulos lähtee kaikille `deliver()`-viestinä.
- **Tulos: aika tai korkeus**: katolle ehtineet ajan mukaan, muut korkeuden mukaan (`standings()`).
