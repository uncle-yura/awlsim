# -*- coding: utf-8 -*-
#
# AWL simulator - FUP - S7 timer box
#
# Copyright 2018 Michael Buesch <m@bues.ch>
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
#from awlsim.common.cython_support cimport * #@cy
from awlsim.common.compat import *

from awlsim.common.locale import _

from awlsim.common.xmlfactory import *

from awlsim.gui.fup.fup_base import *
from awlsim.gui.fup.fup_elem import *
from awlsim.gui.fup.fup_elemoperand import *


class FupElem_T_factory(FupElem_factory):
	def parser_open(self, tag):
		assert(tag)
		x = tag.getAttrInt("x")
		y = tag.getAttrInt("y")
		subType = tag.getAttr("subtype")
		uuid = tag.getAttr("uuid", None)
		enabled = tag.getAttrBool("enabled", True)
		elemClass = {
			FupElem_T_SI.OP_SYM_NAME	: FupElem_T_SI,
			FupElem_T_SV.OP_SYM_NAME	: FupElem_T_SV,
			FupElem_T_SE.OP_SYM_NAME	: FupElem_T_SE,
			FupElem_T_SS.OP_SYM_NAME	: FupElem_T_SS,
			FupElem_T_SA.OP_SYM_NAME	: FupElem_T_SA,
		}.get(subType)
		if not elemClass:
			raise self.Error(_("Timer subtype '{}' is not known "
				"to the element parser." ,
				subType))
		self.elem = elemClass(x=x, y=y, uuid=uuid, enabled=enabled)
		self.elem.grid = self.grid
		self.subelemsFakeGrid = None
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		if tag.name == "connections":
			self.parser_switchTo(FupConn.factory(elem=self.elem))
			return
		if tag.name == "subelements":
			from awlsim.gui.fup.fup_grid import FupGrid
			if self.subelemsFakeGrid:
				raise self.Error(_("Found multiple <subelements> tags "
					"inside of timer <element>."))
			self.subelemsFakeGrid = FupGrid(drawWidget=None,
							width=FupGrid.INFINITE,
							height=FupGrid.INFINITE)
			self.parser_switchTo(FupElem.factory(grid=self.subelemsFakeGrid,
							     CONTAINER_TAG="subelements"))
			return
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		elem = self.elem

		if tag.name == "element":
			# Add body element
			if not self.subelemsFakeGrid or\
			   len(self.subelemsFakeGrid.elems) != 1 or\
			   not isinstance(self.subelemsFakeGrid.elems[0],
					  FupElem_EmbeddedOper):
				raise self.Error(_("Exactly one subelement of type "
					"'embedded operand' is required in "
					"timer <element>."))
			subelements = self.subelemsFakeGrid.elems
			if subelements:
				elem.bodyOper = subelements[0]
				elem.bodyOper.parentElem = elem
				elem.bodyOper.grid = None

			# Insert the element into the grid.
			if not self.grid.placeElem(elem):
				raise self.Error(_("<element> caused "
					"a grid collision."))
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

	def composer_getTags(self):
		elem = self.elem

		connTags = []
		for inp in elem.inputs:
			connTags.extend(inp.factory(conn=inp).composer_getTags())
		for out in elem.outputs:
			connTags.extend(out.factory(conn=out).composer_getTags())

		bodyOper = elem.bodyOper
		subElemTags = bodyOper.factory(elem=bodyOper).composer_getTags()

		return [
			self.Tag(name="element",
				attrs={
					"type" : "timer",
					"subtype" : elem.OP_SYM_NAME,
					"x" : str(elem.x),
					"y" : str(elem.y),
					"uuid" : str(elem.uuid),
					"enabled" : "0" if not elem.enabled else "",
				},
				tags=[
					self.Tag(name="connections",
						 tags=connTags),
					self.Tag(name="subelements",
						 tags=subElemTags),
				])
		]

