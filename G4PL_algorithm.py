# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   Geology from Points and Lines - QGIS Processing Algorithm             *
*   -----------------------------------------------------------           *
*   Date                 : 2026-02-13                                     *
*   Copyright            : (C) 2026 by Giuseppe Cosentino                 *
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

from typing import Dict, Any, Optional, List
from enum import IntEnum

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsWkbTypes,
    QgsFeatureSource,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis
)
import processing

# ============================================================================
# QGIS 4.0 / Qt6 compatibility
# ============================================================================
if Qgis.QGIS_VERSION_INT >= 40000:
    from PyQt6.QtCore import Qt

    # Source types
    _TYPE_POINT   = Qgis.ProcessingSourceType.VectorPoint
    _TYPE_LINE    = Qgis.ProcessingSourceType.VectorLine
    _TYPE_POLYGON = Qgis.ProcessingSourceType.VectorPolygon

    # Geometry types
    _GEOM_POINT = Qgis.GeometryType.Point
    _GEOM_LINE  = Qgis.GeometryType.Line

    # Message levels
    _MSG_CRITICAL = Qgis.MessageLevel.Critical
    _MSG_WARNING  = Qgis.MessageLevel.Warning
    _MSG_INFO     = Qgis.MessageLevel.Info

    # Field data type
    _FIELD_ANY = QgsProcessingParameterField.DataType.Any

    # Number type
    _NUMBER_DOUBLE = QgsProcessingParameterNumber.Type.Double

    def _wkb_display_string(wkb_type):
        return Qgis.displayString(wkb_type)

else:
    from PyQt5.QtCore import Qt

    # Source types
    _TYPE_POINT   = QgsProcessing.TypeVectorPoint
    _TYPE_LINE    = QgsProcessing.TypeVectorLine
    _TYPE_POLYGON = QgsProcessing.TypeVectorPolygon

    # Geometry types
    _GEOM_POINT = QgsWkbTypes.PointGeometry
    _GEOM_LINE  = QgsWkbTypes.LineGeometry

    # Message levels
    _MSG_CRITICAL = Qgis.Critical
    _MSG_WARNING  = Qgis.Warning
    _MSG_INFO     = Qgis.Info

    # Field data type
    _FIELD_ANY = QgsProcessingParameterField.Any

    # Number type
    _NUMBER_DOUBLE = QgsProcessingParameterNumber.Double

    def _wkb_display_string(wkb_type):
        return QgsWkbTypes.displayString(wkb_type)


class SpatialPredicate(IntEnum):
    """Enumeration of spatial predicates for attribute joining."""
    INTERSECTS = 0
    CONTAINS = 1
    WITHIN = 2
    OVERLAPS = 3


