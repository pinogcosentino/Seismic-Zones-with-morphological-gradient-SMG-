# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   Seismic Microzonation Morpphological Analysis - QGIS Algorithm        *
*   -----------------------------------------------------------           *
*   Date                 : 2026-02-13                                     *
*   Copyright            : (C) 2025 by Giuseppe Cosentino                 *
*   Email                : giuseppe.cosentino@cnr.it                      *
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
__author__ = 'Giuseppe Cosentino'
__date__ = '2026-02-13'
__copyright__ = '(C) 2026 by Giuseppe Cosentino'
__version__ = '2.0'  # Updated for QGIS 4.0

from typing import Dict, Any, Optional
import os
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingUtils,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsCategorizedSymbolRenderer,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsProcessingException,
    QgsMessageLog,
    Qgis,
)
from qgis.utils import iface
import processing

# ============================================================================
# QGIS 4.0 / Qt6 compatibility
# ============================================================================
if Qgis.QGIS_VERSION_INT >= 40000:
    _TYPE_POLYGON   = Qgis.ProcessingSourceType.VectorPolygon
    _TYPE_ANY_GEOM  = Qgis.ProcessingSourceType.VectorAnyGeometry
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Type.Integer
    _MSG_CRITICAL   = Qgis.MessageLevel.Critical
    _MSG_WARNING    = Qgis.MessageLevel.Warning
else:
    _TYPE_POLYGON   = QgsProcessing.TypeVectorPolygon
    _TYPE_ANY_GEOM  = QgsProcessing.TypeVectorAnyGeometry
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Integer
    _MSG_CRITICAL   = Qgis.Critical
    _MSG_WARNING    = Qgis.Warning


