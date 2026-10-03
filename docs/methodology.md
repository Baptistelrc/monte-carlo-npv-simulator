# Méthodologie — outil de valorisation Monte Carlo

Notes de travail et d'entretien : la méthode, les choix, les résultats et les
limites. Les termes de finance et de code restent en anglais.

## 1. Objet

Un seul chiffre de NPV (Net Present Value) cache le risque. L'outil remplace
chaque input incertain par une distribution, tire des milliers de scénarios et
décrit la distribution de la NPV : son niveau (mean), sa dispersion (standard
deviation, notée SD, et percentiles P5, P50, P95) et la probabilité que la NPV
soit négative.

## 2. Modèle déterministe

| Input | Base case |
| --- | --- |
| Investment (Year 0) | 800 000 € |
| Durée | 5 ans, salvage value = 0 |
| Volume | 15 000 unités / an |
| Price | 50 € / unité |
| Variable cost | 30 € / unité |
| Fixed costs | 80 000 € / an |
| Discount rate | 10 % |

- Cash flow annuel = Volume × (Price − Variable cost) − Fixed costs = 220 000 €.
- Le cash flow est identique chaque année, donc
  **NPV = −Investment + cash flow annuel × annuity factor**, avec
  annuity factor = (1 − 1,10⁻⁵) / 0,10 = 3,7908.
- NPV du base case = **33 973,09 €**.
- Break-even price = 49,40 € ; break-even volume = 14 552 unités.

À retenir : le projet est fragile. Il suffit que le prix baisse de 0,60 € ou le
volume de 448 unités pour que la NPV passe à zéro.

## 3. Méthode Monte Carlo

1. On tire une valeur de chaque input incertain dans sa distribution.
2. On calcule la NPV de ce scénario.
3. On répète N fois (5 000 comme dans l'Excel, ou 100 000).
4. On décrit les N NPV obtenues.

Choix techniques :

- **Un tirage vaut pour les 5 ans** : le prix tiré est le prix des 5 années.
  C'est ce qui permet la formule en annuity factor (voir les limites, section 9).
- **Inverse CDF** : chaque input est obtenu en tirant une probabilité entre 0 et
  1 puis en appliquant la fonction de répartition inverse de sa distribution
  (comme `NORM.INV(RAND(), …)` et `BETA.INV(RAND(), …)` dans Excel).
- **Seed** : le générateur est initialisé avec un seed (42 par défaut). Même
  seed, mêmes résultats ; autre seed, résultats légèrement différents.
- **Calcul vectorisé** : les N scénarios sont calculés en une seule opération.

## 4. Distributions des inputs

### Leçon 2 — normales indépendantes

Price ~ Normal(50 ; 2,5), Volume ~ Normal(15 000 ; 1 500),
Variable cost ~ Normal(30 ; 1,5), fixed costs constants. Point de départ simple :
tout est symétrique et centré sur le base case.

### Leçon 3 — distributions justifiées

| Input | Distribution | Justification |
| --- | --- | --- |
| Price | PERT (min 44, mode 50, max 52) | avis d'expert : le prix peut baisser nettement plus qu'il ne peut monter |
| Demand | Normal (15 000 ; 1 500) | incertitude symétrique autour de la prévision |
| Volume vendu | min(demand, capacité 17 000) | on ne peut pas vendre plus que ce que l'on produit |
| Variable cost | Normal (30,0625 ; 1,2443) | mean et sample SD (ddof = 1) de 8 valeurs historiques |
| Fixed costs | Constant (80 000 €) | contractuels |

PERT : α = 1 + 4 (mode − min) / (max − min) = 4 ; β = 1 + 4 (max − mode) / (max − min) = 2 ;
tirage = min + (max − min) × Beta(α, β).

Point clé : la PERT est asymétrique. Sa valeur la plus probable (mode) est 50 €,
mais sa mean est (44 + 4 × 50 + 52) / 6 = **49,33 €**. La valeur la plus probable
n'est pas la moyenne. Comme 49,33 € est sous le break-even price (49,40 €), le
prix est sous le break-even dans environ 48 % des tirages.

Dans le dashboard, la Lognormal est paramétrée par la mean et la SD de la
variable elle-même (en euros ou en unités), pas par celles de son logarithme.

### Leçon 4 — corrélation prix–demande

ρ = −0,5 entre prix et demande : quand le prix est bas, la demande tend à être
élevée. Le variable cost reste indépendant.

## 5. Corrélation : Gaussian copula

1. Tirer Z1 et Z2, deux normales standard indépendantes.
2. X1 = Z1 ; X2 = ρ·Z1 + √(1 − ρ²)·Z2 : X1 et X2 sont des normales standard de
   corrélation ρ.
3. U1 = Φ(X1), U2 = Φ(X2) : deux probabilités entre 0 et 1, liées entre elles.
4. Price = inverse CDF de la PERT appliquée à U1 ; Demand = inverse CDF de la
   Normal appliquée à U2.

L'intérêt de la copula : chaque input garde sa propre distribution (PERT,
Normal), seule la façon dont ils bougent ensemble change.

