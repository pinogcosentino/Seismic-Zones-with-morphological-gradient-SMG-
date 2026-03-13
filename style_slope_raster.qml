<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28" styleCategories="Symbology|Rendering">

  <!--
    =========================================================
    Seismic Microzonation Morphological Analysis (SMMA)
    Raster pseudocolor style – Slope map (degrees 0 – 90°)
    ─────────────────────────────────────────────────────────
    Color ramp classes (geomorphological significance):
      0°        white       — pianura / flat
      5°        light green — pendio trascurabile
     15°        yellow      — soglia critica ICMS (default)
     25°        orange      — pendio elevato
     35°        deep orange — pendio molto elevato
     45°        red         — scarpata
     90°        dark maroon — pareti subverticali
    ─────────────────────────────────────────────────────────
    Applied at runtime by SlopeRasterPostProcessor in
    SZMG_algorithm.py; the threshold color-stop label is
    updated dynamically to match the user's chosen value.
    =========================================================
  -->

  <rasterrenderer
      type="singlebandpseudocolor"
      band="1"
      opacity="1"
      nodataColor=""
      alphaBand="-1"
      classificationMin="0"
      classificationMax="90">

    <rasterTransparency/>

    <minMaxOrigin>
      <limits>MinMax</limits>
      <extent>WholeRaster</extent>
      <statAccuracy>Estimated</statAccuracy>
      <cumulativeCutLower>0.02</cumulativeCutLower>
      <cumulativeCutUpper>0.98</cumulativeCutUpper>
      <stdDevFactor>2</stdDevFactor>
    </minMaxOrigin>

    <rastershader>
      <colorrampshader
          colorRampType="INTERPOLATED"
          classificationMode="1"
          clip="0"
          labelPrecision="0"
          maximumValue="90"
          minimumValue="0">

        <colorramp name="[source]" type="gradient">
          <Option type="Map">
            <Option name="color1"       value="255,255,255,255" type="QString"/>
            <Option name="color2"       value="80,0,20,255"     type="QString"/>
            <Option name="direction"    value="cw"              type="QString"/>
            <Option name="rampType"     value="gradient"        type="QString"/>
            <Option name="stops"        value="0.056;204,255,204,255;rgb;cw:0.167;255,255,0,255;rgb;cw:0.278;255,165,0,255;rgb;cw:0.389;255,69,0,255;rgb;cw:0.500;200,0,0,255;rgb;cw" type="QString"/>
          </Option>
        </colorramp>

        <!--
          Each <item> : value in degrees, color as RGBA hex, label for legend.
          The label of the 15° stop is overwritten at runtime by the
          post-processor to show the actual user-selected threshold.
        -->
        <item  value="0"   color="#ffffff" alpha="255" label="0°  (pianura)"/>
        <item  value="5"   color="#ccffcc" alpha="255" label="5°"/>
        <item  value="15"  color="#ffff00" alpha="255" label="15° ← soglia ICMS"/>
        <item  value="25"  color="#ffa500" alpha="255" label="25°"/>
        <item  value="35"  color="#ff4500" alpha="255" label="35°"/>
        <item  value="45"  color="#c80000" alpha="255" label="45° (scarpata)"/>
        <item  value="90"  color="#500014" alpha="255" label="90° (verticale)"/>

      </colorrampshader>
    </rastershader>

  </rasterrenderer>

  <!-- Contrast enhancement: stretch to actual min/max of each layer -->
  <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
  <huesaturation colorizeOn="0" colorizeBlue="128" colorizeGreen="128"
                 colorizeRed="255" colorizeStrength="100"
                 grayscaleMode="0" invertColors="0"
                 saturation="0"/>
  <rasterresampler maxOversampling="2"/>

  <blendMode>0</blendMode>
  <customproperties>
    <Option/>
  </customproperties>

</qgis>
