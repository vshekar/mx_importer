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
    a = Cpt(Puck, "A}", name="A")
    b = Cpt(Puck, "B}", name="B")
    c = Cpt(Puck, "C}", name="C")


class Dewar(Device):
    sectors = DDC(
        {
            f"sector_{i}": (Sector, f"{{Puck:{i}", {"name": "sector_{i}"})
            for i in range(1, 9)
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_connection = DBConnection()
        self.puck_positions = [
            f"{a}{b}"
            for a, b in product([str(i) for i in range(1, 9)], ["A", "B", "C"])
        ]

        for i in range(1, 9):
            sector: Sector = getattr(self.sectors, "sector_{i}")
            sector.a.barcode.subscribe(self.handle_barcode)
            sector.b.barcode.subscribe(self.handle_barcode)
            sector.c.barcode.subscribe(self.handle_barcode)

    def handle_barcode(self, value, old_value, **kwargs):
        if old_value != "" and value:
            print(f"Loading puck {value}. Kwargs : {kwargs}")
        elif value != "" and old_value:
            print(f"Unloading puck {old_value}. Kwargs : {kwargs}")

    def toggle_system(self, value, **kwargs):
        print(value)
        if not value:
            print("System off")
            return

        print("System on")
        for sector_num in range(1, 9):
            sector = getattr(self.sectors, f"sector_{sector_num}", None)
            if sector is None:
                continue
            for puck_pos in ["A", "B", "C"]:
                print(
                    f"{sector_num}{puck_pos} : {getattr(sector, puck_pos).barcode.get()}"
                )

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
        print(f"Loading {puck_name} into {pos_name}")

    def handle_unloading(self, pos_name):
        puck_name = self.puck_barcode[pos_name].get()
        print(f"Unloading {puck_name} from {pos_name}")

    def insertIntoContainer(self, barcode, position):
        print(f"Inserting {barcode} into {position}")
        dewarID = self.db_connection.primary_dewar_uid
        puckID = self.db_connection.getContainer(filter={"name": self.puck_scanned})
        self.db_connection.insertIntoContainer(dewarID, position, puckID)

    def removeFromContainer(self, barcode, position):
        print(f"Removing {barcode} from {position}")
        dewarID = self.db_connection.primary_dewar_uid
        puckID = self.db_connection.getContainer(filter={"name": self.puck_scanned})
        result = self.db_connection.removeFromContainer(dewarID, position, puckID)
        if result:
            print(f"Successfully removed {barcode} from {position}")
        else:
            print(f"Error in removing {barcode} from {position}")


def create_dewar_class(config: "dict[str, Any]"):
    num_sectors = config["dewars"]["sectors"]["total"]

    return type(
        f"Dewar_{num_sectors}Sectors",
        (Dewar,),
        {
            "sectors": DDC(
                {
                    f"sector_{i}": (Sector, f"{{Puck:{i}}}", {"name": f"sector_{i}"})
                    for i in range(1, num_sectors + 1)
                }
            )
        },
    )
