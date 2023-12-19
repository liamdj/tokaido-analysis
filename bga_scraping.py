import requests
from accounts import ACCOUNTS
import json
from bs4 import BeautifulSoup
import os.path
from collections import defaultdict

BASE = 'https://boardgamearena.com'
LOGIN = '/account/account/login.html'
ARENA_RANKING = '/halloffame/halloffame/getRanking.html'
ELO_RANKING = '/gamepanel/gamepanel/getRanking.html'
GAMES = '/gamestats/gamestats/getGames.html'
ARCHIVE = '/gamereview/gamereview/requestTableArchive.html'
REPLAY = '/archive/archive/logs.html'
GAME_ID = 1003
# start and end dates
SEASONS = {
    1: (1587009600, 1594008000),
    2: (1594008000, 1601870400),
    3: (1601870400, 1609822800),
    4: (1609822800, 1617681600),
    5: (1617681600, 1625544000),
    6: (1625544000, 1633492800)
}
DEPELETED = 'You have reached a limit (replay)'
NO_ACCESS = 'Sorry, you need to be registered more than 24 hours and have played at least 2 games to access this feature.'

def session_generator():
    # must be a verified bga account with >=2 games and >24 hours old
    for email, password in ACCOUNTS:
        sess = requests.Session()
        # request to a login page needed to produce csrf token
        resp = sess.get(BASE + '/account')
        soup = BeautifulSoup(resp.content, 'html.parser')
        token = soup.find(id='request_token')['value']
        login_info = {'email': email, 'password': password, 'rememberme': 'off', 'redirect': 'join', 'form_id': 'loginform', 'request_token': token}
        sess.post(BASE + LOGIN, data=login_info)
        yield sess

def get_season_tables_with_players(sess, season, player_ids):
    """ Returns a map with table ids to player ids for arena games.
    """

    tables = defaultdict(list)
    for id in player_ids:
        for table_id in get_arena_tables(sess, id, SEASONS[season][0], SEASONS[season][1]):
            tables[table_id].append(id)
    return tables

def get_player_by_arena_rank(sess, rank, season):
    """ Returns the id for the player with given rank for given arena season.
    """
    # currently broken due ARENA_RANKING request issue
    params = {'start': rank-1, 'game': GAME_ID, 'mode': 'arena', 'season': season}
    resp = sess.get(BASE + ARENA_RANKING, params=params)
    return int(resp.json()['data']['ranks'][0]['id'])

def get_player_by_elo_rank(sess, rank):
    """ Returns the id for the player with given rank by elo.
    """

    params = {'start': rank-1, 'game': GAME_ID, 'mode': 'elo'}
    resp = sess.get(BASE + ELO_RANKING, params=params)
    return int(resp.json()['data']['ranks'][0]['id'])

def get_arena_tables(sess, player_id, start_date, end_date):
    """ Returns the table ids of ranked arena games played between dates for player.
    """

    params = {'page': 0, 'player': player_id, 'game_id': GAME_ID, 'start_date': start_date, 'end_date': end_date, 'finished': 1, 'updateStats': 0}
    table_ids = []
    while True:
        params['page'] += 1
        resp = sess.get(BASE + GAMES, params=params)
        # get ranked arena tables that were not forfeit 
        valid = lambda table: table['arena_win'] != None and table['unranked'] != '1' and int(table['scores'].split(',')[0]) > 1
        ids = [int(table['table_id']) for table in resp.json()['data']['tables'] if valid(table)]
        if len(ids) == 0:
            break
        table_ids.extend(ids)
    return table_ids

def save_table_replays_batch(table_ids):
    """ Saves replay logs for a list of tables. 
        Once an account reaches its replay limit, uses the next session from the generator. 
        Ignores table_ids for which a file already exists.
    """

    generator = session_generator()
    sess = next(generator, None)
    for index, id in enumerate(table_ids):
        fname = 'replays/{}.json'.format(id)
        if not os.path.isfile(fname):
            while sess != None and save_table_replay(sess, id, fname):
                sess = next(generator, None)
        if not sess:
            print("Replays depleted for all logins. There are {} table replays remaining.".format(len(table_ids) - index))
            break
    return sess

def save_table_replay(sess, table_id, file_name):
    """ Saves replay log as json to file.
        Returns true if the current account is unable to access further replays.
    """

    # seemingly required to produce log
    sess.get(BASE + ARCHIVE, params={'table': table_id})
    resp = sess.get(BASE + REPLAY, params={'table': table_id, 'translated': 'true'})
    j = resp.json()
    if 'error' in j:
        if j['error'] == DEPELETED:
            print('Account replay access depleted.')
            return True
        elif j['error'] == NO_ACCESS:
            print('Account cannot access any replays.')
            return True
    
    try:
        moves = j['data']['data']['data']
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(moves, file, ensure_ascii=False)
    except:
        print("Error saving replay for table {}:".format(table_id))
        print(resp.text)
    return False

