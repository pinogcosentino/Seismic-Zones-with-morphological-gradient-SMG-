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
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsVectorLayer,
    QgsProcessingException,
    QgsMessageLog,
    Qgis
)
from qgis.utils import iface
import processing

# ============================================================================
# QGIS 4.0 / Qt6 compatibility
# ============================================================================
if Qgis.QGIS_VERSION_INT >= 40000:
    # Source types
    _TYPE_POLYGON    = Qgis.ProcessingSourceType.VectorPolygon
    _TYPE_ANY_GEOM   = Qgis.ProcessingSourceType.VectorAnyGeometry

    # Number type
    _NUMBER_INTEGER  = QgsProcessingParameterNumber.Type.Integer

    # Message levels
    _MSG_CRITICAL    = Qgis.MessageLevel.Critical
    _MSG_WARNING     = Qgis.MessageLevel.Warning

else:
    # Source types
    _TYPE_POLYGON    = QgsProcessing.TypeVectorPolygon
    _TYPE_ANY_GEOM   = QgsProcessing.TypeVectorAnyGeometry

    # Number type
    _NUMBER_INTEGER  = QgsProcessingParameterNumber.Integer

    # Message levels
    _MSG_CRITICAL    = Qgis.Critical
    _MSG_WARNING     = Qgis.Warning


