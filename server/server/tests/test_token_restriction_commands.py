import io
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from rest_framework.authtoken.models import Token

from server.models import TokenIPRestriction


class TestManageTokenRestrictionsCommand:
    @pytest.fixture
    def setup_token(self):
        """Create a test user and token for testing"""
        user = User.objects.create_user(username="testuser", password="password")
        token = Token.objects.create(user=user)

        # Delete default restrictions to have a clean state
        TokenIPRestriction.objects.filter(token=token).delete()

        return token

    @pytest.mark.django_db
    def test_list_restrictions_empty(self, setup_token):
        """Test listing IP restrictions when none exist"""
        token = setup_token

        stdout = io.StringIO()
        call_command("manage_token_restrictions", token.key, "--list", stdout=stdout)

        output = stdout.getvalue()
        assert "No IP restrictions" in output

    @pytest.mark.django_db
    def test_list_restrictions_with_data(self, setup_token):
        """Test listing IP restrictions when some exist"""
        token = setup_token

        # Add a restriction
        TokenIPRestriction.objects.create(token=token, ip_range="192.168.1.0/24")

        stdout = io.StringIO()
        call_command("manage_token_restrictions", token.key, "--list", stdout=stdout)

        output = stdout.getvalue()
        assert "Current IP restrictions" in output
        assert "192.168.1.0/24" in output

    @pytest.mark.django_db
    def test_add_restriction(self, setup_token):
        """Test adding an IP restriction"""
        token = setup_token

        stdout = io.StringIO()
        call_command(
            "manage_token_restrictions",
            token.key,
            "--add=10.0.0.0/8",
            "--force",
            stdout=stdout,
        )

        # Verify the restriction was added
        assert TokenIPRestriction.objects.filter(
            token=token, ip_range="10.0.0.0/8"
        ).exists()
        assert "Added IP restriction: 10.0.0.0/8" in stdout.getvalue()

    @pytest.mark.django_db
    def test_add_restriction_with_open_policy(self, setup_token):
        """Test adding a restriction when an open policy exists"""
        token = setup_token

        # Add open policy
        TokenIPRestriction.objects.create(token=token, ip_range="0.0.0.0/0")

        # Mock user input to confirm removing open policy
        with patch("builtins.input", return_value="y"):
            stdout = io.StringIO()
            call_command(
                "manage_token_restrictions",
                token.key,
                "--add=10.0.0.0/8",
                stdout=stdout,
            )

            # Verify the open policy was removed and new restriction added
            assert not TokenIPRestriction.objects.filter(
                token=token, ip_range="0.0.0.0/0"
            ).exists()
            assert TokenIPRestriction.objects.filter(
                token=token, ip_range="10.0.0.0/8"
            ).exists()
            assert "Open policy removed" in stdout.getvalue()

    @pytest.mark.django_db
    def test_add_invalid_cidr(self, setup_token):
        """Test adding an invalid CIDR notation"""
        token = setup_token

        with pytest.raises(CommandError) as excinfo:
            call_command("manage_token_restrictions", token.key, "--add=invalid-cidr")

        assert "Invalid CIDR notation" in str(excinfo.value)

    @pytest.mark.django_db
    def test_add_duplicate_restriction(self, setup_token):
        """Test adding a restriction that already exists"""
        token = setup_token

        # Add restriction
        TokenIPRestriction.objects.create(token=token, ip_range="10.0.0.0/8")

        stdout = io.StringIO()
        call_command(
            "manage_token_restrictions",
            token.key,
            "--add=10.0.0.0/8",
            "--force",
            stdout=stdout,
        )

        assert "already exists" in stdout.getvalue()

    @pytest.mark.django_db
    def test_remove_restriction(self, setup_token):
        """Test removing an IP restriction"""
        token = setup_token

        # Add a restriction
        TokenIPRestriction.objects.create(token=token, ip_range="10.0.0.0/8")

        stdout = io.StringIO()
        call_command(
            "manage_token_restrictions",
            token.key,
            "--remove=10.0.0.0/8",
            "--force",
            stdout=stdout,
        )

        # Verify the restriction was removed
        assert not TokenIPRestriction.objects.filter(
            token=token, ip_range="10.0.0.0/8"
        ).exists()
        assert "Removed IP restriction: 10.0.0.0/8" in stdout.getvalue()

    @pytest.mark.django_db
    def test_remove_nonexistent_restriction(self, setup_token):
        """Test removing a restriction that doesn't exist"""
        token = setup_token

        stdout = io.StringIO()
        call_command(
            "manage_token_restrictions",
            token.key,
            "--remove=10.0.0.0/8",
            "--force",
            stdout=stdout,
        )

        assert "not found for this token" in stdout.getvalue()

    @pytest.mark.django_db
    def test_remove_last_restriction_with_confirmation(self, setup_token):
        """Test removing the last restriction with confirmation"""
        token = setup_token

        # Add a restriction
        TokenIPRestriction.objects.create(token=token, ip_range="10.0.0.0/8")

        # Mock user input to confirm removal
        with patch("builtins.input", return_value="y"):
            stdout = io.StringIO()
            call_command(
                "manage_token_restrictions",
                token.key,
                "--remove=10.0.0.0/8",
                stdout=stdout,
            )

            # Verify the restriction was removed
            assert not TokenIPRestriction.objects.filter(token=token).exists()
            assert "Removed IP restriction: 10.0.0.0/8" in stdout.getvalue()

    @pytest.mark.django_db
    def test_remove_last_restriction_cancelled(self, setup_token):
        """Test cancelling removal of the last restriction"""
        token = setup_token

        # Add a restriction
        TokenIPRestriction.objects.create(token=token, ip_range="10.0.0.0/8")

        # Mock user input to cancel removal
        with patch("builtins.input", return_value="n"):
            stdout = io.StringIO()
            call_command(
                "manage_token_restrictions",
                token.key,
                "--remove=10.0.0.0/8",
                stdout=stdout,
            )

            # Verify the restriction still exists
            assert TokenIPRestriction.objects.filter(
                token=token, ip_range="10.0.0.0/8"
            ).exists()
            assert "Operation cancelled" in stdout.getvalue()

    @pytest.mark.django_db
    def test_reset_to_open_policy(self, setup_token):
        """Test resetting to open policy"""
        token = setup_token

        # Add some restrictions
        TokenIPRestriction.objects.create(token=token, ip_range="10.0.0.0/8")
        TokenIPRestriction.objects.create(token=token, ip_range="192.168.1.0/24")

        with patch("builtins.input", return_value="y"):
            stdout = io.StringIO()
            call_command(
                "manage_token_restrictions", token.key, "--reset", stdout=stdout
            )

            # Verify the old restrictions were removed and default ones added
            assert not TokenIPRestriction.objects.filter(
                token=token, ip_range="10.0.0.0/8"
            ).exists()
            assert not TokenIPRestriction.objects.filter(
                token=token, ip_range="192.168.1.0/24"
            ).exists()
            assert TokenIPRestriction.objects.filter(
                token=token, ip_range="0.0.0.0/0"
            ).exists()
            assert TokenIPRestriction.objects.filter(
                token=token, ip_range="::/0"
            ).exists()
            assert "Token reset to default open policy" in stdout.getvalue()

    @pytest.mark.django_db
    def test_reset_cancelled(self, setup_token):
        """Test cancelling a reset operation"""
        token = setup_token

        # Add a restriction
        TokenIPRestriction.objects.create(token=token, ip_range="10.0.0.0/8")

        with patch("builtins.input", return_value="n"):
            stdout = io.StringIO()
            call_command(
                "manage_token_restrictions", token.key, "--reset", stdout=stdout
            )

            # Verify the restriction still exists
            assert TokenIPRestriction.objects.filter(
                token=token, ip_range="10.0.0.0/8"
            ).exists()
            assert "Operation cancelled" in stdout.getvalue()

    @pytest.mark.django_db
    def test_invalid_token(self):
        """Test handling of an invalid token key"""
        with pytest.raises(CommandError) as excinfo:
            call_command("manage_token_restrictions", "nonexistentkey", "--list")

        assert "Token with key 'nonexistentkey' not found" in str(excinfo.value)
