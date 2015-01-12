import buftok
import logging
import os
import time
import watch


class NoSinceDBPathGiven(Exception):
    pass


class Tail(object):

    OPEN_WARN_INTERVAL = int(os.environ.get('FILEWATCH_OPEN_WARN_INTERVAL',
                                            '300'))

    def __init__(self, opts=None):
        if opts is None:
            opts = {}

        if opts.get('logger'):
            self.logger = opts['logger']
        else:
            self.logger = logging.getLogger('filewatch.Tail')

        self.files = {}
        self.lastwarn = {}
        self.buffers = {}
        self.watch = watch.Watch()
        self.watch.logger = self.logger
        self.sincedb = {}
        self.sincedb_last_write = 0
        self.statcache = {}
        self.opts = {
            'sincedb_write_interval': 10,
            'stat_interval': 1,
            'discover_interval': 5,
            'exclude': [],
            'start_at_new_files': 'end'
            }
        self.opts.update(opts)

        if not self.opts.get('sincedb_path'):
            if os.environ.get('HOME'):
                self.opts['sincedb_path'] = os.path.join(os.environ['HOME'],
                                                         '.sincedb')
            if os.environ.get('SINCEDB_PATH'):
                self.opts['sincedb_path'] = os.environ['SINCEDB_PATH']

        if not self.opts.get('sincedb_path'):
            raise NoSinceDBPathGiven(
                "No HOME or SINCEDB_PATH set in environment. I need one of "
                "these set so I can keep track of the files I am following.")

        self.watch.exclude(self.opts['exclude'])
        self._sincedb_open()
        
    def get_logger(self):
        return self._logger

    def set_logger(self, logger):
        self._logger = logger
        self.watch.logger = logger

    property(get_logger, set_logger)

    def tail(self, path):
        self.watch.watch(path)

    def subscribe(self, func):
        def _func(event, path):
            if event in [watch.Watch.create, watch.Watch.create_initial]:
                if path in self.files:
                    self.logger.debug(
                        "%s for %s: already exists in self.files",
                        event, path)
                    return
                if self._open_file(path, event):
                    self._read_file(path, func)

            elif event == watch.Watch.modify:
                if path not in self.files:
                    self.logger.debug(
                        ":modify for %s, does not exist in self.files", path)
                    if self._open_file(path, event):
                        self._read_file(path, func)
                else:
                    self._read_file(path, func)
            elif event == watch.Watch.delete:
                self.logger.debug(
                    ":delete for %s, deleted from self.files", path)
                if path in self.files:
                    self._read_file(path, func)
                    self.files[path].close()
                    del self.files[path]
                    del self.statcache[path]
            else:
                self.logger.warn("unknown event type %s for %s", event, path)

        self.watch.subscribe(_func, self.opts['stat_interval'],
                             self.opts['discover_interval'])

    def _open_file(self, path, event):
        self.logger.debug("_open_file: %s: opening", path)
        try:
            self.files[path] = open(path, 'r')
        except Exception, e:
            # don't emit this message too often. if a file that we can't
            # read is changing a lot, we'll try to open it more often,
            # and might be spammy.
            now = long(time.time())
            if now - self.lastwarn.get(path) > Tail.OPEN_WARN_INTERVAL:
                self.logger.warn("failed to open %s: %s", path, e)
                self.lastwarn[path] = now
            else:
                self.logger.debug("(warn supressed) failed to open %s: %s",
                                  path, e)

            del self.files[path]
            return False
        stat = os.stat(path)

        inode = (str(stat.st_ino), stat.st_dev)

        self.statcache[path] = inode

        if inode in self.sincedb:
            last_size = self.sincedb[inode]
            self.logger.debug("%s: sincedb last value %s, cur size %s", path,
                              self.sincedb[inode], stat.st_size)
            if last_size <= stat.st_size:
                self.logger.debug("%s: sincedb: seeking to %s", path,
                                  last_size)
                self.files[path].seek(last_size)
            else:
                self.logger.debug(
                    "%s: last value size is greater than current value, "
                    "starting over", path)
                self.sincedb[inode] = 0
        elif event == watch.Watch.create_initial and self.files.get(path):
            if self.opts['start_at_new_files'] == 'beginning':
                self.logger.debug(
                    "%s: initial create, no sincedb, "
                    "seeking to beginning of file", path)
                self.files[path].seek(0)
                self.sincedb[inode] = 0
            else:
                # seek to end
                self.logger.debug(
                    "%s: initial create, no sincedb, seeking to end %s",
                    path, stat.st_size)
                self.files[path].seek(stat.st_size)
                self.sincedb[inode] = stat.st_size
        else:
            self.logger.debug("%s: staying at position 0, no sincedb", path)

        return True

    def _read_file(self, path, func):
        buffer = self.buffers.setdefault(path, buftok.BufferedTokenizer())

        changed = False
        while 1:
            self.files[path].seek(self.files[path].tell())
            data = self.files[path].read(1024)
            if not data:
                break
            changed = True
            for line in buffer.extract(data):
                func(path, line)
            self.sincedb[self.statcache[path]] = self.files[path].tell()

        if changed:
            now = long(time.time())
            delta = now - self.sincedb_last_write
            if delta >= self.opts['sincedb_write_interval']:
                self.logger.debug(
                    "writing sincedb (delta since last write = %s)", delta)
                self._sincedb_write()
                self.sincedb_last_write = now

    def sincedb_write(self, reason=None):
        self.logger.debug("caller requested sincedb write (%s)", reason)
        self._sincedb_write()

    def _sincedb_open(self):
        path = self.opts['sincedb_path']
        self.logger.debug("_sincedb_open: reading from %s", path)
        try:
            with open(path, 'r') as db:
                for line in db:
                    ino, dev, pos = line.strip().split(' ', 2)
                    inode = (ino, long(dev))
                    self.logger.debug("_sincedb_open: setting %s to %s", inode,
                                      long(pos))
                    self.sincedb[inode] = long(pos)
        except Exception, e:
            self.logger.debug("_sincedb_open: %s: %s", path, e)
            return

    def _sincedb_write(self):
        path = self.opts['sincedb_path']
        tmp = '%s.new' % path
        try:
            with open(tmp, 'w') as db:
                for inode, pos in self.sincedb.items():
                    db.write('%s %s %s\n' % (inode[0], inode[1], pos))
        except Exception, e:
            self.logger.warn("_sincedb_write failed: %s: %s", tmp, e)
            return
        try:
            os.rename(tmp, path)
        except Exception, e:
            self.logger.warn(
                "_sincedb_write rename/sync failed: %s -> %s: %s",
                tmp, path, e)
