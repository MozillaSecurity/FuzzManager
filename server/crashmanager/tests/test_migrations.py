import pytest
from django.contrib.auth.models import User
from . import migration_hook  # noqa


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.migrate_from('0019_bucket_optimizedsignature')  # noqa
@pytest.mark.migrate_to('0020_add_app_permissions')
def test_user_app_permissions_migrate(migration_hook, settings):
    settings.DEFAULT_PERMISSIONS = []

    # create pre-migration user
    CMUser = migration_hook.apps.get_model('crashmanager', 'User')
    user1 = User.objects.create(username='test-pre-migrate', password='!test')
    CMUser.objects.get_or_create(user_id=user1.id)

    # run migration
    migration_hook()

    # create post-migration user
    CMUser = migration_hook.apps.get_model('crashmanager', 'User')
    user2 = User.objects.create(username='test-post-migrate', password='!test')
    CMUser.objects.get_or_create(user_id=user2.id)

    # refresh pre-migration user
    user1 = User.objects.get(username='test-pre-migrate')

    assert set(user1.get_all_permissions()) == {'crashmanager.view_covmanager',
                                                'crashmanager.view_crashmanager',
                                                'crashmanager.view_ec2spotmanager'}
    assert not user2.get_all_permissions()
