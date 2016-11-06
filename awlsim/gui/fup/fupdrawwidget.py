# -*- coding: utf-8 -*-
#
# AWL simulator - FUP draw widget
#
# Copyright 2016 Michael Buesch <m@bues.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import division, absolute_import, print_function, unicode_literals
from awlsim.common.compat import *

from awlsim.common.xmlfactory import *

from awlsim.gui.icons import *
from awlsim.gui.util import *


class FupBaseClass(object):
	"""Abstract FUP/FBD base class"""

	factory = None

	def __eq__(self, other):
		return self is other

	def __ne__(self, other):
		return self is not other

	def __hash__(self):
		return id(self)

class FupWire_factory(XmlFactory):
	def parser_open(self):
		self.inWire = False
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		if not self.inWire:
			if tag.name == "wire":
				self.inWire = True
				idNum = tag.getAttrInt("id")
				if idNum in (w.idNum for w in self.grid.wires):
					raise self.Error("<wire id=%d> does "
						"already exist." % idNum)
				# Create wire and add it to the grid.
				FupWire(grid=self.grid, idNum=idNum)
				return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inWire:
			if tag.name == "wire":
				self.inWire = False
				return
		else:
			if tag.name == "wires":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		return [
			self.Tag(name="wire",
				attrs={
					"id" : str(self.wire.idNum),
				}),
		]

class FupWire(FupBaseClass):
	"""FUP/FBD wire connecting two FupConn connections."""

	factory = FupWire_factory

	BRANCH_DIA = 4

	def __init__(self, grid, idNum=None):
		FupBaseClass.__init__(self)
		self.grid = grid
		self.connections = set()	# The connections this wire is connected to
		self.outConn = None		# The out-connection this is connected to

		if idNum is None:
			idNum = grid.getUnusedWireIdNum()
		self.idNum = idNum		# The ID number of this wire
		grid.addWire(self)

		self.__wirePen = QPen(QColor("#000000"))
		self.__wirePen.setWidth(2)
		self.__wireBranchPen = QPen(QColor("#000000"))
		self.__wireBranchPen.setWidth(1)
		self.__wireBranchBrush = QBrush(QColor("#000000"))

	def connect(self, conn):
		"""Add a connection to this wire.
		"""
		if conn in self.connections:
			return
		if conn.OUT and\
		   self.outConn is not None and\
		   self.outConn is not conn:
			# We already have an output connection.
			raise ValueError
		self.connections.add(conn)
		conn.wire = self
		if conn.OUT:
			self.outConn = conn

	def disconnectAll(self):
		"""Disconenct all connections.
		"""
		for conn in self.connections:
			conn.wire = None
		self.connections.clear()
		self.outConn = None
		self.grid.removeWire(self)

	def disconnect(self, conn):
		"""Disconnect a connection from this wire.
		"""
		conn.wire = None
		self.connections.remove(conn)
		if self.outConn is conn:
			# Only inputs left. Remove them all.
			self.disconnectAll()
		if len(self.connections) == 1:
			# Only one connection left. Remove that, too.
			self.disconnectAll()
		if not self.connections and not self.outConn:
			self.grid.removeWire(self)

	def draw(self, painter):
		if self.outConn is None:
			return
		xAbs0, yAbs0 = self.outConn.pixCoords
		r, d = self.BRANCH_DIA // 2, self.BRANCH_DIA
		painter.setBrush(self.__wireBranchBrush)
		for conn in self.connections:
			xAbs1, yAbs1 = conn.pixCoords
			painter.setPen(self.__wirePen)
			painter.drawLine(xAbs0, yAbs0, xAbs0, yAbs1)
			painter.drawLine(xAbs0, yAbs1, xAbs1, yAbs1)
			painter.setPen(self.__wireBranchPen)
			painter.drawEllipse(xAbs0 - r, yAbs0 - r, d, d)
			painter.drawEllipse(xAbs1 - r, yAbs1 - r, d, d)

