# -*- coding: utf-8 -*-
from math import sqrt
# from PyQt4 import QtCore
# from PyQt4.QtCore import QCoreApplication
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication
# from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsWkbTypes
from qgis.core import QgsVectorLayer
from qgis.core import QgsGeometry, QgsPolygon

# Angles:
# Real world angles are measured clockwise from the 12 o'clock
# position (north)
# QGIS azimuth angles: clockwise in degrees, starting from north
# (between -180 and 180)
# QT angles are measured counter clockwise from the 3 o'clock
# position (in radians)

# The first bin starts at north + offsetangle (clockwise)
# The width depends on the directionneutral flag and the
# number of bins


class Worker(QtCore.QObject):
    '''The worker that does the heavy lifting.
    The number and length of the line segments of the inputlayer
    line or polygon vector layer is calculated for each angle bin.
    A list of bins is returned.  Each bin contains the total
    length and the number of line segments in the bin.
    '''
    # Define the signals used to communicate
    progress = QtCore.pyqtSignal(int)  # For reporting progress
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)
    # Signal for sending over the result:
    finished = QtCore.pyqtSignal(bool, object)

    def __init__(self, inputvectorlayer, bins, directionneutral,
                                  offsetangle, selectedfeaturesonly,
                                  tilelayer=None):
        """Initialise.

        Arguments:
        inputvectorlayer --     (QgsVectorLayer) The base vector
                                 layer for the join
        bins --                 (int) bins for end point matching
        directionneutral --     (boolean) should lines in oposite
                                 directions be handled as having the
                                 same directionneutral
        offsetangle --          (float) Start the bins at a different
                                 angle
        selectedfeaturesonly -- (boolean) should only selected
                                 features be considered
        tilelayer --            (QgsVectorLayer) The (polygon) tile layer
        """

        QtCore.QObject.__init__(self)  # Essential!
        # Creating instance variables from parameters
        self.inputvectorlayer = inputvectorlayer
        self.bins = int(bins)
        self.directionneutral = directionneutral
        self.offsetangle = offsetangle
        self.selectedfeaturesonly = selectedfeaturesonly
        self.tilelayer = tilelayer
        self.binsize = 360.0 / bins
        if self.directionneutral:
            self.binsize = 180.0 / bins

        # Creating instance variables for the progress bar ++
        # Number of elements that have been processed - updated by
        # calculate_progress
        self.processed = 0
        # Current percentage of progress - updated by
        # calculate_progress
        self.percentage = 0
        # Flag set by kill(), checked in the loop
        self.abort = False
        # Number of features in the input layer - used by
        # calculate_progress
        self.feature_count = self.inputvectorlayer.featureCount()
        # The number of elements that is needed to increment the
        # progressbar - set early in run()
        self.increment = self.feature_count // 1000

    def run(self):
        try:
            inputlayer = self.inputvectorlayer
            if inputlayer is None:
                self.error.emit(self.tr('No input layer defined'))
                self.finished.emit(False, None)
                return
            # Get and check the geometry type of the input layer
            geometryType = self.inputvectorlayer.geometryType()
            if not (geometryType == QgsWkbTypes.LineGeometry or
                    geometryType == QgsWkbTypes.PolygonGeometry):
                self.error.emit('Only line and polygon layers are supported!')
                self.finished.emit(False, None)
                return
            self.processed = 0
            self.percentage = 0
            if self.selectedfeaturesonly:
                self.feature_count = inputlayer.selectedFeatureCount()
            else:
                self.feature_count = inputlayer.featureCount()
            if self.feature_count == 0:
                self.error.emit("No features in layer")
                self.finished.emit(False, None)
                return
            self.increment = self.feature_count // 1000
            # Initialise the result list
            statistics = []
            # Initialise the bins for the over all result
            mybins = []
            for i in range(self.bins):
                mybins.append([0.0, 0])
            # Add the over all bins
            statistics.append(mybins)
            # Get the features (iterator)
            if self.selectedfeaturesonly:
                features = inputlayer.getSelectedFeatures()
