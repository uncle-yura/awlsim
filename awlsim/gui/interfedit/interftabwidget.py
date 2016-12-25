# -*- coding: utf-8 -*-
#
# AWL simulator - Block interface table edit widget
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

from awlsim.gui.interfedit.interftabmodel import *


class AwlInterfaceView(QTableView):
	# Signal: Keyboard focus in/out event.
	focusChanged = Signal(bool)

	def __init__(self, parent=None):
		QTableView.__init__(self, parent)

		if isQt4:
			self.verticalHeader().setMovable(True)
		else:
			self.verticalHeader().setSectionsMovable(True)
		self.verticalHeader().sectionMoved.connect(self.__rowMoved)

		self.pressed.connect(self.__handleMousePress)

		self.setModel(AwlInterfaceModel())

	def __rebuild(self):
		model = self.model()
		yscroll = self.verticalScrollBar().value()
		xscroll = self.horizontalScrollBar().value()
		self.setModel(None)
		self.setModel(model)
		self.verticalScrollBar().setValue(yscroll)
		self.horizontalScrollBar().setValue(xscroll)

	def __rowMoved(self, logicalIndex, oldVisualIndex, newVisualIndex):
		self.model().moveEntry(oldVisualIndex, newVisualIndex)
		self.__rebuild()

	def resizeEvent(self, ev):
		QTableView.resizeEvent(self, ev)

		model = self.model()
		if model:
			hdr = self.horizontalHeader()
			idx = 0
			if hdr.sectionSize(idx) < 150:
				hdr.resizeSection(idx, 150)
			idx = 3 if model.haveInitValue else 2
			if hdr.sectionSize(idx) < 200:
				hdr.resizeSection(idx, 200)

	def deleteRow(self, index=None):
		if not index:
			index = self.currentIndex()
		if index:
			self.model().deleteRow(index.row())

	def __handleMousePress(self, index):
		btns = QApplication.mouseButtons()
		if btns & Qt.RightButton:
			pass#TODO context menu

	def keyPressEvent(self, ev):
		QTableView.keyPressEvent(self, ev)

		if ev.key() == Qt.Key_Delete:
			self.deleteRow()

	def focusInEvent(self, ev):
		QTableView.focusInEvent(self, ev)
		self.focusChanged.emit(True)

	def focusOutEvent(self, ev):
		QTableView.focusOutEvent(self, ev)
		self.focusChanged.emit(False)
