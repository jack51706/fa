from fa import utils

try:
    import idc
except ImportError:
    pass


def get_parser():
    p = utils.ArgumentParserNoExit('make-code',
                                   description='convert into a code block')
    return p


def make_code(addresses):
    utils.verify_ida()
    for ea in addresses:
        idc.create_insn(ea)
    return addresses


def run(segments, args, addresses, **kwargs):
    return make_code(addresses)