from django.core.management.base import BaseCommand, CommandError

from apps.core.models import SocieteMembership, User
from apps.tenants.models import Societe

ROLES = [r[0] for r in SocieteMembership.ROLE_CHOICES]


class Command(BaseCommand):
    help = (
        "Habilite un utilisateur sur une societe (cree ou met a jour son "
        "SocieteMembership). Sans habilitation, un compte connecte n'a acces a "
        "aucune donnee : c'est la garde R8."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="E-mail du compte a habiliter")
        parser.add_argument(
            "--societe",
            help="Code de la societe (ex. KPS_BJ). Facultatif s'il n'en existe qu'une.",
        )
        parser.add_argument(
            "--role", default="admin", choices=ROLES, help="Role sur cette societe (defaut : admin)"
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Accorde aussi l'acces a l'admin Django (is_staff + is_superuser).",
        )

    def handle(self, *args, **o):
        try:
            user = User.objects.get(email=o["email"])
        except User.DoesNotExist as e:
            connus = list(User.objects.values_list("email", flat=True)[:10])
            raise CommandError(
                f"Aucun compte avec l'e-mail '{o['email']}'.\n"
                f"Comptes existants : {', '.join(connus) or '(aucun)'}"
            ) from e

        # Le schema public n'est pas une societe exploitable.
        societes = Societe.objects.exclude(schema_name="public")
        if o["societe"]:
            societe = societes.filter(code=o["societe"]).first()
            if societe is None:
                dispo = ", ".join(societes.values_list("code", flat=True)) or "(aucune)"
                raise CommandError(
                    f"Societe '{o['societe']}' introuvable. Disponibles : {dispo}"
                )
        else:
            nb = societes.count()
            if nb == 0:
                raise CommandError(
                    "Aucune societe n'existe encore. Creez-en une d'abord :\n"
                    "  manage.py bootstrap_tenant        (KPS Benin + plan SYSCOHADA)\n"
                    "  ou manage.py creer_societe --code ... --schema ... --nom ..."
                )
            if nb > 1:
                dispo = ", ".join(societes.values_list("code", flat=True))
                raise CommandError(
                    f"Plusieurs societes existent, precisez --societe. Disponibles : {dispo}"
                )
            societe = societes.first()

        membership, cree = SocieteMembership.objects.get_or_create(
            user=user, societe=societe, defaults={"role": o["role"], "actif": True}
        )
        if not cree:
            # Re-executer la commande doit corriger un role ou reactiver un acces,
            # pas echouer sur la contrainte d'unicite (user, societe).
            membership.role = o["role"]
            membership.actif = True
            membership.save(update_fields=["role", "actif"])

        action = "creee" if cree else "mise a jour"
        self.stdout.write(
            self.style.SUCCESS(f"Habilitation {action} : {user.email} -> {societe.code} ({o['role']})")
        )

        if o["superuser"] and not (user.is_staff and user.is_superuser):
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            self.stdout.write(self.style.SUCCESS("Acces admin Django accorde (is_staff + is_superuser)."))

        self.stdout.write("Reconnectez-vous (ou rechargez la page) pour voir la societe active.")
