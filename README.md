# filewatch 

## Getting Started

* python setup.py installer
* globtail -x '*.gz' '/var/log/*'

For developers, see filewatch.watch.Watch and filewatch.tail.Tail.

Tested on Linux/x86_64 and Mac OS/X.

All operating systems should be supported. If you run the tests on
another platform, please open a Github issue with the output (even
if it passes, so we can update this document).

## Overview

This project provide file and glob watching.
It is a re-implementation in python of the excellent
ruby-filewatch package
(https://github.com/jordansissel/ruby-filewatch)

Goals:

* to provide a python api to get notifications of file or glob changes

Example code (standalone):

    from filewatch.tail import Tail

    def func(path, line):
       print "%s: %s" % (path, line)
    t = Tail()
    t.tail("/tmp/test*.log")
    t.subscribe(func)
