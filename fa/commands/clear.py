from fa import utils


def get_parser():
    p = utils.ArgumentParserNoExit('clear',
                                   description='clears the current '
                                               'search results')
    return p


def run(segments, args, addresses, interpreter=None, **kwargs):
    return []
