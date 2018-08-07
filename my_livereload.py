#!/usr/bin/env python

from livereload import Server, shell
server = Server()
server.watch('./', shell('make html'))
server.serve(root='docs/_build/html')
