# coding=utf-8

import json
import types


class Data(object):
    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def from_json(self, s):
        d = json.loads(s)
        if isinstance(d, types.DictType):
            self.__dict__.update(d)

    def to_dict(self):
        return self.del_none(self._to_dict(self.__dict__))

    def _to_dict(self, obj):
        if isinstance(obj, Data):
            return obj.to_dict()
        elif isinstance(obj, types.TupleType):
            return [self._to_dict(o) for o in obj]
        elif isinstance(obj, types.ListType):
            return [self._to_dict(o) for o in obj]
        elif isinstance(obj, types.DictType):
            return {key: self._to_dict(obj[key]) for key in obj}
        else:
            return obj

    def del_none(self, d):
        """
        Delete keys with the value ``None`` in a dictionary, recursively.
        
        This alters the input so you may wish to ``copy`` the dict first.
        """
        for key, value in d.items():
            if value is None:
                del d[key]
            elif isinstance(value, dict):
                self.del_none(value)

        return d

    def from_dict(self, d):
        self.__dict__.update(d)
