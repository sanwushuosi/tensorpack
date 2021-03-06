#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: tower.py
# Author: Yuxin Wu <ppwwyyxxc@gmail.com>

import tensorflow as tf
from ..utils.naming import PREDICT_TOWER

__all__ = ['get_current_tower_context', 'TowerContext']

_CurrentTowerContext = None


class TowerContext(object):
    """ A context where the current model is being built in. """

    def __init__(self, tower_name, is_training=None,
                 index=0, vs_name=''):
        """
        Args:
            tower_name (str): The name scope of the tower. Currently used
                values are like: 'tower0', 'towerp0', or ''
            is_training (bool): if None, automatically determine from tower_name.
            index (int): index of this tower
            vs_name (str): Open a variable scope with this name, if given.
        """
        self._name = tower_name

        if is_training is None:
            is_training = not self._name.startswith(PREDICT_TOWER)
        self._is_training = bool(is_training)

        self._index = int(index)

        self._vs_name = vs_name

    @property
    def is_main_training_tower(self):
        return self.is_training and self._index == 0

    @property
    def is_main_tower(self):
        return self._index == 0

    @property
    def is_training(self):
        return self._is_training

    @property
    def has_own_variables(self):
        return len(self._vs_name) > 0

    @property
    def name(self):
        return self._name

    # TODO remove this and add something like `tower.variables`
    # variable_scope name
    @property
    def vs_name(self):
        return self._vs_name

    @property
    def index(self):
        return self._index

    # TODO something similar for training
    @staticmethod
    def get_predict_tower_name(towerid=0, prefix=''):
        """
        Args:
            towerid(int): an integer, the id of this predict tower, usually
                used to choose the GPU id.
            prefix(str): an alphanumeric prefix.
        Returns:
            str: the final tower name used to create a predict tower.
                Currently it is ``PREDICT_TOWER + prefix + towerid``.
        """
        assert prefix == '' or prefix.isalnum()
        return PREDICT_TOWER + prefix + str(towerid)

    def __enter__(self):
        global _CurrentTowerContext
        assert _CurrentTowerContext is None, \
            "Nesting TowerContext!"
        _CurrentTowerContext = self
        self._ctxs = []
        if len(self._name):
            if self.has_own_variables:
                if len(self.vs_name):
                    self._ctxs.append(tf.variable_scope(self.vs_name))
            else:
                if self.is_training:
                    reuse = self._index > 0
                    if reuse is True:
                        # clear old name_scope and re-enter the current variable_scope
                        self._ctxs.append(tf.name_scope(None))
                        self._ctxs.append(tf.variable_scope(
                            tf.get_variable_scope(), reuse=True))
                # if not training, should handle vs outside (TODO not good)
                self._ctxs.append(tf.name_scope(self._name))
        for c in self._ctxs:
            c.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _CurrentTowerContext
        _CurrentTowerContext = None
        for c in self._ctxs[::-1]:
            c.__exit__(exc_type, exc_val, exc_tb)
        return False

    def __str__(self):
        return "TowerContext(name={}, is_training={})".format(
            self._name, self._is_training)


def get_current_tower_context():
    global _CurrentTowerContext
    return _CurrentTowerContext
