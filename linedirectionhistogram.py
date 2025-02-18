# -*- coding: utf-8 -*-
"""
/***************************************************************************
 linedirectionhistogram
                                 A QGIS plugin
 Create a line direction histogram
                              -------------------
        begin                : 2015-04-10
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Håvard Tveite, NMBU
        email                : havard.tveite@nmbu.no
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
import os.path
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes
from qgis.PyQt.QtCore import QSettings, QCoreApplication
from qgis.PyQt.QtCore import QTranslator, qVersion
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .linedirectionhistogram_dialog import linedirectionhistogramDialog


# The following user interface components are referenced (in run()):
# "InputLayer", "progressBar"
class linedirectionhistogram:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save a reference to the QGIS interface
        self.iface = iface
        # initialize the plugin directory
        pluginPath = os.path.dirname(__file__)
        # initialize the locale using the QGIS locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            pluginPath,
            'i18n',
            '{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep the reference
        self.dlg = linedirectionhistogramDialog(self.iface)

        # Declare instance attributes
        self.menuname = self.tr(u'&Line Direction Histogram')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LineDirectionHistogram', message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        # Create an action that will start the plugin configuration
        self.action = QAction(
            QIcon(icon_path),
            self.menuname, self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)
        # Add toolbar icon
        if hasattr(self.iface, 'addVectorToolBarIcon'):
            self.iface.addVectorToolBarIcon(self.action)
        else:
            self.iface.addToolBarIcon(self.action)
        # Add menu item
        if hasattr(self.iface, 'addPluginToVectorMenu'):
            self.iface.addPluginToVectorMenu(self.menuname, self.action)
        else:
            self.iface.addPluginToMenu(self.menuname, self.action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        # Remove the plugin menu item
        if hasattr(self.iface, 'removePluginVectorMenu'):
            self.iface.removePluginVectorMenu(self.menuname, self.action)
        else:
            self.iface.removePluginMenu(self.menuname, self.action)
        # Remove the plugin toolbar icon
        if hasattr(self.iface, 'removeVectorToolBarIcon'):
            self.iface.removeVectorToolBarIcon(self.action)
        else:
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Run method that performs all the real work"""
        # Do some initialisations
        # The progressbar
        self.dlg.progressBar.setValue(0)

        # Prepare for sorting
        layers = QgsProject.instance().mapLayers()
        layerslist = []
        for id in layers.keys():
            if layers[id].type() == QgsMapLayer.VectorLayer:
                if not layers[id].isValid():
                    QMessageBox.information(None,
                        self.tr('Information'),
                        'Layer ' + layers[id].name() + ' is not valid')
                else:
                    layerslist.append((layers[id].name(), id))
        # Sort the layers by name
        layerslist.sort(key=lambda x: x[0], reverse=False)
        # Add the layers to the input layer combobox
        self.dlg.InputLayer.clear()
        for layerdescription in layerslist:
            if (layers[layerdescription[1]].geometryType() ==
                  QgsWkbTypes.LineGeometry or
                  layers[layerdescription[1]].geometryType() ==
                  QgsWkbTypes.PolygonGeometry):
                self.dlg.InputLayer.addItem(layerdescription[0],
                                            layerdescription[1])
        # Add the layers to the tiling layer combobox
        self.dlg.TilingLayer.clear()
        for layerdescription in layerslist:
            if (layers[layerdescription[1]].geometryType() ==
                  QgsWkbTypes.PolygonGeometry):
                self.dlg.TilingLayer.addItem(layerdescription[0],
                                             layerdescription[1])
        # show the dialog
        self.dlg.show()
