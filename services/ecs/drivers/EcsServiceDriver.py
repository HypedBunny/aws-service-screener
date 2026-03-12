## https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html

import boto3
import botocore

from utils.Config import Config
from services.Evaluator import Evaluator

class EcsServiceDriver(Evaluator):
    def __init__(self, serviceName, serviceInfo, ecsClient):
        super().__init__()
        self.service = serviceName
        self.serviceInfo = serviceInfo
        self.ecsClient = ecsClient

        self._resourceName = serviceName

        self.init()

    def _checkDesiredCount(self):
        desiredCount = self.serviceInfo.get('desiredCount', 0)

        if desiredCount <= 1:
            self.results['ecsServiceDesiredCount'] = [-1, 'Desired count: ' + str(desiredCount)]

        return

    def _checkRunningCount(self):
        desiredCount = self.serviceInfo.get('desiredCount', 0)
        runningCount = self.serviceInfo.get('runningCount', 0)

        if runningCount < desiredCount:
            self.results['ecsServiceRunningCount'] = [-1, 'Running: ' + str(runningCount) + ', Desired: ' + str(desiredCount)]

        return

    def _checkCircuitBreaker(self):
        deploymentConfig = self.serviceInfo.get('deploymentConfiguration', {})
        circuitBreaker = deploymentConfig.get('deploymentCircuitBreaker', {})

        if not circuitBreaker.get('enable', False):
            self.results['ecsServiceCircuitBreaker'] = [-1, 'Disabled']

        return

    def _checkNetworkMode(self):
        taskDef = self.serviceInfo.get('taskDefinition', '')

        try:
            response = self.ecsClient.describe_task_definition(
                taskDefinition=taskDef
            )
            taskDefInfo = response.get('taskDefinition', {})
            networkMode = taskDefInfo.get('networkMode', 'bridge')

            if networkMode != 'awsvpc':
                self.results['ecsServiceNetworkAwsvpc'] = [-1, 'Network mode: ' + networkMode]

        except botocore.exceptions.ClientError:
            return

        return
