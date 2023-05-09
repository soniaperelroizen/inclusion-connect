import uuid

import jwt
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_id_token_model, get_refresh_token_model

from inclusion_connect.utils.urls import add_url_params, get_url_params
from tests.oidc_overrides.factories import DEFAULT_CLIENT_SECRET, ApplicationFactory, default_client_secret
from tests.users.factories import DEFAULT_PASSWORD


OIDC_PARAMS = {
    "response_type": "code",
    "client_id": "my_application",
    "redirect_uri": "http://localhost/callback",
    "scope": "openid profile email",
    "state": "state",
    "nonce": "nonce",
}


def oidc_flow_followup(client, auth_response_params, user):
    # Call TOKEN endpoint
    # FIXME it's recommanded to use basic auth here, maybe update our documentation ?
    token_data = {
        "client_id": OIDC_PARAMS["client_id"],
        "client_secret": DEFAULT_CLIENT_SECRET,
        "code": auth_response_params["code"],
        "grant_type": "authorization_code",
        "redirect_uri": OIDC_PARAMS["redirect_uri"],
    }
    response = client.post(reverse("oauth2_provider:token"), data=token_data)

    token_json = response.json()
    id_token = token_json["id_token"]
    decoded_id_token = jwt.decode(
        id_token,
        key=default_client_secret(),
        algorithms=["HS256"],
        audience=OIDC_PARAMS["client_id"],
    )
    assert decoded_id_token["nonce"] == OIDC_PARAMS["nonce"]
    assert decoded_id_token["sub"] == str(user.pk)
    assert uuid.UUID(decoded_id_token["sub"]), "Sub should be an uuid"
    assert decoded_id_token["given_name"] == user.first_name
    assert decoded_id_token["family_name"] == user.last_name
    assert decoded_id_token["email"] == user.email

    # Call USER INFO endpoint
    response = client.get(
        reverse("oauth2_provider:user-info"),
        HTTP_AUTHORIZATION=f"Bearer {token_json['access_token']}",
    )
    assert response.json() == {
        "sub": str(user.pk),
        "given_name": user.first_name,
        "family_name": user.last_name,
        "email": user.email,
    }

    return token_json["id_token"]


def oidc_complete_flow(client, user):
    ApplicationFactory(client_id=OIDC_PARAMS["client_id"])
    auth_url = reverse("oidc_overrides:authorize")
    auth_complete_url = add_url_params(auth_url, OIDC_PARAMS)
    response = client.get(auth_complete_url)
    response = client.post(
        response.url,
        data={
            "email": user.email,
            "password": DEFAULT_PASSWORD,
        },
    )
    response = client.get(response.url)
    auth_response_params = get_url_params(response.url)
    return oidc_flow_followup(client, auth_response_params, user)


def has_ongoing_sessions(user):
    ongoing_sessions = [
        s
        for s in Session.objects.filter(expire_date__gte=timezone.now())
        if s.get_decoded().get("_auth_user_id") == str(user.pk)
    ]
    return bool(ongoing_sessions)


def token_are_revoked(user):
    return (
        not get_id_token_model().objects.filter(user=user).exists()
        and not get_access_token_model().objects.filter(user=user).exists()
        and get_refresh_token_model().objects.get().revoked is not None
    )