Généralisation : avec plus de deux inputs, l'étape 2 utilise la décomposition
de Cholesky de la matrice de corrélation (avec deux inputs, elle redonne
exactement la formule ci-dessus). Avant usage, le code vérifie que la matrice
est symétrique, a des 1 sur la diagonale et est positive semi-definite (les
corrélations demandées doivent pouvoir exister ensemble), et affiche une erreur
claire sinon.

Remarque : la corrélation mesurée entre prix et demande est de −0,49 et non
−0,50. La copula impose ρ aux normales sous-jacentes ; la transformation en PERT
asymétrique affaiblit légèrement la corrélation linéaire. L'Excel donne la même
chose (−0,48).

## 6. Statistiques et marge d'erreur

Une statistique simulée est une estimation : elle change un peu à chaque
recalcul. On la donne toujours avec sa standard error (SE).

- SE de la mean = SD / √N.
- SE d'une probabilité = √(p (1 − p) / N).
- Marge d'erreur à 95 % = 1,96 × SE.

Pour diviser la marge par 2, il faut 4 fois plus d'itérations. En leçon 4, la
marge sur la mean est d'environ ± 3 300 € avec 5 000 itérations et de ± 739 €
avec 100 000.

## 7. Résultats (Python, 100 000 itérations, seed 42)

| Statistique | Leçon 2 | Leçon 3 | Leçon 4 |
| --- | ---: | ---: | ---: |
| Mean NPV | 35 201 € | −11 274 € | −14 923 € |
| Marge à 95 % sur la mean | ± 1 252 € | ± 914 € | ± 739 € |
| SD | 201 941 € | 147 509 € | 119 262 € |
| P5 | −281 316 € | −252 994 € | −208 045 € |
| P50 | 26 833 € | −11 532 € | −16 558 € |
| P95 | 381 506 € | 232 399 € | 185 686 € |
| P(NPV < 0) | 44,7 % | 53,1 % | 55,5 % |

Marge à 95 % sur P(NPV < 0) : ± 0,3 point dans les trois cas.

### Lecture

**Leçon 2.** La mean NPV est égale au base case à la marge d'erreur près : les
inputs sont indépendants et centrés sur le base case, donc la moyenne du produit
volume × marge est le produit des moyennes. Pourtant la NPV est négative dans
environ 45 % des scénarios. Une NPV négative signifie que le projet ne couvre
pas son coût du capital, pas qu'il perd de l'argent.

**Leçon 3.** Deux effets distincts, à ne pas expliquer l'un par l'autre :

- *La mean baisse d'environ 46 000 €.* Valeur exacte de la mean : −12 134 €, soit
  le base case moins :
  - ≈ 37 900 € : asymétrie du prix (mean de la PERT à 49,33 € au lieu de 50 €) ;
  - ≈ 4 600 € : plafond de capacité (les ventes moyennes passent de 15 000 à
    14 936 unités, car la demande dépasse 17 000 dans 9 % des scénarios) ;
  - ≈ 3 500 € : mean historique du variable cost à 30,06 € au lieu de 30 €.