class FupConn_factory(XmlFactory):
	def parser_open(self):
		self.inConn = False
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		if not self.inConn:
			if tag.name == "connection":
				pos = tag.getAttrInt("pos")
				dirIn = tag.getAttrInt("dir_in")
				dirOut = tag.getAttrInt("dir_out")
				wireId = tag.getAttrInt("wire")
				if pos < 0 or pos > 0xFFFF:
					raise self.Error("Invalid <connection> pos.")
				wire = self.elem.grid.getWireById(wireId)
				try:
					if dirIn and not dirOut:
						self.elem.inputs.extend(
							[None] * (pos + 1 - len(self.elem.inputs)))
						conn = FupConnIn(elem=self.elem, pos=pos, wire=wire)
						if wire:
							wire.connect(conn)
						self.elem.inputs[pos] = conn
						return
					elif dirOut and not dirIn:
						self.elem.outputs.extend(
							[None] * (pos + 1 - len(self.elem.outputs)))
						conn = FupConnOut(elem=self.elem, pos=pos, wire=wire)
						if wire:
							wire.connect(conn)
						self.elem.outputs[pos] = conn
						return
				except ValueError:
					raise self.Error("Invalid <connection>")
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inConn:
			if tag.name == "connection":
				self.inConn = False
				return
		else:
			if tag.name == "connections":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		return [
			self.Tag(name="connection",
				attrs={
					"dir_in" : str(int(self.conn.IN)),
					"dir_out" : str(int(self.conn.OUT)),
					"pos" : str(self.conn.pos),
					"wire" : -1 if self.conn.wire is None
						 else str(self.conn.wire.idNum),
				}),
		]

class FupConn(FupBaseClass):
	"""FUP/FBD element connection base class"""

	factory = FupConn_factory

	IN = False
	OUT = False

	CONN_OFFS = 4

	def __init__(self, elem, pos=0, wire=None):
		FupBaseClass.__init__(self)
		self.elem = elem	# The FupElem this connection belongs to
		self.pos = pos		# The y position (top is 0)
		self.wire = wire	# The FupWire this connection is connected to (if any).

	@property
	def relPixCoords(self):
		"""Get the (x, y) pixel coordinates of this connection
		relative to the element's root.
		Raises IndexError, if this does not belong to an element.
		"""
		elem = self.elem
		if elem:
			return elem.getConnRelPixCoords(self)
		raise IndexError

	@property
	def pixCoords(self):
		"""Get the absolute (x, y) pixel coordinates of this connection.
		Raises IndexError, if this does not belong to an element.
		"""
		elem = self.elem
		if elem:
			xAbs, yAbs = elem.pixCoords
			xRel, yRel = self.relPixCoords
			return xAbs + xRel, yAbs + yRel
		raise IndexError

	def canConnectTo(self, other):
		"""Check if this connection can connect to another connection.
		"""
		if self.wire is not None and other.wire is not None:
			return False
		return (self is not other) and\
		       (self.elem is not None and other.elem is not None) and\
		       (self.elem is not other.elem) and\
		       ((self.IN and other.OUT) or\
			(self.OUT and other.IN))

	def connectTo(self, other):
		"""Connect this connection to another.
		Raises ValueError, if the connection cannot be done.
		"""
		if not self.canConnectTo(other):
			raise ValueError
		wire = self.wire or other.wire
		if not wire:
			# Create a new wire
			wire = FupWire(self.elem.grid)
		wire.connect(self)
		wire.connect(other)

	def disconnect(self):
		"""Break the current connection, if any.
		Returns True, if there was a connection.
		"""
		if self.wire:
			self.wire.disconnect(self)
			return True
		return False

class FupConnIn(FupConn):
	"""FUP/FBD element input connection"""
	IN = True

class FupConnOut(FupConn):
	"""FUP/FBD element output connection"""
	OUT = True

class FupElem_factory(XmlFactory):
	def parser_open(self):
		self.inElem = False
		self.elem = None
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		if self.inElem:
			if tag.name == "connections":
				self.parser_switchTo(FupConn.factory(elem=self.elem))
				return
		else:
			if tag.name == "element":
				self.inElem = True
				elemType = tag.getAttr("type")
				x = tag.getAttrInt("x")
				y = tag.getAttrInt("y")
				if elemType == "boolean":
					subType = tag.getAttr("subtype")
					if subType == FupElem_AND.OP_SYM_NAME:
						self.elem = FupElem_AND(
							x=x, y=y, nrInputs=0)
						self.elem.grid = self.grid
						return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if self.inElem:
			if tag.name == "element":
				if self.elem:
					# Insert the element into the grid.
					if not self.elem.inputs:
						raise self.Error("<element> does "
							"not have any inputs.")
					if not all(self.elem.inputs) or\
					   not all(self.elem.outputs):
						raise self.Error("<element> connections "
							"are incomplete.")
					if not self.grid.placeElem(self.elem):
						raise self.Error("<element> caused "
							"a grid collision.")
				self.inElem = False
				self.elem = None
				return
		else:
			if tag.name == "elements":
				self.parser_finish()
				return
		XmlFactory.parser_endTag(self, tag)

