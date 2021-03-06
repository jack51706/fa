from fa import utils


def get_parser():
    p = utils.ArgumentParserNoExit('add-offset-range',
                                   description='adds a python-range of '
                                               'offsets, to the current '
                                               'search results')
    p.add_argument('start', type=int)
    p.add_argument('end', type=int)
    p.add_argument('step', type=int)
    return p


@utils.yield_unique
def add_offset_range(addresses, start, end, step):
    for ea in addresses:
        for i in range(start, end, step):
            yield ea + i


def run(segments, args, addresses, interpreter=None, **kwargs):
    gen = add_offset_range(addresses, args.start, args.end, args.step)
    return list(gen)
