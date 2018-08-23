import decimal
from . import TestMigrations


class AddInstanceSizeTests(TestMigrations):

    migrate_from = '0008_remove_aws_creds'
    migrate_to = '0009_add_instance_size'


class Migrated(AddInstanceSizeTests):

    def setUpBeforeMigration(self, apps):
        PoolConfiguration = apps.get_model('ec2spotmanager', 'PoolConfiguration')
        InstancePool = apps.get_model('ec2spotmanager', 'InstancePool')
        Instance = apps.get_model('ec2spotmanager', 'Instance')
        cfg1 = PoolConfiguration.objects.create(
            name='Test config #1',
            size=None,
            ec2_instance_types='["c5.2xlarge"]',
            ec2_max_price=decimal.Decimal('0.10'),
        )
        self.cfg1_pk = cfg1.pk
        cfg2 = PoolConfiguration.objects.create(
            parent=cfg1,
            name='Test config #2',
            size=None,
        )
        self.cfg2_pk = cfg2.pk
        cfg3 = PoolConfiguration.objects.create(
            parent=cfg2,
            name='Test config #3',
            size=2,
            ec2_max_price=decimal.Decimal('0.12'),
        )
        self.cfg3_pk = cfg3.pk
        self.inst_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg3), status_code=0).pk

    def runTest(self):
        PoolConfiguration = self.apps.get_model('ec2spotmanager', 'PoolConfiguration')
        Instance = self.apps.get_model('ec2spotmanager', 'Instance')
        cfg1 = PoolConfiguration.objects.get(pk=self.cfg1_pk)
        cfg2 = PoolConfiguration.objects.get(pk=self.cfg2_pk)
        cfg3 = PoolConfiguration.objects.get(pk=self.cfg3_pk)
        instance = Instance.objects.get(pk=self.inst_pk)

        assert cfg1.size is None
        assert cfg1.ec2_instance_types == '["c5.2xlarge"]'
        assert cfg1.ec2_max_price == decimal.Decimal('0.10') / 8

        assert cfg2.size is None
        assert cfg2.ec2_instance_types is None
        assert cfg2.ec2_max_price is None

        assert cfg3.size == 16  # c5.2xlarge has 8 cores
        assert cfg3.ec2_instance_types is None
        assert cfg3.ec2_max_price == decimal.Decimal('0.12') / 8

        assert instance.size == 8


class NoInstances(AddInstanceSizeTests):

    def setUpBeforeMigration(self, apps):
        PoolConfiguration = apps.get_model('ec2spotmanager', 'PoolConfiguration')
        InstancePool = apps.get_model('ec2spotmanager', 'InstancePool')
        Instance = apps.get_model('ec2spotmanager', 'Instance')
        cfg = PoolConfiguration.objects.create(
            name='Test config #1',
            size=10,
            ec2_max_price=decimal.Decimal('0.10'),
        )
        self.cfg_pk = cfg.pk
        self.inst_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg), status_code=0).pk

    def runTest(self):
        PoolConfiguration = self.apps.get_model('ec2spotmanager', 'PoolConfiguration')
        Instance = self.apps.get_model('ec2spotmanager', 'Instance')
        cfg = PoolConfiguration.objects.get(pk=self.cfg_pk)
        instance = Instance.objects.get(pk=self.inst_pk)

        assert cfg.size == 10
        assert cfg.ec2_instance_types is None
        assert cfg.ec2_max_price == decimal.Decimal('0.10')

        assert instance.size == 1


class DifferentSizes(AddInstanceSizeTests):

    def setUpBeforeMigration(self, apps):
        PoolConfiguration = apps.get_model('ec2spotmanager', 'PoolConfiguration')
        InstancePool = apps.get_model('ec2spotmanager', 'InstancePool')
        Instance = apps.get_model('ec2spotmanager', 'Instance')
        cfg1 = PoolConfiguration.objects.create(
            name='Test config #1',
            size=3,
            ec2_instance_types='["c5.2xlarge"]',
            ec2_max_price=decimal.Decimal('0.10'),
        )
        self.cfg1_pk = cfg1.pk
        cfg2 = PoolConfiguration.objects.create(
            parent=cfg1,
            name='Test config #2',
            ec2_instance_types='["c5.xlarge"]',
            size=2,
            ec2_max_price=decimal.Decimal('0.12'),
        )
        self.cfg2_pk = cfg2.pk
        self.inst1_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg1), status_code=0).pk
        self.inst2_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg2), status_code=0).pk

    def runTest(self):
        PoolConfiguration = self.apps.get_model('ec2spotmanager', 'PoolConfiguration')
        Instance = self.apps.get_model('ec2spotmanager', 'Instance')
        cfg1 = PoolConfiguration.objects.get(pk=self.cfg1_pk)
        cfg2 = PoolConfiguration.objects.get(pk=self.cfg2_pk)
        instance1 = Instance.objects.get(pk=self.inst1_pk)
        instance2 = Instance.objects.get(pk=self.inst2_pk)

        # c5.2xlarge has 8 cores
        assert cfg1.size == 24
        assert cfg1.ec2_instance_types == '["c5.2xlarge"]'
        assert cfg1.ec2_max_price == decimal.Decimal('0.10') / 8

        # c5.xlarge has 4 cores, average is 6
        assert cfg2.size == 12
        assert cfg2.ec2_instance_types == '["c5.xlarge"]'
        assert cfg2.ec2_max_price == decimal.Decimal('0.12') / 6

        assert instance1.size == 8
        assert instance2.size == 6
