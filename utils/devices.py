from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt
from utils.db_lib import DBConnection

class Dewar(Device):
    most_recent = Cpt(EpicsSignalRO, 'mostRecent', string=True)
    barcode = Cpt(EpicsSignalRO, 'barcode', string=True)

    def __init__(self, *args, **kwargs):
        self.position_triggered = False
        self.puck_scanned = False
        super().__init__(*args, **kwargs)
        self.most_recent.subscribe(self.handle_trigger)
        self.barcode.subscribe(self.handle_scan)
        self.db_connection = DBConnection()

    def handle_trigger(self, **kwargs):
        self.position_triggered = True
        self.current_position = kwargs['value']
        self.insertIntoContainer()

    def handle_scan(self, **kwargs):
        self.puck_scanned = True
        self.current_barcode = kwargs['value']
        self.insertIntoContainer()


    def insertIntoContainer(self):
        if self.position_triggered and self.puck_scanned:
            print(f'Inserting {self.current_barcode} into {self.current_position}')
            dewarID = self.db_connection.primary_dewar_uid
            puckID = self.db_connection.getContainer(filter={'name': self.puck_scanned})
            self.db_connection.insertIntoContainer(dewarID, self.current_position, puckID)
            self.puck_scanned = False
            self.position_triggered = False 



    
