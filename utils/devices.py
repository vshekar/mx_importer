from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import DynamicDeviceComponent as DDC
from ophyd import Component as Cpt
from utils.db_lib import DBConnection
from itertools import product

class Puck(Device):
    barcode = Cpt(EpicsSignalRO, 'Barcode', name='Barcode')
    success = Cpt(EpicsSignalRO, 'Success', name='Success')
    error = Cpt(EpicsSignalRO, 'Error', name='Error')

class Sector(Device):
    a = Cpt(Puck, 'a}', name='a')
    b = Cpt(Puck, 'b}', name='b')
    c = Cpt(Puck, 'c}', name='c')

class Dewar(Device):
    system_on_pv = Cpt(EpicsSignalRO, '{IOC:BARCODE}OnOff', name='system_on')
    loading_in = Cpt(EpicsSignalRO, '{IOC:BARCODE}InOut')
    sectors = DDC({f'sector_{i}': (Sector, f'{{Puck:{i}', {'name':'sector_{i}'}) for i in range(1,2)})

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_on_pv: EpicsSignalRO
        self.system_on_pv.subscribe(self.toggle_system)
        self.system_on = self.system_on_pv.get()
        self.db_connection = DBConnection()
        self.puck_positions = [f'{a}{b}' for a,b in product([str(i) for i in range(1,9)], ['a', 'b', 'c'])] 
    
    def toggle_system(self, value, **kwargs):
        print(value)
        if not value:
            print('System off')
            return
        
        print('System on')
        for sector_num in range(1,9):
            sector = getattr(self.sectors, f'sector_{sector_num}', None)
            if sector is None:
                continue
            for puck_pos in ['a', 'b', 'c']:
                print(f'{sector_num}{puck_pos} : {getattr(sector, puck_pos).barcode.get()}')
            
        self.handle_loading_unloading()
            

    def handle_loading_unloading(self):
        self.loading_in: EpicsSignalRO
        loading = self.loading_in.get()
        if loading:
            self.handle_loading()
        else:
            self.handle_unloading()

    def handle_loading(self, pos_name):
        puck_name = self.puck_barcode[pos_name].get()
        print(f'Loading {puck_name} into {pos_name}')

    def handle_unloading(self, pos_name):
        puck_name = self.puck_barcode[pos_name].get()
        print(f'Unloading {puck_name} from {pos_name}')

    def insertIntoContainer(self, barcode, position):
        print(f'Inserting {barcode} into {position}')
        dewarID = self.db_connection.primary_dewar_uid
        puckID = self.db_connection.getContainer(filter={'name': self.puck_scanned})
        self.db_connection.insertIntoContainer(dewarID, position, puckID)
   
    def removeFromContainer(self, barcode, position):
        print(f'Removing {barcode} from {position}')
        dewarID = self.db_connection.primary_dewar_uid
        puckID = self.db_connection.getContainer(filter={'name': self.puck_scanned})
        self.db_connection.removeFromContainer(dewarID, position, puckID)
