import os
from typing import Dict, Any
import time
import getpass
import amostra.client.commands as acc
import conftrak.client.commands as ccc

# from analysisstore.client.commands import AnalysisClient
import conftrak.exceptions


class DBConnection:
    def __init__(self, beamline_id='amx'):
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
        self.beamline_id = beamline_id
        self.owner = getpass.getuser()

    def getContainer(self, filter=None):
        container = {}
        if filter:
            containers = list(self.container_ref.find(**filter))
            container =  containers[0] if containers else {}
        return container

    def createContainer(
        self, name: str, capacity: int, kind: str, **kwargs
    ):
        if capacity is not None:
            kwargs["content"] = [""] * capacity
        uid = self.container_ref.create(
            name=name, owner=self.owner, kind=kind, modified_time=time.time(), **kwargs
        )
        return uid

    def getOrCreateContainer(self, name: str, capacity: int, kind: str, **kwargs):
        container = self.getContainer(filter={'name': name, 'kind': kind})
        if not container:
            container = self.createContainer(name, capacity, kind, **kwargs)
        return container

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
        c = self.getContainer(filter={'uid':id})
        if c is not None:
            c["content"] = [""] * len(c["content"])
            self.updateContainer(c)
            return True
        return False

    def insertIntoContainer(self, parent_uid, position, child_uid):
        #dewar = self.getContainer(filter={'owner':self.owner, 'name': dewar_name})
        #puck = self.getContainer(filter={'owner':self.owner, 'kind': '16_puck_pin', 'name': puck_name})
        parent_container = self.getContainer(filter={'uid': parent_uid})
        if parent_container:
            parent_container["content"][position] = child_uid
            self.updateContainer(parent_container)
            return True
        return False

    def getAllPucks(self):
        filters={"kind": "16_puck_pin","owner":self.owner}
        return list(self.container_ref.find(**filters))

    def getBLConfig(self, paramName):
        return self.beamlineInfo(paramName)["val"]

    def beamlineInfo(self, info_name, info_dict=None):
        """
        to write info:  beamlineInfo('x25', 'det', info_dict={'vendor':'adsc','model':'q315r'})
        to fetch info:  info = beamlineInfo('x25', 'det')
        """

        # if it exists it's a query or update
        try:
            bli = list(self.configuration_ref.find(key='beamline_info', beamline_id=self.beamline_id, info_name=info_name))[0] #hugo put the [0]

            if info_dict is None:  # this is a query
                return bli['info']

            # else it's an update
            bli_uid = bli.pop('uid', '')
            self.configuration_ref.update({'uid': bli_uid},{'info':info_dict})

        # else it's a create
        except conftrak.exceptions.ConfTrakNotFoundException:
            # edge case for 1st create in fresh database
            # in which case this as actually a query
            if info_dict is None:
                return {}

            # normal create
            data = {'key': 'beamline_info', 'info_name':info_name, 'info': info_dict}
            uid = self.configuration_ref.create(self.beamline_id,**data)


    @property
    def primary_dewar_name(self):
        return self.getBLConfig("primaryDewarName")
    
    @property
    def primary_dewar_uid(self):
        return self.getContainer(filter={'name': self.primary_dewar_name})

    def getSample(self, filter):
        samples = list(self.sample_ref.find(**filter))
        if samples:
            return samples[0]
        return {}
    
    def createSample(self, sample_name, kind='pin', proposalID=None, **kwargs):
        if 'request_count' not in kwargs:
            kwargs['request_count'] = 0
        return self.sample_ref.create(name=sample_name, 
                                      owner=self.owner, kind=kind, 
                                      proposalID=proposalID,
                                      **kwargs)