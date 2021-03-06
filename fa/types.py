from abc import abstractmethod
from collections import namedtuple


try:
    import idc
    import idaapi
    import ida_auto
    import ida_enum
    import ida_struct

    IDA_MODULE = True
except ImportError:
    pass


class FaType(object):
    def __init__(self, name):
        self._name = name

    def get_name(self):
        return self._name

    def exists(self):
        return -1 != ida_struct.get_struc_id(self._name)

    @abstractmethod
    def update_idb(self):
        pass


class FaEnum(FaType):
    def __init__(self, name):
        super(FaEnum, self).__init__(name)
        self._values = {}

    def add_value(self, name, value):
        self._values[value] = name

    def update_idb(self):
        id = ida_enum.get_enum(self._name)
        if idc.BADADDR == id:
            id = ida_enum.add_enum(idc.BADADDR, self._name, idaapi.decflag())

        keys = self._values.keys()
        keys.sort()

        for k in keys:
            ida_enum.add_enum_member(id, self._values[k], k)


class FaStruct(FaType):
    Field = namedtuple('Field', ['name', 'type', 'size'])

    def __init__(self, name):
        super(FaStruct, self).__init__(name)
        self._fields = []
        self._size = 0

    def add_field(self, name, type_, size=0, offset=0):
        if (offset != 0) and (offset != self._size):
            self.add_field('padd_{:x}'.format(self._size),
                           'unsigned char[{}]'.format(offset - self._size),
                           offset - self._size)

        self._fields.append(self.Field(name, type_, size))
        self._size += size

    def update_idb(self):
        sid = ida_struct.get_struc_id(self._name)
        if sid != -1:
            sptr = ida_struct.get_struc(sid)
            ida_struct.del_struc(sptr)

        sid = ida_struct.add_struc(idc.BADADDR, self._name, 0)
        sptr = ida_struct.get_struc(sid)

        for f in self._fields:
            ida_struct.add_struc_member(sptr, f.name, idc.BADADDR,
                                        (idc.FF_BYTE | idc.FF_DATA)
                                        & 0xFFFFFFFF,
                                        None, 1)
            member_name = "{}.{}".format(self._name, f.name)
            idc.SetType(idaapi.get_member_by_fullname(member_name)[0].id,
                        f.type)

        ida_auto.auto_wait()


def add_const(name, value):
    fa_consts = FaEnum('FA_CONSTS')
    fa_consts.add_value(name, value)
    fa_consts.update_idb()
