# Assistant local d'investissement mensuel Revolut Trading

Application Python locale concue comme un compagnon personnel d'aide a la decision pour une strategie DCA prudente et patrimoniale.

Objectif:

- donner une vision claire du portefeuille;
- structurer l'analyse des marches;
- afficher des alertes de risque;
- proposer des idees d'actifs a surveiller;
- preparer une repartition mensuelle indicative;
- utiliser des signaux simples: interessant, a surveiller, attendre, eviter.

L'application ne presente jamais ses resultats comme des ordres obligatoires. La decision finale d'achat ou de vente reste manuelle et appartient uniquement a l'investisseur.

## Regles strictes

- Aucun passage d'ordre automatique.
- Aucune connexion a Revolut pour executer un ordre.
- Aucun levier.
- Aucun margin trading.
- Aucune vente a decouvert.
- Aucune certitude affichee comme une prediction fiable.
- Aucun achat propose sur une action deja au-dessus de la limite de concentration.

## Strategie cible

- 70 % ETF long terme
- 20 % actions individuelles
- 10 % cash / opportunites
- risque maximum par action individuelle configurable entre 5 % et 10 %

## Structure

```text
Trading/
|-- app.py
|-- config.py
|-- database.py
|-- market_data.py
|-- portfolio.py
|-- strategy.py
|-- risk_management.py
|-- backtesting.py
|-- charts.py
|-- requirements.txt
|-- README.md
|-- data/
|   `-- trading_app.sqlite3
|-- pages/
|   |-- 1_Portefeuille.py
|   |-- 2_Marches.py
|   |-- 3_Plan_mensuel.py
|   |-- 4_Idees_investissement.py
|   |-- 5_Backtest.py
|   |-- 6_Parametres.py
|   `-- 7_Transactions.py
`-- utils/
    |-- __init__.py
    |-- formatting.py
    `-- ui.py
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Sur cette machine, si `python` ouvre le raccourci Microsoft Store, utiliser:

```bash
py -3 -m pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

Ou avec le lanceur Python Windows:

```bash
py -3 -m streamlit run app.py
```

L'application sera disponible localement, en general sur:

```text
http://localhost:8501
```

## Donnees et confidentialite

- Le portefeuille, les transactions, les parametres, le cache de marche, les idees calculees et les plans mensuels sont stockes dans SQLite: `data/trading_app.sqlite3`.
- L'application n'envoie pas tes donnees personnelles a Revolut.
- Les seuls appels externes prevus servent a recuperer des prix de marche via `yfinance`.
- Si un ticker ne repond pas, l'application affiche une erreur non bloquante et continue avec les autres actifs.
- Aucune API de passage d'ordre n'est presente.

## Tables SQLite

Les tables creees automatiquement au premier lancement:

- `settings`
- `assets`
- `transactions`
- `portfolio_positions`
- `market_data_cache`
- `recommendations`
- `monthly_plans`

La table `recommendations` conserve son nom technique pour eviter une migration inutile, mais l'interface parle d'idees d'investissement et de candidats a analyser.

## Watchlist par defaut

Les tickers sont configurables depuis la page Parametres. La liste initiale contient notamment:

- ETF: `VUSA.L`, `CSPX.L`, `EQQQ.L`, `IWDA.AS`
- Actions: `NVDA`, `MSFT`, `AAPL`, `GOOGL`, `AMZN`, `TSLA`, `ASML`, `LVMH.PA`, `MC.PA`, `AIR.PA`

La disponibilite Revolut peut varier. Verifie toujours le ticker dans Revolut avant toute decision.

## Exemple de portefeuille fictif

Depuis le Dashboard ou Parametres, clique sur `Charger le portefeuille fictif`.

Exemple inclus:

- `IWDA.AS`, ETF MSCI World
- `VUSA.L`, ETF S&P 500
- `MSFT`, action individuelle
- `ASML`, action individuelle
- cash disponible: 1 200 EUR par defaut

## Exemple de strategie mensuelle avec 1 000 EUR

Si l'allocation actuelle est proche de la cible, le moteur part de:

- environ 700 EUR vers les ETF;
- environ 200 EUR vers les actions individuelles;
- environ 100 EUR en cash / opportunites.

Puis il ajuste:

- ETF augmentes si la poche ETF est sous-ponderee;
- actions reduites ou bloquees si la poche actions est trop elevee;
- cash augmente si la poche cash est sous la cible;
- ligne action bloquee si elle depasse la limite individuelle configuree.

Chaque idee affiche:

- ticker;
- type d'actif;
- score de qualite;
- signal pedagogique;
- niveau de risque;
- montant maximum theorique selon la strategie;
- raison de l'idee;
- points de vigilance;
- phrase de validation manuelle.

## Pages

- Dashboard: synthese, allocation, alertes, meilleurs candidats, enveloppe mensuelle.
- Portefeuille: ajout manuel de positions, valorisation, poids, P/L latent, allocation.
- Marches: indicateurs yfinance, MM50, MM200, RSI, volatilite, comparaisons.
- Plan mensuel: repartition indicative de l'enveloppe et candidats a analyser.
- Idees d'investissement: scoring 0 a 100, risque, vigilance et validation manuelle.
- Backtest: DCA ETF, 70/20/10, achat unique au depart.
- Parametres: allocation cible, risque, cash, watchlist configurable.
- Transactions: journal local des operations saisies manuellement.

## Ameliorations possibles

- Conversion FX fiable EUR/USD/GBP pour valoriser toutes les lignes en EUR.
- Import CSV Revolut pour eviter la saisie manuelle.
- Analyse fondamentale simple: croissance, marges, dette, valorisation.
- Limites sectorielles plus fines par ETF avec decomposition look-through.
- Scoring plus robuste par regime de marche.
- Export PDF/CSV du plan mensuel.
- Tests unitaires complets et CI.
