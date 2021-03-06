from tkinter import ttk, Tk
from configparser import ConfigParser

from abc import ABCMeta, abstractmethod
from collections import OrderedDict
import shlex
import sys
import os

import hjson

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.ini')
DEFAULT_SIGNATURES_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'signatures')
COMMANDS_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'commands')

MULTILINE_PREFIX = '    '


class FaInterp:
    __metaclass__ = ABCMeta

    def __init__(self, config_path=CONFIG_PATH):
        self._project = 'generic'
        self._input = None
        self._segments = OrderedDict()
        self._signatures_root = DEFAULT_SIGNATURES_ROOT
        self.history = []
        self.checkpoints = {}
        self.endianity = '<'

        if (config_path is not None) and (os.path.exists(config_path)):
            config = ConfigParser()
            config.read_file(open(config_path))
            self._signatures_root = os.path.expanduser(
                config.get('global', 'signatures_root'))

    @abstractmethod
    def set_input(self, input_):
        pass

    def set_signatures_root(self, path):
        self._signatures_root = path

    def set_project(self, project):
        self._project = project
        self.log('project set: {}'.format(project))

    def symbols(self, output_file_path=None):
        results = {}
        results.update(self.get_python_symbols())
        for sig in self.get_json_signatures():
            sig_results = self.find(sig['name'], decremental=True)

            if len(sig_results) > 0:
                if sig['name'] not in results.keys():
                    results[sig['name']] = set()

                results[sig['name']].update(sig_results)

        errors = ''
        for k, v in results.items():
            if isinstance(v, list) or isinstance(v, set):
                if len(v) != 1:
                    errors += '# {} had too many results\n'.format(k)
                    continue

        print(errors)
        return results

    def interactive_set_project(self):
        app = Tk()
        # app.geometry('200x30')

        label = ttk.Label(app,
                          text="Choose current project")
        label.grid(column=0, row=0)

        combo = ttk.Combobox(app,
                             values=self.list_projects())
        combo.grid(column=0, row=1)

        def combobox_change_project(event):
            self.set_project(combo.get())

        combo.bind("<<ComboboxSelected>>", combobox_change_project)

        app.mainloop()

    def list_projects(self):
        projects = []
        for root, dirs, files in os.walk(self._signatures_root):
            projects += \
                [os.path.relpath(os.path.join(root, filename),
                                 self._signatures_root) for filename in dirs]
        return [p for p in projects if p[0] != '.']

    @staticmethod
    def log(message):
        for line in message.splitlines():
            print('FA> {}'.format(line))

    @abstractmethod
    def reload_segments(self):
        pass

    @staticmethod
    def get_module(name, filename):
        if not os.path.exists(filename):
            raise NotImplementedError("no such filename: {}".format(filename))

        if sys.version == '3':
            # TODO: support python 3.0-3.4
            import importlib.util
            spec = importlib.util.spec_from_file_location(name, filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            import imp
            module = imp.load_source(name, filename)

        return module

    @staticmethod
    def get_command(command):
        filename = os.path.join(COMMANDS_ROOT, "{}.py".format(command))
        return FaInterp.get_module(command, filename)

    def run_command(self, command, addresses):
        args = ''
        if ' ' in command:
            command, args = command.split(' ', 1)
            args = shlex.split(args)

        command = command.replace('-', '_')

        module = self.get_command(command)
        p = module.get_parser()
        args = p.parse_args(args)
        return module.run(self._segments, args, addresses,
                          interpreter=self)

    def get_alias(self):
        retval = {}
        with open(os.path.join(COMMANDS_ROOT, 'alias')) as f:
            for line in f.readlines():
                line = line.strip()
                k, v = line.split('=')
                retval[k.strip()] = v.strip()

        # include also project alias
        project_root = os.path.join(self._signatures_root, self._project)
        project_alias_filename = os.path.join(project_root, 'alias')
        if os.path.exists(project_alias_filename):
            with open(project_alias_filename) as f:
                for line in f.readlines():
                    line = line.strip()
                    k, v = line.split('=')
                    retval[k.strip()] = v.strip()

        return retval

    def save_signature(self, signature):
        filename = os.path.join(
            self._signatures_root,
            self._project,
            signature['name'] + '.sig')
        i = 1
        while os.path.exists(filename):
            filename = os.path.join(self._signatures_root, self._project,
                                    signature['name'] + '.{}.sig'.format(i))
            i += 1

        with open(filename, 'w') as f:
            hjson.dump(signature, f, indent=4)

    def find_from_instructions_list(self, instructions,
                                    decremental=False, addresses=None):
        if addresses is None:
            addresses = []

        self.history = []
        self.checkpoints = {}

        for line in instructions:
            line = line.strip()

            if len(line) == 0:
                continue

            if line.startswith('#'):
                # treat as comment
                continue

            if line == 'stop-if-empty':
                if len(addresses) == 0:
                    return addresses
                else:
                    continue

            # normal commands

            for k, v in self.get_alias().items():
                # handle aliases
                if line.startswith(k):
                    line = line.replace(k, v)

            new_addresses = []
            try:
                new_addresses = self.run_command(line, addresses)
            except ImportError as m:
                FaInterp.log('failed to run: {}. error: {}'
                             .format(line, str(m)))

            if decremental and len(new_addresses) == 0 and len(addresses) > 0:
                return addresses

            addresses = new_addresses
            self.history.append(addresses)

        return addresses

    def find_from_sig_json(self, signature_json, decremental=False):
        """
        Find a signature from a signature JSON data.
        :param dict signature_json: Data of signature's JSON.
        :param bool decremental:
        :return: Addresses of matching signatures.
        :rtype: result list of last returns instruction
        """
        return self.find_from_instructions_list(
            signature_json['instructions'], decremental)

    def find_from_sig_path(self, signature_path, decremental=False):
        """
        Find a signature from a signature file path.
        :param str signature_path: Path to a signature file.
        :param bool decremental:
        :return: Addresses of matching signatures.
        :rtype: result list of last returns instruction
        """
        local_path = os.path.join(
            self._signatures_root, self._project, signature_path)
        if os.path.exists(local_path):
            # prefer local signatures, then external
            signature_path = local_path

        with open(signature_path) as f:
            sig = hjson.load(f)
        return self.find_from_sig_json(sig, decremental)

    def get_python_symbols(self, file_name=None):
        symbols = {}
        project_root = os.path.join(self._signatures_root, self._project)
        sys.path.append(project_root)

        for root, dirs, files in os.walk(project_root):
            for filename in files:
                if not filename.lower().endswith('.py'):
                    continue

                if not file_name or file_name == filename:
                    name = os.path.splitext(filename)[0]
                    filename = os.path.join(project_root, filename)
                    m = FaInterp.get_module(name, filename)
                    symbols.update(m.run(interpreter=self))

        return symbols

    def get_json_signatures(self, symbol_name=None):
        signatures = []
        project_root = os.path.join(self._signatures_root, self._project)

        for root, dirs, files in os.walk(project_root):
            for filename in files:
                if not filename.lower().endswith('.sig'):
                    continue

                filename = os.path.join(project_root, filename)
                with open(filename) as f:
                    try:
                        signature = hjson.load(f)
                    except ValueError as e:
                        self.log('error in json: {}'.format(filename))
                        raise e

                if (symbol_name is None) or (signature['name'] == symbol_name):
                    signatures.append(signature)

        return signatures

    def find(self, symbol_name, decremental=False):
        results = []
        signatures = self.get_json_signatures(symbol_name)
        if len(signatures) == 0:
            raise NotImplementedError('no signature found for: {}'
                                      .format(symbol_name))

        for sig in signatures:
            sig_results = self.find_from_sig_json(sig)

            if isinstance(sig_results, dict):
                if symbol_name in sig_results:
                    results += sig_results[symbol_name]
            else:
                results += sig_results

        return list(set(results))