- *La dispersion baisse* (SD de 201 941 € à 147 509 €) : la fourchette de prix de
  l'expert est plus étroite que la Normal de la leçon 2 (SD du prix de 1,43 €
  contre 2,5 €), celle du coût aussi (1,24 € contre 1,5 €), et la capacité coupe
  les meilleurs scénarios.

**Leçon 4.** La corrélation négative joue comme un natural hedge : un prix bas
est en partie compensé par une demande élevée.

- La SD baisse nettement, de 147 509 € à 119 262 €.
- La mean bouge peu : −3 649 €, proche de l'effet théorique de covariance
  ρ × σ_price × σ_demand × annuity factor = −0,5 × 1,43 × 1 500 × 3,79 ≈ −4 000 €.
- P(NPV < 0) reste voisine (55,5 % contre 53,1 %) : la distribution est plus
  resserrée, mais autour d'une mean un peu plus basse et toujours négative.

On ne donne jamais l'écart entre deux NPV proches de zéro en pourcentage : on le
donne en euros.

## 8. Tornado chart

### Ce qu'il mesure

Pour chaque input, la NPV quand cet input passe seul de son P10 à son P90, les
autres restant au base case. La longueur de la barre est le swing. C'est une
mesure de **sensibilité**, pas de corrélation.

### Pourquoi la demande est classée devant le prix (leçon 4)

Le swing est le produit de deux choses : **sensibilité × incertitude**.

| Input | Effet sur la NPV de 1 % de l'input | Fourchette P10–P90 (en % du base case) | Swing |
| --- | ---: | ---: | ---: |
| Demand | 11 372 € | 25,6 % (13 078 à 16 922 unités) | 291 485 € |
| Price | 28 431 € | 7,5 % (47,33 € à 51,10 €) | 214 553 € |
| Variable cost | 17 059 € | 10,6 % (28,47 € à 31,66 €) | 181 354 € |

- Par pourcent, le prix est l'input le plus sensible : 1 % de prix (0,50 €)
  s'applique aux 15 000 unités et vaut 28 431 € de NPV ; 1 % de demande
  (150 unités) ne rapporte que la marge unitaire de 20 € et vaut 11 372 €.
