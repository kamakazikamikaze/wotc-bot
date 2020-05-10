#!/usr/bin/env python3
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from configparser import ConfigParser
from itertools import zip_longest
from json import loads
from json.decoder import JSONDecodeError
import logging
import logging.handlers
from operator import itemgetter
from praw import Reddit
from re import findall
from requests import get
# from sys import argv
from urllib.parse import urlsplit, parse_qs
# from wotconsole.session import WOTXSession

_WG_API_KEY_ = 'demo'


def setup_logging():
    logger = logging.getLogger('Bot')
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%m-%d %H:%M:%S')
    fh = logging.handlers.RotatingFileHandler(
        'bot.log',
        maxBytes=256000,
        backupCount=7)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.debug('Logger initialized')


def bot_help(contents):
    return """Hi there! Thank you for choosing to use this bot.

# Valid Platform Names

* ps
* xbox

# Valid Commands

(Note: Replace PLAT with a platform from above)

* help
* player PLAT {{summary, recent, efficiency}} NAME
* player PLAT tanks {{efficiency, top}} NAME
* clan PLAT {{summary, active, battles, players, tier, top}} NAME
* tank PLAT {{moe, wn8}} TANK

# Example Usage

`/u/{0} clan summary RDDT`

`/u/{0} player xbox summary DEZERTstorm03`""".format(
        contents[0].split('/')[-1])


def grouper(n, iterable, fillvalue=None):
    r"""
    Step over an object, returning n-sized chunks

    :param int n: Size of chunks to return
    :param iter iterable: iterable object to step over
    :param fillvalue: Values to use if iterable is not divisible by n
    """
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)


