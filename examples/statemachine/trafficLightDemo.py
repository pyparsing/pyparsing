#
# trafficLightDemo.py
#
# Example of a simple state machine modeling the state of a traffic light
#

import statemachine
import trafficlightstate


class TrafficLight:
    def __init__(self):
        # start light in Red state
        self._state = trafficlightstate.Red()

    def change(self):
        self._state = self._state.next_state()

    # get light behavior/properties from current state
    def __getattr__(self, attrname):
        return getattr(self._state, attrname)

    def __str__(self):
        return "{0}: {1}".format(self.__class__.__name__, self._state)


light = TrafficLight()
for i in range(10):
    print("{0} {1}".format(light, ("STOP", "GO")[light.cars_can_go]))
    light.crossing_signal()
    light.delay()
    print()

    light.change()
