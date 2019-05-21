# extracted from https://cloud.google.com/compute/docs/machine-types

import collections


InstanceType = collections.namedtuple("InstanceType", ("api_name", "vCPUs", "RAM"))


INSTANCE_TYPES = tuple(
    [InstanceType("n1-standard-%d" % (cores,), cores, cores * 3.75) for cores in (1, 2, 4, 8, 16, 32, 64, 96)] +
    [InstanceType("n1-highmem-%d" % (cores,), cores, cores * 6.5) for cores in (2, 4, 8, 16, 32, 64, 96)] +
    [InstanceType("n1-highcpu-%d" % (cores,), cores, cores * 0.9) for cores in (2, 4, 8, 16, 32, 64, 96)] +
    [InstanceType("f1-micro", 0.2, 0.6)] +
    [InstanceType("g1-small", 0.5, 1.7)] +
    [InstanceType("n1-ultramem-%d" % (cores,), cores, cores * 24.025) for cores in (40, 80, 160)] +
    [InstanceType("n1-megamem-96", 96, 1433.6)]
)


CORES_PER_INSTANCE = {instance.api_name: instance.vCPUs for instance in INSTANCE_TYPES}
RAM_PER_INSTANCE = {instance.api_name: instance.RAM for instance in INSTANCE_TYPES}