def player_info(contents):
    PLAYER_VALID = {
        'summary': (
            '##Name: {0[Name]}\n\n'
            '|Stat|Career Average|\n'
            ':--|:--\n'
            'Eff|{0[Eff]}\n'
            'WN7|{0[WN7]}\n'
            'WN8|{0[WN8]}\n\n'
        ),
        'recent': (
            '##Name: {0[Name]}\n\n'
            '|Stat|Week|Month|Overall|\n'
            ':--|:--|:--|:--\n'
        ),
        'efficiency': (
            '##Name: {0[Name]}\n\n'
            '|From|To|Efficiency|WN7|WN8|Battles|Wins|\n'
            ':--|:--|:--|:--|:--|:--|:--\n'
        )
    }
    PLAYER_TANK_VALID = {
        'efficiency': (
            '##Name: {0[Name]}\n\n'
            '|Tier|Mastery|Name|Type|Win rate|Wins|Battles|Avg Dmg|'
            'Percent of all battles|Efficiency|WN8|\n'
            ':--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--\n'
        ),
        'top': (
            '##Name: {0[Name]}\n\n'
            '*Note: These tanks are sorted by WN8 and Total battles. This '
            'sorting is arbitrary and may not accurately reflect the '
            'overall performance of the player*\n\n'
            '|Tier|Mastery|Name|Type|Win rate|Wins|Battles|Avg Dmg|'
            'Percent of all battles|Efficiency|WN8|\n'
            ':--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--\n'
        )
    }
    if contents[2] not in ('ps4', 'xbox'):
        return 'Bad platform. Please use "ps4" or "xbox" and try again!'
    if contents[3] == 'tanks' and len(contents) < 5:
        return 'Something is wrong with your request. Please retry!'
    elif contents[3] == 'tanks' and contents[4] not in PLAYER_TANK_VALID:
        return 'Bad subcommand request "{}". Please retry!'.format(contents[4])
    elif len(contents) < 4:
        return 'Something is wrong with your request. Please retry!'
    elif contents[3] != 'tanks' and contents[3] not in PLAYER_VALID:
        return 'Bad subcommand request "{}". Please retry!'.format(contents[3])
    offset = 5 if contents[3] == 'tanks' else 4
    r = get(
        'http://www.wotinfo.net/en/efficiency',
        params={
            'server': contents[2],
            'playername': ' '.join(
                contents[offset:])
        })
    if r.status_code != 200:
        return (
            'I received an error code of {} from the server. Please try again '
            'later!'
        )
    if contents[3] == 'tanks':
        player = {'Name': ' '.join(contents[offset:])}
        soup = BeautifulSoup(r.content, 'html.parser')
        href = soup.find('li', class_='activemenu').a['href']
        try:
            playerid = parse_qs(urlsplit(href).query)['playerid'][0]
        except KeyError:
            return (
                'Sorry, it looks like you either have an invalid player '
                'name or the wrong platform in your request. Please '
                'review your query and try again. If you are still having '
                'issues, please contact my author for assistance!'
            )
        vehicles = get(
            'http://wotinfo.net/en/vehicles',
            params={
                'playerid': playerid,
                'server': contents[2]})
        if vehicles.status_code != 200:
            return (
                'I was able to find this user on wotinfo but I '
                'experienced an error accessing their vehicle statistics. '
                'Tagging /u/KamikazeRusher to review this when he gets '
                'the mention notification.'
            )
        # vehicles_soup = BeautifulSoup(vehicles.content, 'html.parser')
        # source = vehicles_soup.find(
        #     'script',
        #     src='https://www.google.com/jsapi'
        # ).next_sibling.next_sibling
        ranks = {
            'rank_01.png': '1',
            'rank_02.png': '2',
            'rank_03.png': '3',
            'rank_m.png': 'M',
            'FFFFFF-0.png': ''
        }
        # Extract all Google Visualization rows that get added
        rows = []
        for row in findall(
                r'data\.addRow\([^\;]+;', vehicles.content.decode('utf8')):
            # We're cheating here by taking the data entered into the rows and
            # forcing it into a JSON format for easy parsing.
            data = []
            r = loads('{ "data": ' + row[12:-2].replace(
                # Replace the double-quotes with a character not used
                '"', '!').replace(
                # Change the single-quotes to double-quotes
                "'", '"').replace(
                # Change the original double-quotes to single-quotes
                '!', "'").replace(
                # Surround parameters with quotes for JSON validity
                'v:', '"v":').replace(
                'f:', '"f":') + '}')['data']
            # Tier
            data.append(r[0])
            # Mastery
            data.append(ranks[r[1].split("'")[1].split('/')[-1]])
            # Name
            data.append(r[3].split('>')[1][:-3])
            # Type
            data.append(r[5].split("'")[-2].split('/')[-1].split('.')[0])
            # Win rate
            data.append(r[6]['f'])
            # Wins
            data.append(r[7])
            # Battles
            data.append(r[8])
            # Average damage
            data.append(r[9])
            # % of all battles
            data.append(r[10]['f'])
            # Efficiency
            data.append(r[11]['v'])
            # WN8
            data.append(r[12]['v'])
            rows.append(data)
        if contents[4] == 'efficiency':
            return PLAYER_TANK_VALID[
                contents[offset - 1]
            ].format(player) + '\n'.join(
                map(
                    lambda r: '{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}'.format(*r),
                    rows)
            ) + '\n\nSource: {}\n'.format(vehicles.url)
        elif contents[4] == 'top':
            sorted_rows = sorted(rows, key=itemgetter(6, 10), reverse=True)
            return PLAYER_TANK_VALID[
                contents[offset - 1]
            ].format(player) + '\n'.join(
                map(
                    lambda r: '{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}'.format(*r),
                    sorted_rows[:10])
            ) + '\n\nSource: {}\n'.format(vehicles.url)
    else:
        player = {'Name': ' '.join(contents[offset:])}
        soup = BeautifulSoup(r.content, 'html.parser')
        if contents[3] == 'summary':
            var = soup.find_all('var')
            if len(var) != 6:
                return (
                    'I did not receive an expected response, which means '
                    'you may have entered the wrong player name or '
                    'platform by accident. Please review your request and '
                    'try again!'
                )
            else:
                for name, value in grouper(2, var):
                    player[name.text.strip()] = value.text.strip()
                return PLAYER_VALID[
                    contents[offset - 1]
                ].format(player) + '\nSource: {}'.format(r.url)
        elif contents[3] == 'recent':
            href = soup.find('li', class_='activemenu').a['href']
            try:
                playerid = parse_qs(urlsplit(href).query)['playerid'][0]
            except KeyError:
                return (
                    'Sorry, it looks like you either have an invalid player '
                    'name or the wrong platform in your request. Please '
                    'review your query and try again. If you are still having '
                    'issues, please contact my author for assistance!'
                )
            recent = get(
                'http://wotinfo.net/en/recent',
                params={
                    'playerid': playerid,
                    'server': contents[2]})
            if r.status_code != 200:
                return (
                    'I was able to find this user on wotinfo but I '
                    'experienced an error accessing their recent statistics. '
                    'Tagging /u/KamikazeRusher to review this when he gets '
                    'the mention notification.'
                )
            recent_soup = BeautifulSoup(recent.content, 'html.parser')
            # table = recent_soup.find('div', class_='container col-sm-12')
            stats = {'week': [], 'month': [], 'overall': []}
            week_and_month = recent_soup.find_all(
                'div', class_='col-xs-4 col-sm-4 my_plan1')
            overall = recent_soup.find_all(
                'div', class_='col-xs-4 col-sm-4 my_plan2')
            titles = recent_soup.find_all(
                'div', class_='col-xs-12 col-sm-3 my_feature')
            stats['titles'] = [[i.strip() for i in s.strings][0]
                               for s in titles]
            i = 0
            # for period, title in zip_longest(week_and_month, titles):
            for period in week_and_month:
                if i % 2 == 0:
                    stats['week'].append(period.text.split()[0])
                else:
                    stats['month'].append(period.text.split()[0])
                i += 1
            # for period, title in zip(overall, titles):
            for period in overall:
                stats['overall'].append(period.text.split()[0])
            return PLAYER_VALID[
                contents[offset - 1]
            ].format(player) + '\n'.join(
                map(
                    lambda z: '{}|{}|{}|{}'.format(*z),
                    zip(
                        stats['titles'],
                        stats['week'],
                        stats['month'],
                        stats['overall']))
            ) + '\n\nSource: {}\n'.format(recent.url)
        elif contents[3] == 'efficiency':
            href = soup.find('li', class_='activemenu').a['href']
            try:
                playerid = parse_qs(urlsplit(href).query)['playerid'][0]
            except KeyError:
                return (
                    'Sorry, it looks like you either have an invalid player '
                    'name or the wrong platform in your request. Please '
                    'review your query and try again. If you are still having '
                    'issues, please contact my author for assistance!'
                )
            trend = get(
                'http://wotinfo.net/en/trend',
                params={
                    'playerid': playerid,
                    'server': contents[2]})
            if trend.status_code != 200:
                return (
                    'I was able to find this user on wotinfo but I '
                    'experienced an error accessing their efficiency trend. '
                    'Tagging /u/KamikazeRusher to review this when he gets '
                    'the mention notification.'
                )
            trend_soup = BeautifulSoup(trend.content, 'html.parser')
            # data_parent = trend_soup.find('ul', class_='thumbnails')
            # data = data_parent.find_all('div', class_='row')
            data = trend_soup.find_all('ul', class_='event-list')
            all_data = []
            for point in data:
                l = []
                # times = point.li('time')
                # l.append(' '.join(times[0].text.split()[1:]))
                # l.append(' '.join(times[1].text.split()[1:]))
                for time in point.li('time'):
                    l.append(' '.join(time.text.split()[1:]))
                for div in point.find_all('div', class_='progress'):
                    l.append(div.text.strip())
                i = 0
                for li in point.li.div.ul.find_all('li'):
                    if i < 2:
                        l.append(li.text.split()[0])
                    i += 1
                all_data.append(l)
            return PLAYER_VALID[contents[
                offset - 1]
            ].format(player) + '\n'.join(
                map(lambda l: '{}|{}|{}|{}|{}|{}|{}'.format(*l), all_data)
            ) + '\n\nSource: {}\n'.format(trend.url)