class FupElem(FupBaseClass):
	"""FUP/FBD element base class"""

	factory = FupElem_factory

	# Element areas
	EnumGen.start
	AREA_NONE	= EnumGen.item
	AREA_BODY	= EnumGen.item
	AREA_INPUT	= EnumGen.item
	AREA_OUTPUT	= EnumGen.item
	EnumGen.end

	def __init__(self, x, y):
		FupBaseClass.__init__(self)
		self.x = x		# X position as grid coordinates
		self.y = y		# Y position as grid coordinates
		self.grid = None

		self.inputs = []	# The input FupConn-ections
		self.outputs = []	# The output FupConn-ections

	def breakConnections(self, breakInputs=True, breakOutputs=True):
		"""Disconnect all connections.
		"""
		if breakInputs:
			for conn in self.inputs:
				conn.disconnect()
		if breakOutputs:
			for conn in self.outputs:
				conn.disconnect()

	def getInput(self, index):
		try:
			return self.inputs[index]
		except IndexError:
			return None

	def getOutput(self, index):
		try:
			return self.outputs[index]
		except IndexError:
			return None

	def getAreaViaPixCoord(self, pixelX, pixelY):
		"""Get (AREA_xxx, area_index) via pixel coordinates
		relative to the element.
		"""
		return self.AREA_BODY, 0

	def getConnViaPixCoord(self, pixelX, pixelY):
		"""Get a connection via pixel coordinates
		relative to the element.
		"""
		area, idx = self.getAreaViaPixCoord(pixelX, pixelY)
		if area == self.AREA_INPUT:
			return self.inputs[idx]
		elif area == self.AREA_OUTPUT:
			return self.outputs[idx]
		return None

	@property
	def pixCoords(self):
		"""Get the (x, y) positions of this element as absolute pixel coordinates.
		"""
		grid = self.grid
		if grid:
			return self.x * grid.cellPixWidth,\
			       self.y * grid.cellPixHeight
		return 0

	def getConnRelPixCoords(self, conn):
		"""Get the (x, y) pixel coordinates of a connection
		relative to the element's root.
		Raises IndexError, if there is no such connection.
		"""
		raise IndexError

	def isInGridRect(self, gridX0, gridY0, gridX1, gridY1):
		"""Returns true, if this element is placed under
		the specified grid rectangle.
		"""
		x0, y0 = min(gridX0, gridX1), min(gridY0, gridY1)
		x1, y1 = max(gridX0, gridX1), max(gridY0, gridY1)
		return self.x >= x0 and self.y >= y0 and\
		       self.x + self.width - 1 <= x1 and self.y + self.height - 1 <= y1

	@property
	def height(self):
		return 1

	@property
	def width(self):
		return 1

	@property
	def selected(self):
		return self in self.grid.selectedElems

	def remove(self):
		if self.grid:
			self.grid.removeElem(self)

	def draw(self, painter):
		pass

	def prepareContextMenu(self, menu):
		pass

	def __repr__(self):
		return "FupElem(%d, %d)" % (self.x, self.y)

class FupElem_BOOLEAN_factory(FupElem_factory):
	def composer_getTags(self):
		connTags = []
		for inp in self.elem.inputs:
			connTags.extend(inp.factory(conn=inp).composer_getTags())
		for out in self.elem.outputs:
			connTags.extend(out.factory(conn=out).composer_getTags())
		return [
			self.Tag(name="element",
				attrs={
					"type" : "boolean",
					"subtype" : self.elem.OP_SYM_NAME,
					"x" : str(self.elem.x),
					"y" : str(self.elem.y),
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
				])
		]

