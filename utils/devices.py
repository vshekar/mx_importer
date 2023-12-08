from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import DynamicDeviceComponent as DDC
from ophyd import Component as Cpt
from utils.db_lib import DBConnection
from itertools import product
from typing import Any


class Puck(Device):
    barcode = Cpt(EpicsSignalRO, "Barcode", name="Barcode")
    success = Cpt(EpicsSignalRO, "Success", name="Success")
    metadata = Cpt(EpicsSignalRO, "Metadata", name="Metadata")


class Sector(Device):
    A = Cpt(Puck, "A}", name="A")
    B = Cpt(Puck, "B}", name="B")
    C = Cpt(Puck, "C}", name="C")


class Dewar(Device):
    sectors = DDC(
        {
            f"sector_{i}": (Sector, f"{{Puck:{i}", {"name": "sector_{i}"})
            for i in range(1, 9)
        }
    )
    num_sectors = 8

    def __init__(self, *args, beamline_id='amx', db_host='localhost', owner='mx', **kwargs):
        super().__init__(*args, **kwargs)
        self.db_connection = DBConnection(beamline_id=beamline_id, host=db_host, owner=owner)
        
        for i in range(1, self.num_sectors+1):
            sector: Sector = getattr(self.sectors, f"sector_{i}")
            sector.A.barcode.subscribe(self.handle_barcode)
            sector.B.barcode.subscribe(self.handle_barcode)
            sector.C.barcode.subscribe(self.handle_barcode)
    
    def handle_barcode(self, value, old_value, **kwargs):
        location = kwargs['obj'].parent.name.split("_")[-1]
        sector = kwargs['obj'].parent.name.split("_")[-2]
        puck_pos = self.pos_to_int(sector, location)
        if isinstance(value, str) and value != '':
            print(f"Loading puck {value} at pos {puck_pos}")
            self.insertIntoContainer(value, puck_pos)

        elif value == "" and isinstance(old_value, str) and old_value != "":
            print(f"Unloading puck {old_value} at pos {puck_pos}")
            self.removeFromContainer(old_value, puck_pos)

    def pos_to_int(self, sector, location):
        sector = int(sector)
        location = ord(location) - 65
        return (sector-1)*3 + location

    def remove_newline(self, barcode):
        if barcode.endswith("\\n"):
            barcode = barcode.split("\\n")[0]
        barcode = str(barcode).strip()
        return barcode

    def insertIntoContainer(self, barcode, position):
        barcode = self.remove_newline(barcode)
        print(f"Inserting {barcode} into {position}")
        dewarID = self.db_connection.primary_dewar_uid
        puckID = self.db_connection.getContainer(filter={"name": barcode}).get('uid')
        if puckID:
            self.db_connection.insertIntoContainer(dewarID, position, puckID)
        else:
            print(f"Puck ID not found for {barcode}")

    def removeFromContainer(self, barcode, position):
        barcode = self.remove_newline(barcode)
        print(f"Removing {barcode} from {position}")
        dewarID = self.db_connection.primary_dewar_uid
        puckID = self.db_connection.getContainer(filter={"name": barcode})['uid']
        result = self.db_connection.removeFromContainer(dewarID, position, puckID)
        if result:
            print(f"Successfully removed {barcode} from {position}")
        else:
            print(f"Error in removing {barcode} from {position}")


def create_dewar_class(config: "dict[str, Any]"):
    num_sectors = config["dewar"]["sectors"]["total"]

    return type(
        f"Dewar_{num_sectors}Sectors",
        (Dewar,),
        {
            "sectors": DDC(
                {
                    f"sector_{i}": (Sector, f"{{Puck:{i}", {"name": f"sector_{i}"})
                    for i in range(1, num_sectors + 1)
                }
            )
        },
    )