def clan_info(contents):
    CLAN_VALID = {
        'summary': (
            '##Name: {0[Name]}\n\n'
            '|||\n'
            ':--|:--\n'
            'This month\'s battles|{0[MonthBattles]}\n'
            'Total members|{0[Count]}\n'
            'Active members|{0[Active]}\n'
            'Percent of players active|{0[ActivePercent]:.3%}\n'
            'Total WN8|{0[TotalWn8]}\n'
            'Total win rate|{0[TotalWinRate]:.3%}\n\n'
        ),
        'active': (
            '##Name: {0[Name]}\n\n'
            '|||\n'
            ':--|:--\n'
            'Active member count|{0[Active]}\n'
            'Percent of players active|{0[ActivePercent]:.3%}\n'
            'This month\'s battles|{0[MonthBattles]}\n'
            'Win rate|{0[ActiveWinRate]:.3%}\n'
            'WN8|{0[ActiveWn8]}\n'
            'Average tier|{0[ActiveAvgTier]}\n\n'
            '###Active players\n\n'
            '{1}\n\n'
        ),
        'battles': (
            '##Name: {0[Name]}\n\n'
            '|||\n'
            ':--|:--\n'
            'Total battles|{0[TotalBattles]}\n'
            'Total win rate|{0[TotalWinRate]:.3%}\n'
            'This month\'s battles|{0[MonthBattles]}\n'
            'This month\'s win rate|{0[MonthWinRate]}\n'
            'Active player battles|{0[ActiveBattles]}\n'
            'Top 15 player battles|{0[Top15Battles]}\n\n'
        ),
        'players': (
            '##Name: {0[Name]}\n\n'
            '|||\n'
            ':--|:--\n'
            'Total members|{0[Count]}\n'
            'Active members|{0[Active]}\n\n'
            '###All clan members\n\n'
            '{1}\n\n'
        ),
        'tiers': (
            '##Name: {0[Name]}\n\n'
            '|||\n'
            ':--|:--\n'
            'Total average tier|{0[TotalAvgTier]}\n'
            'Active average tier|{0[ActiveAvgTier]}\n'
            'Top 15 average tier|{0[Top15AvgTier]}\n\n'
            '{1}\n\n'
        ),
        'top': (
            '##Name: {0[Name]}\n\n'
            '{1}\n\n'
        )
    }
    if contents[2] not in ('ps', 'xbox'):
        return 'Bad platform. Please use "ps" or "xbox"'
    if contents[2] == 'ps':
        url = 'https://ps.wotclans.com.br/api/clan/'
    else:
        url = 'https://wotclans.com.br/api/clan/'
    if len(contents) < 5:
        return 'No clan name entered. Please retry!'
    if contents[3] in CLAN_VALID:
        r = get(url + contents[4])
        if r.status_code == 200:
            try:
                data = r.json()
                players = []
                if contents[3] == 'active':
                    players = [
                        '{0[Name]} | {0[MonthBattles]}'.format(
                            p) for p in list(
                            filter(
                                lambda p: p['MonthBattles'],
                                data['Players']))]
                    players.insert(0, 'Player | Months\'s battles')
                    players.insert(1, ':-:|:-:')
                elif contents[3] == 'players':
                    players = [
                        '{0[Name]} | {0[TotalWn8]} | {0[MonthWn8]}'.format(
                            p) for p in data['Players']]
                    players.insert(
                        0, 'Player | Total WN8 | Month\'s WN8')
                    players.insert(1, ':-:|:-:|:-:')
                elif contents[3] == 'tiers':
                    players = [
                        '{0[Name]} | {0[TotalTier]} | {0[MonthTier]}'.format(
                            p) for p in data['Players']]
                    players.insert(
                        0,
                        (
                            'Player | Lifetime tier average | '
                            'Month\'s tier average'
                        ))
                    players.insert(1, ':-:|:-:|:-:')
                elif contents[3] == 'top':
                    top_all = sorted(
                        data['Players'],
                        key=lambda p: p['TotalWn8'],
                        reverse=True)[0:7]
                    top_rec = sorted(
                        data['Players'],
                        key=lambda p: p['MonthWn8'],
                        reverse=True)[0:7]
                    players = [
                        '{0[Name]} | {0[MonthWn8]}'.format(p) for p in top_rec]
                    players.insert(0, '###Top 7 active players\n')
                    players.insert(1, 'Player | Month\'s WN8')
                    players.insert(2, ':-:|:-:')
                    players += ['\n', '###Top 7 players overall\n',
                                'Player | Lifetime WN8', ':-:|:-:']
                    players += ['{0[Name]} | {0[TotalWn8]}'.format(p)
                                for p in top_all]
                return (
                    CLAN_VALID[contents[3]].format(data, '\n'.join(players)) +
                    'Source: {}'.format(r.url)
                )
            except JSONDecodeError:
                return """Data returned by the website is not in a valid JSON
format. You may manually check this at https://wotclans.com.br/Clan/{}, but I'm
afraid that I cannot properly respond to your request at this time. Sorry!

¯\\\\\\_(ツ)\\_/¯""".format(contents[4])
        else:
            return """There appears to be an error at
https://wotclans.com.br/api/clan/{}. If your clan is not yet added to the site
database, please follow instructions at https://wotclans.com.br/About#addClan
to have it added. Sorry!""".format(
                contents[4])
    else:
        return (
            'Invalid clan command. Please try one of the following: {}'
        ).format(', '.join(CLAN_VALID.keys()))


