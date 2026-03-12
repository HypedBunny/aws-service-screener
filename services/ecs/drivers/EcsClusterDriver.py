## https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html

import boto3
import botocore

from utils.Config import Config
from services.Evaluator import Evaluator

class EcsClusterDriver(Evaluator):
    def __init__(self, clusterName, clusterInfo, ecsClient):
        super().__init__()
        self.cluster = clusterName
        self.clusterInfo = clusterInfo
        self.ecsClient = ecsClient

        self._resourceName = clusterName

        self.init()

    def _checkContainerInsights(self):
        settings = self.clusterInfo.get('settings', [])

        for setting in settings:
            if setting.get('name') == 'containerInsights' and setting.get('value') == 'enabled':
                return

        self.results['ecsContainerInsights'] = [-1, 'Disabled']
        return
