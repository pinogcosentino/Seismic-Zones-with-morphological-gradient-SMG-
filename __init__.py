# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SeismicMicrozonation
                                 A QGIS plugin
 This plugin identifies areas with a morphological gradient with slopes ≥15° within seismic zones (Input vector file) starting from the DTM
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2025-01-17
        copyright            : (C) 2025 by Giuseppe Cosentino (Pino)
        email                : giuseppe.cosentino@cnr.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'Giuseppe Cosentino (Pino)'
__date__ = '2025-01-17'
__copyright__ = '(C) 2025 by Giuseppe Cosentino (Pino)'


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SeismicMicrozonation class from file SeismicMicrozonation.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .SZMG import SeismicMicrozonationPlugin
    return SeismicMicrozonationPlugin()
