import binascii

from fa.commands import find_bytes


def get_parser():
    p = find_bytes.get_parser()
    p.prog = 'find-str'
    p.description = 'expands the search results by the given string'
    p.add_argument('--null-terminated', action='store_true')
    return p


def find_str(string, null_terminated=False):
    hex_str = binascii.hexlify(string)
    if null_terminated:
        hex_str += '00'
    return find_bytes.find_bytes(hex_str)


def run(segments, args, addresses, interpreter=None, **kwargs):
    hex_str = binascii.hexlify(args.hex_str)
    if args.null_terminated:
        hex_str += '00'
    setattr(args, 'hex_str', hex_str)
    return find_bytes.run(segments, args, addresses, **kwargs)
