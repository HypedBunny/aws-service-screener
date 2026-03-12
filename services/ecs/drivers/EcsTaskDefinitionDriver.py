## https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html

import boto3
import botocore
import re

from utils.Config import Config
from services.Evaluator import Evaluator

class EcsTaskDefinitionDriver(Evaluator):
    SECRET_PATTERNS = re.compile(
        r'(password|secret|key|token|api_key|apikey|access_key|private_key)',
        re.IGNORECASE
    )

    def __init__(self, taskDefName, taskDefInfo, ecsClient):
        super().__init__()
        self.taskDefName = taskDefName
        self.taskDefInfo = taskDefInfo
        self.ecsClient = ecsClient

        self._resourceName = taskDefName

        self.init()

    def _checkLogging(self):
        containers = self.taskDefInfo.get('containerDefinitions', [])

        for container in containers:
            logConfig = container.get('logConfiguration')
            if logConfig is None:
                self.results['ecsTaskDefinitionLogging'] = [-1, container.get('name', 'unknown') + ': No log configuration']
                return

        return

    def _checkRootUser(self):
        containers = self.taskDefInfo.get('containerDefinitions', [])

        for container in containers:
            user = container.get('user', '')
            if user == 'root' or user == '0':
                self.results['ecsTaskDefinitionRootUser'] = [-1, container.get('name', 'unknown') + ': Running as root']
                return

        return

    def _checkReadonlyRootFilesystem(self):
        containers = self.taskDefInfo.get('containerDefinitions', [])

        for container in containers:
            if not container.get('readonlyRootFilesystem', False):
                self.results['ecsTaskDefinitionReadonlyRoot'] = [-1, container.get('name', 'unknown') + ': Writable root filesystem']
                return

        return

    def _checkHardcodedSecrets(self):
        containers = self.taskDefInfo.get('containerDefinitions', [])

        for container in containers:
            envVars = container.get('environment', [])
            for env in envVars:
                envName = env.get('name', '')
                if self.SECRET_PATTERNS.search(envName):
                    self.results['ecsTaskDefinitionNoSecrets'] = [-1, container.get('name', 'unknown') + ': Possible secret in env var ' + envName]
                    return

        return

    def _checkExecutionRole(self):
        executionRoleArn = self.taskDefInfo.get('executionRoleArn')

        if not executionRoleArn:
            self.results['ecsTaskDefinitionExecutionRole'] = [-1, 'No execution role configured']

        return

    def _checkResourceLimits(self):
        # Task-level CPU/memory
        taskCpu = self.taskDefInfo.get('cpu')
        taskMemory = self.taskDefInfo.get('memory')

        if taskCpu and taskMemory:
            return

        # Check container-level limits
        containers = self.taskDefInfo.get('containerDefinitions', [])

        for container in containers:
            cpu = container.get('cpu', 0)
            memory = container.get('memory')
            memoryReservation = container.get('memoryReservation')

            if cpu == 0 and memory is None and memoryReservation is None:
                self.results['ecsTaskDefinitionResourceLimits'] = [-1, container.get('name', 'unknown') + ': No CPU/memory limits']
                return

        return

    def _checkPrivileged(self):
        containers = self.taskDefInfo.get('containerDefinitions', [])

        for container in containers:
            if container.get('privileged', False):
                self.results['ecsTaskDefinitionPrivileged'] = [-1, container.get('name', 'unknown') + ': Privileged mode enabled']
                return

        return
