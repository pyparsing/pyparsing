import statemachine
import trafficlight

tl = trafficLight.Red()
for i in range(10):
    print(tl, end='')
    print(("STOP", "GO")[tl.carsCanGo])
    tl.crossingSignal()
    tl.delay()
    print()

    tl = tl.nextState()