def thank_you(contents):
    return """Thank you! I may not be handsome, but I hope you at least find me
handy!

Credit for my development goes to
[KamikazeRusher](https://reddit.com/u/KamikazeRusher). Credit for data goes to
the author of the cited source(s)."""


def tank_info(contents):
    TANK_VALID = {
        'moe': (
            '##Name: {0[Name]}\n\n'
            '{0[TypeName]} tier {0[Tier]} tank ({0[NatioName]})\n\n'
            'Mark | Average Damage\n'
            ':-:|:-:\n'
            '1|{0[Moe1Dmg]}\n'
            '2|{0[Moe2Dmg]}\n'
            '3|{0[Moe3Dmg]}\n\n'
            'Source: {1}'
        ),
        'wn8': (
            '##Name: {0[Name]}\n\n'
            '{0[TypeName]} tier {0[Tier]} tank ({0[NatioName]})\n\n'
            '*Note: These are the Expected Values, which reflect the 65^th '
            'percentile of players! (Matching these gives a WN8 of 1565)*\n\n'
            '|||\n'
            ':--|:--\n'
            'Damage|{0[Damage]}\n'
            'Win rate|{0[WinRate]}\n'
            'Kill ratio|{0[Frag]}\n'
            'Spot ratio|{0[Spot]}\n'
            'Defense ratio|{0[Def]}\n\n'
            'Source: {1}'
        )
    }
    # BOT tank PLAT {moe, wn8} TANK
    if contents[2] not in ('ps', 'xbox'):
        return 'Bad platform. Please use "ps" or "xbox"'
    if contents[2] == 'ps':
        url = 'https://ps.wotclans.com.br/api/tanks/{}'
    else:
        url = 'https://wotclans.com.br/api/tanks/{}'
    if len(contents) < 5:
        return 'No tank name entered. Please retry!'
    if contents[3] in TANK_VALID:
        r = get(
            url.format(contents[3]),
            params={'tank': ' '.join(contents[4:])}
        )
        if r.status_code != 200:
            return (
                'The API does not appear to accept your tank. Perhaps you '
                'misspelled?'
            )
        tanks = r.json()['Tanks']
        if len(tanks) < 1:
            return (
                'The API does not appear to accept your tank. Perhaps you '
                'misspelled?'
            )
        elif len(tanks) > 1:
            return (
                'Multiple tanks were returned for that name. This means there '
                'is not an exact match. You can retry with one of the '
                'following (assuming it contains what you want):\n\n'
                '|Tank|\n'
                '|:-:|\n{}\n\n'
            ).format('\n'.join(
                map(lambda t: '|' + t['Name'] + '|', tanks))
            )
        else:
            return TANK_VALID[contents[3]].format(tanks[0], r.url)
    else:
        return (
            'Invalid tank command. Please try one of the following: {}'
        ).format(', '.join(TANK_VALID.keys()))


