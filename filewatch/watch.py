import fnmatch
import glob
import logging
import os
import time


class FileInfo:
    def __init__(self, inode, initial):
        self.inode = inode
        self.initial = initial
        self.size = 0
        self.create_sent = False


class Watch(object):

    create_initial = 'create_initial'
    create = 'create'
    modify = 'modify'
    delete = 'delete'

    def __init__(self, opts=None):
        if opts is None:
            opts = {}

        if opts.get('logger'):
            self.logger = opts['logger']
        else:
            self.logger = logging.getLogger('filewatch.Watch')

        self._watching = set()
        self._exclude = set()
        self._files = {}

    def get_logger(self):
        return self._logger
    
    def set_logger(self, logger):
        self._logger = logger
    
    logger = property(get_logger, set_logger)

    def exclude(self, path):
        '''exclude either a path or list of paths'''
        if isinstance(path, basestring):
            self._exclude.add(path)
        else:
            for p in path:
                self._exclude.add(p)

    def watch(self, path):
        if path not in self._watching:
            self._watching.add(path)
            self._discover_file(path, True)
        return True

    def each(self, func):
        for path, info in self._files.items():
            if not info.create_sent:
                if info.initial:
                    func(Watch.create_initial, path)
                else:
                    func(Watch.create, path)
                info.create_sent = True

        for path, info in self._files.items():
            try:
                stat = os.stat(path)
            except OSError, e:
                if e.errno == os.errno.ENOENT:
                    del self._files[path]
                    self.logger.debug(
                        "%s: stat failed (%s), deleting from @files", path, e)
                    func(Watch.delete, path)
                    continue

            inode = [stat.st_ino, stat.st_dev]
            if inode != info.inode:
                self.logger.debug(
                    "%s: old inode was %s, new is %s", path, info.inode, inode)
                func(Watch.delete, path)
                func(Watch.create, path)
            elif stat.st_size < info.size:
                self.logger.debug(
                    "%s: file rolled, new size is %s, old size %s", path,
                    stat.st_size, info.size)
                func(Watch.delete, path)
                func(Watch.create, path)
            elif stat.st_size > info.size:
                self.logger.debug("%s: file grew, old size %s, new size %s",
                                  path, info.size, stat.st_size)
                func(Watch.modify, path)

            info.size = stat.st_size
            info.inode = inode

    def discover(self):
        for path in self._watching:
            self._discover_file(path)

    def subscribe(self, func, stat_interval = 1, discover_interval = 5):
        count = 0
        self.quit = False
        while not self.quit:
            self.each(func)
            count += 1
            if count == discover_interval:
                self.discover()
                count = 0

            time.sleep(stat_interval)

    def _discover_file(self, path, initial = False):
        globbed_dirs = glob.glob(path)
        self.logger.debug("_discover_file_glob: %s: glob is: %s", path, globbed_dirs)

        for file in globbed_dirs:
            if file in self._files:
                continue
            if not os.path.isfile(file):
                continue

            self.logger.debug("_discover_file: %s: new: %s (exclude is %s)",
                              path, file, self._exclude)

            skip = False
            for pattern in self._exclude:
                if fnmatch.fnmatch(os.path.basename(file), pattern):
                    self.logger.debug("_discover_file: %s: skipping because "
                                      "it matches exclude %s", file, pattern)
                    skip = True
                    break

            if skip:
                continue

            stat = os.stat(file)
            inode = [stat.st_ino, stat.st_dev]
            self._files[file] = FileInfo(inode, initial)

    def quit(self):
        self.quit = True