#                features = inputlayer.selectedFeaturesIterator()
            else:
                features = inputlayer.getFeatures()
            # Create a list for the (possible) tile (Polygon)
            # geometries
            tilegeoms = []
            if self.tilelayer is not None:
                self.status.emit("Using tiles!")
                for tilefeat in self.tilelayer.getFeatures():
                    tilegeoms.append(tilefeat.geometry())
                # Initialise and add bins for all the tiles
                for i in range(len(tilegeoms)):
                    mybins = []
                    for j in range(self.bins):
                        mybins.append([0.0, 0])
                    statistics.append(mybins)
            # Go through the features
            for feat in features:
                # Allow user abort
                if self.abort is True:
                    break
                # Prepare for the histogram creation by extracting
                # line geometries (QgsGeometry) from the input layer

                # First we do all the lines of the layer.  Later we
                # will do the lines per tile
                # We use a list of line geometries to be able to
                # handle MultiPolylines and Polygons
                inputlines = []
                geom = feat.geometry()  # QgsGeometry
                if geometryType == QgsWkbTypes.LineGeometry:
                    # Lines!
                    if geom.isMultipart():
                        theparts = geom.constParts()
                        # QgsGeometryConstPartIterator
                        # Go through the parts of the multigeometry
                        for part in theparts:
                            # QgsAbstractGeometry - QgsLineString
                            partgeom = QgsGeometry.fromPolyline(part)
                            inputlines.append(partgeom)  # QgsGeometry
                    else:
                        inputlines.append(geom)
                # There are only two possibilites for geometry type, so
                # this elif: could be replaced with an else:
                elif geometryType == QgsWkbTypes.PolygonGeometry:
                    # Polygons!
                    # We use a list of polygon geometries to be able to
                    # handle MultiPolygons
                    inputpolygons = []
                    if geom.isMultipart():
                        # Multi polygon
                        multipoly = geom.asMultiPolygon()
                        for geompoly in multipoly:
                            # list of list of QgsPointXY
                            # abstract geometry -> QgsGeometry polygon
                            polygeometry = QgsGeometry.fromPolygonXY(geompoly)
                            inputpolygons.append(polygeometry)
                    else:
                        # Non-multi polygon
                        # Make sure it is a QgsGeometry polygon
                        singlegeom = geom.asPolygon()
                        polygeometry = QgsGeometry.fromPolygonXY(singlegeom)
                        inputpolygons.append(polygeometry)  # QgsGeometry
                    # Add the polygon rings
                    for polygon in inputpolygons:
                        # create a list of list of QgsPointXY
                        poly = polygon.asPolygon()
                        for ring in poly:
                            # list of QgsPointXY
                            # Create a QgsGeometry line
                            geometryring = QgsGeometry.fromPolylineXY(ring)
                            inputlines.append(geometryring)  # QgsGeometry
                else:
                    # We should never end up here
                    self.status.emit("Unexpected geometry type!")
                # We introduce a list of line geometries for the tiling
                tilelinecoll = [None] * (len(tilegeoms) + 1)
                # Use the first element to store all the input lines
                # (for the over all histogram)
                tilelinecoll[0] = inputlines
                # Clip the lines based on the tile layer
                if self.tilelayer is not None:
                    i = 1  # The first one is used for the complete dataset
                    for tile in tilegeoms:  # Go through the tiles
                        # Create a list for the lines in the tile
                        newlines = []
                        for linegeom in inputlines:
                            # QgsGeometry
                            # Clip
                            clipres = linegeom.intersection(tile)
                            if clipres.isEmpty():
                                continue
                            if clipres.isMultipart():
                                # MultiLineString
                                clipresparts = clipres.constParts()
                                for clipline in clipresparts:
                                  # Create a QgsGeometry line
                                  linegeom = QgsGeometry.fromPolyline(clipline)
                                  newlines.append(linegeom)  # QgsGeometry
                            else:
                                # ?
                                newlines.append(clipres)
                        tilelinecoll[i] = newlines
                        i = i + 1
                # Do calculations (line length and directions)
                j = 0  # Counter for the tiles
                for tilelines in tilelinecoll:  # Handling the tiles
                  for inputlinegeom in tilelines:  # Handling the lines
                    # QgsGeometry line - wkbType 2
                    if inputlinegeom is None:
                        continue
                    numvert = 0
                    for v in inputlinegeom.vertices():
                       numvert = numvert + 1
                    if numvert == 0:
                        continue
                    if numvert < 2:
                        self.status.emit("Less than two vertices!")
                        continue
                    # Go through all the segments of this line
                    thispoint = inputlinegeom.vertexAt(0)  # QgsPoint
                    first = True
                    for v in inputlinegeom.vertices():
                        if first:
                            first = False
                            continue
                        nextpoint = v
                        linelength = sqrt(thispoint.distanceSquared(nextpoint))
                        # Find the angle of the line segment
                        lineangle = thispoint.azimuth(nextpoint)
                        if lineangle < 0:
                            lineangle = 360 + lineangle
                        if self.directionneutral:
                            if lineangle >= 180.0:
                                lineangle = lineangle - 180
                        # Find the bin
                        if lineangle > self.offsetangle:
                            fitbin = (int((lineangle - self.offsetangle) /
                                      self.binsize) % self.bins)
                        else:
                            fitbin = (int((360 + lineangle -
                                           self.offsetangle) / self.binsize) %
                                      self.bins)
                        # Have to handle special case to keep index in range?
                        if fitbin == self.bins:
                            self.status.emit("fitbin == self.bins")
                            fitbin = 0
                        # Add to the length of the bin of this tile (j)
                        statistics[j][fitbin][0] = (statistics[j][fitbin][0] +
                                                    linelength)
                        # Add to the number of line segments in the bin
                        statistics[j][fitbin][1] = (statistics[j][fitbin][1] +
                                                    1)
                        thispoint = nextpoint  # advance to the next point
                  j = j + 1  # Next tile
                self.calculate_progress()
        except Exception as e:
            self.status.emit("Exception occurred - " + str())
            self.error.emit(str(e))
            self.finished.emit(False, None)
        else:
            if self.abort:
                self.status.emit("Aborted")
                self.finished.emit(False, None)
            else:
                self.status.emit("Completed")
                self.finished.emit(True, statistics)

    def calculate_progress(self):
        '''Update progress and emit a signal with the percentage'''
        self.processed = self.processed + 1
        # update the progress bar at certain increments
        if self.increment == 0 or self.processed % self.increment == 0:
            percentage_new = (self.processed * 100) / self.feature_count
            if percentage_new > self.percentage:
                self.percentage = int(percentage_new)
                self.progress.emit(self.percentage)

    def kill(self):
        '''Kill the thread by setting the abort flag'''
        self.abort = True

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LineDirectionEngine', message)