class SeismicMicrozonationAlgorithm(QgsProcessingAlgorithm):
    """
    QGIS Processing Algorithm for Seismic Microzonation Morphological Analysis.

    Identifies areas susceptible to topographic amplification or slope
    instability based on slope threshold analysis.

    Symbology is applied in postProcessAlgorithm(), which is called by the
    framework after all output layers have been loaded into the project.
    This is the only crash-safe approach: QgsProcessingLayerPostProcessorInterface
    causes a crash because the framework already registers declared output layers
    via addLayerToLoadOnCompletion() -- calling it again for the same IDs creates
    a double-load conflict that crashes QGIS.
    """

    # ── Parameter names ──────────────────────────────────────────────────────
    INPUT_DTM             = 'digital_terrain_model_raster_input'
    INPUT_ZONES           = 'geological_seismic_zones_vector_input'
    INPUT_SLOPE_THRESHOLD = 'slope_threshold'
    INPUT_MIN_AREA        = 'minimum_area'
    OUTPUT_SLOPE          = 'slope_output'
    OUTPUT_ZONES          = 'zones_output'

    # ── Algorithm constants ───────────────────────────────────────────────────
    DEFAULT_SLOPE_THRESHOLD = 15
    MIN_SLOPE_THRESHOLD     = 0
    MAX_SLOPE_THRESHOLD     = 90
    DEFAULT_MIN_AREA        = 0.0
    TOTAL_STEPS             = 6

    def __init__(self) -> None:
        super().__init__()
        # State shared between processAlgorithm and postProcessAlgorithm
        self._output_slope_id: str = ''
        self._output_zones_id: str = ''
        self._slope_threshold: int = self.DEFAULT_SLOPE_THRESHOLD

    # =========================================================================
    # initAlgorithm
    # =========================================================================
    def initAlgorithm(self, config: Optional[Dict] = None) -> None:
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_DTM,
                self.tr('Digital Terrain Model (DTM)'),
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_ZONES,
                self.tr('Geological Seismic Zones'),
                types=[_TYPE_POLYGON],
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_SLOPE_THRESHOLD,
                self.tr('Slope Threshold (degrees)'),
                type=_NUMBER_INTEGER,
                minValue=self.MIN_SLOPE_THRESHOLD,
                maxValue=self.MAX_SLOPE_THRESHOLD,
                defaultValue=self.DEFAULT_SLOPE_THRESHOLD
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_MIN_AREA,
                self.tr('Minimum Area (m2) - polygons smaller than this value will be discarded (0 = keep all)'),
                type=QgsProcessingParameterNumber.Type.Double,
                minValue=0.0,
                defaultValue=self.DEFAULT_MIN_AREA,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_SLOPE,
                self.tr('Slope Map (degrees)'),
                createByDefault=True,
                defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ZONES,
                self.tr('High Slope Zones'),
                optional=True,
                type=_TYPE_ANY_GEOM,
                createByDefault=True,
                defaultValue='TEMPORARY_OUTPUT'
            )
        )

    # =========================================================================
    # processAlgorithm  -- pure geoprocessing, no symbology here
    # =========================================================================
    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: Any,
        model_feedback: Any,
    ) -> Dict[str, Any]:
        """
        Execute the algorithm workflow.

        Returns:
            Dictionary containing output results.

        Raises:
            QgsProcessingException: If processing fails at any step.
        """
        feedback = QgsProcessingMultiStepFeedback(self.TOTAL_STEPS, model_feedback)
        results  = {}
        outputs  = {}

        try:
            # Step 1 -- Clip DTM
            feedback.pushInfo(self.tr('Step 1/6: Clipping DTM with geological zones...'))
            outputs['clipped_dtm'] = self._clip_raster(parameters, context, feedback)
            feedback.setCurrentStep(1)
            if feedback.isCanceled():
                return {}

            # Step 2 -- Calculate slope
            feedback.pushInfo(self.tr('Step 2/6: Calculating slope map...'))
            outputs['slope'] = self._calculate_slope(
                parameters, outputs['clipped_dtm']['OUTPUT'], context, feedback
            )
            results[self.OUTPUT_SLOPE] = outputs['slope']['OUTPUT']
            feedback.setCurrentStep(2)
            if feedback.isCanceled():
                return {}

            # Step 3 -- Apply threshold
            feedback.pushInfo(
                self.tr('Step 3/6: Identifying slopes >= {}...').format(
                    parameters[self.INPUT_SLOPE_THRESHOLD]
                )
            )
            outputs['threshold_raster'] = self._apply_slope_threshold(
                parameters, outputs['slope']['OUTPUT'], context, feedback
            )
            feedback.setCurrentStep(3)
            if feedback.isCanceled():
                return {}

            # Step 4 -- Polygonize
            feedback.pushInfo(self.tr('Step 4/6: Converting to vector polygons...'))
            outputs['polygons'] = self._polygonize_raster(
                outputs['threshold_raster']['OUTPUT'], context, feedback
            )
            feedback.setCurrentStep(4)
            if feedback.isCanceled():
                return {}

            # Step 5 -- Minimum area filter
            min_area = parameters.get(self.INPUT_MIN_AREA, self.DEFAULT_MIN_AREA) or 0.0
            if min_area > 0:
                feedback.pushInfo(
                    self.tr('Step 5/6: Removing polygons smaller than {} m2...').format(min_area)
                )
                outputs['filtered'] = self._filter_by_min_area(
                    outputs['polygons']['OUTPUT'], min_area, context, feedback
                )
            else:
                feedback.pushInfo(self.tr('Step 5/6: Minimum area filter skipped (value = 0).'))
                outputs['filtered'] = outputs['polygons']
            feedback.setCurrentStep(5)
            if feedback.isCanceled():
                return {}

            # Step 6 -- Join attributes
            feedback.pushInfo(self.tr('Step 6/6: Joining with seismic zones attributes...'))
            outputs['final'] = self._join_attributes(
                parameters, outputs['filtered']['OUTPUT'], context, feedback
            )
            results[self.OUTPUT_ZONES] = outputs['final']['OUTPUT']

            # Store state for postProcessAlgorithm()
            self._output_slope_id = results[self.OUTPUT_SLOPE]
            self._output_zones_id = results[self.OUTPUT_ZONES]
            self._slope_threshold = parameters[self.INPUT_SLOPE_THRESHOLD]

            feedback.pushInfo(self.tr('Processing completed successfully!'))

        except Exception as e:
            msg = self.tr('Error during processing: {}').format(str(e))
            self._log_error(msg)
            raise QgsProcessingException(msg)

        return results

    # =========================================================================
    # postProcessAlgorithm  -- called by QGIS after layers are in the project
    # =========================================================================
    def postProcessAlgorithm(
        self,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """
        Apply QML styles to both output layers.

        At this point the framework has already loaded both layers into the
        project. We retrieve them via QgsProcessingUtils and apply styles
        directly -- no PostProcessorInterface, no addLayerToLoadOnCompletion.
        """
        plugin_dir = os.path.dirname(os.path.abspath(__file__))

        # -- Style the vector output (categorized DN green/red) ---------------
        vector_layer = QgsProcessingUtils.mapLayerFromString(
            self._output_zones_id, context
        )
        if isinstance(vector_layer, QgsVectorLayer):
            vector_layer.setName('Slope_Zones')
            self._apply_vector_style(vector_layer, self._slope_threshold, plugin_dir)
            self._refresh_symbology(vector_layer)

        # -- Style the raster output (pseudocolor slope map) ------------------
        raster_layer = QgsProcessingUtils.mapLayerFromString(
            self._output_slope_id, context
        )
        if isinstance(raster_layer, QgsRasterLayer):
            raster_layer.setName('Slope_Map_deg')
            self._apply_raster_style(raster_layer, self._slope_threshold, plugin_dir)
            self._refresh_symbology(raster_layer)

        return {}

    # =========================================================================
    # Styling helpers
    # =========================================================================
    def _apply_vector_style(
        self,
        layer: QgsVectorLayer,
        slope_threshold: int,
        plugin_dir: str,
    ) -> None:
        """Load style.qml and update DN category labels with the actual threshold."""
        qml_path = os.path.join(plugin_dir, 'style.qml')
        if not os.path.isfile(qml_path):
            self._log_warning(
                self.tr('[SZMG] style.qml not found in {} -- vector symbology skipped.').format(plugin_dir)
            )
            return

        msg, success = layer.loadNamedStyle(qml_path)
        if not success:
            self._log_warning(self.tr('[SZMG] Vector QML could not be applied: {}').format(msg))
            return

        renderer = layer.renderer()
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            label_low  = self.tr('Slope < {} gradi (stabile)').format(slope_threshold)
            label_high = self.tr('Slope >= {} gradi (critica)').format(slope_threshold)
            for idx, cat in enumerate(renderer.categories()):
                if str(cat.value()) == '0':
                    renderer.updateCategoryLabel(idx, label_low)
                elif str(cat.value()) == '1':
                    renderer.updateCategoryLabel(idx, label_high)
            layer.setRenderer(renderer)

        layer.triggerRepaint()

    def _apply_raster_style(
        self,
        layer: QgsRasterLayer,
        slope_threshold: int,
        plugin_dir: str,
    ) -> None:
        """Load style_slope_raster.qml onto the slope raster layer."""
        qml_path = os.path.join(plugin_dir, 'style_slope_raster.qml')
        if not os.path.isfile(qml_path):
            self._log_warning(
                self.tr('[SZMG] style_slope_raster.qml not found in {} -- raster symbology skipped.').format(plugin_dir)
            )
            return

        msg, success = layer.loadNamedStyle(qml_path)
        if not success:
            self._log_warning(self.tr('[SZMG] Raster QML could not be applied: {}').format(msg))
            return

        layer.triggerRepaint()

    @staticmethod
    def _refresh_symbology(layer) -> None:
        """Refresh the layer tree icon if the QGIS GUI is available."""
        try:
            if iface:
                iface.layerTreeView().refreshLayerSymbology(layer.id())
        except Exception:
            pass  # headless / test run

    # =========================================================================
    # Geoprocessing steps
    # =========================================================================
    def _clip_raster(
        self,
        parameters: Dict[str, Any],
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Clip DTM raster using vector mask."""
        return processing.run(
            'gdal:cliprasterbymasklayer',
            {
                'ALPHA_BAND':      False,
                'CROP_TO_CUTLINE': True,
                'DATA_TYPE':       0,
                'EXTRA':           '',
                'INPUT':           parameters[self.INPUT_DTM],
                'KEEP_RESOLUTION': False,
                'MASK':            parameters[self.INPUT_ZONES],
                'MULTITHREADING':  False,
                'NODATA':          None,
                'OPTIONS':         '',
                'SET_RESOLUTION':  False,
                'SOURCE_CRS':      'ProjectCrs',
                'TARGET_CRS':      'ProjectCrs',
                'TARGET_EXTENT':   parameters[self.INPUT_ZONES],
                'X_RESOLUTION':    None,
                'Y_RESOLUTION':    None,
                'OUTPUT':          QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    def _calculate_slope(
        self,
        parameters: Dict[str, Any],
        input_raster: str,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Calculate slope from DTM in degrees."""
        return processing.run(
            'gdal:slope',
            {
                'AS_PERCENT':    False,
                'BAND':          1,
                'COMPUTE_EDGES': False,
                'EXTRA':         '',
                'INPUT':         input_raster,
                'OPTIONS':       '',
                'SCALE':         1,
                'ZEVENBERGEN':   False,
                'OUTPUT':        parameters[self.OUTPUT_SLOPE],
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    def _apply_slope_threshold(
        self,
        parameters: Dict[str, Any],
        slope_raster: str,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Binary raster: 1 where slope >= threshold, 0 elsewhere."""
        threshold = parameters[self.INPUT_SLOPE_THRESHOLD]
        return processing.run(
            'native:modelerrastercalc',
            {
                'CELL_SIZE':  None,
                'CRS':        'ProjectCrs',
                'EXPRESSION': f'"A@1" >= {threshold}',
                'EXTENT':     None,
                'LAYERS':     slope_raster,
                'OUTPUT':     QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    def _polygonize_raster(
        self,
        threshold_raster: str,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Convert binary raster to vector polygons (field = DN)."""
        return processing.run(
            'gdal:polygonize',
            {
                'BAND':                1,
                'EIGHT_CONNECTEDNESS': False,
                'EXTRA':               '',
                'FIELD':               'DN',
                'INPUT':               threshold_raster,
                'OUTPUT':              QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    def _extract_high_slopes(
        self,
        polygons: str,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Extract only DN=1 polygons (high slope areas)."""
        return processing.run(
            'native:extractbyattribute',
            {
                'FIELD':    'DN',
                'INPUT':    polygons,
                'OPERATOR': 0,
                'VALUE':    '1',
                'OUTPUT':   QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    def _filter_by_min_area(
        self,
        polygons: str,
        min_area: float,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Remove polygons whose area is below min_area (CRS units squared)."""
        return processing.run(
            'native:extractbyexpression',
            {
                'INPUT':      polygons,
                'EXPRESSION': f'$area >= {min_area}',
                'OUTPUT':     QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    def _join_attributes(
        self,
        parameters: Dict[str, Any],
        extracted_polygons: str,
        context: Any,
        feedback: Any,
    ) -> Dict[str, Any]:
        """Spatially join seismic zone attributes to the slope polygons."""
        return processing.run(
            'native:joinattributesbylocation',
            {
                'DISCARD_NONMATCHING': False,
                'INPUT':               extracted_polygons,
                'JOIN':                parameters[self.INPUT_ZONES],
                'JOIN_FIELDS':         [''],
                'METHOD':              0,
                'PREDICATE':           [0, 1, 2, 4, 5, 6],
                'PREFIX':              '',
                'OUTPUT':              parameters[self.OUTPUT_ZONES],
            },
            context=context, feedback=feedback, is_child_algorithm=True,
        )

    # =========================================================================
    # Logging
    # =========================================================================
    def _log_error(self, message: str) -> None:
        QgsMessageLog.logMessage(message, self.displayName(), _MSG_CRITICAL)

    def _log_warning(self, message: str) -> None:
        QgsMessageLog.logMessage(message, self.displayName(), _MSG_WARNING)

    # =========================================================================
    # Algorithm metadata
    # =========================================================================
    def name(self) -> str:
        return 'seismic_microzonation_morphology'

    def displayName(self) -> str:
        return self.tr('Seismic Microzonation Morphological Analysis (SMMA)')

    def group(self) -> str:
        return self.tr('Seismic Microzonation')

    def groupId(self) -> str:
        return 'seismic_microzonation'

    def shortHelpString(self) -> str:
        return self.tr("""<html>
<body>
<p>This algorithm identifies areas with slopes exceeding a critical threshold
within seismic or geological zones, useful for assessing areas susceptible
to topographic amplification or slope instability.</p>

<h3>Input Parameters:</h3>
<ul>
  <li><b>Digital Terrain Model:</b> Elevation raster layer (DTM/DEM)</li>
  <li><b>Geological Seismic Zones:</b> Polygon layer defining study areas</li>
  <li><b>Slope Threshold:</b> Critical slope angle in degrees (0-90, default: 15)</li>
  <li><b>Minimum Area (m2):</b> Polygons smaller than this value are discarded.
      Set to 0 (default) to keep all polygons.</li>
</ul>

<h3>Workflow:</h3>
<ol>
  <li><b>DTM Clipping:</b> The DTM is clipped using the geological vector mask</li>
  <li><b>Slope Calculation:</b> A slope map is generated in degrees</li>
  <li><b>Threshold Analysis:</b> Areas exceeding the slope threshold are isolated</li>
  <li><b>Vectorization:</b> Identified areas are converted to polygons</li>
  <li><b>Minimum Area Filter:</b> Polygons smaller than the specified area are removed</li>
  <li><b>Attribute Join:</b> Original seismic zone attributes are preserved</li>
  <li><b>Symbology:</b> Both outputs are automatically styled via plugin QML files:
      green (DN=0, stable) / red (DN=1, critical) for vector;
      pseudocolor white-yellow-red-maroon for the slope raster.</li>
</ol>

<h3>Outputs:</h3>
<ul>
  <li><b>Slope Map:</b> Raster layer showing slope in degrees (pseudocolor)</li>
  <li><b>Slope Zones:</b> Vector layer with slope zones color-coded by DN class</li>
</ul>

<h3>References:</h3>
<p>
- Italian Seismic Microzonation Guidelines - ICMS (2008)<br>
- QGIS Project (2024). PyQGIS Developer Cookbook
</p>
<p><b>Note:</b> Areas with slopes >=15 degrees are typically classified as prone to
local seismic amplification or instability effects.</p>
</body>
</html>""")

    def tr(self, string: str) -> str:
        return string

    def createInstance(self) -> 'SeismicMicrozonationAlgorithm':
        return SeismicMicrozonationAlgorithm()
