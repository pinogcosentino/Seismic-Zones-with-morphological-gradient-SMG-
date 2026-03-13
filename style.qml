<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28" styleCategories="Symbology|Labeling">

  <!--
    =========================================================
    Seismic Microzonation Morphological Analysis (SMMA)
    Categorized style – field: DN
    ─────────────────────────────────────────────────────────
    DN = 0  →  Slope BELOW threshold  (green)
    DN = 1  →  Slope AT/ABOVE threshold (red)
    =========================================================
    Labels are set at runtime by _apply_symbology() in
    SZMG_algorithm.py using the actual slope threshold.
    The placeholder strings below are never shown to the user.
    =========================================================
  -->

  <renderer-v2
      type="categorizedSymbol"
      attr="DN"
      forceraster="0"
      symbollevels="0"
      enableorderby="0"
      referencescale="-1">

    <categories>
      <!-- DN = 0 : stable / below threshold -->
      <category
          value="0"
          label="Slope &lt; soglia (stabile)"
          render="true"
          symbol="0"
          uuid="{szmg-cat-0}"/>

      <!-- DN = 1 : critical / at or above threshold -->
      <category
          value="1"
          label="Slope ≥ soglia (critica)"
          render="true"
          symbol="1"
          uuid="{szmg-cat-1}"/>
    </categories>

    <symbols>

      <!-- ── Symbol 0 : green fill (DN = 0, stable slope) ── -->
      <symbol name="0" type="fill" alpha="0.78"
              clip_to_extent="1" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name"  value=""           type="QString"/>
            <Option name="properties"/>
            <Option name="type"  value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" pass="0" enabled="1" locked="0">
          <Option type="Map">
            <!-- Forest-green fill, semi-transparent -->
            <Option name="color"          value="34,139,34,200"  type="QString"/>
            <Option name="style"          value="solid"          type="QString"/>
            <!-- Dark-green border -->
            <Option name="outline_color"  value="0,100,0,255"    type="QString"/>
            <Option name="outline_style"  value="solid"          type="QString"/>
            <Option name="outline_width"  value="0.26"           type="QString"/>
            <Option name="outline_width_unit" value="MM"         type="QString"/>
            <Option name="joinstyle"      value="miter"          type="QString"/>
            <Option name="border_width_map_unit_scale"
                    value="3x:0,0,0,0,0,0"                       type="QString"/>
            <Option name="offset"         value="0,0"            type="QString"/>
            <Option name="offset_unit"    value="MM"             type="QString"/>
          </Option>
          <effect enabled="0" type="effectStack">
            <effect type="dropShadow"/>
            <effect type="outerGlow"/>
            <effect type="drawSource"/>
            <effect type="innerGlow"/>
            <effect type="innerShadow"/>
          </effect>
        </layer>
      </symbol>

      <!-- ── Symbol 1 : red fill (DN = 1, critical slope) ── -->
      <symbol name="1" type="fill" alpha="0.78"
              clip_to_extent="1" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name"  value=""           type="QString"/>
            <Option name="properties"/>
            <Option name="type"  value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleFill" pass="0" enabled="1" locked="0">
          <Option type="Map">
            <!-- Crimson fill, semi-transparent -->
            <Option name="color"          value="220,20,20,200"  type="QString"/>
            <Option name="style"          value="solid"          type="QString"/>
            <!-- Dark-red border -->
            <Option name="outline_color"  value="139,0,0,255"    type="QString"/>
            <Option name="outline_style"  value="solid"          type="QString"/>
            <Option name="outline_width"  value="0.26"           type="QString"/>
            <Option name="outline_width_unit" value="MM"         type="QString"/>
            <Option name="joinstyle"      value="miter"          type="QString"/>
            <Option name="border_width_map_unit_scale"
                    value="3x:0,0,0,0,0,0"                       type="QString"/>
            <Option name="offset"         value="0,0"            type="QString"/>
            <Option name="offset_unit"    value="MM"             type="QString"/>
          </Option>
          <effect enabled="0" type="effectStack">
            <effect type="dropShadow"/>
            <effect type="outerGlow"/>
            <effect type="drawSource"/>
            <effect type="innerGlow"/>
            <effect type="innerShadow"/>
          </effect>
        </layer>
      </symbol>

    </symbols>

    <rotation/>
    <sizescale/>
  </renderer-v2>

  <!-- Simple labeling: disabled by default -->
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style fontWeight="50" fontSize="8" fontFamily="Sans Serif"
                  textOpacity="1" namedStyle="Regular" fieldName=""
                  isExpression="0" textColor="0,0,0,255"/>
      <rendering drawLabels="0"/>
    </settings>
  </labeling>

  <customproperties>
    <Option/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>

</qgis>
