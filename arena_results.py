import json
from collections import namedtuple
import pandas as pd

def parse_game_result(file_path):
    """ Returns map from player id to traveler, position, score, and rank for each player from a stored table replay,
        if the file exists.
    """

    outcomes = {}
    try:
        with open(file_path) as file:
            replay = json.load(file)
            start_infos = {}
            for move in replay:
                if not start_infos:
                    for data in move['data']:
                        if data['type'] == 'travelerChosen':
                            start_infos[data['args']['player_id']] = data['args']

            last_move = next(move['data'] for move in reversed(replay) if move["move_id"] != None)
            results = last_move[len(last_move) - 2]['args']['args']['result']
            ranks = [res['rank'] for res in results]

            for index in range(len(results)):
                placement = (sum(1 if ranks[index] < r else 0.5 if ranks[index] == r else 0 for r in ranks) - 0.5)
                score = int(results[index]['score'])
                achievements = int(results[index]['score_aux'])
                id = int(results[index]['player'])
                outcomes[id] = start_infos[id]['traveler'], int(start_infos[id]['player_position_order']), placement, score, achievements

            return outcomes

    except FileNotFoundError:
        print('File {} does not exist.'.format(file_path))

def summary_data(df):
    return len(df.index), df['placement'].mean(), df['placement'].std(), df['points'].mean(), df['points'].std(), df['achievements'].mean()

def create_results_summary(tables):

    Result = namedtuple('Result', ['table_id', 'traveler', 'position', 'placement', 'points', 'achievements'])
    results = []
    for table_id, players in tables.items():
        outcomes = parse_game_result('s5-arena/replays/{}.json'.format(table_id))
        if outcomes:
            results.extend([Result(table_id, res[0], res[1], res[2], res[3], res[4]) for id, res in outcomes.items() if id in players])
    data = pd.DataFrame(results)
    data.to_csv('s5-arena/results.csv')

    rows = {}
    rows['all'] = summary_data(data)
    for trvl in data["traveler"].unique():
        rows[trvl] = summary_data(data.loc[data['traveler'] == trvl])
    for pos in range(1, 5):
        rows[str(pos)] = summary_data(data.loc[data['position'] == pos])
    
    summary = pd.DataFrame.from_dict(rows, orient='index', columns=['count', 'placement avg', 'placement std', 'points avg', 'points std', 'achievements avg'])
    summary.insert(0, 'frequency', summary['count'] / len(data))
    summary.to_csv("s5-arena/summary.csv")
