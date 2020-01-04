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

#Valid Platform Names

* ps
* xbox

#Valid Commands

(Note: Replace PLAT with a platform from above)

* help
* player PLAT {{summary, efficiency, activity}} NAME
* player PLAT tanks {{efficiency, top, recent}} NAME
* clan {{summary, active, battles, players, tier, top}} NAME
* community PLAT {{summary, today}}
* community PLAT {{active, inactive, new}} DAYS

#Example Usage

`/u/{0} clan summary RDDT`
`/u/{0} player xbox summary DEZERTstorm03""".format(contents[0].split('/')[-1])


def player_info(contents):
    pass


def clan_info(contents):
    CLAN_VALID = {
        'summary': (
            'Name: {0[Name]}\n\nThis month\'s battles: {0[MonthBattles]}\n\n'
            'Total members: {0[Count]}\n\nActive members: {0[Active]}\n\n'
            'Total WN8: {0[TotalWn8]}\n\nTotal Win Rate: {0[TotalWinRate]:.3%}'
            '\n\n'
        ),
        'active': '',
        'battles': '',
        'players': '',
        'tiers': '',
        'top': ''
    }
    if contents[2] in CLAN_VALID.keys():
        r = requests.get('https://wotclans.com.br/api/clan/' + contents[3])
        if r.status_code == 200:
            try:
                data = r.json()
                return (CLAN_VALID[contents[2]].format(data) +
                        'https://wotclans.com.br/Clan/{}'.format(contents[3]))
            except JSONDecodeError:
                return """It appears that you have entered either an invalid
clan tag or one that is not yet being tracked by the website. Please manually
check this at https://wotclans.com.br/Clan/{}""".format(contents[3])
        else:
            return """There appears to be an error at
https://wotclans.com.br/api/clan/{}. Sorry! ¯\\\\\\_(ツ)\\_/¯.""".format(
                contents[3])


def community_info(contents):
    pass


VALID = {
    'help': bot_help,
    'player': player_info,
    'clan': clan_info,
    'community': community_info
}


def parse(message):
    contents = message.body.split()
    if contents[1] not in VALID.keys():
        return """Oops! Your first command is not valid. Please review your
spelling and try again. If you continue to have this issue, please
check the wiki over at /r/{} or ask a mod there for help.""".format(
            contents[0].split('/')[-1])
    else:
        return VALID[contents[1]](contents)


def process(message):
    message.reply(parse(message))


def run(bot_name, subreddit):
    setup_logging()
    logger = logging.getLogger('Bot')
    reddit = Reddit(bot_name)
    for message in reddit.inbox.unread(limit=None):
        if message.subreddit is None:
            logger.warning(
                'Recevied direct message from {0.author}'.format(message))
            # We don't respond to direct messages
            message.mark_read()
        elif message.subreddit.display_name.lower() == subreddit.lower():
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
    run(argv[1], argv[2])
