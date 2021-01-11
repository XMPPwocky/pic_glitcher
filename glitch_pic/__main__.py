from glitch_pic import Glitcher
from nmigen_boards.tinyfpga_bx import *
from nmigen import *
from nmigen.build import *

import sys

if sys.argv[1] == "program":
    platform = TinyFPGABXPlatform()
    platform.add_resources([Resource("glitch_trig", 0, Pins("A2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33"))])
    platform.add_resources([Resource("target_reset", 0, Pins("A1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33"))])

    platform.build(Glitcher(), do_program=True)
else:
    from nmigen import *
    from nmigen.back.pysim import Simulator, Delay, Settle

    glitcher = Glitcher()
    sim = Simulator(glitcher)
    sim.add_clock(1/(16e6), domain="sync")

    def process():
        # To be defined
        yield Delay(100e-3)

    sim.add_process(process) # or sim.add_sync_process(process), see below
    with sim.write_vcd("test.vcd", "test.gtkw", traces=glitcher.ports()):
        sim.run()