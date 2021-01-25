# ===============
# === Imports ===
# ===============

import typing
from datetime import datetime
from typing import List, Tuple

from ytmusicapi import YTMusic

# ================================
# === Note to readers / Coders ===
# ================================

# ! YTM search (the actual POST request), courtesy of Elliot G. (@rocketinventor)
# ! result parsing and song matching system by @Mikhail-Zex
# !
# ! Essentially, Without Elliot, you wouldn't have a YTM search provider at all.

# ! YTMusic api client
ytmApiClient = YTMusic()


# ========================================================================
# === Background functions/Variables (Not meant to be called directly) ===
# ========================================================================


def __parse_duration(duration: str) -> float:
    if len(duration) > 5:
        time_obj = datetime.strptime(duration, '%H:%M:%S') - datetime(1900, 1, 1)
    else:
        time_obj = datetime.strptime(duration, '%M:%S') - datetime(1900, 1, 1)
    
    seconds = time_obj.total_seconds()

    return seconds


def __map_result_to_song_data(result: dict) -> dict:
    song_data = {
        'link': f'https://youtube.com/watch?v={result.get("videoId")}',
        'type': result['resultType'],
        'length': __parse_duration(result.get('duration', '0:0'))
    }

    return song_data


def __query_and_simplify(searchTerm: str) -> List[dict]:
    '''
    `str` `searchTerm` : the search term you would type into YTM's search bar

    RETURNS `list<dict>`

    For structure of dict, see comment at function declaration
    '''

    print(f'Searching For {searchTerm}')
    searchResults = ytmApiClient.search(searchTerm)

    return list(map(__map_result_to_song_data, searchResults))


# =======================
# === Search Provider ===
# =======================

def search_and_order_ytm_results(songName: str, songArtists: List[str],
                                 songDuration: float) -> List[Tuple[float, str]]:
    '''
    `str` `songName` : name of song

    `list<str>` `songArtists` : list containing name of contributing artists

    `int` `songDuration`

    RETURNS `dict`

    each entry in the result if formated as ($time_diffferece, $yt_link)
    '''

    # Query YTM
    searchTerm = f'{songName} - {", ".join(songArtists)}'
    results = __query_and_simplify(searchTerm)

    song_results = []
    video_results = []

    for result in results:
        # calculate the time difference between the search result and provided song
        time_diff = abs(result['length'] - songDuration)
        
        if result['type'] == 'song':
            song_results.append((time_diff, result['link']))
        else:
            video_results.append((time_diff, result['link']))
    

    #! Prefer Song Results over Video Results
    found_results =  sorted(song_results, key=lambda x: x[0]) + sorted(video_results, key=lambda x: x[0])

    return found_results

def search_and_get_best_match(songName: str, songArtists: List[str],
                              songDuration: float) -> typing.Optional[str]:
    '''
    `str` `songName` : name of song

    `list<str>` `songArtists` : list containing name of contributing artists

    `int` `songDuration` : duration of the song

    RETURNS `str` : link of the best match
    '''

    results = search_and_order_ytm_results(
        songName, songArtists,
        songDuration
    )

    if len(results) == 0:
        return None

    return results[0][1]
