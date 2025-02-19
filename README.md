# qgislinedirectionhistogramplugin
A QGIS plugin to create a histogram (rose diagram) of line directions. Visualize the distribution of line segment 
directions as a rose diagram (weighted using the line segment lengths). Save the rose diagram as CSV, PDF or SVG. 

Created by Håvard Tveite, who passed away several years ago. Updated for use in modern QGIS versions by KoBold Metals.

Tested with QGIS 3.40.1 on Mac and PC, but 3.36 should work too

## Users
You can install the Zip file included with the 3.2 release of this git repository. Download it and open QGIS

1 - Access the Plugins menu -> Manage and Install Plugins
2 - On the Left side, click 'Install From Zip'
3 - Find your downloaded ZIP file (do not unzip it) and click Install

## Developers
Updates to this plugin should now be done using PB Tool (https://g-sherman.github.io/plugin_build_tool/)

1 - Clone the repository
2 - Locate your locale QGIS plugin directory with `os.path.join(QgsApplication.qgisSettingsDirPath(), 'python/plugins')`
3 - Add this directory path to pb_tool.cfg under 'plugin_path'
4 - Run `pb_tool deploy` to copy your changes to your local QGIS dir
5 - Use the plugin reloader plugin to bring the changes into the active environment without restarting QGIS (https://plugins.qgis.org/plugins/plugin_reloader/)

## Issues
Please report issues through github, and include as much detail as possible about what you were doing, what the desired outcome was,
and any error messages that may have appeared in the 'Log Messages' panel in QGIS during usage.