class FupElem_BOOLEAN(FupElem):
	"""Boolean FUP/FBD element base class"""

	OP_SYM		= ""
	OP_SYM_NAME	= ""	# XML ABI name

	factory = FupElem_BOOLEAN_factory

	def __init__(self, x, y, nrInputs=2):
		FupElem.__init__(self, x, y)

		self.inputs = [ FupConnIn(self, i)\
				for i in range(nrInputs) ]
		self.outputs = [ FupConnOut(self) ]

		lineWidth = 2
		self.__outlinePen = QPen(QColor("#000000"))
		self.__outlinePen.setWidth(lineWidth)
		self.__outlineSelPen = QPen(QColor("#0000FF"))
		self.__outlineSelPen.setWidth(lineWidth)
		self.__connPen = QPen(QColor("#000000"))
		self.__connPen.setWidth(lineWidth)
		self.__connOpenPen = QPen(QColor("#DF6060"))
		self.__connOpenPen.setWidth(lineWidth)
		self.__bgBrush = QBrush(QColor("#FFFFFF"))

	def getAreaViaPixCoord(self, pixelX, pixelY):
		if self.grid:
			cellWidth = self.grid.cellPixWidth
			cellHeight = self.grid.cellPixHeight
			totalWidth = cellWidth
			totalHeight = cellHeight * self.height
			xpad = self.__xpadding
			ypad = self.__ypadding
			if pixelY > ypad and pixelY < totalHeight - ypad:
				if pixelX < xpad:
					# inputs
					idx = pixelY // cellHeight
					return self.AREA_INPUT, idx
				elif pixelX > totalWidth - xpad:
					# outputs
					if pixelY >= totalHeight - cellHeight:
						return self.AREA_OUTPUT, 0
				else:
					# body
					return self.AREA_BODY, 0
		return self.AREA_NONE, 0

	def getConnRelPixCoords(self, conn):
		if self.grid:
			cellHeight = self.grid.cellPixHeight
			cellWidth = self.grid.cellPixWidth
			if isinstance(conn, FupConnIn):
				idx = self.inputs.index(conn)
				x = FupConn.CONN_OFFS
			elif isinstance(conn, FupConnOut):
				idx = self.outputs.index(conn)
				if idx >= 0:
					idx = self.height - 1
					x = cellWidth - FupConn.CONN_OFFS
			if idx >= 0:
				y = (idx * cellHeight) + (cellHeight // 2)
				return x, y
		return FupElem.getConnRelPixCoords(self, conn)

	@property
	def height(self):
		return len(self.inputs)

	@property
	def __xpadding(self):
		if self.grid:
			return self.grid.cellPixWidth // 6
		return 0

	@property
	def __ypadding(self):
		if self.grid:
			return self.grid.cellPixHeight // 8
		return 0

	def draw(self, painter):
		if not self.grid:
			return
		cellWidth = self.grid.cellPixWidth
		cellHeight = self.grid.cellPixHeight

		xpad = self.__xpadding
		ypad = self.__ypadding

		elemHeight = cellHeight * self.height
		elemWidth = cellWidth

		# Draw inputs
		for i, conn in enumerate(self.inputs):
			y = (i * cellHeight) + (cellHeight // 2)
			painter.setPen(self.__connPen if conn.wire
				       else self.__connOpenPen)
			painter.drawLine(0, y, xpad, y)

		# Draw output
		y = elemHeight - (cellHeight // 2)
		painter.setPen(self.__connPen if self.outputs[0].wire
			       else self.__connOpenPen)
		painter.drawLine(cellWidth - xpad, y,
				 cellWidth, y)

		# Draw body
		painter.setPen(self.__outlineSelPen if self.selected
			       else self.__outlinePen)
		painter.setBrush(self.__bgBrush)
		polygon = QPolygon((QPoint(xpad, ypad),
				    QPoint(elemWidth - xpad, ypad),
				    QPoint(elemWidth - xpad, elemHeight - ypad),
				    QPoint(xpad, elemHeight - ypad)))
		painter.drawPolygon(polygon, Qt.OddEvenFill)

		# Draw symbol text
		font = painter.font()
		font.setPointSize(16)
		painter.setFont(font)
		painter.drawText(0, 5,
				 elemWidth, elemHeight - 5,
				 Qt.AlignCenter | Qt.AlignTop,
				 self.OP_SYM)

	def prepareContextMenu(self, menu):
		menu.enableAddInput(True)

class FupElem_AND(FupElem_BOOLEAN):
	"""AND FUP/FBD element"""

	OP_SYM		= "&"
	OP_SYM_NAME	= "and"	# XML ABI name

class FupElem_OPERAND(FupElem):
	"""Generic operand element"""

class FupElem_ASSIGN(FupElem_OPERAND):
	"""Assignment operand element"""

class FupElem_LOAD(FupElem_OPERAND):
	"""Load/read operand element"""

class FupGrid_factory(XmlFactory):
	def parser_open(self):
		self.grid.clear()
		XmlFactory.parser_open(self)

	def parser_beginTag(self, tag):
		if tag.name == "wires":
			self.parser_switchTo(FupWire.factory(grid=self.grid))
			return
		if tag.name == "elements":
			self.parser_switchTo(FupElem.factory(grid=self.grid))
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		if tag.name == "grid":
			self.grid.removeOrphanWires()
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		wireTags = []
		for wire in sorted(self.grid.wires, key=lambda w: w.idNum):
			wireTags.extend(wire.factory(wire=wire).composer_getTags())
		elemTags = []
		for elem in self.grid.elems:
			elemTags.extend(elem.factory(elem=elem).composer_getTags())
		return [
			self.Tag(name="grid",
				tags=[
					self.Tag(name="wires",
						 tags=wireTags),
					self.Tag(name="elements",
						 tags=elemTags),
				],
				attrs={
					"width" : self.grid.width,
					"height" : self.grid.height,
				}),
		]

class FupGrid(object):
	"""FUP/FBD element grid"""

	factory = FupGrid_factory

	def __init__(self, drawWidget, width, height):
		self.__drawWidget = drawWidget
		self.width = width
		self.height = height

		self.elems = []		# The FupElem_xxx()s in this grid
		self.wires = set()	# The FupConnIn/Out()s in this grid

		self.selectedElems = set()

	def clear(self):
		for wire in self.wires:
			wire.disconnectAll()
		self.wires.clear()
		self.elems = []
		self.selectedElems.clear()

	def getUnusedWireIdNum(self):
		"""Get an unused wire idNum.
		"""
		if self.wires:
			return max(w.idNum for w in self.wires) + 1
		return 0

	def addWire(self, wire):
		"""Add a wire to the grid.
		Does nothing, if the wire does exist already.
		"""
		self.wires.add(wire)

	def removeWire(self, wire):
		"""Remove a wire to the grid.
		Does nothing, if the wire does not exist.
		"""
		with contextlib.suppress(KeyError):
			self.wires.remove(wire)

	def getWireById(self, wireIdNum):
		"""Get a wire by its idNum.
		"""
		if wireIdNum >= 0:
			for wire in self.wires:
				if wire.idNum == wireIdNum:
					return wire
		return None

	def removeOrphanWires(self):
		"""Remove all unconnected wires.
		"""
		newWiresSet = set()
		while self.wires:
			wire = self.wires.pop()
			if wire.connections:
				newWiresSet.add(wire)
		self.wires = newWiresSet

	def renumberWires(self):
		"""Re-assign all wire idNums.
		"""
		for i, wire in enumerate(self.wires):
			wire.idNum = i

	@property
	def cellPixWidth(self):
		if self.__drawWidget:
			return self.__drawWidget.cellPixWidth
		return 0

	@property
	def cellPixHeight(self):
		if self.__drawWidget:
			return self.__drawWidget.cellPixHeight
		return 0

	def __haveCollision(self, x, y, height, excludeElems=set()):
		if x < 0 or x >= self.width or\
		   y < 0 or y >= self.height:
			# Position is not on grid.
			return True
		for yy in range(y, y + height):
			elem = self.getElemAt(x, yy)
			if elem in excludeElems:
				continue # Element is ignored.
			if elem:
				return True # Collision with other element.
		return False

	def placeElem(self, elem):
		# Check if we have a collision.
		if self.__haveCollision(elem.x, elem.y, elem.height):
			return False
		# Add the element.
		self.elems.append(elem)
		elem.grid = self
		return True

	def removeElem(self, elem):
		with contextlib.suppress(ValueError):
			self.elems.remove(elem)
		elem.breakConnections()
		with contextlib.suppress(ValueError):
			self.selectedElems.remove(elem)

	def removeElemAt(self, x, y):
		elem = self.getElemAt(x, y)
		if elem:
			self.removeElem(elem)
			return True
		return False

	def moveElemTo(self, elem, toX, toY,
		       relativeCoords=False,
		       checkOnly=False,
		       excludeCheckElems=set()):
		"""Move elem to position (toX, toY).
		If relativeCoords=True, the (toX, toY) coodinates are relative
		to the current position.
		If checkOnly=True, the actual move is not performed.
		All elements included in excludeCheckElems are excluded from
		the collision check.
		"""
		if relativeCoords:
			toX, toY = elem.x + toX, elem.y + toY
		if toX == elem.x and toY == elem.y:
			return True # No move needed
		# Check collision
		excludeElems = excludeCheckElems.copy()
		excludeElems.add(elem) # Can't collide with ourselves.
		if self.__haveCollision(toX, toY, elem.height,
					excludeElems=excludeElems):
			return False # Collision. Cannot move.
		# Move the element.
		if not checkOnly:
			elem.x = toX
			elem.y = toY
		return True

	def getElemAt(self, x, y):
		for elem in self.elems:
			ex, ey = elem.x, elem.y
			ew, eh = elem.width, elem.height
			if x >= ex and x < ex + ew and\
			   y >= ey and y < ey + eh:
				return elem
		return None

	def haveElemAt(self, x, y):
		return self.getElemAt(x, y) is not None

	def getElemsInRect(self, x0, y0, x1, y1):
		"""Get all elements placed within the given grid rectangle.
		"""
		return (elem for elem in self.elems
			if elem.isInGridRect(x0, y0, x1, y1))

	def selectElem(self, elem):
		if elem:
			self.selectedElems.add(elem)

	def selectElemAt(self, x, y):
		elem = self.getElemAt(x, y)
		if elem:
			self.selectElem(elem)
		else:
			self.deselectAll()

	def selectElemsInRect(self, x0, y0, x1, y1, clear=False):
		"""Select all elements within the given grid rectangle.
		"""
		if clear:
			self.deselectAll()
		for elem in self.getElemsInRect(x0, y0, x1, y1):
			self.selectElem(elem)

	def deselectElem(self, elem):
		pass#TODO

	def deselectElemAt(self, x, y):
		pass#TODO

	def deselectAll(self):
		self.selectedElems.clear()

class FupContextMenu(QMenu):
	"""FUP/FBD draw widget context menu."""

	add = Signal(FupElem)
	remove = Signal(int, int)

	def __init__(self, parent=None):
		QMenu.__init__(self, parent)

		self.gridX = 0
		self.gridY = 0

		self.__actInsAND = self.addAction(getIcon("doc_new"),
						  "Insert &AND", self.__addAND)
		self.addSeparator()
		self.__actInsLOAD = self.addAction(getIcon("doc_new"),
						   "Insert &LOAD operand",
						   self.__addLOAD)
		self.__actInsASSIGN = self.addAction(getIcon("doc_new"),
						     "Insert A&SSIGN operand",
						     self.__addASSIGN)
		self.addSeparator()
		self.__actDel = self.addAction(getIcon("doc_close"),
					       "Remove element", self.__del)
		self.addSeparator()
		self.__actAddInp = self.addAction(getIcon("new"),
						  "Add input signal",
						  self.__addInput)

	def __addAND(self):
		self.add.emit(FupElem_AND(self.gridX, self.gridY))

	def __addLOAD(self):
		pass#TODO

	def __addASSIGN(self):
		pass#TODO

	def __del(self):
		self.remove.emit(self.gridX, self.gridY)

	def __addInput(self):
		pass

	def enableInsert(self, en=True):
		self.__actInsAND.setEnabled(en)

	def enableDelete(self, en=True):
		self.__actDel.setEnabled(en)

	def enableAddInput(self, en=True):
		self.__actAddInp.setEnabled(en)

class FupDrawWidget(QWidget):
	"""FUP/FBD draw widget."""

	# Signal: Something in the FUP diagram changed
	diagramChanged = Signal()

	def __init__(self, parent=None):
		QWidget.__init__(self, parent)

		self.__contextMenu = FupContextMenu(self)
		self.__contextMenu.add.connect(self.addElem)
		self.__contextMenu.remove.connect(self.removeElem)

		self.__bgBrush = QBrush(QColor("#F5F5F5"))
		self.__gridPen = QPen(QColor("#E0E0E0"))
		self.__gridPen.setWidth(1)
		self.__textPen = QColor("#808080")
		self.__dragConnPenOpen = QPen(QColor("#FF0000"))
		self.__dragConnPenOpen.setWidth(4)
		self.__dragConnPenClosed = QPen(QColor("#000000"))
		self.__dragConnPenClosed.setWidth(4)
		self.__selRectPen = QPen(QColor("#0000FF"))
		self.__selRectPen.setWidth(3)

		# Start and end pixel coordinates of a selection rectangle.
		self.__selectStartPix = None
		self.__selectEndPix = None

		# Start grid coordinates of an element drag.
		self.__dragStart = None

		# The dragged connection.
		self.__draggedConn = None

		self.__cellHeight = 20
		self.__cellWidth = 60

		self.__grid = FupGrid(self, 12, 32)

		self.resize(self.__grid.width * self.__cellWidth,
			    self.__grid.height * self.__cellHeight)

	def __contentChanged(self):
		self.repaint()
		self.diagramChanged.emit()

	@property
	def grid(self):
		return self.__grid

	@property
	def cellPixHeight(self):
		return self.__cellHeight

	@property
	def cellPixWidth(self):
		return self.__cellWidth

	def addElem(self, elem):
		if self.__grid.placeElem(elem):
			self.__grid.deselectAll()
			self.__grid.selectElem(elem)
			self.__contentChanged()

	def removeElem(self, gridX, gridY):
		if self.__grid.removeElemAt(gridX, gridY):
			self.__contentChanged()

	def moveElem(self, elem, toGridX, toGridY,
		     relativeCoords=False,
		     checkOnly=False,
		     excludeCheckElems=set()):
		if self.__grid.moveElemTo(elem, toGridX, toGridY,
					  relativeCoords=relativeCoords,
					  checkOnly=checkOnly,
					  excludeCheckElems=excludeCheckElems):
			if not checkOnly:
				self.__contentChanged()
			return True
		return False

	def establishWire(self, fromConn, toConn):
		if fromConn and toConn:
			if fromConn.canConnectTo(toConn):
				with contextlib.suppress(ValueError):
					fromConn.connectTo(toConn)
					self.__contentChanged()

	def disconnectConn(self, conn):
		if conn:
			conn.disconnect()
			self.__contentChanged()

	def paintEvent(self, event=None):
		grid = self.__grid
		if not grid:
			return

		size = self.size()
		width, height = size.width(), size.height()
		p = QPainter(self)

		# Draw background
		p.fillRect(self.rect(), self.__bgBrush)

		# Set font
		font = p.font()
		font.setFamily("Mono")
		font.setPointSize(7)
		p.setFont(font)

		# Draw the grid
		p.setPen(self.__gridPen)
		# vertical lines
		for x in range(0, width, self.__cellWidth):
			p.drawLine(x, 0, x, height)
			p.drawText(x, -5, self.__cellWidth, self.__cellHeight,
				   Qt.AlignCenter | Qt.AlignTop,
				   str(x // self.__cellWidth))
		# horizontal lines
		for y in range(0, height, self.__cellHeight):
			p.drawLine(0, y, width, y)
			p.drawText(5, y, self.__cellWidth, self.__cellHeight,
				   Qt.AlignLeft | Qt.AlignVCenter,
				   str(y // self.__cellHeight))

		# Draw the help text, if the grid is empty.
		if not grid.elems:
			p.setPen(self.__textPen)
			font = p.font()
			font.setPointSize(9)
			p.setFont(font)
			x, y = self.__cellWidth + 5, self.__cellHeight * 2 - 5
			p.drawText(x, y, width - x, height - y,
				   Qt.AlignLeft | Qt.AlignTop,
				   "Hints:\n"
				   "* Right click here to insert FUP/FBD element\n"
				   "* Left-drag to connect inputs and outputs\n"
				   "* Middle-click to delete connections and wires")

		# Draw the elements
		prevX, prevY = 0, 0
		for elem in grid.elems:
			xAbs, yAbs = elem.pixCoords
			p.translate(xAbs - prevX, yAbs - prevY)
			prevX, prevY = xAbs, yAbs
			elem.draw(p)
		p.translate(-prevX, -prevY)

		# Draw the connection wires
		for wire in grid.wires:
			wire.draw(p)

		# Draw the dragged connection
		draggedConn = self.__draggedConn
		if draggedConn and draggedConn.elem:
			xAbs, yAbs = draggedConn.pixCoords
			gridX, gridY = self.posToGridCoords(xAbs, yAbs)
			mousePos = self.mapFromGlobal(QCursor.pos())
			elem, _, _, elemRelX, elemRelY = self.posToElem(
					mousePos.x(), mousePos.y())
			# Check if we hit a possible target connection
			p.setPen(self.__dragConnPenOpen)
			if elem:
				targetConn = elem.getConnViaPixCoord(elemRelX, elemRelY)
				if targetConn and draggedConn.canConnectTo(targetConn):
					p.setPen(self.__dragConnPenClosed)
			p.drawLine(xAbs, yAbs, mousePos.x(), mousePos.y())

		# Draw selection rectangle
		if self.__selectStartPix and self.__selectEndPix:
			xAbs0 = min(self.__selectStartPix[0], self.__selectEndPix[0])
			yAbs0 = min(self.__selectStartPix[1], self.__selectEndPix[1])
			xAbs1 = max(self.__selectStartPix[0], self.__selectEndPix[0])
			yAbs1 = max(self.__selectStartPix[1], self.__selectEndPix[1])
			selWidth, selHeight = xAbs1 - xAbs0, yAbs1 - yAbs0
			r = 2
			p.setBrush(Qt.NoBrush)
			p.setPen(self.__selRectPen)
			p.drawRoundedRect(xAbs0, yAbs0,
					  selWidth, selHeight,
					  r, r)

	def posToGridCoords(self, pixX, pixY):
		"""Convert pixel coordinates to grid coordinates.
		"""
		return pixX // self.__cellWidth,\
		       pixY // self.__cellHeight

	def posToElem(self, pixX, pixY):
		"""Convert pixel coordinates to element and element coordinates.
		Returns:
		(FupElem, gridX, gridY, elemRelativePixX, elemRelativePixY)
		"""
		gridX, gridY = self.posToGridCoords(pixX, pixY)
		elem = self.__grid.getElemAt(gridX, gridY)
		elemRelX = pixX % self.__cellWidth
		elemRelY = pixY % self.__cellHeight
		if elem:
			elemRelX += (gridX - elem.x) * self.__cellWidth
			elemRelY += (gridY - elem.y) * self.__cellHeight
		return elem, gridX, gridY, elemRelX, elemRelY

	def mousePressEvent(self, event):
		x, y = event.x(), event.y()

		# Get the element (if any)
		elem, gridX, gridY, elemRelX, elemRelY = self.posToElem(x, y)
		self.__contextMenu.gridX = gridX
		self.__contextMenu.gridY = gridY

		# Get the connection (if any)
		conn = None
		if elem:
			area, areaIdx = elem.getAreaViaPixCoord(elemRelX, elemRelY)
			if area == FupElem.AREA_INPUT:
				conn = elem.getInput(areaIdx)
			elif area == FupElem.AREA_OUTPUT:
				conn = elem.getOutput(areaIdx)

		# Handle left button press
		if event.button() == Qt.LeftButton:
			if elem:
				if area == FupElem.AREA_BODY:
					# Start dragging of the selected element(s).
					self.__dragStart = (gridX, gridY)
					if not elem.selected:
						# Select this element.
						self.__grid.deselectAll()
						self.__grid.selectElem(elem)
						self.repaint()
				if conn and (not conn.wire or conn.OUT):
					# Start dragging of the selected connection.
					self.__draggedConn = conn
					self.repaint()
			else:
				# Start a multi-selection
				self.__grid.deselectAll()
				self.__selectStartPix = (x, y)
				self.__selectEndPix = None
				self.repaint()

		# Handle middle button press
		if event.button() == Qt.MidButton:
			self.disconnectConn(conn)

		# Handle right button press
		if event.button() == Qt.RightButton:
			self.__grid.selectElem(elem)
			self.repaint()
			# Open the context menu
			self.__contextMenu.enableInsert(elem is None)
			self.__contextMenu.enableDelete(elem is not None)
			self.__contextMenu.enableAddInput(False)
			if elem:
				elem.prepareContextMenu(self.__contextMenu)
			self.__contextMenu.exec_(self.mapToGlobal(event.pos()))

		QWidget.mousePressEvent(self, event)

	def mouseReleaseEvent(self, event):
		x, y = event.x(), event.y()
		elem, gridX, gridY, elemRelX, elemRelY = self.posToElem(x, y)

		# Handle end of multi-selection
		if self.__selectStartPix:
			self.__selectStartPix = None
			self.__selectEndPix = None
			self.repaint()

		# Handle end of element dragging
		self.__dragStart = None

		# Handle end of connection dragging
		draggedConn = self.__draggedConn
		if draggedConn:
			# Try to establish the dragged connection.
			if elem:
				targetConn = elem.getConnViaPixCoord(elemRelX, elemRelY)
				self.establishWire(draggedConn, targetConn)
			self.__draggedConn = None
			self.repaint()

		QWidget.mouseReleaseEvent(self, event)

	def mouseMoveEvent(self, event):
		x, y = event.x(), event.y()
		gridX, gridY = self.posToGridCoords(x, y)

		# Handle multi-selection
		if self.__selectStartPix:
			self.__selectEndPix = (x, y)
			# Mark all elements within the rectangle as selected.
			startGridX, startGridY = self.posToGridCoords(*self.__selectStartPix)
			self.__grid.selectElemsInRect(startGridX, startGridY,
						      gridX, gridY, clear=True)
			self.repaint()

		# Handle element dragging
		if self.__dragStart:
			deltaX, deltaY = gridX - self.__dragStart[0],\
					 gridY - self.__dragStart[1]
			if deltaX or deltaY:
				selectedElems = self.__grid.selectedElems
				# First check if we can move all elements
				allOk = True
				for elem in selectedElems:
					if not self.moveElem(elem, deltaX, deltaY,
							     relativeCoords=True,
							     checkOnly=True,
							     excludeCheckElems=selectedElems):
						allOk = False
						break
				# If everything is Ok, move all elements.
				if allOk:
					for elem in selectedElems:
						self.moveElem(elem, deltaX, deltaY,
							      relativeCoords=True,
							      checkOnly=False,
							      excludeCheckElems=selectedElems)
					self.__dragStart = (gridX, gridY)

		# Handle connection dragging
		if self.__draggedConn:
			self.repaint()

		QWidget.mouseMoveEvent(self, event)
