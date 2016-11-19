# -*- coding: utf-8 -*-
#
# AWL simulator - instructions
#
# Copyright 2012-2014 Michael Buesch <m@bues.ch>
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

from awlsim.core.instructions.main import * #@nocy
from awlsim.core.operators import *
#from awlsim.core.instructions.main cimport * #@cy


class AwlInsn_INCAR2(AwlInsn): #+cdef

	__slots__ = ()

	def __init__(self, cpu, rawInsn=None, **kwargs):
		AwlInsn.__init__(self, cpu, AwlInsn.TYPE_INCAR2, rawInsn, **kwargs)
		self.assertOpCount((0, 1))
		if self.ops:
			self.ops[0].assertType(AwlOperator.IMM_PTR, widths={32,})

	def run(self):
#@cy		cdef S7StatusWord s

		ar = self.cpu.ar2.get()
		if self.ops:
			ar = (ar & 0xFF000000) |\
			     (((ar & 0x00FFFFFF) + self.ops[0].value.toPointerValue()) & 0x00FFFFFF)
		else:
			ar = (ar & 0xFF000000) |\
			     (((ar & 0x00FFFFFF) + self.cpu.accu1.getSignedWord()) & 0x00FFFFFF)
		self.cpu.ar2.set(ar)
