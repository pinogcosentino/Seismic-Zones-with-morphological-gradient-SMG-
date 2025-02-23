# -*- coding: utf-8 -*-

"""
/***************************************************************************
 SeismicMicrozonation
                                 A QGIS plugin
 This plugin identifies areas with a morphological gradient with slopes ≥15° within seismic zones (Input vector file) starting from the DTM
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2025-02-01
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
"""

__author__ = 'Giuseppe Cosentino (Pino)'
__date__ = '2025-02-01'
__copyright__ = '(C) 2025 by Giuseppe Cosentino (Pino)'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsVectorLayer
from qgis.utils import iface 
import processing


class SeismicMicrozonationAlgorithm(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('digital__terrain_model_raster_input', 'Digital  terrain model (raster INPUT)', defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('geological_seismic_zones_vector_input', 'Geological Seismic Zones (Vector INPUT)', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('Slope', 'Slope (°)', createByDefault=True, defaultValue=''))
        self.addParameter(QgsProcessingParameterFeatureSink('Zs15', 'ZS15', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue='TEMPORARY_OUTPUT'))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(6, model_feedback)
        results = {}
        outputs = {}

        # Ritaglia raster con maschera
        alg_params = {
            'ALPHA_BAND': False,
            'CROP_TO_CUTLINE': True,
            'DATA_TYPE': 0,  # Usa Il Tipo Dati del Layer in Ingresso
            'EXTRA': '',
            'INPUT': parameters['digital__terrain_model_raster_input'],
            'KEEP_RESOLUTION': False,
            'MASK': parameters['geological_seismic_zones_vector_input'],
            'MULTITHREADING': False,
            'NODATA': None,
            'OPTIONS': '',
            'SET_RESOLUTION': False,
            'SOURCE_CRS': 'ProjectCrs',
            'TARGET_CRS': 'ProjectCrs',
            'TARGET_EXTENT': parameters['geological_seismic_zones_vector_input'],
            'X_RESOLUTION': None,
            'Y_RESOLUTION': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RitagliaRasterConMaschera'] = processing.run('gdal:cliprasterbymasklayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Pendenza
        alg_params = {
            'AS_PERCENT': False,
            'BAND': 1,
            'COMPUTE_EDGES': False,
            'EXTRA': '',
            'INPUT': outputs['RitagliaRasterConMaschera']['OUTPUT'],
            'OPTIONS': '',
            'SCALE': 1,
            'ZEVENBERGEN': False,
            'OUTPUT': parameters['Slope']
        }
        outputs['Pendenza'] = processing.run('gdal:slope', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Slope'] = outputs['Pendenza']['OUTPUT']

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Calcolatore raster
        alg_params = {
            'CELL_SIZE': None,
            'CRS': 'ProjectCrs',
            'EXPRESSION': '"A@1" >= 15',
            'EXTENT': None,
            'LAYERS': outputs['Pendenza']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcolatoreRaster'] = processing.run('native:modelerrastercalc', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Poligonizzazione (da raster a vettore)
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': outputs['CalcolatoreRaster']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PoligonizzazioneDaRasterAVettore'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Estrai per attributo
        alg_params = {
            'FIELD': 'DN',
            'INPUT': outputs['PoligonizzazioneDaRasterAVettore']['OUTPUT'],
            'OPERATOR': 0,  # =
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['EstraiPerAttributo'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Unisci attributi per posizione
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['EstraiPerAttributo']['OUTPUT'],
            'JOIN': parameters['geological_seismic_zones_vector_input'],
            'JOIN_FIELDS': [''],
            'METHOD': 0,  # Crea elementi separati per ciascun elemento corrispondente (uno-a-molti)
            'PREDICATE': [1,2,4,5,6,0],  # contiene,è uguale,sovrappone,sono contenuti,attraversa,interseca
            'PREFIX': '',
            'OUTPUT': parameters['Zs15']
        }
        outputs['UnisciAttributiPerPosizione'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        output_path = outputs['UnisciAttributiPerPosizione']['OUTPUT']
        output_layer = QgsVectorLayer(output_path, 'temp_name', 'ogr')
        output_layer.setName('Zs15')
        iface.layerTreeView().refreshLayerSymbology(output_layer.id())
        results['Zs15'] = output_layer
        return results

    def name(self):
        return 'Seismic microzones with morphological gradient'

    def displayName(self):
        return 'Seismic microzones with morphological gradient'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:9.5pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Seismic Zones with morphological gradient (SMG)</p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">The morphological gradient in seismic areas with slopes greater than 15° can influence the propagation of seismic waves, amplifying their energy and increasing the risks of landslides or ground subsidence. This plugin identifies areas with a morphological gradient with slopes ≥15° within seismic zones (Input vector file) starting from the DTM</p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Useful Link: <a href="https://www.centromicrozonazionesismica.it/documents/18/GuidelinesForSeismicMicrozonation.pdf"><span style=" text-decoration: underline; color:#0000ff;">Guidelines For Seismic Microzonation</span></a></p></body></html></p>
<p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">}
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:9.5pt; font-weight:400; font-style:normal;">
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><br /></p></body></html></p><br><p align="right">Autore algoritmo: Giuseppe Cosentino (Pino)</p><p align="right">Versione algoritmo: 0.3 20250201</p></body></html>"""

    def createInstance(self):
        return SeismicMicrozonationAlgorithm()