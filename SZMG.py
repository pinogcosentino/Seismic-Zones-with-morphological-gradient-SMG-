# -*- coding: utf-8 -*-

"""
/***************************************************************************
 SeismicMicrozonation
                                 A QGIS plugin
 This plugin identifies areas with a morphological gradient with slopes
 >= 15° within seismic zones starting from the DTM
        begin                : 2025-02-02
        copyright            : (C) 2025 by Giuseppe Cosentino (Pino)
 ***************************************************************************/
"""

__author__ = 'Giuseppe Cosentino (Pino)'
__date__ = '2025-02-02'
__copyright__ = '(C) 2025 by Giuseppe Cosentino (Pino)'
__revision__ = '$Format:%H$'

import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from .SZMG_provider import SeismicMicrozonationProvider

plugin_dir = os.path.dirname(__file__)


class SeismicMicrozonationPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.toolbar = None
        self.action = None

    def initProcessing(self):
        """Registra il provider nel Processing Framework."""
        self.provider = SeismicMicrozonationProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        icon_path = os.path.join(plugin_dir, 'icon.png')

        self.action = QAction(
            QIcon(icon_path),
            'Seismic Microzonation Morphological Analysis (SMMA)',
            self.iface.mainWindow()
        )
        self.action.setToolTip('Seismic Microzonation Morphological Analysis (SMMA)')
        self.action.triggered.connect(self.run)

        self.iface.addPluginToMenu('Seismic Microzonation', self.action)

        self.toolbar = self.iface.addToolBar('Seismic Microzonation')
        self.toolbar.setObjectName('SeismicMicrozonationToolbar')
        self.toolbar.addAction(self.action)

    def unload(self):
        self.iface.removePluginMenu('Seismic Microzonation', self.action)

        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        """Apre il dialogo dell'algoritmo Seismic Microzonation."""
        from qgis import processing

        provider = QgsApplication.processingRegistry().providerById(
            self.provider.id()
        )
        if not provider or not provider.algorithms():
            self.iface.messageBar().pushWarning(
                'Seismic Microzonation', 'Nessun algoritmo trovato nel provider.'
            )
            return

        processing.execAlgorithmDialog(provider.algorithms()[0].id())