class SeismicMicrozonationAlgorithm(QgsProcessingAlgorithm):
    """
    QGIS Processing Algorithm for Seismic Microzonation Morphological Analysis.
    
    This algorithm identifies areas susceptible to topographic amplification 
    or slope instability based on slope threshold analysis.
    """
    
    # Parameter names as constants
    INPUT_DTM = 'digital_terrain_model_raster_input'
    INPUT_ZONES = 'geological_seismic_zones_vector_input'
    INPUT_SLOPE_THRESHOLD = 'slope_threshold'
    OUTPUT_SLOPE = 'slope_output'
    OUTPUT_ZONES = 'zones_output'
    
    # Algorithm constants
    DEFAULT_SLOPE_THRESHOLD = 15
    MIN_SLOPE_THRESHOLD = 0
    MAX_SLOPE_THRESHOLD = 90
    TOTAL_STEPS = 6

    def __init__(self):
        """Initialize the algorithm."""
        super().__init__()

    def initAlgorithm(self, config: Optional[Dict] = None) -> None:
        """
        Define algorithm parameters.
        
        Args:
            config: Optional configuration dictionary
        """
        # Input DTM raster
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_DTM,
                self.tr('Digital Terrain Model (DTM)'),
                defaultValue=None
            )
        )
        
        # Input seismic zones vector
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_ZONES,
                self.tr('Geological Seismic Zones'),
                types=[_TYPE_POLYGON],         # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorPolygon
                defaultValue=None
            )
        )
        
        # Slope threshold parameter
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_SLOPE_THRESHOLD,
                self.tr('Slope Threshold (°)'),
                type=_NUMBER_INTEGER,          # ← QGIS 4.0: QgsProcessingParameterNumber.Type.Integer
                minValue=self.MIN_SLOPE_THRESHOLD,
                maxValue=self.MAX_SLOPE_THRESHOLD,
                defaultValue=self.DEFAULT_SLOPE_THRESHOLD
            )
        )
        
        # Output slope raster
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_SLOPE,
                self.tr('Slope Map (°)'),
                createByDefault=True,
                defaultValue=None
            )
        )
        
        # Output zones with slope > threshold
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ZONES,
                self.tr('High Slope Zones'),
                optional=True,
                type=_TYPE_ANY_GEOM,           # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorAnyGeometry
                createByDefault=True,
                defaultValue='TEMPORARY_OUTPUT'
            )
        )

    def processAlgorithm(
        self, 
        parameters: Dict[str, Any], 
        context: Any, 
        model_feedback: Any
    ) -> Dict[str, Any]:
        """
        Execute the algorithm workflow.
        
        Args:
            parameters: Dictionary of input parameters
            context: Processing context
            model_feedback: Feedback object for progress reporting
            
        Returns:
            Dictionary containing output results
            
        Raises:
            QgsProcessingException: If processing fails at any step
        """
        feedback = QgsProcessingMultiStepFeedback(self.TOTAL_STEPS, model_feedback)
        results = {}
        outputs = {}
        
        try:
            # Step 1: Clip DTM with vector mask
            feedback.pushInfo(self.tr('Step 1/6: Clipping DTM with geological zones...'))
            outputs['clipped_dtm'] = self._clip_raster(
                parameters, context, feedback
            )
            
            feedback.setCurrentStep(1)
            if feedback.isCanceled():
                return {}

            # Step 2: Calculate slope
            feedback.pushInfo(self.tr('Step 2/6: Calculating slope map...'))
            outputs['slope'] = self._calculate_slope(
                parameters, outputs['clipped_dtm']['OUTPUT'], context, feedback
            )
            results[self.OUTPUT_SLOPE] = outputs['slope']['OUTPUT']
            
            feedback.setCurrentStep(2)
            if feedback.isCanceled():
                return {}

            # Step 3: Apply threshold to identify critical slopes
            feedback.pushInfo(
                self.tr('Step 3/6: Identifying slopes >= {}°...').format(
                    parameters[self.INPUT_SLOPE_THRESHOLD]
                )
            )
            outputs['threshold_raster'] = self._apply_slope_threshold(
                parameters, outputs['slope']['OUTPUT'], context, feedback
            )
            
            feedback.setCurrentStep(3)
            if feedback.isCanceled():
                return {}

            # Step 4: Vectorize threshold areas
            feedback.pushInfo(self.tr('Step 4/6: Converting to vector polygons...'))
            outputs['polygons'] = self._polygonize_raster(
                outputs['threshold_raster']['OUTPUT'], context, feedback
            )
            
            feedback.setCurrentStep(4)
            if feedback.isCanceled():
                return {}

            # Step 5: Extract areas with DN=1 (slope >= threshold)
            feedback.pushInfo(self.tr('Step 5/6: Extracting high slope areas...'))
            outputs['extracted'] = self._extract_high_slopes(
                outputs['polygons']['OUTPUT'], context, feedback
            )
            
            feedback.setCurrentStep(5)
            if feedback.isCanceled():
                return {}

            # Step 6: Join with original seismic zones attributes
            feedback.pushInfo(self.tr('Step 6/6: Joining with seismic zones attributes...'))
            outputs['final'] = self._join_attributes(
                parameters, outputs['extracted']['OUTPUT'], context, feedback
            )
            
            # Finalize output layer
            results[self.OUTPUT_ZONES] = self._finalize_output_layer(
                outputs['final']['OUTPUT']
            )
            
            feedback.pushInfo(self.tr('Processing completed successfully!'))
            
        except Exception as e:
            error_msg = self.tr('Error during processing: {}').format(str(e))
            self._log_error(error_msg)
            raise QgsProcessingException(error_msg)
        
        return results

    def _clip_raster(
        self, 
        parameters: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> Dict[str, Any]:
        """Clip DTM raster using vector mask."""
        alg_params = {
            'ALPHA_BAND': False,
            'CROP_TO_CUTLINE': True,
            'DATA_TYPE': 0,  # Use input layer data type
            'EXTRA': '',
            'INPUT': parameters[self.INPUT_DTM],
            'KEEP_RESOLUTION': False,
            'MASK': parameters[self.INPUT_ZONES],
            'MULTITHREADING': False,
            'NODATA': None,
            'OPTIONS': '',
            'SET_RESOLUTION': False,
            'SOURCE_CRS': 'ProjectCrs',
            'TARGET_CRS': 'ProjectCrs',
            'TARGET_EXTENT': parameters[self.INPUT_ZONES],
            'X_RESOLUTION': None,
            'Y_RESOLUTION': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        return processing.run(
            'gdal:cliprasterbymasklayer', 
            alg_params, 
            context=context, 
            feedback=feedback, 
            is_child_algorithm=True
        )

    def _calculate_slope(
        self, 
        parameters: Dict[str, Any], 
        input_raster: str, 
        context: Any, 
        feedback: Any
    ) -> Dict[str, Any]:
        """Calculate slope from DTM in degrees."""
        alg_params = {
            'AS_PERCENT': False,
            'BAND': 1,
            'COMPUTE_EDGES': False,
            'EXTRA': '',
            'INPUT': input_raster,
            'OPTIONS': '',
            'SCALE': 1,
            'ZEVENBERGEN': False,
            'OUTPUT': parameters[self.OUTPUT_SLOPE]
        }
        return processing.run(
            'gdal:slope', 
            alg_params, 
            context=context, 
            feedback=feedback, 
            is_child_algorithm=True
        )

    def _apply_slope_threshold(
        self, 
        parameters: Dict[str, Any], 
        slope_raster: str, 
        context: Any, 
        feedback: Any
    ) -> Dict[str, Any]:
        """Apply threshold to slope raster (1 if >= threshold, 0 otherwise)."""
        threshold = parameters[self.INPUT_SLOPE_THRESHOLD]
        alg_params = {
            'CELL_SIZE': None,
            'CRS': 'ProjectCrs',
            'EXPRESSION': f'"A@1" >= {threshold}',
            'EXTENT': None,
            'LAYERS': slope_raster,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        return processing.run(
            'native:modelerrastercalc', 
            alg_params, 
            context=context, 
            feedback=feedback, 
            is_child_algorithm=True
        )

    def _polygonize_raster(
        self, 
        threshold_raster: str, 
        context: Any, 
        feedback: Any
    ) -> Dict[str, Any]:
        """Convert raster to vector polygons."""
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': threshold_raster,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        return processing.run(
            'gdal:polygonize', 
            alg_params, 
            context=context, 
            feedback=feedback, 
            is_child_algorithm=True
        )

    def _extract_high_slopes(
        self, 
        polygons: str, 
        context: Any, 
        feedback: Any
    ) -> Dict[str, Any]:
        """Extract only polygons with DN=1 (high slope areas)."""
        alg_params = {
            'FIELD': 'DN',
            'INPUT': polygons,
            'OPERATOR': 0,  # equals
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        return processing.run(
            'native:extractbyattribute', 
            alg_params, 
            context=context, 
            feedback=feedback, 
            is_child_algorithm=True
        )

    def _join_attributes(
        self, 
        parameters: Dict[str, Any], 
        extracted_polygons: str, 
        context: Any, 
        feedback: Any
    ) -> Dict[str, Any]:
        """Join attributes from seismic zones to high slope polygons."""
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': extracted_polygons,
            'JOIN': parameters[self.INPUT_ZONES],
            'JOIN_FIELDS': [''],
            'METHOD': 0,  # Create separate features for each match
            'PREDICATE': [0, 1, 2, 4, 5, 6],  # intersects, contains, equals, overlaps, within, crosses
            'PREFIX': '',
            'OUTPUT': parameters[self.OUTPUT_ZONES]
        }
        return processing.run(
            'native:joinattributesbylocation', 
            alg_params, 
            context=context, 
            feedback=feedback, 
            is_child_algorithm=True
        )

    def _finalize_output_layer(self, output_path: str) -> QgsVectorLayer:
        """
        Create and configure the final output layer.
        
        Args:
            output_path: Path to the output vector file
            
        Returns:
            Configured QgsVectorLayer
        """
        output_layer = QgsVectorLayer(output_path, 'High_Slope_Zones', 'ogr')
        
        if not output_layer.isValid():
            raise QgsProcessingException(
                self.tr('Failed to create output layer')
            )
        
        output_layer.setName('High_Slope_Zones')
        
        # Refresh symbology if interface is available
        if iface:
            try:
                iface.layerTreeView().refreshLayerSymbology(output_layer.id())
            except Exception as e:
                self._log_warning(
                    self.tr('Could not refresh layer symbology: {}').format(str(e))
                )
        
        return output_layer

    def _log_error(self, message: str) -> None:
        """Log error message."""
        QgsMessageLog.logMessage(message, self.displayName(), _MSG_CRITICAL)  # ← QGIS 4.0: Qgis.MessageLevel.Critical

    def _log_warning(self, message: str) -> None:
        """Log warning message."""
        QgsMessageLog.logMessage(message, self.displayName(), _MSG_WARNING)   # ← QGIS 4.0: Qgis.MessageLevel.Warning

    def name(self) -> str:
        """Return the algorithm name."""
        return 'seismic_microzonation_morphology'

    def displayName(self) -> str:
        """Return the translatable display name."""
        return self.tr('Seismic Microzonation Morphological Analysis (SMMA)')

    def group(self) -> str:
        """Return the group name."""
        return self.tr('Seismic Microzonation')

    def groupId(self) -> str:
        """Return the group ID."""
        return 'seismic_microzonation'

    def shortHelpString(self) -> str:
        """Return the help documentation."""
        return self.tr("""<html>
<body>
<p>This algorithm identifies areas with slopes exceeding a critical threshold 
within seismic or geological zones, useful for assessing areas susceptible 
to topographic amplification or slope instability.</p>

<h3>Input Parameters:</h3>
<ul>
  <li><b>Digital Terrain Model:</b> Elevation raster layer (DTM/DEM)</li>
  <li><b>Geological Seismic Zones:</b> Polygon layer defining study areas</li>
  <li><b>Slope Threshold:</b> Critical slope angle in degrees (0-90°, default: 15°)</li>
</ul>

<h3>Workflow:</h3>
<ol>
  <li><b>DTM Clipping:</b> The DTM is clipped using the geological vector mask</li>
  <li><b>Slope Calculation:</b> A slope map is generated in degrees</li>
  <li><b>Threshold Analysis:</b> Areas exceeding the slope threshold are isolated</li>
  <li><b>Vectorization:</b> Identified areas are converted to polygons</li>
  <li><b>Attribute Join:</b> Original seismic zone attributes are preserved</li>
</ol>

<h3>Outputs:</h3>
<ul>
  <li><b>Slope Map:</b> Raster layer showing slope in degrees</li>
  <li><b>High Slope Zones:</b> Vector layer of areas exceeding the threshold</li>
</ul>

<h3>References:</h3>
<p>
- Italian Seismic Microzonation Guidelines - Indirizzi e Criteri per la microzononazione sismica (ICMS, 2008)<br>
- QGIS Project (2024). PyQGIS Developer Cookbook<br>

<p><b>Note:</b> Areas with slopes ≥15° are typically classified as prone to 
local seismic amplification or instability effects.</p>
</body>
</html>""")

    def tr(self, string: str) -> str:
        """
        Return a translatable string with the self.tr() function.
        
        Args:
            string: String to translate
            
        Returns:
            Translated string
        """
        return string

    def createInstance(self) -> 'SeismicMicrozonationAlgorithm':
        """Create a new instance of the algorithm."""
        return SeismicMicrozonationAlgorithm()