from nmigen import *
from nmigen.build import *
from nmigen_boards.tinyfpga_bx import *


class Glitcher(Elaboratable):
    def elaborate(self, platform):

        if platform is not None:
            self.glitch_trigger_out = platform.request("glitch_trig")
            self.target_reset = platform.request("target_reset")


        else:
            self.glitch_trigger_out = Signal()
            self.target_reset = Signal()

        counter  = Signal(18)

        glitch_trigger = Signal()

        TIME_PER_CLOCK = 1/16e6 # 16mhz clk
        counter_glitch = Signal(19)

        glitch_duration = int(1.25e-6 // TIME_PER_CLOCK)

        glitch_start_clocks = Signal.like(counter_glitch, reset=1)
        glitch_start = int(100e-6 // TIME_PER_CLOCK)

        reset_duration = int(50e-6 // TIME_PER_CLOCK)


        print(glitch_start)


        m = Module()
        if platform:
            m.domains.sync = ClockDomain()
            clk16   = platform.request("clk16", 0)
            m.d.comb += ClockSignal().eq(clk16.i)


        m.d.sync += counter.eq(counter + 1)
        m.d.comb += self.target_reset.o.eq(~(counter < reset_duration))
        m.d.comb += self.glitch_trigger_out.o.eq(~glitch_trigger)
        
        with m.FSM():
            with m.State("IDLE"):
                m.d.comb += glitch_trigger.eq(False)
                with m.If(counter == 0):
                    m.d.sync += counter_glitch.eq(0)
                    m.next = "ARMED"
            
            with m.State("ARMED"):
                m.d.sync += counter_glitch.eq(counter_glitch + 1)
                #print(type(reset_duration), glitch_start)
                m.d.comb += glitch_trigger.eq(False)
                with m.If(counter >= reset_duration + glitch_start_clocks):
                    m.next = "GLITCHING"
            
            with m.State("GLITCHING"):
                m.d.sync += counter_glitch.eq(counter_glitch + 1)
                m.d.comb += glitch_trigger.eq(True)
                with m.If(counter >= reset_duration + glitch_start_clocks + glitch_duration):
                    m.next = "IDLE"
                    with m.If(glitch_start_clocks >= int(300e-6//TIME_PER_CLOCK)):
                        m.d.sync += glitch_start_clocks.eq(1)
                    with m.Else():
                        m.d.sync += glitch_start_clocks.eq(glitch_start_clocks + int(0.6e-6 // TIME_PER_CLOCK))
        print("ok")
        return m

    def ports(self):
        return [self.glitch_trigger_out, self.target_reset]