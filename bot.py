#!/usr/bin/env python3
from json.decoder import JSONDecodeError
import logging
import logging.handlers
from praw import Reddit
import requests
from sys import argv


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
* player PLAT {{summary, efficiency, activity}} NAME
* player PLAT tanks {{efficiency, top, recent}} NAME
* clan {{summary, active, battles, players, tier, top}} NAME
* community PLAT {{summary, today}}
* community PLAT {{active, inactive, new}} DAYS
* tank {{moe, wn8}} TANK

# Example Usage

`/u/{0} clan summary RDDT`
`/u/{0} player xbox summary DEZERTstorm03`""".format(
        contents[0].split('/')[-1])


def player_info(contents):
    pass


def clan_info(contents):
    CLAN_VALID = {
        'summary': (
            '##Name: {0[Name]}\n\n'
            'This month\'s battles: {0[MonthBattles]}\n\n'
            'Total members: {0[Count]}\n\n'
            'Active members: {0[Active]}\n\n'
            'Percent of players active: {0[ActivePercent]:.3%}\n\n'
            'Total WN8: {0[TotalWn8]}\n\n'
            'Total win rate: {0[TotalWinRate]:.3%}\n\n'
        ),
        'active': (
            '##Name: {0[Name]}\n\nActive member count: {0[Active]}\n\n'
            'Percent of players active: {0[ActivePercent]:.3%}\n\n'
            'This month\'s battles: {0[MonthBattles]}\n\n'
            'Win rate: {0[ActiveWinRate]:.3%}\n\n'
            'WN8: {0[ActiveWn8]}\n\n'
            'Average tier: {0[ActiveAvgTier]}\n\n'
            '{1}\n\n'
        ),
        'battles': (
            '##Name: {0[Name]}\n\n'
            'Total battles: {0[TotalBattles]}\n\n'
            'Total win rate: {0[TotalWinRate]:.3%}\n\n'
            'This month\'s battles: {0[MonthBattles]}\n\n'
            'This month\'s win rate: {0[MonthWinRate]}\n\n'
            'Active player battles: {0[ActiveBattles]}\n\n'
            'Top 15 player battles: {0[Top15Battles]}\n\n'
        ),
        'players': (
            '##Name: {0[Name]}\n\n'
            'Total members: {0[Count]}\n\n'
            'Active members: {0[Active]}\n\n'
            '{1}\n\n'
        ),
        'tiers': (
            '##Name: {0[Name]}\n\n'
            'Total average tier: {0[TotalAvgTier]}\n\n'
            'Active average tier: {0[ActiveAvgTier]}\n\n'
            'Top 15 average tier: {0[Top15AvgTier]}\n\n'
            '{1}\n\n'
        ),
        'top': (
            '##Name: {0[Name]}\n\n'
            '{1}\n\n'
        )
    }
    if contents[2].lower() in CLAN_VALID:
        r = requests.get('https://wotclans.com.br/api/clan/' + contents[3])
        if r.status_code == 200:
            try:
                data = r.json()
                players = []
                if contents[2].lower() == 'active':
                    players = [
                        '{0[Name]} | {0[MonthBattles]}'.format(
                            p) for p in list(
                            filter(
                                lambda p: p['MonthBattles'],
                                data['Players']))]
                    players.insert(0, 'Player | Months\'s battles')
                    players.insert(1, ':-:|:-:')
                elif contents[2].lower() == 'players':
                    players = [
                        '{0[Name]} | {0[TotalWn8]} | {0[MonthWn8]}'.format(
                            p) for p in data['Players']]
                    players.insert(
                        0, 'Player | Total WN8 | Month\'s WN8')
                    players.insert(1, ':-:|:-:|:-:')
                elif contents[2].lower() == 'tiers':
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
                elif contents[2].lower() == 'top':
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
                    CLAN_VALID[contents[2]].format(data, '\n'.join(players)) +
                    'Source: {}'.format(r.url)
                )
            except JSONDecodeError:
                return """Data returned by the website is not in a valid JSON
format. You may manually check this at https://wotclans.com.br/Clan/{}, but I'm
afraid that I cannot properly respond to your request at this time. Sorry!

¯\\\\\\_(ツ)\\_/¯""".format(contents[3])
        else:
            return """There appears to be an error at
https://wotclans.com.br/api/clan/{}. If your clan is not yet added to the site
database, please follow instructions at https://wotclans.com.br/About#addClan
to have it added. Sorry!""".format(
                contents[3])
    else:
        return (
            'Invalid clan command. Please try one of the following: {}'
        ).format(', '.join(CLAN_VALID.keys()))


def community_info(contents):
    pass


def thank_you(contents):
    return """Thank you! I may not be handsome, but I hope you at least find me
handy!

Credit for my development goes to /u/KamikazeRusher. Credit for data goes to
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
            'percentile of players! (Matching this gives a WN8 of 1565)*\n\n'
            'Damage: {0[Damage]}\n\n'
            'Win rate: {0[WinRate]}\n\n'
            'Kill ratio: {0[Frag]}\n\n'
            'Spot ratio: {0[Spot]}\n\n'
            'Defense ratio: {0[Def]}\n\n'
            'Source: {1}'
        )
    }
    # BOT tank {moe, wn8} TANK
    if len(contents) < 4:
        return 'No tank name entered. Please retry!'
    if contents[2].lower() in TANK_VALID:
        r = requests.get(
            'https://wotclans.com.br/api/tanks/{}'.format(
                contents[2].lower()),
            params={'tank': ' '.join(contents[3:])}
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
                'following (assuming it contains what you want):\n\n|Tank|\n'
                '|:-:|\n{}\n\n'
            ).format('\n'.join(
                map(lambda t: '|' + t['Name'] + '|', tanks))
            )
        else:
            return TANK_VALID[contents[2].lower()].format(tanks[0], r.url)
    else:
        return (
            'Invalid tank command. Please try one of the following: {}'
        ).format(', '.join(TANK_VALID.keys()))


VALID = {
    'help': bot_help,
    'player': player_info,
    'clan': clan_info,
    'community': community_info,
    'good': thank_you,
    'tank': tank_info
}


def parse(message):
    contents = message.body.split()
    if contents[1].lower() not in VALID:
        return """Oops! Your first command is not valid. Please review your
spelling and try again. If you continue to have this issue, please
check the wiki over at /r/{} or ask a mod there for help.""".format(
            contents[0].split('/')[-1])
    else:
        return VALID[contents[1].lower()](contents)


def process(message):
    message.reply(parse(message))


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
            process(message)
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
    with open(argv[2]) as f:
        allowed = list(map(lambda s: s.strip().lower(), f.readlines()))
    run(argv[1], allowed)