# def tank_cost(contents):
#     session = WOTXSession(_WG_API_KEY_)
#     vehicle_info = session.vehicle_info(
#         fields=['name', 'price_credit', 'price_gold'])


def parse(message):
    VALID = {
        'help': bot_help,
        'player': player_info,
        'clan': clan_info,
        'tank': tank_info,
        # 'cost': tank_cost
    }
    RESPONSES = {
        'good': thank_you,
    }
    contents = message.body.lower().split()
    if len(contents) == 1:
        return VALID['help'](contents)
    if '/' not in contents[0]:
        if contents[0] in RESPONSES:
            return RESPONSES[contents[0]](contents)
        else:
            return None
    elif contents[1] not in VALID:
        return """Oops! Your first command is not valid. Please review your
spelling and try again. If you continue to have this issue, please
check the wiki over at /r/{} or ask a mod there for help.""".format(
            contents[0].split('/')[-1])
    else:
        return VALID[contents[1]](contents)


def process(message, reddit):
    response = parse(message)
    if response is None:
        pass
    elif len(response) <= 10000:
        message.reply(response)
    else:
        sub = reddit.subreddit(reddit.config.username)
        submission = sub.submit(
            'Response to ' + str(message.author),
            response,
            send_replies=False)
        message.reply((
            "I'm sorry, it appears my response is greater than the maximum "
            "allowed comment length. (Max: 10000, Mine: {}). I have created a "
            "self-post at {}"
        ).format(len(response), submission.url))