class GeologyAlgorithm(QgsProcessingAlgorithm):
    """
    QGIS Processing Algorithm for creating geological maps from point and line data.
    
    This algorithm automates the generation of geological polygons and contact lines
    by combining:
    - Point features containing geological attributes (formation codes, lithology, etc.)
    - Line features representing geological contacts
    
    The workflow:
    1. Cleans duplicate geometries from input points
    2. Polygonizes line features to create enclosed areas
    3. Joins geological attributes from points to polygons using spatial predicates
    4. Generates geological contact lines with inherited attributes
    5. Produces clean, topologically correct output layers
    
    Use cases:
    - Digital geological mapping
    - Geological unit boundary generation
    - Automated cartographic production
    - Geological database construction
    """
    
    # Input parameter names
    INPUT_POINTS = 'points_with_geological_information'
    INPUT_ATTRIBUTE = 'geological_attribute_field'
    INPUT_LINES = 'line_drawing_geological_contacts'
    TOLERANCE = 'vertex_tolerance'
    SPATIAL_PREDICATE = 'spatial_predicate'
    
    # Output parameter names
    OUTPUT_POLYGONS = 'intermediate_polygons'
    OUTPUT_CLEAN_POINTS = 'clean_points'
    OUTPUT_SEGMENTS = 'line_segments'
    OUTPUT_GEOLOGICAL_POLYGONS = 'geological_polygons'
    OUTPUT_CONTACTS = 'geological_contacts'
    
    # Processing constants
    DEFAULT_TOLERANCE = 0.000001
    MIN_TOLERANCE = 0.0
    TOTAL_STEPS = 10
    
    # Join method
    JOIN_METHOD_ONE_TO_MANY = 0

    def __init__(self):
        """Initialize the algorithm."""
        super().__init__()

    # ========================================================================
    # Translation and Metadata Methods
    # ========================================================================
    
    def tr(self, string: str) -> str:
        """
        Return a translatable string with the self.tr() function.
        
        Args:
            string: String to translate
            
        Returns:
            Translated string
        """
        return QCoreApplication.translate('Processing', string)

    def name(self) -> str:
        """Return internal algorithm name."""
        return 'geology_from_points_and_lines'

    def displayName(self) -> str:
        """Return user-friendly algorithm name."""
        return self.tr('Geology Drawing')

    def shortHelpString(self) -> str:
        """Return algorithm help documentation."""
        return self.tr("""<html><body>

<p>This algorithm creates an accurate digital drawing for geological map from point and line data, 
automating the generation of geological units and simplifying detailed geological mapping.</p>

<h3>Workflow Overview:</h3>
<ol>
<li><b>Prepare line data:</b> Draw geological contact lines that intersect or touch 
to form closed polygons (geological unit boundaries)</li>
<li><b>Add point data:</b> Place points inside each polygon with geological attributes 
such as formation codes, lithology, age, etc.</li>
<li><b>Run algorithm:</b> The tool will automatically:
    <ul>
    <li>Clean duplicate geometries from points and lines</li>
    <li>Create polygons from the line network</li>
    <li>Transfer geological attributes from points to polygons</li>
    <li>Generate geological contact lines with attributes</li>
    <li>Produce topologically clean outputs</li>
    </ul>
</li>
</ol>

<h3>Input Parameters:</h3>

<p><b>Points with Geological Information:</b></p>
<ul>
<li>Point layer containing geological attributes (typically centroids of units)</li>
<li>Each point should be located within a distinct geological polygon</li>
<li>Points must have attribute fields with geological information</li>
</ul>

<p><b>Geological Attribute Field:</b></p>
<ul>
<li>The field containing the primary geological classification</li>
<li>Can be formation code, lithology, stratigraphic unit, etc.</li>
<li>This attribute will be transferred to polygons</li>
</ul>

<p><b>Line Drawing (Geological Contacts):</b></p>
<ul>
<li>Line layer representing boundaries between geological units</li>
<li>Lines should form a network of closed polygons</li>
<li>Gaps or overlaps may cause processing errors</li>
</ul>

<p><b>Vertex Tolerance:</b></p>
<ul>
<li>Distance threshold for removing duplicate vertices (in map units)</li>
<li>Default: 0.000001 (suitable for decimal degrees)</li>
<li>Adjust based on coordinate system and required precision</li>
</ul>

<p><b>Spatial Predicate:</b></p>
<ul>
<li><b>Intersects:</b> Point touches or is inside polygon (most common)</li>
<li><b>Contains:</b> Polygon completely contains point</li>
<li><b>Within:</b> Point is completely within polygon</li>
<li><b>Overlaps:</b> Geometries share some but not all points</li>
</ul>

<h3>Outputs:</h3>

<p><b>Geological Polygons:</b></p>
<ul>
<li>Final polygon layer with geological attributes from points</li>
<li>One polygon per geological unit</li>
<li>Inherits all attributes from the point layer</li>
</ul>

<p><b>Geological Contacts:</b></p>
<ul>
<li>Line layer representing boundaries between different geological units</li>
<li>Useful for contact-type analysis (fault, conformity, etc.)</li>
</ul>

<p><b>Intermediate Outputs:</b></p>
<ul>
<li><b>Clean Points:</b> Point layer after duplicate removal</li>
<li><b>Intermediate Polygons:</b> Polygons before attribute joining</li>
<li><b>Line Segments:</b> Individual line segments of contacts</li>
<li>Useful for quality control and troubleshooting</li>
</ul>

<h3>Best Practices:</h3>

<p><b>Line Preparation:</b></p>
<ul>
<li>Ensure all lines connect properly to form closed polygons</li>
<li>Use snapping tools to avoid small gaps between lines</li>
<li>Check for and fix topology errors before processing</li>
<li>Lines should not self-intersect unnecessarily</li>
</ul>

<p><b>Point Placement:</b></p>
<ul>
<li>Place exactly one point per geological polygon</li>
<li>Points should be well inside polygons (not near boundaries)</li>
<li>Ensure points have valid geological attribute values</li>
<li>Check for missing or null attribute values</li>
</ul>

<p><b>Coordinate Systems:</b></p>
<ul>
<li>Use projected coordinate systems for accurate topology</li>
<li>Adjust vertex tolerance based on coordinate system units</li>
<li>For geographic coordinates (degrees): use very small tolerance (0.000001)</li>
<li>For projected coordinates (meters): use appropriate tolerance (0.001-0.01)</li>
</ul>

<p><b>Quality Control:</b></p>
<ul>
<li>Check intermediate outputs if results are unexpected</li>
<li>Verify that polygons were created successfully</li>
<li>Ensure all polygons received attributes from points</li>
<li>Inspect contact lines for proper attribute assignment</li>
</ul>

<h3>Troubleshooting:</h3>

<p><b>No polygons created:</b></p>
<ul>
<li>Check that lines form closed polygons without gaps</li>
<li>Verify line endpoints snap together properly</li>
<li>Look for self-intersecting or overlapping lines</li>
</ul>

<p><b>Polygons missing attributes:</b></p>
<ul>
<li>Ensure each polygon contains exactly one point</li>
<li>Check spatial predicate setting (try "Intersects")</li>
<li>Verify points are actually inside polygons</li>
</ul>

<p><b>Multiple polygons with same attributes:</b></p>
<ul>
<li>This may be intentional (same geological unit in multiple areas)</li>
<li>Or may indicate duplicate or misplaced points</li>
</ul>

<h3>Technical Notes:</h3>
<ul>
<li>Algorithm preserves all attributes from input point layer</li>
<li>Processing uses QGIS native algorithms for maximum compatibility</li>
<li>Temporary outputs are stored unless specified otherwise</li>
<li>Final outputs are topologically clean and ready for GIS analysis</li>
</ul>

</body></html>""".format(
            author=__author__,
            email='giuseppe.cosentino@cnr.it',
            version=__version__
        ))

    def createInstance(self) -> 'GeologyAlgorithm':
        """
        Create a new instance of the algorithm.
        
        Returns:
            New algorithm instance
        """
        return GeologyAlgorithm()

    # ========================================================================
    # Parameter Initialization
    # ========================================================================
    
    def initAlgorithm(self, config: Optional[Dict] = None) -> None:
        """
        Define inputs and outputs of the algorithm.
        
        Args:
            config: Optional configuration dictionary
        """
        # Input: Points with geological information
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_POINTS,
                self.tr('Points with Geological Information'),
                types=[_TYPE_POINT],           # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorPoint
                defaultValue=None
            )
        )
        
        # Input: Geological attribute field
        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_ATTRIBUTE,
                self.tr('Geological Attribute Field'),
                type=_FIELD_ANY,               # ← QGIS 4.0: QgsProcessingParameterField.DataType.Any
                parentLayerParameterName=self.INPUT_POINTS,
                allowMultiple=False,
                defaultValue=None
            )
        )
        
        # Input: Line drawing (geological contacts)
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_LINES,
                self.tr('Line Drawing (Geological Contacts)'),
                types=[_TYPE_LINE],            # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorLine
                defaultValue=None
            )
        )
        
        # Advanced parameter: Vertex tolerance
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TOLERANCE,
                self.tr('Vertex Tolerance (for duplicate removal)'),
                type=_NUMBER_DOUBLE,           # ← QGIS 4.0: QgsProcessingParameterNumber.Type.Double
                minValue=self.MIN_TOLERANCE,
                defaultValue=self.DEFAULT_TOLERANCE,
                optional=False
            )
        )
        
        # Advanced parameter: Spatial predicate
        self.addParameter(
            QgsProcessingParameterEnum(
                self.SPATIAL_PREDICATE,
                self.tr('Spatial Predicate for Joining Attributes'),
                options=[
                    self.tr('Intersects'),
                    self.tr('Contains'),
                    self.tr('Within'),
                    self.tr('Overlaps')
                ],
                defaultValue=SpatialPredicate.INTERSECTS,
                optional=False
            )
        )
        
        # Output: Intermediate polygons
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_POLYGONS,
                self.tr('Polygons (Intermediate)'),
                type=_TYPE_POLYGON,            # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorPolygon
                createByDefault=True,
                defaultValue='TEMPORARY_OUTPUT'
            )
        )
        
        # Output: Clean points
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_CLEAN_POINTS,
                self.tr('Clean Points (Intermediate)'),
                type=_TYPE_POINT,              # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorPoint
                createByDefault=True,
                defaultValue='TEMPORARY_OUTPUT'
            )
        )
        
        # Output: Line segments
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_SEGMENTS,
                self.tr('Line Segments (Intermediate)'),
                type=_TYPE_LINE,               # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorLine
                createByDefault=True,
                defaultValue='TEMPORARY_OUTPUT'
            )
        )
        
        # Output: Geological polygons (main output)
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_GEOLOGICAL_POLYGONS,
                self.tr('Geological Polygons'),
                type=_TYPE_POLYGON,            # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorPolygon
                createByDefault=True,
                supportsAppend=True,
                defaultValue=None
            )
        )
        
        # Output: Geological contacts (main output)
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_CONTACTS,
                self.tr('Geological Contacts (with Attributes)'),
                type=_TYPE_LINE,               # ← QGIS 4.0: Qgis.ProcessingSourceType.VectorLine
                createByDefault=True,
                supportsAppend=True,
                defaultValue=None
            )
        )

    # ========================================================================
    # Input Validation
    # ========================================================================
    
    def checkParameterValues(
        self, 
        parameters: Dict[str, Any], 
        context: Any
    ) -> tuple[bool, str]:
        """
        Validate parameters before processing starts.
        
        Args:
            parameters: Dictionary of input parameters
            context: Processing context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate points layer
        points_source = self.parameterAsSource(parameters, self.INPUT_POINTS, context)
        if points_source is None:
            return False, self.tr('Invalid points layer')
        
        if points_source.featureCount() == 0:
            return False, self.tr('Points layer is empty')
        
        # Validate point geometry type
        geom_type = points_source.wkbType()
        if QgsWkbTypes.geometryType(geom_type) != _GEOM_POINT:  # ← QGIS 4.0: Qgis.GeometryType.Point
            return False, self.tr('Input must be a point layer')
        
        # Validate lines layer
        lines_layer = self.parameterAsVectorLayer(parameters, self.INPUT_LINES, context)
        if lines_layer is None:
            return False, self.tr('Invalid lines layer')
        
        if lines_layer.featureCount() == 0:
            return False, self.tr('Lines layer is empty')
        
        # Validate line geometry type
        geom_type = lines_layer.wkbType()
        if QgsWkbTypes.geometryType(geom_type) != _GEOM_LINE:   # ← QGIS 4.0: Qgis.GeometryType.Line
            return False, self.tr('Input must be a line layer')
        
        # Validate attribute field exists
        attribute_field = self.parameterAsString(parameters, self.INPUT_ATTRIBUTE, context)
        if not attribute_field:
            return False, self.tr('Geological attribute field must be specified')
        
        if attribute_field not in points_source.fields().names():
            return False, self.tr(f'Field "{attribute_field}" not found in points layer')
        
        # Validate tolerance
        tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)
        if tolerance < self.MIN_TOLERANCE:
            return False, self.tr('Tolerance must be greater than or equal to {}'.format(
                self.MIN_TOLERANCE
            ))
        
        return super().checkParameterValues(parameters, context)

    # ========================================================================
    # Main Processing Algorithm
    # ========================================================================
    
    def processAlgorithm(
        self, 
        parameters: Dict[str, Any], 
        context: Any, 
        model_feedback: Any
    ) -> Dict[str, Any]:
        """
        Execute the geological mapping algorithm.
        
        Args:
            parameters: Dictionary of input parameters
            context: Processing context
            model_feedback: Feedback object for progress reporting
            
        Returns:
            Dictionary containing output results
            
        Raises:
            QgsProcessingException: If processing fails at any step
        """
        # Setup multi-step feedback
        feedback = QgsProcessingMultiStepFeedback(self.TOTAL_STEPS, model_feedback)
        results = {}
        outputs = {}
        
        try:
            # Get parameters
            tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)
            spatial_predicate = self.parameterAsEnum(parameters, self.SPATIAL_PREDICATE, context)
            attribute_field = self.parameterAsString(parameters, self.INPUT_ATTRIBUTE, context)
            
            feedback.pushInfo(self.tr('=' * 60))
            feedback.pushInfo(self.tr('Starting Geological Mapping Process'))
            feedback.pushInfo(self.tr('=' * 60))
            feedback.pushInfo(self.tr(f'Geological attribute field: {attribute_field}'))
            feedback.pushInfo(self.tr(f'Vertex tolerance: {tolerance}'))
            feedback.pushInfo('')
            
            # Step 1: Clean duplicate point geometries
            feedback.pushInfo(self.tr('Step 1/{}: Cleaning duplicate point geometries...').format(
                self.TOTAL_STEPS
            ))
            outputs['clean_points'] = self._remove_duplicate_points(
                parameters, context, feedback
            )
            results[self.OUTPUT_CLEAN_POINTS] = outputs['clean_points']
            
            feedback.setCurrentStep(1)
            if feedback.isCanceled():
                return {}
            
            # Step 2: Polygonize lines
            feedback.pushInfo(self.tr('Step 2/{}: Creating polygons from line network...').format(
                self.TOTAL_STEPS
            ))
            outputs['polygons'] = self._polygonize_lines(
                parameters, context, feedback
            )
            
            feedback.setCurrentStep(2)
            if feedback.isCanceled():
                return {}
            
            # Validate polygonization
            if not outputs['polygons']:
                raise QgsProcessingException(
                    self.tr('Polygonization failed. Ensure lines form closed polygons without gaps.')
                )
            
            # Step 3: Clean duplicate polygon geometries
            feedback.pushInfo(self.tr('Step 3/{}: Cleaning duplicate polygon geometries...').format(
                self.TOTAL_STEPS
            ))
            outputs['clean_polygons'] = self._remove_duplicate_polygons(
                outputs['polygons'], parameters, context, feedback
            )
            results[self.OUTPUT_POLYGONS] = outputs['clean_polygons']
            
            feedback.setCurrentStep(3)
            if feedback.isCanceled():
                return {}
            
            # Step 4: Join geological attributes
            feedback.pushInfo(self.tr('Step 4/{}: Joining geological attributes to polygons...').format(
                self.TOTAL_STEPS
            ))
            outputs['geological_polygons'] = self._join_attributes_to_polygons(
                outputs['clean_polygons'],
                outputs['clean_points'],
                attribute_field,
                spatial_predicate,
                parameters,
                context,
                feedback
            )
            results[self.OUTPUT_GEOLOGICAL_POLYGONS] = outputs['geological_polygons']
            
            feedback.setCurrentStep(4)
            if feedback.isCanceled():
                return {}
            
            # Validate attribute joining
            self._validate_attribute_join(
                outputs['geological_polygons'], 
                attribute_field, 
                context, 
                feedback
            )
            
            # Step 5: Convert polygons to lines
            feedback.pushInfo(self.tr('Step 5/{}: Converting polygons to boundary lines...').format(
                self.TOTAL_STEPS
            ))
            outputs['polygon_lines'] = self._convert_polygons_to_lines(
                outputs['geological_polygons'], context, feedback
            )
            
            feedback.setCurrentStep(5)
            if feedback.isCanceled():
                return {}
            
            # Step 6: Remove duplicate vertices
            feedback.pushInfo(self.tr('Step 6/{}: Removing duplicate vertices (tolerance: {})...').format(
                self.TOTAL_STEPS, tolerance
            ))
            outputs['cleaned_lines'] = self._remove_duplicate_vertices(
                outputs['polygon_lines'], tolerance, context, feedback
            )
            
            feedback.setCurrentStep(6)
            if feedback.isCanceled():
                return {}
            
            # Step 7: Explode lines to segments
            feedback.pushInfo(self.tr('Step 7/{}: Exploding lines into segments...').format(
                self.TOTAL_STEPS
            ))
            outputs['exploded_lines'] = self._explode_lines(
                outputs['cleaned_lines'], context, feedback
            )
            
            feedback.setCurrentStep(7)
            if feedback.isCanceled():
                return {}
            
            # Step 8: Clean duplicate line segments
            feedback.pushInfo(self.tr('Step 8/{}: Cleaning duplicate line segments...').format(
                self.TOTAL_STEPS
            ))
            outputs['clean_segments'] = self._remove_duplicate_line_segments(
                outputs['exploded_lines'], parameters, context, feedback
            )
            results[self.OUTPUT_SEGMENTS] = outputs['clean_segments']
            
            feedback.setCurrentStep(8)
            if feedback.isCanceled():
                return {}
            
            # Step 9: Dissolve by geological attribute
            feedback.pushInfo(self.tr('Step 9/{}: Dissolving lines by geological attribute...').format(
                self.TOTAL_STEPS
            ))
            outputs['dissolved_lines'] = self._dissolve_by_attribute(
                outputs['clean_segments'], attribute_field, context, feedback
            )
            
            feedback.setCurrentStep(9)
            if feedback.isCanceled():
                return {}
            
            # Step 10: Convert multipart to singleparts
            feedback.pushInfo(self.tr('Step 10/{}: Converting to single-part features...').format(
                self.TOTAL_STEPS
            ))
            outputs['contacts'] = self._multipart_to_singleparts(
                outputs['dissolved_lines'], parameters, context, feedback
            )
            results[self.OUTPUT_CONTACTS] = outputs['contacts']
            
            # Processing complete
            feedback.pushInfo('')
            feedback.pushInfo(self.tr('=' * 60))
            feedback.pushInfo(self.tr('✓ Geological mapping completed successfully!'))
            feedback.pushInfo(self.tr('=' * 60))
            self._print_summary(results, context, feedback)
            
            return results
            
        except QgsProcessingException:
            raise
        except Exception as e:
            error_msg = self.tr(f'Unexpected error during processing: {str(e)}')
            self._log_error(error_msg)
            raise QgsProcessingException(error_msg)

    # ========================================================================
    # Helper Methods for Processing Steps
    # ========================================================================
    
    def _remove_duplicate_points(
        self, 
        parameters: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Remove duplicate geometries from points layer.
        
        Args:
            parameters: Algorithm parameters
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to cleaned points layer
        """
        alg_params = {
            'INPUT': parameters[self.INPUT_POINTS],
            'OUTPUT': parameters[self.OUTPUT_CLEAN_POINTS]
        }
        result = processing.run(
            'native:deleteduplicategeometries',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _polygonize_lines(
        self, 
        parameters: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Create polygons from line network.
        
        Args:
            parameters: Algorithm parameters
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to polygonized layer
        """
        alg_params = {
            'INPUT': parameters[self.INPUT_LINES],
            'KEEP_FIELDS': True,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        result = processing.run(
            'native:polygonize',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _remove_duplicate_polygons(
        self, 
        input_layer: str, 
        parameters: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Remove duplicate polygon geometries.
        
        Args:
            input_layer: Input polygon layer
            parameters: Algorithm parameters
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to cleaned polygons layer
        """
        alg_params = {
            'INPUT': input_layer,
            'OUTPUT': parameters[self.OUTPUT_POLYGONS]
        }
        result = processing.run(
            'native:deleteduplicategeometries',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _join_attributes_to_polygons(
        self,
        polygons_layer: str,
        points_layer: str,
        attribute_field: str,
        spatial_predicate: int,
        parameters: Dict[str, Any],
        context: Any,
        feedback: Any
    ) -> str:
        """
        Join geological attributes from points to polygons.
        
        Args:
            polygons_layer: Input polygons layer
            points_layer: Points layer with attributes
            attribute_field: Geological attribute field name
            spatial_predicate: Spatial predicate for joining
            parameters: Algorithm parameters
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to polygons with joined attributes
        """
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': polygons_layer,
            'JOIN': points_layer,
            'JOIN_FIELDS': [attribute_field],
            'METHOD': self.JOIN_METHOD_ONE_TO_MANY,
            'PREDICATE': [spatial_predicate],
            'PREFIX': '',
            'OUTPUT': parameters[self.OUTPUT_GEOLOGICAL_POLYGONS]
        }
        result = processing.run(
            'native:joinattributesbylocation',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _convert_polygons_to_lines(
        self, 
        input_layer: str, 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Convert polygon boundaries to lines.
        
        Args:
            input_layer: Input polygons layer
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to lines layer
        """
        alg_params = {
            'INPUT': input_layer,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        result = processing.run(
            'native:polygonstolines',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _remove_duplicate_vertices(
        self, 
        input_layer: str, 
        tolerance: float, 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Remove duplicate vertices from lines.
        
        Args:
            input_layer: Input lines layer
            tolerance: Distance tolerance
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to cleaned lines layer
        """
        alg_params = {
            'INPUT': input_layer,
            'TOLERANCE': tolerance,
            'USE_Z_VALUE': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        result = processing.run(
            'native:removeduplicatevertices',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _explode_lines(
        self, 
        input_layer: str, 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Explode lines into individual segments.
        
        Args:
            input_layer: Input lines layer
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to exploded lines layer
        """
        alg_params = {
            'INPUT': input_layer,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        result = processing.run(
            'native:explodelines',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _remove_duplicate_line_segments(
        self, 
        input_layer: str, 
        parameters: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Remove duplicate line segment geometries.
        
        Args:
            input_layer: Input lines layer
            parameters: Algorithm parameters
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to cleaned segments layer
        """
        alg_params = {
            'INPUT': input_layer,
            'OUTPUT': parameters[self.OUTPUT_SEGMENTS]
        }
        result = processing.run(
            'native:deleteduplicategeometries',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _dissolve_by_attribute(
        self, 
        input_layer: str, 
        attribute_field: str, 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Dissolve lines by geological attribute.
        
        Args:
            input_layer: Input lines layer
            attribute_field: Field to dissolve by
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to dissolved lines layer
        """
        alg_params = {
            'FIELD': [attribute_field],
            'INPUT': input_layer,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        result = processing.run(
            'native:dissolve',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']
    
    def _multipart_to_singleparts(
        self, 
        input_layer: str, 
        parameters: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> str:
        """
        Convert multipart features to singlepart.
        
        Args:
            input_layer: Input layer
            parameters: Algorithm parameters
            context: Processing context
            feedback: Feedback object
            
        Returns:
            Path to singlepart layer
        """
        alg_params = {
            'INPUT': input_layer,
            'OUTPUT': parameters[self.OUTPUT_CONTACTS]
        }
        result = processing.run(
            'native:multiparttosingleparts',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        return result['OUTPUT']

    # ========================================================================
    # Validation and Quality Control
    # ========================================================================
    
    def _validate_attribute_join(
        self, 
        output_layer: str, 
        attribute_field: str, 
        context: Any, 
        feedback: Any
    ) -> None:
        """
        Validate that attribute joining was successful.
        
        Args:
            output_layer: Output layer path
            attribute_field: Attribute field name
            context: Processing context
            feedback: Feedback object
        """
        try:
            layer = QgsVectorLayer(output_layer, 'temp', 'ogr')
            if not layer.isValid():
                feedback.pushWarning(
                    self.tr('Could not validate attribute joining')
                )
                return
            
            feature_count = layer.featureCount()
            if feature_count == 0:
                feedback.pushWarning(
                    self.tr('Warning: No polygons received geological attributes!')
                )
                feedback.pushWarning(
                    self.tr('Check that points are located inside polygons')
                )
            else:
                feedback.pushInfo(
                    self.tr(f'  ✓ {feature_count} polygons successfully attributed')
                )
                
        except Exception as e:
            feedback.pushWarning(
                self.tr(f'Could not validate results: {str(e)}')
            )

    def _print_summary(
        self, 
        results: Dict[str, Any], 
        context: Any, 
        feedback: Any
    ) -> None:
        """
        Print processing summary.
        
        Args:
            results: Processing results dictionary
            context: Processing context
            feedback: Feedback object
        """
        try:
            # Count features in outputs
            for output_name, output_path in results.items():
                try:
                    layer = QgsVectorLayer(output_path, 'temp', 'ogr')
                    if layer.isValid():
                        count = layer.featureCount()
                        geom_type = _wkb_display_string(layer.wkbType())  # ← QGIS 4.0: Qgis.displayString()
                        feedback.pushInfo(
                            self.tr(f'  - {output_name}: {count} features ({geom_type})')
                        )
                except:
                    pass
                    
        except Exception as e:
            feedback.pushWarning(
                self.tr(f'Could not generate summary: {str(e)}')
            )

    # ========================================================================
    # Logging Methods
    # ========================================================================
    
    def _log_error(self, message: str) -> None:
        """
        Log error message.
        
        Args:
            message: Error message to log
        """
        QgsMessageLog.logMessage(
            message, 
            self.displayName(), 
            _MSG_CRITICAL  # ← QGIS 4.0: Qgis.MessageLevel.Critical
        )
    
    def _log_warning(self, message: str) -> None:
        """
        Log warning message.
        
        Args:
            message: Warning message to log
        """
        QgsMessageLog.logMessage(
            message, 
            self.displayName(), 
            _MSG_WARNING   # ← QGIS 4.0: Qgis.MessageLevel.Warning
        )
    
    def _log_info(self, message: str) -> None:
        """
        Log info message.
        
        Args:
            message: Info message to log
        """
        QgsMessageLog.logMessage(
            message, 
            self.displayName(), 
            _MSG_INFO      # ← QGIS 4.0: Qgis.MessageLevel.Info
        )

    def helpUrl(self) -> str:
        """
        Return URL to algorithm documentation.
        
        Returns:
            Help URL (empty string if not available)
        """
        return ''