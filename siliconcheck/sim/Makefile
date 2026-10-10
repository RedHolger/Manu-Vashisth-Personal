# SiliconCheck simulation harness (cocotb + Icarus).
# Usage: make TOP=axis_adapter TESTMOD=test_axis DEPTH=16 DW=32
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
RTL_DIR := $(abspath ../rtl)
VERILOG_SOURCES += $(RTL_DIR)/fifo.sv $(RTL_DIR)/axis_adapter.sv
TOPLEVEL := $(TOP)
MODULE := $(TESTMOD)
SIM_BUILD ?= $(abspath sim_build/$(TOP)_$(DEPTH)x$(DW))
export PYTHONPATH := $(abspath ../tests):$(PYTHONPATH)
COMPILE_ARGS += -g2012
export CFG_DEPTH := $(DEPTH)
export CFG_DW := $(DW)
# Parameter override attempt; verified per-run by a DEPTH-sensitive assertion.
COMPILE_ARGS += -P $(TOP).DEPTH=$(DEPTH) -P $(TOP).DATA_WIDTH=$(DW)
include $(shell cocotb-config --makefiles)/Makefile.sim
