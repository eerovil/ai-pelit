# Seittisankari: kiipeily ja seittiheilunta pilvenpiirtäjissä

Suunnitelma uudesta 3D-pelistä (#529). Pelaaja liikkuu yhdessä kaupungissa: juoksee kadulla ja katoilla, kiipeää minkä tahansa talon seinää pitkin ja heilahtaa seitillä talosta toiseen. Tehtävät ovat lyhyitä ja ajastettuja; putoaminen kadulle ei ole kuolema, vain hukattua aikaa.

```mermaid
flowchart TD
    A[Valikko: tehtävät ja Vapaa kaupunki] --> B{Keskeneräinen tehtävä tallessa?}
    B -- Kyllä --> C[Jatka samasta kohdasta]
    B -- Ei --> D[Tehtävän alku katolla tai kadulla]
    C --> E
    D --> E[Ohjaus: tikku, Hyppy, pidä Seitti, kameran veto]
    E --> F{Missä sankari on?}
    F -- Kadulla tai katolla --> G[Juoksu ja hyppy]
    F -- Seinässä kiinni --> H[Kiipeily seinää pitkin, reunalta katolle]
    F -- Ilmassa --> I{Seitti pohjassa ja kiinnekohta 45 m sisällä?}
    I -- Kyllä --> J[Heiluri: köyden pituus pysyy, kelaa hitaasti sisään]
    I -- Ei --> K[Lento: painovoima, vähän ohjausta]
    J --> L[Irrota: vauhti jatkuu]
    L --> K
    K --> M{Osuu seinään?}
    M -- Kyllä --> H
    M -- Ei --> N{Osuu katuun?}
    N -- Kyllä --> G
    G --> O{Tehtävän tavoite täyttyy?}
    H --> O
    J --> O
    O -- Kyllä --> P[Valmis: aika, ennätys, seuraava tehtävä auki]
    O -- Ei --> Q{Aika loppui?}
    Q -- Kyllä --> R[Yritä uudelleen]
    Q -- Ei --> E
    P --> S[Tallenna puhelimeen ja lähetä aika listalle]
    E --> T[Tallenna paikka 2 s välein]
    class A,B,C,D blue
    class E,G,H violet
    class I,J,K,L,M,N teal
    class O,P green
    class Q,R rose
    class S,T amber
```

## Colours

- **blue**: valikko ja tehtävän aloitus
- **violet**: pelaajan ohjaus, juoksu ja kiipeily
- **teal**: seitti, heilunta ja lento
- **green**: tavoite ja onnistuminen
- **rose**: aika loppui
- **amber**: tallennus ja ennätyslista

## Boxes

- **Valikko: tehtävät ja Vapaa kaupunki**: seitsemän tehtävää järjestyksessä, seuraava aukeaa edellisen läpäisystä; Vapaa kaupunki on auki alusta asti. Suunnitelma: `games/seittisankari/v1/ui.js`.
- **Ohjaus: tikku, Hyppy, pidä Seitti, kameran veto**: vasen peukalo liikuttaa (tikku syntyy kosketuskohtaan), oikean alakulman napit Hyppy ja Seitti, veto muualla oikealla puolella kääntää kameraa. Kamera kääntyy itsestään liikesuuntaan.
- **Kiipeily seinää pitkin, reunalta katolle**: seinään osuessa sankari tarttuu siihen; tikku liikuttaa seinän pinnalla, yläreunassa hän nousee katolle, Hyppy ponnistaa irti seinästä. Talot ovat suorakulmaisia laatikoita, joten seinä on aina yksi tasopinta. Suunnitelma: `hero.js`.
- **Seitti pohjassa ja kiinnekohta 45 m sisällä?**: peli näyttää koko ajan merkin kohdassa, johon seitti tarttuisi: korkein talon kulma tai reuna edessä ja yläpuolella, kameran suunnassa. Ilman kohdetta (aukea paikka) nappi on himmeä.
- **Heiluri: köyden pituus pysyy, kelaa hitaasti sisään**: köysi pitää etäisyyden kiinnekohtaan, joten sankari heilahtaa kaarella; köysi lyhenee 2 m/s, jotta seitillä voi myös nousta.
- **Tehtävän tavoite täyttyy?**: tavoite on tehtäväkohtainen: lippu katolla, kissa antennista, ilmapallot, varkaan kiinniotto seitillä, karanneet dronet. Suunnitelma: `missions.js`.
- **Tallenna puhelimeen ja lähetä aika listalle**: avoimet tehtävät `ai-pelit:seittisankari:taso`, parhaat ajat `ai-pelit:seittisankari:ajat`, ja `AiPelitScores.submit()` tehtävän omalle listalle (pienin aika paras).
- **Tallenna paikka 2 s välein**: `ai-pelit:seittisankari:kierros` pitää tehtävän, ajan ja sankarin paikan, joten uudelleenlataus tai puhelimen kääntö jatkaa samasta kohdasta.
