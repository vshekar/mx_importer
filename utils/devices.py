from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt

class Dewar(Device):
    most_recent = Cpt(EpicsSignal, 'mostRecent', string=True)
    barcode = Cpt(EpicsSignal, 'barcode', string=True)
    