'''
Example:
>>> import update_prices, json
>>> with open('index.json') as jsonf:
...     data = json.load(jsonf)
...
>>> data = update_prices.get_instance_types(index_json=data)
>>> ','.join(t for t,obj in data.items() if obj['vcpu'] == 8 and obj['memory'] >= 30)
i2.2xlarge,r3.2xlarge,m3.2xlarge,m5.2xlarge,m2.4xlarge,d2.2xlarge,i3.2xlarge,r4.2xlarge,p3.2xlarge,m4.2xlarge,
f1.2xlarge,h1.2xlarge,x1e.2xlarge,m5d.2xlarge,t2.2xlarge
'''

from __future__ import print_function
import json
import requests
import sys


# for some reason, the pricing API uses friendly names for regions, not API names
# this is a mapping from friendly name to API name
REGION_NAMES = {
    "US East (N. Virginia)": "us-east-1",
    "US East (Ohio)": "us-east-2",
    "US West (N. California)": "us-west-1",
    "US West (Oregon)": "us-west-2",
    "Canada (Central)": "ca-central-1",
    "EU (Frankfurt)": "eu-central-1",
    "EU (Ireland)": "eu-west-1",
    "EU (London)": "eu-west-2",
    "EU (Paris)": "eu-west-3",
    "Asia Pacific (Tokyo)": "ap-northeast-1",
    "Asia Pacific (Seoul)": "ap-northeast-2",
    "Asia Pacific (Osaka-Local)": "ap-northeast-3",
    "Asia Pacific (Singapore)": "ap-southeast-1",
    "Asia Pacific (Sydney)": "ap-southeast-2",
    "Asia Pacific (Mumbai)": "ap-south-1",
    "South America (Sao Paulo)": "sa-east-1",
}

# fields we don't care about
FIELDS_BLACKLIST = {
    "capacitystatus",
    "instanceType",
    "licenseModel",
    "location",
    "locationType",
    "operatingSystem",
    "operation",
    "preInstalledSw",
    "servicecode",
    "servicename",
    "tenancy",
    "usagetype",
}


def get_instance_types(regions=True, index_json=None):
    """Fetch instance type data from EC2 pricing API.

    regions: if True, this will add a "regions" field to each instance type, stating which regions support it.
    index_json: the data blob is large. if it is cached locally for testing, you can pass in the JSON decoded
                dictionary here.
    returns:
    {
      "c5.xlarge": {
        "clockSpeed": "3.0 Ghz",
        "currentGeneration": "Yes",
        "dedicatedEbsThroughput": "Upto 2250 Mbps",
        "ecu": 17.0,
        "enhancedNetworkingSupported": "Yes",
        "gpu": 0,
        "instanceFamily": "Compute optimized",
        "memory": 8.0,
        "metal": False,
        "networkPerformance": "Up to 10 Gigabit",
        "normalizationSizeFactor": "8",
        "physicalProcessor": "Intel Xeon Platinum 8124M",
        "processorArchitecture": "64-bit",
        "processorFeatures": "Intel AVX, Intel AVX2, Intel AVX512, Intel Turbo",
        "storage": "EBS only",
        "vcpu": 4
      },
      ...
    }
    """
    if index_json is None:
        index_json = \
            requests.get("https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json").json()

    data = index_json['products']

    instance_types = {}

    for product in data.values():
        if product["productFamily"] not in {"Compute Instance", "Compute Instance (bare metal)"} or \
                product["attributes"]["operatingSystem"] != "Linux" or \
                product["attributes"]["preInstalledSw"] != "NA" or \
                product["attributes"]["capacitystatus"] == "None" or \
                product["attributes"]["location"] not in REGION_NAMES:
            continue
        instance_data = instance_types.setdefault(product["attributes"]["instanceType"], {})
        if instance_data:
            # assert that all fields are the same!
            new_data = {key: value for key, value in product["attributes"].items() if key not in FIELDS_BLACKLIST}
            new_data["metal"] = product["productFamily"] == "Compute Instance (bare metal)"
            if regions:
                old_data = instance_data.copy()
                del old_data["regions"]
                assert new_data == old_data
                # add to region list
                instance_data["regions"].add(REGION_NAMES[product["attributes"]["location"]])
            else:
                assert new_data == instance_data
        else:
            for field, value in product["attributes"].items():
                if field not in FIELDS_BLACKLIST:
                    instance_data[field] = value
            if regions:
                instance_data["regions"] = {REGION_NAMES[product["attributes"]["location"]]}
            instance_data["metal"] = product["productFamily"] == "Compute Instance (bare metal)"

    # normalize units
    for instance_data in instance_types.values():
        if regions:
            instance_data["regions"] = list(instance_data["regions"])
        instance_data["vcpu"] = int(instance_data["vcpu"])
        instance_data["gpu"] = int(instance_data.get("gpu", "0"))
        assert instance_data["memory"].endswith(" GiB"), instance_data["memory"]
        instance_data["memory"] = float(instance_data["memory"][:-4].replace(",", ""))
        if instance_data["ecu"] == "Variable":
            instance_data["ecu"] = None
        else:
            instance_data["ecu"] = float(instance_data["ecu"])

    return instance_types


def main():
    index_json = None
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as data_fp:
            index_json = json.load(data_fp)

    print(json.dumps(get_instance_types(index_json=index_json), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