class FupElem_T(FupElem):
	"""FUP/FBD S7 timer box.
	"""

	factory = FupElem_T_factory

	OP_SYM		= None
	OP_SYM_NAME	= None # XML ABI name

	def __init__(self, x, y, **kwargs):
		FupElem.__init__(self, x, y, **kwargs)

		self.inputs = [
			FupConnIn(self, text="EN"),
			FupConnIn(self, text="S"),
			FupConnIn(self, text="TV"),
			FupConnIn(self, text="R"),
		]

		self.outputs = [
			FupConnOut(self, text="BIN"),
			FupConnOut(self, text="BCD"),
			FupConnOut(self, text="Q"),
			FupConnOut(self, text="ENO"),
		]

		self.bodyOper = FupElem_EmbeddedOper(parentElem=self)

	# Overridden method. For documentation see base class.
	def getAreaViaPixCoord(self, pixelX, pixelY):
		if self.grid:
			cellWidth = self.grid.cellPixWidth
			cellHeight = self.grid.cellPixHeight
			totalWidth = cellWidth
			totalHeight = cellHeight * self.height
			xpad, ypad = self._xpadding, self._ypadding

			if pixelY >= ypad and pixelY < cellHeight and\
			   pixelX >= xpad and pixelX < cellWidth - xpad:
				return self.AREA_BODYOPER, 0

			if pixelY >= cellHeight + ypad and\
			   pixelY < totalHeight - ypad:
				if pixelX < xpad:
					# inputs
					idx = (pixelY // cellHeight) - self.headerHeight
					if idx >= 0 and idx < len(self.inputs):
						return self.AREA_INPUT, idx
				elif pixelX >= totalWidth - xpad:
					# outputs
					idx = pixelY // cellHeight
					height = self.height
					first = height - len(self.outputs)
					if idx >= first and idx < height:
						idx -= first
						return self.AREA_OUTPUT, idx
				else:
					# body
					return self.AREA_BODY, 0
		return self.AREA_NONE, 0

	# Overridden method. For documentation see base class.
	def getConnRelCoords(self, conn):
		x, y = 0, -1
		if conn.IN:
			y = self.inputs.index(conn)
			if y >= 0:
				y += self.headerHeight
		elif conn.OUT:
			y = self.outputs.index(conn)
			if y >= 0:
				y = self.height - len(self.outputs) + y
		if x >= 0 and y >= 0:
			return x, y
		return FupElem.getConnRelCoords(self, conn)

	@property
	def headerHeight(self):
		return 2

	# Overridden method. For documentation see base class.
	@property
	def height(self):
		return max(len(self.inputs), len(self.outputs)) + self.headerHeight

	# Overridden method. For documentation see base class.
	def draw(self, painter):
		grid = self.grid
		if not grid:
			return
		cellWidth = grid.cellPixWidth
		cellHeight = grid.cellPixHeight
		xpad, ypad = self._xpadding, self._ypadding
		height = self.height
		headerHeight = self.headerHeight
		elemHeight = cellHeight * height
		elemWidth = cellWidth
		selected = self.selected

		# Draw body
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.setBrush(self._bgSelBrush if selected
				 else self._bgBrush)
		(tlX, tlY), (trX, trY), (blX, blY), (brX, brY) = self._calcBodyBox()
		painter.drawRoundedRect(tlX, tlY + cellHeight,
					trX - tlX, blY - (tlY + cellHeight),
					self.BODY_CORNER_RADIUS,
					self.BODY_CORNER_RADIUS)

		# Draw inputs
		painter.setFont(self.getFont(8))
		for i, conn in enumerate(self.inputs):
			cellIdx = i + headerHeight # skip header

			x = conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			if conn.text in {"S", "TV"} and not conn.isConnected:
				painter.setPen(self._connOpenPen)
			else:
				painter.setPen(self._connPen)
			painter.drawLine(x, y, xpad, y)

			x = xpad + 2
			y = (cellIdx * cellHeight)
			painter.drawText(x, y,
					 elemWidth, cellHeight,
					 Qt.AlignLeft | Qt.AlignVCenter,
					 conn.text)

		# Draw outputs
		painter.setFont(self.getFont(8))
		cellIdx = height - 1
		for conn in reversed(self.outputs):
			x = cellWidth - conn.drawOffset
			y = (cellIdx * cellHeight) + (cellHeight // 2)
			painter.setPen(self._connPen)
			painter.drawLine(cellWidth - xpad, y,
					 x, y)

			x = 0
			y = (cellIdx * cellHeight)
			painter.drawText(x, y,
					 elemWidth - xpad - 2, cellHeight,
					 Qt.AlignRight | Qt.AlignVCenter,
					 conn.text)
			cellIdx -= 1

		# Draw element descriptor text
		painter.setFont(self.getFont(9, bold=True))
		painter.setPen(self._outlineSelPen if selected
			       else self._outlinePen)
		painter.drawText(0, cellHeight,
				 elemWidth, cellHeight,
				 Qt.AlignHCenter | Qt.AlignVCenter,
				 self.OP_SYM)

		# Draw body operator
		self.bodyOper.draw(painter)

		# Draw disable-marker
		self._drawDisableMarker(painter)

	# Overridden method. For documentation see base class.
	def edit(self, parentWidget):
		return self.bodyOper.edit(parentWidget)

	# Overridden method. For documentation see base class.
	def expand(self, expand=True, area=None):
		if not expand or area == self.AREA_BODYOPER:
			changed = self.bodyOper.expand(expand)
			self.expanded = self.bodyOper.expanded
			return changed
		return False

	# Overridden method. For documentation see base class.
	def prepareContextMenu(self, menu, area=None, conn=None):
		menu.enableEdit(True)
		menu.enableDisconnWire(conn is not None and conn.isConnected)

class FupElem_T_SI(FupElem_T):
	"""FUP/FBD S7 timer box - SI
	"""

	OP_SYM		= "pulse"
	OP_SYM_NAME	= "si" # XML ABI name

class FupElem_T_SV(FupElem_T):
	"""FUP/FBD S7 timer box - SV
	"""

	OP_SYM		= "ex pulse"
	OP_SYM_NAME	= "sv" # XML ABI name

class FupElem_T_SE(FupElem_T):
	"""FUP/FBD S7 timer box - SE
	"""

	OP_SYM		= "ON-dly"
	OP_SYM_NAME	= "se" # XML ABI name

class FupElem_T_SS(FupElem_T):
	"""FUP/FBD S7 timer box - SS
	"""

	OP_SYM		= "ex ON-dly"
	OP_SYM_NAME	= "ss" # XML ABI name

class FupElem_T_SA(FupElem_T):
	"""FUP/FBD S7 timer box - SA
	"""

	OP_SYM		= "OFF-dly"
	OP_SYM_NAME	= "sa" # XML ABI name
