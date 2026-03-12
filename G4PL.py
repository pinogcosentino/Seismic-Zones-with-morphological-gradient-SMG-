# -*- coding: utf-8 -*-

__author__ = 'Giuseppe Cosentino'
__date__ = '2026-02-19'
__copyright__ = '(C) 2026 by Giuseppe Cosentino'
__revision__ = '$Format:%H$'

import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from .G4PL_provider import GeologyProvider

plugin_dir = os.path.dirname(__file__)


class GeologyPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.toolbar = None
        self.action = None

    def initProcessing(self):
        """Registra il provider nel Processing Framework."""
        self.provider = GeologyProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        icon_path = os.path.join(plugin_dir, 'icon.png')

        self.action = QAction(
            QIcon(icon_path),
            'Geology from Points and Lines',
            self.iface.mainWindow()
        )
        self.action.setToolTip('Geology from Points and Lines')
        self.action.triggered.connect(self.run)

        self.iface.addPluginToMenu('Geology Tools', self.action)

        self.toolbar = self.iface.addToolBar('Geology Tools')
        self.toolbar.setObjectName('GeologyToolsToolbar')
        self.toolbar.addAction(self.action)

    def unload(self):
        self.iface.removePluginMenu('Geology Tools', self.action)

        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        """Apre il dialogo dell'algoritmo Geology from Points and Lines."""
        from qgis import processing

        provider = QgsApplication.processingRegistry().providerById(
            self.provider.id()
        )
        if not provider or not provider.algorithms():
            self.iface.messageBar().pushWarning(
                'Geology Tools', 'Nessun algoritmo trovato nel provider.'
            )
            return

        processing.execAlgorithmDialog(provider.algorithms()[0].id())
