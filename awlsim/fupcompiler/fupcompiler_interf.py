# -*- coding: utf-8 -*-
#
# AWL simulator - FUP compiler - Interface
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

from awlsim.fupcompiler.fupcompiler_base import *


class FupCompiler_InterfFactory(XmlFactory):
	def parser_open(self, tag=None):
		XmlFactory.parser_open(self, tag)

	def parser_beginTag(self, tag):
		#TODO
		XmlFactory.parser_beginTag(self, tag)

	def parser_endTag(self, tag):
		#TODO
		if tag.name == "interface":
			self.parser_finish()
			return
		XmlFactory.parser_endTag(self, tag)

class FupCompiler_Interf(FupCompiler_BaseObj):
	factory = FupCompiler_InterfFactory

	def __init__(self, compiler):
		FupCompiler_BaseObj.__init__(self)
		self.compiler = compiler	# FupCompiler