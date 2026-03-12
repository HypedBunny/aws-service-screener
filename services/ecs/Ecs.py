## https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html

import boto3
import botocore

from botocore.config import Config as AWSConfig
from utils.Config import Config
from services.Service import Service
from services.ecs.drivers.EcsClusterDriver import EcsClusterDriver
from services.ecs.drivers.EcsServiceDriver import EcsServiceDriver
from services.ecs.drivers.EcsTaskDefinitionDriver import EcsTaskDefinitionDriver

from utils.Tools import _pi

class Ecs(Service):
    def __init__(self, region):
        super().__init__(region)

        ssBoto = self.ssBoto
        self.ecsClient = ssBoto.client('ecs', config=self.bConfig)

    def getClusters(self):
        arr = []
        results = self.ecsClient.list_clusters()
        arr = results.get('clusterArns', [])

        while results.get('nextToken') is not None:
            results = self.ecsClient.list_clusters(
                nextToken=results.get('nextToken')
            )
            arr = arr + results.get('clusterArns', [])

        if not arr:
            return []

        response = self.ecsClient.describe_clusters(
            clusters=arr,
            include=['SETTINGS', 'TAGS']
        )

        return response.get('clusters', [])

    def getServices(self, clusterArn):
        arr = []
        results = self.ecsClient.list_services(cluster=clusterArn)
        arr = results.get('serviceArns', [])

        while results.get('nextToken') is not None:
            results = self.ecsClient.list_services(
                cluster=clusterArn,
                nextToken=results.get('nextToken')
            )
            arr = arr + results.get('serviceArns', [])

        if not arr:
            return []

        # describe_services accepts max 10 at a time
        services = []
        for i in range(0, len(arr), 10):
            batch = arr[i:i+10]
            response = self.ecsClient.describe_services(
                cluster=clusterArn,
                services=batch
            )
            services = services + response.get('services', [])

        return services

    def getTaskDefinitions(self, services):
        taskDefArns = set()
        for svc in services:
            taskDefArns.add(svc.get('taskDefinition'))

        taskDefs = []
        for arn in taskDefArns:
            try:
                response = self.ecsClient.describe_task_definition(
                    taskDefinition=arn
                )
                taskDefs.append(response.get('taskDefinition'))
            except botocore.exceptions.ClientError as e:
                print(f"Unable to describe task definition {arn}: {e.response['Error']['Code']}")

        return taskDefs

    def advise(self):
        objs = {}
        clusters = self.getClusters()

        for cluster in clusters:
            clusterName = cluster.get('clusterName')
            _pi('ECS:Cluster', clusterName)

            if self.tags:
                nTags = cluster.get('tags', [])
                formattedTags = [{'Key': t['key'], 'Value': t['value']} for t in nTags]
                if self.resourceHasTags(formattedTags) == False:
                    continue

            # Cluster-level checks
            obj = EcsClusterDriver(clusterName, cluster, self.ecsClient)
            obj.run(self.__class__)
            objs['Cluster::' + clusterName] = obj.getInfo()
            del obj

            # Service-level checks
            services = self.getServices(cluster.get('clusterArn'))
            for svc in services:
                serviceName = svc.get('serviceName')
                _pi('ECS:Service', serviceName)

                obj = EcsServiceDriver(serviceName, svc, self.ecsClient)
                obj.run(self.__class__)
                objs['Service::' + clusterName + '/' + serviceName] = obj.getInfo()
                del obj

            # Task definition checks
            taskDefs = self.getTaskDefinitions(services)
            for taskDef in taskDefs:
                family = taskDef.get('family')
                revision = str(taskDef.get('revision'))
                taskDefName = family + ':' + revision
                _pi('ECS:TaskDefinition', taskDefName)

                obj = EcsTaskDefinitionDriver(taskDefName, taskDef, self.ecsClient)
                obj.run(self.__class__)
                objs['TaskDefinition::' + taskDefName] = obj.getInfo()
                del obj

        return objs