def run(bot_name, subreddits):
    setup_logging()
    logger = logging.getLogger('Bot')
    reddit = Reddit(bot_name)
    for message in reddit.inbox.unread(limit=None):
        if message.subreddit is None:
            logger.warning(
                'Recevied direct message from {0.author}'.format(message))
            # We don't respond to direct messages
            message.mark_read()
        elif message.subreddit.display_name.lower() in subreddits:
            process(message, reddit)
            message.mark_read()
            logger.debug('Completed message {0.id}'.format(message))
        else:
            logger.warning(
                ('Message from {0.author} is from subreddit {0.subreddit} '
                 'which is outside of our scope'
                 ).format(message))
            # We'll instead ignore any mentions outside of scope
            message.mark_read()

if __name__ == '__main__':
    # with open(argv[2]) as f:
    #     allowed = list(map(lambda s: s.strip().lower(), f.readlines()))
    # run(argv[1], allowed)
    argparse = ArgumentParser(description='World of Tanks Console Reddit Bot')
    argparse.add_argument('filename', help='Name of configuration file')
    argparse.add_argument(
        '-g',
        '--generate',
        action='store_true',
        help='Generate a configuration file with default values')
    args = argparse.parse_args()
    config = ConfigParser()
    if args.generate:
        config['DEFAULT'] = {
            'Bot Name': 'wotc_bot',
            'Subreddits': 'worldoftanksconsole,wotc_bot',
            'WG API': 'demo'
        }
        with open(args.filename, 'w') as f:
            config.write(f)
    else:
        config.read(args.filename)
        try:
            _WG_API_KEY_ = config['DEFAULT']['WG API']
            run(config['DEFAULT']['Bot Name'],
                config['DEFAULT']['Subreddits'].split(','))
        except KeyError as e:
            print('You are missing this key value:', e.args[0])
