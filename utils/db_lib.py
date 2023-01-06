import os
from typing import Dict, Any
import time
import amostra.client.commands as acc
import conftrak.client.commands as ccc

# from analysisstore.client.commands import AnalysisClient
import conftrak.exceptions


class DBConnection:
    def __init__(self):
        main_server = os.environ["MONGODB_HOST"]

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

    def getContainerbyName(self, container_name: str, owner: str):
        containers = list(self.container_ref.find(owner=owner, name=container_name))
        return containers[0] if containers else {}

    def getContainerByID(self, id):
        containers = list(self.container_ref.find(uid=id))
        return containers[0]

    def createContainer(
        self, name: str, capacity: int, owner: str, kind: str, **kwargs
    ):
        if capacity is not None:
            kwargs["content"] = [""] * capacity
        uid = self.container_ref.create(
            name=name, owner=owner, kind=kind, modified_time=time.time(), **kwargs
        )
        return uid

    def createSample(
        self, sample_name: str, owner: str, kind: str, proposalID: int, **kwargs
    ):
        if "request_count" not in kwargs:
            kwargs["request_count"] = 0

        uid = self.sample_ref.create(
            name=sample_name, owner=owner, kind=kind, proposalID=proposalID, **kwargs
        )
        return uid

    def updateContainer(
        self, container: Dict[str, Any]
    ):  # really updating the contents
        cont = container["uid"]
        q = {"uid": container.pop("uid", "")}
        container.pop("time", "")
        self.container_ref.update(
            q, {"content": container["content"], "modfied_time": time.time()}
        )

        return cont

    def emptyContainer(self, id):
        c = self.getContainerByID(id)
        if c is not None:
            c["content"] = [""] * len(c["content"])
            self.updateContainer(c)
            return True
        return False

    def insertIntoContainer(self, container_name, owner, position, itemID):
        c = self.getContainerbyName(container_name, owner)
        if c:
            c["content"][position - 1] = itemID  # most people don't zero index things
            self.updateContainer(c)
            return True
        return False
