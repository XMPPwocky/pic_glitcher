from nmigen import *
from nmigen.build import *
from nmigen_boards.tinyfpga_bx import *

from nmigen              import Elaboratable, Module

from luna                import top_level_cli
from luna.full_devices   import USBSerialDevice


class USBSerialDeviceExample(Elaboratable):
    """ Device that acts as a 'USB-to-serial' loopback using our premade gateware. """

    def elaborate(self, platform):
        m = Module()

        return m


class Glitcher(Elaboratable):
    def elaborate(self, platform):

        if platform is not None:
            self.glitch_trigger_out = platform.request("glitch_trig")
            self.target_reset = platform.request("target_reset")


        else:
            self.glitch_trigger_out = Signal()
            self.target_reset = Signal()

        counter  = Signal(16)

        glitch_trigger = Signal()

        TIME_PER_CLOCK = 1/48e6 # 48mhz clk
        counter_glitch = Signal(17)

        
        glitch_duration =  Signal.like(counter_glitch, reset=int(1e-6 // TIME_PER_CLOCK)) # 1.25 worked

        glitch_start_min_clocks = int(0e-6//TIME_PER_CLOCK)
        glitch_start_max_clocks = int(180e-6//TIME_PER_CLOCK)
        glitch_start_clocks = Signal.like(counter_glitch, reset=glitch_start_min_clocks)

        reset_duration = int(100e-6 // TIME_PER_CLOCK)



        m = Module()

        if platform:

            # Generate our domain clocks/resets.
            m.submodules.car = platform.clock_domain_generator()

            # Create our USB-to-serial converter.
            ulpi = platform.request(platform.default_usb_connection)
            m.submodules.usb_serial = usb_serial = \
                    USBSerialDevice(bus=ulpi, idVendor=0x16d0, idProduct=0x0f3b)

            m.d.comb += [
                # Place the streams into a loopback configuration...
                usb_serial.tx.payload  .eq(usb_serial.rx.payload + 1),
                usb_serial.tx.valid    .eq(usb_serial.rx.valid),
                usb_serial.tx.first    .eq(usb_serial.rx.first),
                usb_serial.tx.last     .eq(usb_serial.rx.last),
                #usb_serial.rx.ready    .eq(usb_serial.tx.ready),

                # ... and always connect by default.
                usb_serial.connect     .eq(1)
            ]
        
        GLITCH_ADJ_CLOCKS = 1
        GLITCH_MAX_CLOCKS = int(5e-6 // TIME_PER_CLOCK)

        # USB commands
        usb_char = Signal.like(usb_serial.rx.payload)
        with m.FSM(name="USB"):
            with m.State("IDLE"):
                m.d.comb += [
                    usb_serial.rx.ready.eq(True),
                ]
                with m.If(usb_serial.rx.valid):
                    m.d.comb += [
                        usb_serial.rx.ready.eq(False),
                    ]
                    m.d.sync += usb_char.eq(usb_serial.rx.payload)
                    m.next = "PARSING"
            with m.State("PARSING"):
                m.d.comb += [
                    usb_serial.rx.ready.eq(True),
                ]
                m.next = "IDLE"

                with m.If(usb_char == ord(b"q")):
                    m.d.sync += glitch_duration.eq(Mux(
                        glitch_duration > GLITCH_ADJ_CLOCKS,
                        glitch_duration - GLITCH_ADJ_CLOCKS,
                        GLITCH_ADJ_CLOCKS))
                with m.Elif(usb_char == ord(b"w")):
                    m.d.sync += glitch_duration.eq(Mux(
                        glitch_duration < (GLITCH_MAX_CLOCKS - GLITCH_ADJ_CLOCKS),
                        glitch_duration+GLITCH_ADJ_CLOCKS,
                        GLITCH_MAX_CLOCKS))
                #m.d.sync += self.glitch_trigger_out.o.eq(usb_char[0])


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
                    with m.If(glitch_start_clocks >= glitch_start_max_clocks):
                        m.d.sync += glitch_start_clocks.eq(glitch_start_min_clocks)
                        #m.d.sync += glitch_duration.eq(glitch_duration + 1)
                    with m.Else():
                        m.d.sync += glitch_start_clocks.eq(glitch_start_clocks + int(0.05e-6 // TIME_PER_CLOCK))
                        
        print("ok")
        return m

    def ports(self):
        return [self.glitch_trigger_out, self.target_reset]