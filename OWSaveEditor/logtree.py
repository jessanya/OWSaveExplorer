#!/usr/bin/env python
# -*- coding: utf-8 -*-

class LogTree():
    def __init__(self, app, root):
        self.app = app
        self.root = root
        self.id = id(self)
        self.sorted_by = 'alpha'

    def __repr__(self):
        return f'LogFactTree({id(self.root)}, id={self.id}) | {id(self)}'

    def sort(self, sort_by):
        if sort_by == 'reveal':
            key = lambda x: self.app.save.get(x.data['path'], {}).get('revealOrder', -1)
        elif sort_by == 'alpha':
            key = lambda x: self.app.save.get(x.data['path'], {})['id']
        else:
            raise ValueError(f'Invalid sort method: {sort_by!r}')

        self.sorted_by = sort_by

        children = list(self.root.children)
        children.sort(key=key, reverse=True)
        self.root._children = []
        for node in children:
            self.root._children.insert(0, node)
        self.root._tree._invalidate()

        self.app.refresh_bindings()

    def show_binding(self, param):
        if param != 'alpha' and self.sorted_by == 'alpha':
            return True
        if param != 'reveal' and self.sorted_by == 'reveal':
            return True
        return False

