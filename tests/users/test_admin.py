import datetime

from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from pytest_django.asserts import assertContains, assertNotContains, assertRedirects

from inclusion_connect.users.models import EmailAddress
from tests.helpers import parse_response_to_soup
from tests.users.factories import UserFactory


class TestUserAdmin:
    def test_admin_detail(self, client):
        user = UserFactory(is_superuser=True, is_staff=True)
        client.force_login(user)
        response = client.get(reverse("admin:users_user_change", kwargs={"object_id": user.pk}))
        assert response.status_code == 200

    def test_search_by_email_address(self, client, snapshot):
        admin = UserFactory(
            first_name="Admin",
            last_name="Istrator",
            email="administrator@theadmin.com",
            is_staff=True,
            is_superuser=True,
        )
        alice_id = "11111111-1111-1111-1111-111111111111"
        bob_id = "22222222-2222-2222-2222-222222222222"
        charlie_chaplin_id = "33333333-3333-3333-3333-333333333333"
        charlie_dupont_id = "44444444-4444-4444-4444-444444444444"
        alice_not_verified = UserFactory(username=alice_id, first_name="Alice", last_name="Adam", email="")
        EmailAddress.objects.create(user=alice_not_verified, email="a.a@mailinator.com")
        UserFactory(
            username=bob_id,
            first_name="Bob",
            last_name="Bear",
            email="b.b@mailinator.com",
        )
        charlie_chaplin = UserFactory(
            username=charlie_chaplin_id,
            first_name="Charlie",
            last_name="Chaplin",
            email="charlie.chaplin@mailinator.com",
        )
        # Charlie Chaplin is in the process of changing changing their email.
        EmailAddress.objects.create(user=charlie_chaplin, email="c.chaplin@mailinator.com")
        UserFactory(
            username=charlie_dupont_id,
            first_name="Charlie",
            last_name="Dupont",
            email="c.dupont@mailinator.com",
        )

        client.force_login(admin)
        result_id = "#result_list"

        def search(terms):
            response = client.get(reverse("admin:users_user_changelist"), {"q": terms})
            assert response.status_code == 200
            return str(parse_response_to_soup(response, selector=result_id))

        # Email not verified.
        assert search("a.a") == snapshot(name="a.a → only Alice")
        # Email verified.
        assert search("b.b") == snapshot(name="b.b → only Bob")
        assert search("mAiLiNaToR") == snapshot(name="mAiLiNaToR → all users, no duplicates, case insensitive")
        assert search(".chaplin") == snapshot(name=".chaplin → only Charlie Chaplin")
        assert search("c.") == snapshot(name="c. → both Charlie")
        assert search("charlie chaplin") == snapshot(name="charlie chaplin → only Charlie Chaplin")
        # Uses AND as a connector, searching both Alice and Bob yields no results.
        assertNotContains(client.get(reverse("admin:users_user_changelist"), {"q": "alice bob"}), result_id)
        # Using exact search with quotes.
        assertNotContains(client.get(reverse("admin:users_user_changelist"), {"q": "'charlie c'"}), result_id)

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_verify_email(self, client):
        user = UserFactory(email="")
        email_address = EmailAddress.objects.create(email="me@mailinator.com", user=user)
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "1",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "me@mailinator.com",
                "email_addresses-0-verified_at_0": "12/05/2023",
                "email_addresses-0-verified_at_1": "16:42:03",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "me@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.email == "me@mailinator.com"
        assert email_address.user_id == user.pk
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, 42, 3, tzinfo=datetime.timezone.utc)

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_verify_email_ignores_other_emails(self, client):
        user = UserFactory(email="")
        email_address = EmailAddress.objects.create(email="me@mailinator.com", user=user)
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "me@mailinator.com",
                "email_addresses-0-verified_at_0": "12/05/2023",
                "email_addresses-0-verified_at_1": "16:42:03",
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "other@mailinator.com",
                "email_addresses-1-verified_at_0": "",
                "email_addresses-1-verified_at_1": "",
                "email_addresses-__prefix__-user": user.pk,
                "email_addresses-__prefix__-email": "",
                "email_addresses-__prefix__-verified_at_0": "",
                "email_addresses-__prefix__-verified_at_1": "",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "me@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.email == "me@mailinator.com"
        assert email_address.user_id == user.pk
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, 42, 3, tzinfo=datetime.timezone.utc)

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_add_verified_email(self, client):
        user = UserFactory(email="")
        email_address = EmailAddress.objects.create(email="other@mailinator.com", user=user)
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                # Specifying the old email address
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "me@mailinator.com",
                "email_addresses-0-verified_at_0": "",
                "email_addresses-0-verified_at_1": "",
                "email_addresses-0-DELETE": "on",
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "me@mailinator.com",
                "email_addresses-1-verified_at_0": "12/05/2023",
                "email_addresses-1-verified_at_1": "16:42:03",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "me@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.email == "me@mailinator.com"
        assert email_address.user_id == user.pk
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, 42, 3, tzinfo=datetime.timezone.utc)

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_with_existing_verified_email(self, client):
        user = UserFactory(email="me@mailinator.com", email_address=False)
        email_address = EmailAddress.objects.create(email="me@mailinator.com", user=user, verified_at=timezone.now())
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "1",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "me@mailinator.com",
                "email_addresses-0-verified_at_0": "12/05/2023",
                "email_addresses-0-verified_at_1": "16:42:03",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "me@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.email == "me@mailinator.com"
        assert email_address.user_id == user.pk
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, 42, 3, tzinfo=datetime.timezone.utc)

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_change_verified_email(self, client):
        user = UserFactory(email="old@mailinator.com", email_address=False)
        email_address = EmailAddress.objects.create(email="old@mailinator.com", user=user, verified_at=timezone.now())
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "1",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "new@mailinator.com",
                "email_addresses-0-verified_at_0": "25/05/2023",
                "email_addresses-0-verified_at_1": "11:11:11",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "new@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.email == "new@mailinator.com"
        assert email_address.user_id == user.pk
        assert email_address.verified_at == datetime.datetime(2023, 5, 25, 9, 11, 11, tzinfo=datetime.timezone.utc)

    def test_save_reset_verified_at(self, client):
        user = UserFactory(email="me@mailinator.com", email_address=False)
        email_address = EmailAddress.objects.create(email="me@mailinator.com", user=user, verified_at=timezone.now())
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "1",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "me@mailinator.com",
                "email_addresses-0-verified_at_0": "",
                "email_addresses-0-verified_at_1": "",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == ""
        email_address = user.email_addresses.get()
        assert email_address.email == "me@mailinator.com"
        assert email_address.user_id == user.pk
        assert email_address.verified_at is None

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_removes_verified_email(self, client):
        user = UserFactory(email="old@mailinator.com", email_address=False)
        email_address = EmailAddress.objects.create(email="old@mailinator.com", user=user, verified_at=timezone.now())
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "1",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": email_address.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "me@mailinator.com",
                "email_addresses-0-verified_at_0": "12/05/2023",
                "email_addresses-0-verified_at_1": "16:42:03",
                "email_addresses-0-DELETE": "on",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == ""
        assert user.email_addresses.exists() is False

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_while_user_is_changing_email(self, client):
        user = UserFactory(email="old@mailinator.com", email_address=False)
        [old, new] = EmailAddress.objects.bulk_create(
            [
                EmailAddress(email="old@mailinator.com", user=user, verified_at=timezone.now()),
                EmailAddress(email="new@mailinator.com", user=user),
            ]
        )
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "2",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": old.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "old@mailinator.com",
                "email_addresses-0-verified_at_0": "12/05/2023",
                "email_addresses-0-verified_at_1": "16:42:03",
                "email_addresses-1-id": new.pk,
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "new@mailinator.com",
                "email_addresses-1-verified_at_0": "",
                "email_addresses-1-verified_at_1": "",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "old@mailinator.com"
        [new, old] = user.email_addresses.order_by("email")
        assert old.verified_at == datetime.datetime(2023, 5, 12, 14, 42, 3, tzinfo=datetime.timezone.utc)
        assert old.email == "old@mailinator.com"
        assert new.verified_at is None
        assert new.email == "new@mailinator.com"

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_update_verified_at(self, client):
        user = UserFactory(email="old@mailinator.com", email_address=False)
        [old, new] = EmailAddress.objects.bulk_create(
            [
                EmailAddress(email="old@mailinator.com", user=user, verified_at=timezone.now()),
                EmailAddress(email="new@mailinator.com", user=user),
            ]
        )
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "2",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-id": old.pk,
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "old@mailinator.com",
                "email_addresses-0-verified_at_0": "20/02/2002",
                "email_addresses-0-verified_at_1": "12:33:21",
                "email_addresses-1-id": new.pk,
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "new@mailinator.com",
                "email_addresses-1-verified_at_0": "",
                "email_addresses-1-verified_at_1": "",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "old@mailinator.com"
        [new, old] = user.email_addresses.order_by("email")
        assert old.verified_at == datetime.datetime(2002, 2, 20, 11, 33, 21, tzinfo=datetime.timezone.utc)
        assert old.email == "old@mailinator.com"
        assert new.verified_at is None
        assert new.email == "new@mailinator.com"

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_two_verified_emails_error(self, client):
        user = UserFactory(email="me@mailinator.com")
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "newme@mailinator.com",
                "email_addresses-0-verified_at_0": "15/05/2023",
                "email_addresses-0-verified_at_1": "16:42:03",
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "anotherme@mailinator.com",
                "email_addresses-1-verified_at_0": "15/05/2023",
                "email_addresses-1-verified_at_1": "16:45:12",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertContains(response, "L’utilisateur ne peut avoir qu’une seule adresse e-mail vérifiée.")
        user.refresh_from_db()
        assert user.email == "me@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, tzinfo=datetime.timezone.utc)
        assert email_address.email == "me@mailinator.com"

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_two_unverified_emails_error(self, client):
        user = UserFactory(email="me@mailinator.com")
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "newme@mailinator.com",
                "email_addresses-0-verified_at_0": "",
                "email_addresses-0-verified_at_1": "",
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "anotherme@mailinator.com",
                "email_addresses-1-verified_at_0": "",
                "email_addresses-1-verified_at_1": "",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertContains(response, "L’utilisateur ne peut avoir qu’une seule adresse e-mail non vérifiée.")
        user.refresh_from_db()
        assert user.email == "me@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, tzinfo=datetime.timezone.utc)
        assert email_address.email == "me@mailinator.com"

    @freeze_time("2023-05-12T16:00:00+02:00")
    def test_save_ignores_deleted_email(self, client):
        user = UserFactory(email="old@mailinator.com")
        client.force_login(UserFactory(is_superuser=True, is_staff=True))
        url = reverse("admin:users_user_change", kwargs={"object_id": user.pk})
        response = client.post(
            url,
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": "on",
                "last_login_0": "11/05/2023",
                "last_login_1": "11:01:25",
                "date_joined_0": "11/05/2023",
                "date_joined_1": "10:59:39",
                "initial-date_joined_0": "11/05/2023",
                "initial-date_joined_1": "10:59:39",
                "email_addresses-TOTAL_FORMS": "2",
                "email_addresses-INITIAL_FORMS": "1",
                "email_addresses-MIN_NUM_FORMS": "0",
                "email_addresses-MAX_NUM_FORMS": "1000",
                "email_addresses-0-user": user.pk,
                "email_addresses-0-email": "old@mailinator.com",
                "email_addresses-0-verified_at_0": "01/01/2023",
                "email_addresses-0-verified_at_1": "12:34:56",
                "email_addresses-0-DELETE": "on",
                "email_addresses-1-user": user.pk,
                "email_addresses-1-email": "new@mailinator.com",
                "email_addresses-1-verified_at_0": "12/05/2023",
                "email_addresses-1-verified_at_1": "16:45:12",
                "_continue": "Enregistrer+et+continuer+les+modifications",
            },
        )
        assertRedirects(response, url)
        user.refresh_from_db()
        assert user.email == "new@mailinator.com"
        email_address = user.email_addresses.get()
        assert email_address.email == "new@mailinator.com"
        assert email_address.verified_at == datetime.datetime(2023, 5, 12, 14, 45, 12, tzinfo=datetime.timezone.utc)

    def test_admin_password_update(self, client):
        staff_user = UserFactory(is_superuser=True, is_staff=True)
        client.force_login(staff_user)

        user = UserFactory()
        password = "toto"
        response = client.post(
            reverse("admin:auth_user_password_change", args=(user.pk,)),
            data={"password1": password, "password2": password},
        )
        assertRedirects(response, reverse("admin:users_user_change", args=(user.pk,)))

        user.refresh_from_db()
        assert user.must_reset_password