- Mais la demande est beaucoup plus incertaine : sa fourchette P10–P90 fait
  25,6 % du base case, contre 7,5 % pour le prix (fourchette étroite de l'expert).
- Le produit donne le classement : 11 372 × 25,6 ≈ 291 000 € pour la demande,
  28 431 × 7,5 ≈ 215 000 € pour le prix.

Preuve par la leçon 2 : avec un prix en Normal(50 ; 2,5), la fourchette du prix
est de 12,8 % et le prix repasse en tête (swing de 364 357 €).

À dire en entretien : « le prix est l'input auquel le projet est le plus
sensible, la demande est celui qui contribue le plus au risque ».

### Limites du tornado

- **Un input à la fois.** Les autres restent fixes : le tornado ne montre aucune
  interaction entre inputs (par exemple prix bas et coût élevé en même temps).
- **Il ignore la corrélation.** Avec ρ = −0,5, un prix bas viendrait avec une
  demande élevée ; le tornado fait bouger le prix sans toucher à la demande. Il
  est donc identique en leçon 3 et en leçon 4, alors que le risque total diffère.
- **Il est ancré sur le base case**, qui n'est pas la moyenne des distributions.
  Le prix va de 47,33 € à 51,10 € autour d'un base case à 50 € : la barre est
  plus longue à gauche qu'à droite. Et le plafond de capacité n'apparaît pas :
  le P90 de la demande (16 922) reste sous 17 000.
- Il ne regarde que P10 et P90 : les scénarios extrêmes n'y figurent pas.

Le tornado sert à classer les inputs ; la simulation complète sert à mesurer le
risque.

## 9. Limites du modèle

Limites principales :

1. **Un tirage pour 5 ans.** Prix, demande et coût sont tirés une fois et
   conservés toute la durée du projet. Un mauvais tirage reste mauvais 5 ans :
   rien ne se compense d'une année sur l'autre. La dispersion de la NPV est donc
   dans le haut de ce qu'un modèle année par année donnerait. Ordre de grandeur :
   si les cinq cash flows étaient tirés indépendamment chaque année, la SD de la
   NPV serait environ 2,2 fois plus faible. La réalité est entre les deux.
2. **Pas d'impôts ni de NWC (net working capital).** Le cash flow est la marge
   d'exploitation : ni impôt sur les sociétés, ni économie d'impôt liée à
   l'amortissement, ni investissement en besoin en fonds de roulement.
3. **Variable cost indépendant.** Il ne dépend ni du prix ni de la demande. En
   réalité, coûts et prix peuvent monter ensemble (inflation) et le coût unitaire
   peut dépendre du volume.
4. **Normales non tronquées.** Une Normal peut en théorie donner une demande ou
   un coût négatif. Ici ce serait à 10 SD de la moyenne : aucun effet pratique,
   mais ce ne serait plus vrai avec des inputs plus dispersés.
5. **Fourchette de prix d'un seul expert.** La PERT (44, 50, 52) est un jugement
   individuel, et c'est elle qui produit l'essentiel du résultat : environ
   38 000 € de baisse de la mean viennent de son asymétrie.

Autres limites :

6. Le variable cost est estimé sur 8 observations seulement, et l'incertitude sur
   cette estimation est ignorée. La SE de sa mean est 1,2443 / √8 ≈ 0,44 € ; un
   écart de 0,44 € sur le coût vaut environ 25 000 € de NPV.
7. Discount rate, investment, fixed costs, capacité et durée sont certains.
8. Pas de salvage value, et pas de réaction du management en cours de projet
   (arrêter, augmenter la capacité, changer le prix).
9. La Gaussian copula ne crée pas de dépendance renforcée dans les scénarios
   extrêmes, et ρ = −0,5 est une hypothèse, pas une estimation.
10. Le prix et la demande sont liés par une corrélation, pas par un modèle
    économique (courbe de demande).

## 10. Validation

- **Déterministe** : base case égal à l'Excel au centime (33 973,09 €), break-even
  price et volume vérifiés.
- **Python contre Excel** ([validation.md](validation.md)) : pour chaque leçon,
  comparaison de la mean, de la SD, de P5, de P95 et de P(NPV < 0) dans la marge
  d'erreur. 28 comparaisons sur 30 sont dans la marge à 95 % ; on en attend
  environ 1,5 en dehors par pur hasard. Les deux sorties sont des P95, sur deux
  tirages Excel différents.
- **Convergence** : avec 1 000 000 d'itérations et trois seeds, la mean NPV
  converge vers sa valeur analytique exacte (33 973,09 € en leçon 2,
  −12 134 € en leçon 3), à moins de 2 SE.
- **Tests automatiques** : 79 tests, dont ρ = 0 qui redonne exactement la
  leçon 3, le volume jamais au-dessus de la capacité, les tirages PERT dans
  [min, max] et la corrélation mesurée proche de ρ.

## 11. Règles de lecture à respecter

- NPV négative : le projet ne couvre pas son coût du capital ; il ne perd pas
  forcément de l'argent.
- Mean et dispersion ont des causes différentes : ne jamais expliquer l'une par
  l'autre.
- Toute statistique simulée se donne avec sa standard error ou sa marge.
- Pas de pourcentage de variation sur un nombre proche de zéro.
- La valeur la plus probable n'est pas la moyenne quand la distribution est
  asymétrique.
- La corrélation n'est pas la sensibilité : le tornado mesure la sensibilité ; ρ
  décrit comment deux variables bougent ensemble.

## 12. Comment l'outil a été construit

Nous avons conçu le modèle, choisi les hypothèses et construit le classeur Excel
de référence. Le code Python a été écrit avec Claude Code, phase par phase, selon
notre spécification ; nous avons validé chaque phase contre notre Excel et contre
la théorie avant de passer à la suivante.
