from fa.commands import utils

try:
    import idc
except ImportError:
    pass


def get_parser():
    p = utils.ArgumentParserNoExit()
    p.add_argument('name')
    return p


def locate(name):
    return idc.LocByName(name)


def run(segments, args, addresses, **kwargs):
    utils.verify_ida()
    return locate(args.name)
