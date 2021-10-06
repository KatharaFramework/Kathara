from typing import Tuple, Any

from ...exceptions import ClassNotFoundError
from ...utils import class_for_name


class Factory(object):
    __slots__ = ['module_template', 'name_template']

    def get_module_name(self, args: Tuple) -> str:
        return self.module_template % args

    def get_class_name(self, args: Tuple) -> str:
        return self.name_template % args

    def get_class(self, module_args: Tuple = (), class_args: Tuple = ()) -> Any:
        module_name = self.get_module_name(module_args)
        class_name = self.get_class_name(class_args)

        try:
            return class_for_name(module_name, class_name)
        except ImportError as e:
            if e.name == "%s.%s" % (module_name, class_name):
                raise ClassNotFoundError
            else:
                raise ImportError from e

    def create_instance(self, module_args: Tuple = (), class_args: Tuple = ()) -> Any:
        return self.get_class(module_args, class_args)()
