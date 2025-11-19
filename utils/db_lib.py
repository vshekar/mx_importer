import os
from typing import Dict, Any
import time
import getpass
import amostra.client.commands as acc
import conftrak.client.commands as ccc
from utils import distance_from_reso, energy2wave

# from analysisstore.client.commands import AnalysisClient
import conftrak.exceptions
import requests
from pathlib import Path
import getpass


class DBConnection:
    def __init__(
        self,
        beamline_id="99id1",
        host=None,
        owner=None,
        api_url=None,
        detector_name=None,
    ):
        self.detector_name = "Eiger" if detector_name is None else detector_name
        if not host:
            main_server = os.environ.get("MONGODB_HOST", "localhost")
        else:
            main_server = host
        self.api_url = api_url

        services_config = {
            "amostra": {"host": main_server, "port": "7770"},
            "conftrak": {"host": main_server, "port": "7771"},
            "metadataservice": {"host": main_server, "port": "7772"},
            "analysisstore": {"host": main_server, "port": "7773"},
        }
        self.sample_ref = acc.SampleReference(**services_config["amostra"])
        self.container_ref = acc.ContainerReference(**services_config["amostra"])
        self.request_ref = acc.RequestReference(**services_config["amostra"])

        self.configuration_ref = ccc.ConfigurationReference(
            **services_config["conftrak"]
        )
        self.beamline_id = beamline_id
        if owner is not None:
            self.owner = getpass.getuser()
        else:
            self.owner = owner

    def getContainer(self, filter=None):
        container = {}
        if filter:
            containers = list(self.container_ref.find(**filter))
            if containers:
                container = max(
                    containers, key=lambda x: x.get("modified_time", float("-inf"))
                )
            else:
                container = {}
        return container

    def createContainer(self, name: str, capacity: int, kind: str, **kwargs):
        if capacity is not None:
            kwargs["content"] = [""] * capacity
        uid = self.container_ref.create(
            name=name, owner=self.owner, kind=kind, modified_time=time.time(), **kwargs
        )
        return uid

    def getOrCreateContainerID(self, name: str, capacity: int, kind: str, **kwargs):
        container = self.getContainer(
            filter={"name": name, "kind": kind, "owner": self.owner}
        )
        if not container:
            container_id = self.createContainer(name, capacity, kind, **kwargs)
        else:
            container_id = container["uid"]
        return container_id

    def updateContainer(
        self, container: Dict[str, Any]
    ):  # really updating the contents
        cont = container["uid"]
        q = {"uid": container.pop("uid", "")}
        container.pop("time", "")
        self.container_ref.update(
            q, {"content": container["content"], "modified_time": time.time()}
        )

        return cont

    def emptyContainer(self, id):
        c = self.getContainer(filter={"uid": id})
        if c is not None:
            c["content"] = [""] * len(c["content"])
            self.updateContainer(c)
            return True
        return False

    def insertIntoContainer(self, parent_uid, position, child_uid):
        # dewar = self.getContainer(filter={'owner':self.owner, 'name': dewar_name})
        # puck = self.getContainer(filter={'owner':self.owner, 'kind': '16_pin_puck', 'name': puck_name})
        parent_container = self.getContainer(filter={"uid": parent_uid})
        if parent_container:
            parent_container["content"][position] = child_uid
            self.updateContainer(parent_container)
            return True
        return False

    def removeFromContainer(self, parent_uid, position, child_uid):
        parent_container = self.getContainer(filter={"uid": parent_uid})
        if parent_container:
            if parent_container["content"][position] == child_uid:
                parent_container["content"][position] = ""
                self.updateContainer(parent_container)
                return True
        return False

    def getAllPucks(self):
        filters = {"kind": "16_pin_puck", "owner": self.owner}
        return list(self.container_ref.find(**filters))

    def getBLConfig(self, paramName):
        return self.beamlineInfo(paramName).get("val", None)

    def beamlineInfo(self, info_name) -> Dict[str, Any]:
        """
        to fetch info:  info = beamlineInfo('x25', 'det')
        """

        # if it exists it's a query or update
        try:
            bli = list(
                self.configuration_ref.find(
                    key="beamline_info",
                    beamline_id=self.beamline_id,
                    info_name=info_name,
                )
            )[0]
            return bli["info"]

        # else it's a create
        except conftrak.exceptions.ConfTrakNotFoundException:
            return {}

    @property
    def primary_dewar_name(self):
        return self.getBLConfig("primaryDewarName")

    @property
    def primary_dewar_uid(self):
        return self.getContainer(
            filter={"name": self.primary_dewar_name, "owner": self.beamline_id.lower()}
        )["uid"]

    def getSample(self, filter):
        samples = list(self.sample_ref.find(**filter))
        if samples:
            return samples[0]
        return {}

    def createSample(self, sample_name, kind="pin", proposalID=None, **kwargs):
        if "request_count" not in kwargs:
            kwargs["request_count"] = 0
        return self.sample_ref.create(
            name=sample_name,
            owner=self.owner,
            kind=kind,
            proposalID=proposalID,
            **kwargs,
        )

    def get_proposal_info(self, proposal_num):
        if str(proposal_num) == "999999":
            response = {
                "proposal": {
                    "users": [],
                    "proposal_id": "999999",
                    "title": "Test proposal",
                }
            }
            return response
        try:
            response = requests.get(f"{self.api_url}/proposal/{proposal_num}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Proposal information not found: {e}"

    def get_visit_directories(self, proposal_num):
        """
        Uses the proposal directory returned by the API and returns
        the latest visit directory inside it
        """
        try:
            response = requests.get(
                f"{self.api_url}/proposal/{proposal_num}/directories"
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Exception in getting proposal directories: {e}")
            return None
        response_data = response.json()
        proposal_directories = []
        for directory in response_data["directories"]:
            if directory["beamline"].lower() == self.beamline_id.lower():
                proposal_directories.append(directory["path"])

        if not proposal_directories:
            return None

        for proposal_directory in reversed(proposal_directories):
            path = Path(proposal_directory)
            if path.is_dir():
                break
                # raise ValueError(f"The path {path} is not a valid directory")

        directories = [d for d in path.iterdir() if d.is_dir()]
        if not directories:
            return None

        most_recent_dir = sorted(
            directories, key=lambda d: os.path.getmtime(d), reverse=True
        )
        return most_recent_dir

    ## Code to add requests
    def addRequest(self, sample_id, row_data, selected_path):
        if self.beamline_id.lower() == "fmx":
            default_energy = 12660
            transmission_mapping = {"225": 0.7, "360": 0.4}
            default_transmission = transmission_mapping.get(
                str(int(float(row_data["oscrange"]))),
                float(self.getBLConfig("stdTrans")),
            )
        else:
            default_energy = float(self.getBLConfig("screen_default_energy"))
            default_transmission = 0.1

        if self.beamline_id.lower() == "amx":
            img_width_mapping = {
                "225": 0.1,
                "360": 0.2,
            }
            default_img_width = img_width_mapping.get(
                str(int(float(row_data["oscrange"]))),
                float(self.getBLConfig("screen_default_width")),
            )
            default_exp_time = 0.005
        else:
            # default_img_width = float(self.getBLConfig("screen_default_width"))
            default_img_width = 0.2
            default_exp_time = 0.01
        default_wavelength = energy2wave(default_energy)
        detector_distance = distance_from_reso(
            self.getBLConfig("detRadius"),
            float(row_data["resolution"]),
            default_wavelength,
            0,
        )
        base_path = str(selected_path)

        visit_name = f"mx{row_data['proposalnum']}-1"
        collection_dir = selected_path / Path(visit_name) / Path(row_data["samplename"])
        existing_dirs = None
        if collection_dir.exists():
            existing_dirs = [
                int(p.name)
                for p in collection_dir.iterdir()
                if p.is_dir() and p.name.isdigit()
            ]

        if existing_dirs:
            next_dir_number = max(existing_dirs) + 1
        else:
            next_dir_number = 1

        directory = (
            collection_dir
            / Path(str(next_dir_number))
            / Path(row_data["puckname"] + "_" + str(row_data["position"]))
        )
        # str(base_path)+"/" + visit_name + "/"+ row_data["samplename"] + "/1/" + row_data["puckname"] +"_"+ row_data["position"]+"/",
        request = {
            "sample": sample_id,
            "beamline": self.beamline_id,
            "request_type": "standard",
            "proposalID": row_data["proposalnum"],
            "priority": 5000 + int(float(row_data["priority"])),
            "owner": getpass.getuser(),
            "request_obj": {
                "sample": sample_id,
                "sweep_start": float(row_data["startangle"]),
                "sweep_end": float(row_data["startangle"])
                + float(row_data["oscrange"]),
                "osc_range": float(row_data["oscrange"]),
                "img_width": default_img_width,
                "exposure_time": default_exp_time,
                "protocol": "standard",
                "detDist": float(detector_distance),
                "parentReqID": -1,
                "basePath": str(base_path),
                "dataPath": self.getBLConfig("data_path"),
                "file_prefix": row_data["samplename"],
                "directory": str(directory) + "/",
                "file_number_start": 1,
                "energy": default_energy,
                "wavelength": default_wavelength,
                "resolution": float(row_data["resolution"]),
                "slit_height": float(self.getBLConfig("screen_default_beamHeight")),
                "slit_width": float(self.getBLConfig("screen_default_beamWidth")),
                "attenuation": float(default_transmission),
                "visit_name": visit_name,
                "detector": self.detector_name,
                "beamline": self.beamline_id.lower(),
                "pos_x": -999,
                "pos_y": 0,
                "pos_z": 0,
                "pos_type": "A",
                "gridStep": 20,
                "centeringOption": "AutoRaster",
                "runNum": 1,
                "fastDP": True,
                "fastEP": False,
                "dimple": True,
                "xia2": False,
            },
        }

        self.request_ref.create(**request)
