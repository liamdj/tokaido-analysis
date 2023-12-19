# Tokaido Analysis
This repository contains tools to analyze the board game tokaido. [This article](https://medium.com/@liamjoh99/web-scraping-for-board-game-analysis-8f584379f3c) discusses the code and results for collecting bga arena mode games.

To use the code, you must include a file `accounts.py` that defines `ACCOUNTS = [(email1, password1), (email2, password2), ...]`. Note that the number of replays each account can access is capped, and accounts must be a day old and have at least 2 completed games.

The following script produces the data and results used in the article:
```python
import bga_scraping as bga
import arena_results as arena

sess = next(bga.session_generator())
# get top 10 season 5 arena players
players = [bga.get_player_by_arena_rank(sess, rank, 5) for rank in range(1, 11)]
# get all season 5 arena tables with one of those players
tables = bga.get_season_tables_with_players(sess, 5, players)
# save the tables replays
bga.save_table_replays_batch(tables.keys())
# make a file with all results and a file with basic statistics
arena.create_results_summary(tables, 's5-arena')
```
