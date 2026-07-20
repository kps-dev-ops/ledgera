"""Creation des configurations fiscales par defaut d'une societe.

Sans ces configurations, les ecrans TVA / IS / AIB affichent un menu deroulant vide et
aucune declaration ne peut etre creee : le module fiscal est inutilisable a la
livraison d'une nouvelle entite. `bootstrap_tenant` amorcait le plan de comptes, les
journaux et l'exercice, mais pas ces configurations -- c'etait le chainon manquant.

A appeler DANS le contexte du schema tenant. Idempotent.
"""

from decimal import Decimal

from apps.comptabilite.models import CompteComptable, Journal

from .models import ConfigurationAIB, ConfigurationIS, ConfigurationTVA

# Comptes et taux par referentiel. Les deux nomenclatures divergent completement sur la
# fiscalite : ce tableau est le seul endroit ou cette correspondance est ecrite.
REFERENTIELS = {
    "SYSCOHADA": {
        "tva": {
            "libelle": "TVA — régime normal",
            "collectee": ["4431"],
            "deductible": ["4452", "4451"],
            "due": "4441",
            "credit": "4449",
        },
        # Taux d'impot sur les benefices au Benin.
        "is": {"libelle": "Impôt sur les bénéfices", "taux": "30.00", "charge": "891", "dette": "441"},
        "aib": {"libelle": "AIB — 1 %", "taux": "1.00", "aib": "4492", "tresorerie": "521"},
    },
    "PCG": {
        "tva": {
            "libelle": "TVA — régime réel normal",
            "collectee": ["44571"],
            "deductible": ["44566"],
            "due": "44551",
            "credit": "44567",
        },
        # Taux normal de l'impot sur les societes en France.
        "is": {"libelle": "Impôt sur les sociétés", "taux": "25.00", "charge": "695", "dette": "444"},
        # Pas d'AIB : c'est un acompte propre a la fiscalite beninoise.
        "aib": None,
    },
}


class ComptesManquants(Exception):
    """Le plan de la societe ne contient pas les comptes exiges par une configuration."""


def _resoudre(*numeros: str) -> dict[str, CompteComptable]:
    """Resout d'un coup TOUS les comptes exiges par une configuration.

    On verifie l'ensemble avant de creer quoi que ce soit, pour signaler la liste
    complete des comptes manquants : sinon l'administrateur en corrige un, relance,
    en decouvre un autre, et recommence autant de fois qu'il en manque.
    """
    demandes = [n for n in numeros if n]
    trouves = {c.numero: c for c in CompteComptable.objects.filter(numero__in=demandes)}
    absents = sorted(set(demandes) - trouves.keys())
    if absents:
        raise ComptesManquants(", ".join(absents))
    return trouves


def init_configurations_fiscales(societe, journal_code: str = "OD") -> dict[str, str]:
    """Cree les configurations TVA / IS / AIB adaptees au referentiel de la societe.

    Renvoie un rapport {module: message}. Un module dont les comptes sont absents du
    plan est signale, pas fatal : une societe peut utiliser un plan sur mesure, et les
    autres configurations doivent tout de meme etre creees.
    """
    reglages = REFERENTIELS.get(societe.referentiel)
    if reglages is None:
        return {"tout": f"Référentiel « {societe.referentiel} » inconnu — aucune configuration créée."}

    journal = Journal.objects.filter(code=journal_code).first()
    if journal is None:
        return {"tout": f"Journal « {journal_code} » absent — créer les journaux d'abord."}

    rapport: dict[str, str] = {}
    rapport["TVA"] = _init_tva(reglages["tva"], journal)
    rapport["IS"] = _init_is(reglages["is"], journal)
    rapport["AIB"] = _init_aib(reglages["aib"], journal)
    return rapport


def _echec(e: ComptesManquants) -> str:
    return f"comptes absents du plan ({e}) — configuration non créée"


def _init_tva(reglages: dict, journal: Journal) -> str:
    if ConfigurationTVA.objects.filter(actif=True).exists():
        return "déjà configurée"
    try:
        comptes = _resoudre(
            *reglages["collectee"], *reglages["deductible"], reglages["due"], reglages["credit"]
        )
    except ComptesManquants as e:
        return _echec(e)
    config = ConfigurationTVA.objects.create(
        libelle=reglages["libelle"],
        periodicite="MENSUELLE",
        compte_tva_due=comptes[reglages["due"]],
        compte_credit_tva=comptes[reglages["credit"]],
        journal=journal,
    )
    config.comptes_collectee.set([comptes[n] for n in reglages["collectee"]])
    config.comptes_deductible.set([comptes[n] for n in reglages["deductible"]])
    return f"créée ({reglages['libelle']})"


def _init_is(reglages: dict, journal: Journal) -> str:
    if ConfigurationIS.objects.filter(actif=True).exists():
        return "déjà configurée"
    try:
        comptes = _resoudre(reglages["charge"], reglages["dette"])
    except ComptesManquants as e:
        return _echec(e)
    ConfigurationIS.objects.create(
        libelle=reglages["libelle"],
        taux=Decimal(reglages["taux"]),
        compte_charge_impot=comptes[reglages["charge"]],
        compte_dette_impot=comptes[reglages["dette"]],
        journal=journal,
    )
    return f"créée (taux {reglages['taux']} %)"


def _init_aib(reglages: dict | None, journal: Journal) -> str:
    if reglages is None:
        return "sans objet pour ce référentiel"
    if ConfigurationAIB.objects.filter(actif=True).exists():
        return "déjà configurée"
    try:
        comptes = _resoudre(reglages["aib"], reglages["tresorerie"])
    except ComptesManquants as e:
        return _echec(e)
    ConfigurationAIB.objects.create(
        libelle=reglages["libelle"],
        taux=Decimal(reglages["taux"]),
        compte_aib=comptes[reglages["aib"]],
        compte_tresorerie=comptes[reglages["tresorerie"]],
        journal=journal,
    )
    return f"créée (taux {reglages['taux']} %)"
