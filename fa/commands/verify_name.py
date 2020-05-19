from fa.commands import utils
from fa.commands.locate import locate

try:
    import idc
except ImportError:
    pass


def get_parser():
    p = utils.ArgumentParserNoExit('verify-name', description='verifies the given name appears in result set')
    p.add_argument('name')
    return p


@utils.yield_unique
def verify_name(addresses, name):
    ref = locate(name)
    for address in addresses:
        if ref == address:
            yield address


def run(segments, args, addresses, **kwargs):
    utils.verify_ida()
    return list(verify_name(addresses, args.name))
